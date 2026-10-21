# -*- coding: utf-8 -*-
"""藏文 → 威利（Wylie）转写。

- 有音节表（``data/syllables.tsv``）时按音节整字查表，正字法分字准确；
- 表里没有的音节（梵文咒语、罕见连写）按字符表逐件拼写，尽量给出可读的转写。

音节之间用空格分隔，藏文标点 ``།`` 写作 ``|``。
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# 字母与元音符号（不含 tsheg / shad / 数字等标点）
def _is_letter(ch: str) -> bool:
    return (
        "\u0f40" <= ch <= "\u0f6c"
        or "\u0f71" <= ch <= "\u0f84"
        or "\u0f90" <= ch <= "\u0fbc"
    )


VOWELS = {"\u0f72", "\u0f74", "\u0f7a", "\u0f7c", "\u0f71", "\u0f7b", "\u0f7d", "\u0f80"}
SUFFIXES = set("གངདནབམའརལས")


def _load(path: Path) -> dict[str, str]:
    table: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("\t")
        table[key] = value
    return table


CHARS = _load(DATA / "wylie-chars.tsv") if (DATA / "wylie-chars.tsv").is_file() else {}
SYLLABLES = _load(DATA / "syllables.tsv") if (DATA / "syllables.tsv").is_file() else {}

PUNCT = {
    "་": " ",
    "༌": " ",
    "།": "|",
    "༎": "||",
    "༏": "|",
    "༐": "|",
    "༑": "|",
    "༔": "|",
    "༄": "@",
    "༅": "@",
    "ༀ": "oM",
    "༡": "1",
    "༢": "2",
    "༣": "3",
    "༤": "4",
    "༥": "5",
    "༦": "6",
    "༧": "7",
    "༨": "8",
    "༩": "9",
    "༠": "0",
}


def _fallback(syllable: str) -> str:
    """音节表里没有时逐件拼：梵文咒语、罕见连写用，尽量给出可读的转写。"""
    chars = list(syllable)
    merged: list[str] = []
    i = 0
    while i < len(chars):
        if chars[i] == "ཱ" and i + 1 < len(chars) and chars[i + 1] in ("ི", "ུ"):
            merged.append("I" if chars[i + 1] == "ི" else "U")
            i += 2
            continue
        merged.append(chars[i])
        i += 1

    marks = ("ཾ", "ྂ", "ྃ", "ཿ")
    consonants = [c for c in merged if c in CHARS and c not in VOWELS and c not in marks]
    vowels = [CHARS.get(c, c) for c in merged if c in VOWELS or c in ("I", "U")]
    mark_text = "".join(CHARS.get(c, c) for c in merged if c in marks)
    # ཨ 作基字时元音符号直接读元音（ཨོཾ → oM）
    base_is_a = bool(merged) and merged[0] == "ཨ" and bool(vowels)
    body = "".join(CHARS[c] for c in consonants)
    if base_is_a:
        body = body[1:] if body.startswith("a") else body
    if vowels:
        return body + "".join(vowels) + mark_text
    if mark_text:
        return body + "a" + mark_text
    # 没有元音符号也没有标记：按后缀集合粗略判断隐含 a 的位置
    n = len(consonants)
    suffix_len = 0
    for c in reversed(consonants):
        if c in SUFFIXES and n - suffix_len > 1:
            suffix_len += 1
            if suffix_len == 2:
                break
        else:
            break
    head = "".join(CHARS[c] for c in consonants[: n - suffix_len])
    tail = "".join(CHARS[c] for c in consonants[n - suffix_len :])
    return head + "a" + tail


def to_wylie(text: str) -> str:
    """把一段藏文转成威利。"""
    out: list[str] = []
    run: list[str] = []

    def flush() -> None:
        if not run:
            return
        syllable = "".join(run)
        out.append(SYLLABLES.get(syllable) or _fallback(syllable))
        run.clear()

    for ch in text:
        if _is_letter(ch):
            run.append(ch)
        else:
            flush()
            out.append(PUNCT.get(ch, ch))
    flush()
    return " ".join("".join(out).split())


def has_tibetan(text: str) -> bool:
    return any(_is_letter(ch) for ch in text)


def unknown_syllables(text: str) -> list[str]:
    """列出音节表里查不到的音节（做数据质量检查用）。"""
    missing: list[str] = []
    run: list[str] = []

    def flush() -> None:
        if run:
            syllable = "".join(run)
            if syllable not in SYLLABLES:
                missing.append(syllable)
            run.clear()

    for ch in text:
        if _is_letter(ch):
            run.append(ch)
        else:
            flush()
    flush()
    return missing


if __name__ == "__main__":
    import sys

    sample = sys.argv[1] if len(sys.argv) > 1 else "བོད་ཡིག"
    print(to_wylie(sample))
