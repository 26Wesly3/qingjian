# -*- coding: utf-8 -*-
"""探查藏汉词典源数据：切分释义、统计可反查的中文词条。"""
import re
import sys
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources" / "藏汉词典.txt"
if not SRC.is_file():
    SRC = ROOT / "research-tip" / "T10_藏汉电子词典设计" / "藏汉词典.txt"

# 中文字符范围（含扩展 A 少量常用字）
CJK = re.compile(r"^[\u3400-\u4dbf\u4e00-\u9fff]+$")
# 释义里常见的前缀标记，如 [古]、[敬]、[方]
MARK = re.compile(r"^\[[^\]]{1,4}\]")


def clean_gloss(text: str):
    """把一条释义拆成若干简洁的中文词条。"""
    text = text.strip()
    # 去掉 [古]、[敬] 这类方言/语体标记
    text = MARK.sub("", text)
    # 编号 1． 2． 3、 等
    text = re.sub(r"(^|[\s；;。，,、])\d+\s*[．.、]\s*", r"\1", text)
    parts = re.split(r"[；;。，,、/／\|（）()\[\]【】\s]+", text)
    out = []
    for part in parts:
        part = part.strip(" 　:：!！?？~～-—…")
        if not part:
            continue
        if not CJK.match(part):
            continue
        if len(part) > 8:
            continue
        # 跳过「同XXX」「见XXX」这类互参
        if part.startswith(("同", "见", "参见", "即", "又称", "亦称", "别称")):
            continue
        out.append(part)
    return out


def load():
    raw = open(SRC, encoding="utf-16").read()
    entries = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        if "\t" not in line:
            continue
        tib, gloss = line.split("\t", 1)
        tib = tib.strip()
        if not tib:
            continue
        entries.append((tib, gloss, clean_gloss(gloss)))
    return entries


def main():
    entries = load()
    print("总条目", len(entries))
    pairs = defaultdict(list)  # 中文 -> [(藏文, 位置)]
    for tib, gloss, gl in entries:
        for i, g in enumerate(gl):
            pairs[g].append((tib, i))
    print("中文词条", len(pairs))
    print("一词多藏文（前 10）：")
    for g, v in sorted(pairs.items(), key=lambda kv: -len(kv[1]))[:10]:
        print(" ", g, len(v), v[:3])
    print("释义平均中文词条", sum(len(v) for v in pairs.values()) / len(pairs))

    targets = sys.argv[1:]
    if targets:
        for t in targets:
            print(f"\n=== 查 {t}")
            for g, v in pairs.items():
                if t in g:
                    for tib, pos in v[:3]:
                        print(f"  {g}\t{tib}")
                    if len(v) > 3:
                        print(f"  ... 共 {len(v)} 个藏文")


if __name__ == "__main__":
    main()
