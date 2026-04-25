#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

from circlekit import GatewayClientSync


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deposit USDC into Circle Gateway.")
    parser.add_argument("--amount", required=True, help="USDC amount, e.g. 0.01")
    parser.add_argument("--chain", default="arcTestnet", help="Gateway chain name.")
    parser.add_argument("--env-file", default=".env", help="Path to .env file.")
    parser.add_argument(
        "--rpc-url",
        default=None,
        help="Custom RPC URL (overrides ARC_RPC_URL from .env if provided).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(Path(args.env_file).expanduser().resolve())

    private_key = os.getenv("BUYER_PRIVATE_KEY", "").strip()
    if not private_key:
        raise SystemExit("Missing BUYER_PRIVATE_KEY in environment/.env")
    rpc_url = (args.rpc_url or os.getenv("ARC_RPC_URL", "")).strip() or None

    try:
        with GatewayClientSync(
            chain=args.chain,
            private_key=private_key,
            rpc_url=rpc_url,
        ) as client:
            before = client.get_gateway_balance()
            print(f"Gateway balance before: {before.formatted_total} USDC")

            result = client.deposit(args.amount)
            if getattr(result, "approval_tx_hash", None):
                print(f"Approval tx: {result.approval_tx_hash}")
            print(f"Deposit tx: {result.deposit_tx_hash}")
            print(f"Deposited: {result.formatted_amount} USDC")

            after = client.get_gateway_balance()
            print(f"Gateway balance after:  {after.formatted_total} USDC")
    except Exception as exc:
        if type(exc).__name__ != "HTTPError":
            raise
        endpoint = rpc_url or f"default RPC for chain={args.chain}"
        raise SystemExit(
            "RPC request failed while talking to "
            f"{endpoint}. "
            "Try a different RPC endpoint with --rpc-url, e.g. "
            "`--rpc-url https://<another-arc-testnet-rpc>`."
        ) from exc

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
