#!/usr/bin/env python3
"""Manage global beta invite code for username/password tester onboarding."""

import argparse
import asyncio
import hashlib
import secrets
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import db  # noqa: E402

INVITE_HASH_PREFIX = "sha256$"


def hash_invite_code(invite_code: str) -> str:
    normalized = invite_code.strip()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"{INVITE_HASH_PREFIX}{digest}"


async def ensure_db() -> None:
    await db.init_db()


async def set_code(plain_code: str) -> None:
    await ensure_db()
    await db.set_beta_invite_code_hash(hash_invite_code(plain_code))
    print("Invite code updated.")


async def rotate_code() -> None:
    await ensure_db()
    plain_code = secrets.token_urlsafe(24)
    await db.set_beta_invite_code_hash(hash_invite_code(plain_code))
    print("New invite code generated (store this now; it will not be shown again):")
    print(plain_code)


async def show_status() -> None:
    await ensure_db()
    status = await db.get_beta_invite_status()
    configured = "yes" if status["configured"] else "no"
    print(f"Configured: {configured}")
    print(f"Updated at: {status['updated_at'] or 'never'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage global beta invite code")
    subparsers = parser.add_subparsers(dest="command", required=True)

    set_parser = subparsers.add_parser("set", help="Set the invite code")
    set_parser.add_argument("--code", required=True, help="Plaintext invite code")

    subparsers.add_parser("rotate", help="Generate and set a new random invite code")
    subparsers.add_parser("status", help="Show invite code status")

    args = parser.parse_args()

    if args.command == "set":
        asyncio.run(set_code(args.code))
    elif args.command == "rotate":
        asyncio.run(rotate_code())
    elif args.command == "status":
        asyncio.run(show_status())
    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
