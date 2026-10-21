# -*- coding: utf-8 -*-
"""把 pack/ 里的藏文数据装进青简输入法。

两种模式：
  annotation（默认）  中文候选不动，候选下方显示「藏文 + 威利」（可再拼上原日语译词）
  candidate            候选直接是藏文，下方显示威利（藏文优先输入）

会改动的用户数据全部先备份到 backup/：
  %APPDATA%\\Qingjian\\dicts\\tibetan.tsv
  %APPDATA%\\Qingjian\\user-glossary-<语言>.tsv
  %APPDATA%\\Qingjian\\user-choices.tsv
  %APPDATA%\\Qingjian\\config.toml
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "pack"
BACKUP = ROOT / "backup"
APP = Path(os.environ["APPDATA"]) / "Qingjian"
STATE = BACKUP / "install-state.json"

FONT_DEFAULT = "Microsoft Himalaya"
GLOSSARY_HEADER = "# 青简个人释义表（{lang}）：释义兜底从云端写来的，格式同随包释义表，可手改。词\\t[词性. ]译词[|读音]"
CHOICES_HEADER = "# 青简按输入串记的选择：输入串\t词\t次数"


def timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def backup(path: Path) -> str | None:
    if not path.exists():
        return None
    BACKUP.mkdir(parents=True, exist_ok=True)
    dst = BACKUP / f"{path.name}.{timestamp()}.bak"
    shutil.copy2(path, dst)
    return str(dst)


def rows(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    out: list[list[str]] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        out.append(raw.split("\t"))
    return out


def write_glossary(path: Path, additions: list[list[str]], remove_keys: set[str]) -> int:
    entries: dict[str, list[str]] = {}
    for row in rows(path):
        if len(row) >= 2 and row[0] and row[0] not in remove_keys:
            entries[row[0]] = row
    added = 0
    for row in additions:
        if len(row) >= 2 and row[0]:
            entries[row[0]] = row
            added += 1
    lang = path.stem.replace("user-glossary-", "")
    text = GLOSSARY_HEADER.format(lang=lang) + "\n"
    text += "".join("\t".join(entries[key]) + "\n" for key in sorted(entries))
    atomic_write(path, text)
    return added


def write_choices(path: Path, additions: list[list[str]], remove_pairs: set[tuple[str, str]]) -> int:
    entries: dict[tuple[str, str], int] = {}
    for row in rows(path):
        if len(row) >= 3 and row[0] and row[1]:
            try:
                count = int(row[2])
            except ValueError:
                continue
            if (row[0], row[1]) in remove_pairs:
                continue
            entries[(row[0], row[1])] = count
    added = 0
    for row in additions:
        if len(row) >= 3 and row[0] and row[1]:
            try:
                count = int(row[2])
            except ValueError:
                continue
            key = (row[0], row[1])
            entries[key] = max(entries.get(key, 0), count)
            added += 1
    text = CHOICES_HEADER + "\n" + "".join(
        f"{key}\t{word}\t{count}\n" for (key, word), count in sorted(entries.items())
    )
    atomic_write(path, text)
    return added


def set_config_value(text: str, section: str, key: str, value: str) -> str:
    lines = text.splitlines()
    current = None
    replaced = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped[1:-1]
            continue
        if current == section and re.match(rf"\s*{re.escape(key)}\s*=", line):
            indent = line[: len(line) - len(line.lstrip())]
            lines[i] = f"{indent}{key} = {value}"
            replaced = True
    if not replaced:
        out: list[str] = []
        inserted = False
        for line in lines:
            out.append(line)
            if not inserted and line.strip() == f"[{section}]":
                out.append(f"{key} = {value}")
                inserted = True
        lines = out
    return "\n".join(lines) + "\n"


def read_config_value(text: str, section: str, key: str) -> str | None:
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped[1:-1]
            continue
        if current == section:
            match = re.match(rf"\s*{re.escape(key)}\s*=\s*(.+?)\s*$", line)
            if match:
                return match.group(1).strip().strip('"')
    return None


def kill_server() -> None:
    subprocess.run(
        ["taskkill", "/IM", "qingjian-server.exe", "/F"],
        capture_output=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="安装青简藏文适配")
    parser.add_argument("--mode", choices=["annotation", "candidate"], default="annotation",
                        help="annotation：中文候选 + 下方藏文/威利；candidate：候选直接出藏文")
    parser.add_argument("--annotations", choices=["combined", "tibetan"], default="combined",
                        help="annotation 模式下注释是否拼上原有日语译词")
    parser.add_argument("--lang", help="个人释义表写入哪种学习语言（默认跟随配置）")
    parser.add_argument("--font", default=FONT_DEFAULT, help="候选窗字体；传空字符串跳过")
    parser.add_argument("--keep-cloud", action="store_true", help="保留云释义兜底")
    parser.add_argument("--no-restart", action="store_true", help="不改动正在运行的 Server")
    parser.add_argument("--set-language", action="store_true", help="把配置里的学习语言改成本次 --lang")
    args = parser.parse_args()

    if not (PACK / "tibetan.tsv").is_file():
        sys.exit("pack/ 里没有数据，先运行 python tools/build_pack.py")

    config_path = APP / "config.toml"
    config = config_path.read_text(encoding="utf-8")
    state: dict = {"installed_at": time.strftime("%Y-%m-%d %H:%M:%S"), "files": {}}

    previous_language = read_config_value(config, "general", "learning_language")
    state["learning_language_before"] = previous_language
    lang = args.lang
    if not lang:
        lang = read_config_value(config, "general", "learning_language") or "ja"
        if lang == "off":
            state["learning_language_before"] = "off"
            config = set_config_value(config, "general", "learning_language", '"ja"')
            lang = "ja"

    glossary_path = APP / f"user-glossary-{lang}.tsv"
    choices_path = APP / "user-choices.tsv"
    dict_path = APP / "dicts" / "tibetan.tsv"
    for path in (config_path, glossary_path, choices_path, dict_path, APP / "dicts" / "tibetan.qj"):
        saved = backup(path)
        if saved:
            state["files"][path.name] = saved

    # 先停 Server，避免它定时把内存里的学习数据写回文件
    if not args.no_restart:
        kill_server()

    # 两套词条的键：候选模式用藏文词，注释模式用中文词；切换时互相清掉
    tibetan_words = {row[0] for row in rows(PACK / "glossary.tsv") if row}
    annotation_words: set[str] = set()
    for name in ("annotations-tibetan.tsv", "annotations-combined.tsv"):
        annotation_words |= {row[0] for row in rows(PACK / name) if row}
    choice_pairs = {(row[0], row[1]) for row in rows(PACK / "choices.tsv") if len(row) >= 2}

    if args.mode == "annotation":
        # 候选保持中文：撤掉藏文词库与预置选择
        for name in ("tibetan.tsv", "tibetan.qj"):
            path = APP / "dicts" / name
            if path.exists():
                path.unlink()
        write_choices(choices_path, [], choice_pairs)
        annotation_file = PACK / ("annotations-combined.tsv" if args.annotations == "combined" else "annotations-tibetan.tsv")
        added_gloss = write_glossary(glossary_path, rows(annotation_file), tibetan_words | annotation_words)
        # 切语言时把其它语言的同批注释也清掉，避免上一门语言的残留
        for other in APP.glob("user-glossary-*.tsv"):
            if other.resolve() != glossary_path.resolve():
                write_glossary(other, [], tibetan_words | annotation_words)
        summary = f"{added_gloss} 条中文候选注释（藏文+威利{'，拼日语' if args.annotations == 'combined' else ''}）"
    else:
        dicts = APP / "dicts"
        dicts.mkdir(parents=True, exist_ok=True)
        stale = dicts / "tibetan.qj"
        if stale.exists():
            stale.unlink()
        shutil.copy2(PACK / "tibetan.tsv", dict_path)
        write_glossary(glossary_path, rows(PACK / "glossary.tsv"), annotation_words | tibetan_words)
        added_choices = write_choices(choices_path, rows(PACK / "choices.tsv"), set())
        summary = f"{added_choices} 条藏文候选与预置选择"

    if args.set_language:
        config = set_config_value(config, "general", "learning_language", json.dumps(lang))
    if args.font:
        state["font_before"] = read_config_value(config, "general", "font")
        config = set_config_value(config, "general", "font", json.dumps(args.font, ensure_ascii=False))
    if not args.keep_cloud:
        state["predict_enabled_before"] = read_config_value(config, "predict", "enabled")
        config = set_config_value(config, "predict", "enabled", "false")
    atomic_write(config_path, config)

    state.update({"mode": args.mode, "annotations": args.annotations, "language": lang,
                  "font_after": args.font})
    BACKUP.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    print("安装完成：")
    print(f"  模式      {args.mode}（{summary}）")
    print(f"  释义表    {glossary_path}")
    print(f"  字体      {args.font or '未改'}")
    print(f"  云释义兜底{'保留' if args.keep_cloud else '已关闭'}")
    if args.mode == "annotation":
        print("  下一步：切走再切回青简，打 zangwen；候选 1 是「藏文」，下方显示 བོད་ཡིག  bod yig。")
    else:
        print("  下一步：切走再切回青简，打 zangwen；候选 1 是 བོད་ཡིག，下方显示 bod yig。")


if __name__ == "__main__":
    main()
