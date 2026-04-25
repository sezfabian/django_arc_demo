#!/usr/bin/env python3
"""
Generate a random EOA for BUYER_PRIVATE_KEY (Arc / Gateway testing only).

Uses eth_account (already installed with circle-titanoboa-sdk). Does not write
to disk unless you pass --append-dotenv.

Examples::

    python scripts/gen_buyer_wallet.py
    python scripts/gen_buyer_wallet.py --append-dotenv

Never reuse test keys on mainnet. Fund Arc testnet + deposit USDC into Gateway
before running micro_pay_sim.py (see circle-titanoboa-sdk README / deposit).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

from eth_account import Account


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--append-dotenv",
        action="store_true",
        help=f"Append BUYER_PRIVATE_KEY to {ROOT / '.env'} (create file if missing)",
    )
    args = parser.parse_args()

    acct = Account.create()
    pk_hex = acct.key.hex()
    if not pk_hex.startswith("0x"):
        pk_hex = "0x" + pk_hex

    print("New test buyer wallet (keep private; testnet use only):")
    print(f"  Address:          {acct.address}")
    print(f"  BUYER_PRIVATE_KEY={pk_hex}")
    print()
    print("Add the line above to .env, then:")
    print("  1. Get Arc testnet USDC from https://faucet.circle.com (Arc Testnet)")
    print("  2. Deposit USDC into Circle Gateway for this address (circlekit deposit)")
    print("  3. Ensure ARC_PAY_SELLER_ADDRESS is a different address than this buyer")

    if args.append_dotenv:
        env_path = ROOT / ".env"
        line = f"\nBUYER_PRIVATE_KEY={pk_hex}\n"
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(line)
        print()
        print(f"Appended BUYER_PRIVATE_KEY to {env_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
