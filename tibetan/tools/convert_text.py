# -*- coding: utf-8 -*-
"""把一段中文转成藏文（逐词替换）并附威利转写。

用法：
  python tools/convert_text.py "藏文是藏族人民使用的文字"
  python tools/convert_text.py --format both "中国 西藏 拉萨"
  echo "..." | python tools/convert_text.py --stdin

只做词级替换：词表来自 pack/wylie-reference.tsv（人工常用词 + 《藏汉词典》反查），
按最长匹配切分；词表里没有的字保持原样。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "pack"


def load_table() -> dict[str, tuple[str, str]]:
    table: dict[str, tuple[str, str]] = {}
    path = PACK / "wylie-reference.tsv"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        zh, reading, tib, wylie = parts[0], parts[1], parts[2], parts[3]
        # 人工层优先（同一个中文词可能同时出现在两层）
        if zh not in table or parts[4] == "curated":
            table[zh] = (tib, wylie)
    return table


def convert(text: str, table: dict[str, tuple[str, str]], max_word: int) -> tuple[str, str]:
    tokens: list[tuple[str, str, str]] = []
    i = 0
    while i < len(text):
        matched = None
        for size in range(min(max_word, len(text) - i), 0, -1):
            word = text[i : i + size]
            if word in table:
                matched = (size, table[word])
                break
        if matched:
            size, (tib, wylie) = matched
            tokens.append(("tib", tib, wylie))
            i += size
        else:
            ch = text[i]
            tokens.append(("raw", ch, ch))
            i += 1
    tibetan = ""
    wylie_parts: list[str] = []
    pending_tsheg = False
    for kind, part, wylie in tokens:
        if kind == "tib":
            if tibetan and pending_tsheg and not tibetan.endswith(("་", " ")):
                tibetan += "་"
            tibetan += part
            wylie_parts.append(wylie)
            pending_tsheg = True
        elif part.isspace():
            tibetan += " "
            wylie_parts.append("")
            pending_tsheg = False
        else:
            tibetan += part
            wylie_parts.append(wylie)
            pending_tsheg = False
    return tibetan.strip(), " ".join(p for p in wylie_parts if p)


def main() -> None:
    parser = argparse.ArgumentParser(description="中文 → 藏文 + 威利")
    parser.add_argument("text", nargs="*", help="要转换的中文；--stdin 时从标准输入读")
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--format", choices=["tibetan", "wylie", "both", "pairs"], default="both")
    parser.add_argument("--table", help="自定义对照表（中文<TAB>藏文），会覆盖内置词表")
    args = parser.parse_args()

    table = load_table()
    if args.table:
        for line in Path(args.table).read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            zh, tib = line.split("\t")[:2]
            from wylie import to_wylie  # 延迟导入，避免找不到 tools 目录时影响 --help

            table[zh] = (tib, to_wylie(tib))

    text = sys.stdin.read() if args.stdin else " ".join(args.text)
    tibetan, wylie = convert(text, table, max(len(word) for word in table))
    if args.format == "tibetan":
        print(tibetan)
    elif args.format == "wylie":
        print(wylie)
    elif args.format == "pairs":
        for ch in text:
            if ch in table:
                print(f"{ch}\t{table[ch][0]}\t{table[ch][1]}")
    else:
        print(tibetan)
        print(wylie)


if __name__ == "__main__":
    main()
