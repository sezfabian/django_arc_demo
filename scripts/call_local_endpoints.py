#!/usr/bin/env python3
"""
Call local API endpoints repeatedly and log all responses.

Default run plan:
- /api/free/      -> 5 calls
- /api/cheap/     -> 50 calls
- /api/expensive/ -> 10 calls
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from circlekit import GatewayClientSync


DEFAULT_COUNTS: Dict[str, int] = {
    "free": 5,
    "cheap": 50,
    "expensive": 10,
}


def load_dotenv(dotenv_path: Path) -> None:
    """Minimal .env loader without external dependencies."""
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_json(value: object) -> str:
    try:
        return json.dumps(value, ensure_ascii=True)
    except Exception:
        return str(value)


def markdown_escape(value: object) -> str:
    """Escape Markdown table-special characters in a cell."""
    text = safe_json(value)
    return text.replace("|", "\\|").replace("\n", "<br>")


def build_error_details(exc: Exception) -> dict:
    """Best-effort structured error extraction for payment failures."""
    details: Dict[str, object] = {
        "type": type(exc).__name__,
        "message": str(exc),
    }

    response = getattr(exc, "response", None)
    if response is not None:
        status_code = getattr(response, "status_code", None)
        if status_code is not None:
            details["status_code"] = status_code

        response_body: object
        try:
            response_body = response.json()
        except Exception:
            response_body = getattr(response, "text", None) or str(response)
        details["response_body"] = sanitize_error_body(response_body)

    request = getattr(exc, "request", None)
    if request is not None:
        method = getattr(request, "method", None)
        url = getattr(request, "url", None)
        if method:
            details["request_method"] = method
        if url:
            details["request_url"] = str(url)

    return details


def sanitize_error_body(value: object) -> object:
    """Shorten noisy HTML error payloads into actionable diagnostics."""
    if isinstance(value, dict):
        out: Dict[str, object] = {}
        for key, item in value.items():
            if isinstance(item, str):
                out[key] = summarize_html_error(item)
            else:
                out[key] = item
        return out
    if isinstance(value, str):
        return summarize_html_error(value)
    return value


def summarize_html_error(text: str) -> str:
    lowered = text.lower()
    if "<html" not in lowered:
        return text

    if "error 1015" in lowered or "you are being rate limited" in lowered:
        ray_match = re.search(r"ray id:\s*([a-zA-Z0-9]+)", text, flags=re.IGNORECASE)
        ray_suffix = f" ray_id={ray_match.group(1)}" if ray_match else ""
        return f"Cloudflare rate limited (Error 1015){ray_suffix}"

    return "HTML error response received (omitted)"


def call_endpoint_many(
    client: GatewayClientSync,
    base_url: str,
    endpoint_name: str,
    call_count: int,
    log_file: Path,
    start_log_no: int,
    delay_seconds: float,
) -> Tuple[int, int, int]:
    """Call one endpoint repeatedly, writing a Markdown table per endpoint."""
    success = 0
    failure = 0
    log_no = start_log_no
    url = f"{base_url}/api/{endpoint_name}/"
    rows: List[str] = []

    for i in range(1, call_count + 1):
        start_ts = utc_now()
        try:
            result = client.pay(url, method="GET")
            console_line = (
                f"[#{log_no}] endpoint={endpoint_name} attempt={i}/{call_count} "
                f"status={result.status} paid_amount={result.formatted_amount} "
                f"tx={result.transaction or 'N/A'} body={safe_json(result.data)}"
            )
            print(console_line)
            rows.append(
                "| {log_no} | {attempt} | {timestamp} | {status} | {paid_amount} | {tx} | {body} |".format(
                    log_no=log_no,
                    attempt=f"{i}/{call_count}",
                    timestamp=markdown_escape(start_ts),
                    status=result.status,
                    paid_amount=markdown_escape(result.formatted_amount),
                    tx=markdown_escape(result.transaction or "N/A"),
                    body=markdown_escape(result.data),
                )
            )
            success += 1
        except Exception as exc:
            error_details = build_error_details(exc)
            console_line = (
                f"[#{log_no}] endpoint={endpoint_name} attempt={i}/{call_count} "
                f"status=ERROR error={safe_json(error_details)}"
            )
            print(console_line)
            rows.append(
                "| {log_no} | {attempt} | {timestamp} | ERROR | - | - | {error} |".format(
                    log_no=log_no,
                    attempt=f"{i}/{call_count}",
                    timestamp=markdown_escape(start_ts),
                    error=markdown_escape(error_details),
                )
            )
            failure += 1
        log_no += 1
        if delay_seconds > 0:
            time.sleep(delay_seconds)

    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(f"### Endpoint `/api/{endpoint_name}/`\n\n")
        fh.write(
            "| Log # | Attempt | Timestamp (UTC) | Status | Paid Amount (USDC) | Transaction | Response / Error |\n"
        )
        fh.write("|---:|---|---|---|---|---|---|\n")
        for row in rows:
            fh.write(f"{row}\n")
        fh.write("\n")
        fh.write(f"- Total calls: `{call_count}`\n")
        fh.write(f"- Success: `{success}`\n")
        fh.write(f"- Failure: `{failure}`\n\n")
        fh.flush()

    return success, failure, log_no


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Call local endpoints and log responses.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL.")
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to .env file containing ARC_PAY_BUYER_ADDRESS and BUYER_PRIVATE_KEY.",
    )
    parser.add_argument(
        "--log-file",
        default="endpoint_call_log.md",
        help="Where to append Markdown request/response logs.",
    )
    parser.add_argument("--chain", default="arcTestnet", help="Gateway chain name.")
    parser.add_argument("--free", type=int, default=DEFAULT_COUNTS["free"], help="Free calls.")
    parser.add_argument("--cheap", type=int, default=DEFAULT_COUNTS["cheap"], help="Cheap calls.")
    parser.add_argument(
        "--expensive",
        type=int,
        default=DEFAULT_COUNTS["expensive"],
        help="Expensive calls.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0.75,
        help="Sleep between each request to reduce upstream rate limiting.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    env_path = Path(args.env_file).expanduser().resolve()
    log_path = Path(args.log_file).expanduser().resolve()
    load_dotenv(env_path)

    buyer_address = os.getenv("ARC_PAY_BUYER_ADDRESS", "").strip()
    buyer_private_key = os.getenv("BUYER_PRIVATE_KEY", "").strip()
    if not buyer_private_key:
        raise SystemExit("Missing BUYER_PRIVATE_KEY in environment/.env.")
    if not buyer_address:
        raise SystemExit("Missing ARC_PAY_BUYER_ADDRESS in environment/.env.")

    run_start = utc_now()
    run_header = (
        f"\n## Run `{run_start}`\n\n"
        f"- Base URL: `{args.base_url}`\n"
        f"- Chain: `{args.chain}`\n"
        f"- Buyer: `{buyer_address}`\n\n"
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(run_header)
        fh.flush()

    totals = {"success": 0, "failure": 0}
    next_log_no = 1
    plan = [("free", args.free), ("cheap", args.cheap), ("expensive", args.expensive)]

    with GatewayClientSync(chain=args.chain, private_key=buyer_private_key) as client:
        for endpoint, count in plan:
            success, failure, next_log_no = call_endpoint_many(
                client=client,
                base_url=args.base_url.rstrip("/"),
                endpoint_name=endpoint,
                call_count=count,
                log_file=log_path,
                start_log_no=next_log_no,
                delay_seconds=max(0.0, args.delay_seconds),
            )
            totals["success"] += success
            totals["failure"] += failure

    run_end = utc_now()
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write("### Run Summary\n\n")
        fh.write("| Started (UTC) | Finished (UTC) | Success | Failure |\n")
        fh.write("|---|---|---:|---:|\n")
        fh.write(
            f"| `{run_start}` | `{run_end}` | {totals['success']} | {totals['failure']} |\n\n"
        )

    print(
        f"Run finished {run_end} | success={totals['success']} failure={totals['failure']}"
    )
    print(f"Log file: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
