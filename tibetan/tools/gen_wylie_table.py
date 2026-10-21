# -*- coding: utf-8 -*-
"""从《藏文转拉丁》项目的数据生成威利转写表。

输入：
  research-tip/T08_藏文转拉丁/TibetTolatSyallcode.txt  单字/构件 → 拉丁
  research-tip/T08_藏文转拉丁/Classified.xls           18785 个音节的构件分解
输出：
  data/wylie-chars.tsv   构件 → 拉丁
  data/syllables.tsv     音节 → 威利

做法：音节分解表把每个音节拆成「前加字 + 上加字 + 基字 + 下加字 + 再下加字 + 元音 + 后加字 + 再后加字」，
逐件查表拼接，没有元音符号时在基字/下加字之后补隐含的 a，正好是威利的书写顺序。
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vendor"))
import xlrd  # noqa: E402

SRC = ROOT / "sources"
if not (SRC / "Classified.xls").is_file():
    SRC = ROOT / "research-tip" / "T08_藏文转拉丁"
OUT = ROOT / "data"

# 下加字（U+0F90–U+0FBC）的威利写法；源表只有「上加字+基字」的复合写法
SUBJOINED = {
    "ྐ": "k", "ྑ": "kh", "ྒ": "g", "ྒྷ": "gh", "ྔ": "ng",
    "ྕ": "c", "ྖ": "ch", "ྗ": "j", "ྙ": "ny",
    "ྚ": "ṭ", "ྛ": "ṭh", "ྜ": "ḍ", "ྜྷ": "ḍh", "ྞ": "ṇ",
    "ྟ": "t", "ྠ": "th", "ྡ": "d", "ྡྷ": "dh", "ྣ": "n",
    "ྤ": "p", "ྥ": "ph", "ྦ": "b", "ྦྷ": "bh", "ྨ": "m",
    "ྩ": "ts", "ྪ": "tsh", "ྫ": "dz", "ྫྷ": "dzh", "ྭ": "w",
    "ྮ": "zh", "ྯ": "z", "ྰ": "'", "ྱ": "y", "ྲ": "r", "ླ": "l",
    "ྴ": "sh", "ྵ": "ṣ", "ྶ": "s", "ྷ": "h", "ྸ": "a",
    "ྐྵ": "kṣ", "ྺ": "w", "ྻ": "y", "ྼ": "r",
}

# 元音符号与梵文标记（源表未收，补上以免转写里漏出藏文字符）
MARKS = {
    "ཱ": "A", "ི": "i", "ུ": "u", "ེ": "e", "ོ": "o",
    "ཻ": "ai", "ཽ": "au", "ྀ": "i", "ཱྀ": "u",
    "ཾ": "M", "ྂ": "M", "ྃ": "~M", "ཿ": "H", "྄": "",
    "྅": "@", "ྈ": "", "ྉ": "", "ྊ": "", "ྋ": "",
}


def load_chars() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for line in (SRC / "TibetTolatSyallcode.txt").read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2:
            mapping[parts[0]] = parts[1]
    # 标准威利用 ' 表示 འ；源表沿用了输入法里常见的 v
    mapping["འ"] = "'"
    for char, latin in MARKS.items():
        mapping.setdefault(char, latin)
    # 梵文转写用的基字，源表未收
    for char, latin in {
        "ཊ": "ṭ", "ཋ": "ṭh", "ཌ": "ḍ", "ཎ": "ṇ", "ཥ": "ṣ",
        "ཀྵ": "kṣ", "ཪ": "r", "ཨ": "a",
    }.items():
        mapping.setdefault(char, latin)
    # 下加字逐件补上
    for char, latin in SUBJOINED.items():
        mapping.setdefault(char, latin)
    return mapping


def main() -> None:
    chars = load_chars()
    OUT.mkdir(exist_ok=True)
    with (OUT / "wylie-chars.tsv").open("w", encoding="utf-8") as f:
        f.write("# 构件\t威利\n")
        for k in sorted(chars):
            f.write(f"{k}\t{chars[k]}\n")

    wb = xlrd.open_workbook(str(SRC / "Classified.xls"))
    sh = wb.sheet_by_name("字符结构")
    seen: dict[str, str] = {}
    missing: list[tuple[str, str]] = []
    for i in range(1, sh.nrows):
        values = [sh.cell_value(i, c) for c in range(10)]
        syllable = values[0]
        parts = values[1:9]  # 前加字 … 再后加字
        out: list[str] = []
        ok = True
        for part in parts:
            if not part:
                continue
            if part not in chars:
                ok = False
                missing.append((syllable, part))
                break
            out.append(chars[part])
        if not ok:
            continue
        if not values[6]:  # 没有元音符号 → 隐含 a，放在基字/下加字之后
            head = "".join(chars[p] for p in values[1:6] if p)
            tail = "".join(chars[p] for p in values[7:9] if p)
            wylie = head + "a" + tail
        else:
            wylie = "".join(out)
        # ཨ 作为基字时本身读 a，避免叠成 aa
        if values[3] == "ཨ":
            wylie = wylie.replace("aa", "a")
        seen.setdefault(syllable, wylie)

    with (OUT / "syllables.tsv").open("w", encoding="utf-8") as f:
        f.write("# 音节\t威利\n")
        for syllable in sorted(seen):
            f.write(f"{syllable}\t{seen[syllable]}\n")
    print(f"音节 {len(seen)} 条，构件 {len(chars)} 个，缺映射 {len(missing)} 处")
    if missing[:10]:
        print("缺映射示例", missing[:10])


if __name__ == "__main__":
    main()
