# -*- coding: utf-8 -*-
"""生成青简藏文词库、威利释义与预置选择记录。

数据来源：
  1. 《藏汉词典》（research-tip/T10_藏汉电子词典设计/藏汉词典.txt，UTF-16）
     —— 逐条取出「藏文词 + 中文释义」，把释义切成简短中文词条，反查成 中文 → 藏文。
  2. data/curated.tsv —— 常用词人工核对层，优先。
  3. data/extra.tsv   —— 用户自己加的「中文<TAB>藏文」词条（可选，存在就合并）。

产物（pack/）：
  tibetan.tsv          青简用户词库：藏文词<TAB>拼音<TAB>词频
  glossary.tsv         个人释义表：藏文词<TAB>威利转写
  choices.tsv          预置选择：输入串<TAB>藏文词<TAB>次数
  wylie-reference.tsv  对照表：中文<TAB>拼音<TAB>藏文<TAB>威利<TAB>层
  report.txt           统计与自检
"""
from __future__ import annotations

import itertools
import re
from collections import defaultdict
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "vendor"))

from pypinyin import Style, pinyin  # noqa: E402

from explore_dict import load  # noqa: E402
from wylie import to_wylie, unknown_syllables  # noqa: E402

CURATED = ROOT / "data" / "curated.tsv"
EXTRA = ROOT / "data" / "extra.tsv"
PHRASES = ROOT / "data" / "phrases.tsv"
PACK = ROOT / "pack"
JP_GLOSSARY = ROOT.parent / "assets" / "glossary" / "glossary-ja.tsv"
if not JP_GLOSSARY.is_file():
    JP_GLOSSARY = ROOT / "qingjian-src" / "assets" / "glossary" / "glossary-ja.tsv"

CURATED_FREQ = 4_000_000_000
BROAD_FREQ = 200_000_000
MAX_PINYIN_VARIANTS = 4
MAX_TIBETAN_PER_GLOSS = 1
GLOSS_MIN, GLOSS_MAX = 2, 6
CJK = re.compile(r"^[\u4e00-\u9fff]+$")


def pinyin_variants(text: str) -> list[str]:
    """一个中文词的多种读法，去重后最多 MAX_PINYIN_VARIANTS 个。"""
    if not CJK.match(text):
        return []
    chars = pinyin(text, style=Style.NORMAL, heteronym=True, errors="ignore")
    if not chars or any(not c for c in chars):
        return []
    variants: list[str] = []
    for combo in itertools.islice(itertools.product(*chars), 64):
        reading = " ".join(combo).replace("ü", "v")
        if reading not in variants:
            variants.append(reading)
        if len(variants) >= MAX_PINYIN_VARIANTS:
            break
    return variants


def load_curated() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if not CURATED.is_file():
        return out
    for raw in CURATED.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        parts = raw.split("\t")
        if len(parts) < 2:
            continue
        zh, tib = parts[0].strip(), parts[1].strip()
        if zh and tib:
            out.append((zh, tib))
    return out


def load_phrases() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if not PHRASES.is_file():
        return out
    for raw in PHRASES.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        parts = raw.split("\t")
        if len(parts) < 2:
            continue
        zh, tib = parts[0].strip(), parts[1].strip()
        if zh and tib:
            out.append((zh, tib))
    return out


def load_extra() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if not EXTRA.is_file():
        return out
    for raw in EXTRA.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        parts = raw.split("\t")
        if len(parts) < 2:
            continue
        zh, tib = parts[0].strip(), parts[1].strip()
        if zh and tib:
            out.append((zh, tib))
    return out


def load_japanese() -> dict[str, str]:
    """青简随包日语释义表 → 中文词的第一条译词（去掉词性、假名、换行）。"""
    out: dict[str, str] = {}
    if not JP_GLOSSARY.is_file():
        return out
    for raw in JP_GLOSSARY.read_text(encoding="utf-8-sig").splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        parts = raw.split("\t")
        if len(parts) < 2:
            continue
        zh = parts[0].strip()
        sense = parts[1].strip()
        sense = re.sub(r"^[A-Za-z]+\.\s*", "", sense)  # n. / v. / int. …
        sense = sense.split("|")[0].strip()
        sense = " ".join(sense.split())
        if not zh or not sense:
            continue
        if len(sense) > 20:
            sense = sense[:20] + "…"
        out.setdefault(zh, sense)
    return out


def broad_pairs() -> tuple[list[tuple[str, str]], int]:
    """从《藏汉词典》反查：中文释义 → 藏文词。每个中文词留一个最像常用词的。"""
    entries = load()
    candidates: dict[str, list[tuple[int, int, int, str]]] = defaultdict(list)
    # (释义位置, 藏文音节数, 藏文长度, 藏文)
    for tib, gloss, glosses in entries:
        if gloss.startswith("同") or gloss.startswith("见") or "同" in gloss[:2]:
            continue
        syllables = tib.count("་") + 1
        for position, zh in enumerate(glosses):
            if not (GLOSS_MIN <= len(zh) <= GLOSS_MAX):
                continue
            candidates[zh].append((position, syllables, len(tib), tib))
    pairs: list[tuple[str, str]] = []
    for zh, items in candidates.items():
        items.sort()
        chosen: list[str] = []
        for _, _, _, tib in items:
            if tib in chosen:
                continue
            chosen.append(tib)
            if len(chosen) >= MAX_TIBETAN_PER_GLOSS:
                break
        for tib in chosen:
            pairs.append((zh, tib))
    return pairs, len(candidates)


def main() -> None:
    PACK.mkdir(exist_ok=True)
    broad, gloss_count = broad_pairs()
    curated = load_curated() + load_phrases() + load_extra()

    # (藏文, 拼音) → (词频, 层, 中文)
    rows: dict[tuple[str, str], tuple[int, str, str]] = {}
    for zh, tib in curated:
        for reading in pinyin_variants(zh):
            rows[(tib, reading)] = (CURATED_FREQ, "curated", zh)
    for zh, tib in broad:
        for reading in pinyin_variants(zh):
            key = (tib, reading)
            if key not in rows or rows[key][0] < BROAD_FREQ:
                rows[key] = (BROAD_FREQ, "broad", zh)

    # 同一个藏文词可能由同一读音的多个中文词命中，按最高词频去重
    merged: dict[tuple[str, str], tuple[int, str, str]] = {}
    for (tib, reading), value in rows.items():
        old = merged.get((tib, reading))
        if old is None or value[0] > old[0]:
            merged[(tib, reading)] = value

    # 词库
    with (PACK / "tibetan.tsv").open("w", encoding="utf-8") as f:
        f.write("# 青简藏文词库：藏文词\t拼音\t词频\n")
        for (tib, reading), (freq, _, _) in sorted(merged.items()):
            f.write(f"{tib}\t{reading}\t{freq}\n")

    # 释义表：藏文 → 威利
    wylie_of: dict[str, str] = {}
    for tib, _ in merged:
        wylie_of.setdefault(tib, to_wylie(tib))
    with (PACK / "glossary.tsv").open("w", encoding="utf-8") as f:
        f.write("# 青简个人释义表：藏文词\t威利转写\n")
        for tib in sorted(wylie_of):
            w = wylie_of[tib]
            if w:
                f.write(f"{tib}\t{w}\n")

    # 预置选择：常用词整串输入时排第一（只对 curated 层）
    choices: dict[tuple[str, str], int] = {}
    for (tib, reading), (_, layer, _) in merged.items():
        key = reading.replace(" ", "")
        # 人工层给更高的次数，普通词条只要压过「没选过」就行
        choices[(key, tib)] = 100 if layer == "curated" else 20
    with (PACK / "choices.tsv").open("w", encoding="utf-8") as f:
        f.write("# 青简输入串选择：输入串\t藏文词\t次数\n")
        for (key, tib) in sorted(choices):
            f.write(f"{key}\t{tib}\t{choices[(key, tib)]}\n")

    # 对照表 + 自检
    missing = []
    lines = []
    for (tib, reading), (freq, layer, zh) in sorted(merged.items(), key=lambda kv: (kv[1][2], kv[0][0])):
        w = wylie_of.get(tib, "")
        missing.extend(unknown_syllables(tib))
        lines.append(f"{zh}\t{reading}\t{tib}\t{w}\t{layer}")
    (PACK / "wylie-reference.tsv").write_text(
        "# 中文\t拼音\t藏文\t威利\t层\n" + "\n".join(lines) + "\n", encoding="utf-8"
    )

    # 中文候选的注释：藏文 + 威利（可选再拼上原日语译词）
    japanese = load_japanese()
    best: dict[str, tuple[str, str, str]] = {}
    for (tib, _reading), (_freq, layer, zh) in merged.items():
        current = best.get(zh)
        if current is None or (layer == "curated" and current[1] != "curated"):
            best[zh] = (tib, layer, wylie_of.get(tib, ""))
    annotations = []
    combined = []
    for zh in sorted(best):
        tib, _layer, w = best[zh]
        if not w:
            continue
        annotations.append(f"{zh}\t{tib}  {w}")
        ja = japanese.get(zh)
        combined.append(f"{zh}\t{tib}  {w}｜{ja}" if ja else f"{zh}\t{tib}  {w}")
    (PACK / "annotations-tibetan.tsv").write_text(
        "# 中文候选注释：中文\t藏文 威利\n" + "\n".join(annotations) + "\n", encoding="utf-8"
    )
    (PACK / "annotations-combined.tsv").write_text(
        "# 中文候选注释：中文\t藏文 威利｜原日语译词\n" + "\n".join(combined) + "\n", encoding="utf-8"
    )

    uniq_missing = sorted(set(missing))
    report = [
        "青简藏文适配 —— 数据自检",
        f"藏汉词典反查中文词条：{gloss_count}",
        f"人工常用词：{len(curated)}",
        f"词库条目（藏文×读音）：{len(merged)}",
        f"其中人工层：{sum(1 for v in merged.values() if v[1] == 'curated')}",
        f"藏文词数：{len(wylie_of)}",
        f"威利表缺失音节：{len(uniq_missing)}",
        "缺失示例：" + " ".join(uniq_missing[:20]),
        f"预置选择：{len(choices)}",
        f"中文候选注释：藏文+威利 {len(annotations)} 条，拼日语 {sum(1 for a in combined if "｜" in a)} 条",
    ]
    (PACK / "report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
