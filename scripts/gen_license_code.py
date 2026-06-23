#!/usr/bin/env python3
"""根据授权 key 生成激活码（与 app/services/license.py 算法一致）。"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.license import activation_hash, format_key_label


def parse_key(raw: str) -> date:
    text = raw.strip()
    for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError("无法解析 key，请使用 YYYY/MM/DD 格式，例如 2026/06/20")


def generate_code(key: str) -> tuple[str, str]:
    expires_on = parse_key(key)
    key_label = format_key_label(expires_on)
    return key_label, activation_hash(expires_on)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="输入授权 key（到期日期），输出对应激活码。",
    )
    parser.add_argument(
        "key",
        nargs="?",
        help="授权 key，格式 YYYY/MM/DD 或 YYYY-MM-DD，例如 2026/06/20",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    key_input = args.key
    if not key_input:
        try:
            key_input = input("请输入 key (YYYY/MM/DD): ").strip()
        except EOFError:
            print("未输入 key。", file=sys.stderr)
            return 1

    if not key_input:
        print("key 不能为空。", file=sys.stderr)
        return 1

    try:
        key_label, code = generate_code(key_input)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"key:    {key_label}")
    print(f"激活码: {code}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
