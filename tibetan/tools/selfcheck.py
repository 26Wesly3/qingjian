# -*- coding: utf-8 -*-
"""安装前自检：词库 / 释义表 / 选择记录 / 中文注释表是否对得上，威利是否残留藏文字符。

用法：python tools/selfcheck.py（退出码 0 才建议安装）
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from wylie import has_tibetan  # noqa: E402

PACK = ROOT / "pack"


def rows(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        out.append(line.split("\t"))
    return out


def main() -> int:
    problems: list[str] = []

    dictionary = rows(PACK / "tibetan.tsv")
    glossary = rows(PACK / "glossary.tsv")
    choices = rows(PACK / "choices.tsv")
    reference = rows(PACK / "wylie-reference.tsv")
    annotations = rows(PACK / "annotations-tibetan.tsv")
    combined = rows(PACK / "annotations-combined.tsv")

    if not dictionary:
        problems.append("pack/tibetan.tsv 为空，先运行 build_pack.py")

    words = {row[0] for row in dictionary if row}
    gloss_words = {row[0] for row in glossary if row}
    missing_gloss = words - gloss_words
    extra_gloss = gloss_words - words
    if missing_gloss:
        problems.append(f"{len(missing_gloss)} 个词没有威利注释，例如 {sorted(missing_gloss)[:3]}")
    if extra_gloss:
        problems.append(f"{len(extra_gloss)} 条注释找不到对应词，例如 {sorted(extra_gloss)[:3]}")

    # 选择记录：输入串应该等于词库读音去掉空格
    by_word: dict[str, set[str]] = {}
    for row in dictionary:
        if len(row) >= 2:
            by_word.setdefault(row[0], set()).add(row[1].replace(" ", ""))
    bad_choices = [row for row in choices if len(row) >= 2 and row[1] not in by_word]
    if bad_choices:
        problems.append(f"{len(bad_choices)} 条选择记录对应不到词库词，例如 {bad_choices[:2]}")

    # 中文注释表：每条都得有藏文 + 威利，且藏文词出现在藏文释义表里
    if not annotations:
        problems.append("pack/annotations-tibetan.tsv 为空")
    bad_annotation = []
    for row in annotations:
        if len(row) < 2 or not row[1].strip():
            bad_annotation.append(row)
            continue
        tib = row[1].split("  ", 1)[0].strip()
        if tib not in gloss_words:
            bad_annotation.append(row)
    if bad_annotation:
        problems.append(f"{len(bad_annotation)} 条中文注释缺藏文/威利或藏文词不在释义表，例如 {bad_annotation[:2]}")
    if not combined:
        problems.append("pack/annotations-combined.tsv 为空")

    # 威利字段不能残留藏文
    for row in reference:
        if len(row) >= 4 and has_tibetan(row[3]):
            problems.append(f"威利里还有藏文：{row[0]} {row[2]} -> {row[3]}")
            break
    for row in annotations:
        if len(row) >= 2 and has_tibetan(row[1].split("  ", 1)[-1]):
            problems.append(f"中文注释的威利里还有藏文：{row[0]} -> {row[1]}")
            break

    print(
        f"词库 {len(dictionary)} 条 / 藏文词 {len(words)} / 藏文释义 {len(glossary)} / "
        f"选择 {len(choices)} / 中文注释 {len(annotations)} / 对照 {len(reference)}"
    )
    if problems:
        print("自检失败：")
        for problem in problems:
            print(" -", problem)
        return 1
    print("自检通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
