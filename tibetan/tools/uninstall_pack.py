# -*- coding: utf-8 -*-
"""卸载青简藏文适配：删词库、撤掉藏文/威利条目与预置选择，还原字体/云兜底设置。

只撤掉本包装进去的条目：个人释义表按词删除（藏文词与中文注释键都清），
选择表按「输入串 + 藏文词」删除，其它个人数据原样保留。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "pack"
BACKUP = ROOT / "backup"
STATE = BACKUP / "install-state.json"
APP = Path(os.environ["APPDATA"]) / "Qingjian"


def rows(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    out: list[list[str]] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        out.append(raw.split("\t"))
    return out


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


def kill_server() -> None:
    subprocess.run(
        ["taskkill", "/IM", "qingjian-server.exe", "/F"],
        capture_output=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def main() -> None:
    if not STATE.is_file():
        sys.exit("找不到 backup/install-state.json，无法确定装过什么；可手动删除 %APPDATA%\\Qingjian\\dicts\\tibetan.tsv")
    state = json.loads(STATE.read_text(encoding="utf-8"))
    lang = state.get("language", "ja")

    # 先停 Server，免得它把内存里的旧学习数据写回来
    kill_server()

    # 1. 词库
    for name in ("tibetan.tsv", "tibetan.qj"):
        path = APP / "dicts" / name
        if path.exists():
            path.unlink()
            print("已删除", path)

    # 2. 释义表：藏文词键 + 中文注释键都删
    key_set = {row[0] for row in rows(PACK / "glossary.tsv") if row}
    for name in ("annotations-tibetan.tsv", "annotations-combined.tsv"):
        key_set |= {row[0] for row in rows(PACK / name) if row}
    glossary_path = APP / f"user-glossary-{lang}.tsv"
    if glossary_path.exists():
        lines = glossary_path.read_text(encoding="utf-8-sig").splitlines()
        header = next((line for line in lines if line.startswith("#")), "")
        kept = [
            line
            for line in lines
            if line.strip() and not line.startswith("#") and line.split("\t")[0] not in key_set
        ]
        glossary_path.write_text(
            (header + "\n" if header else "") + "\n".join(kept) + ("\n" if kept else ""),
            encoding="utf-8",
        )
        print(f"已从 {glossary_path.name} 删除藏文/威利条目")

    # 3. 选择记录：删掉「输入串 + 藏文词」完全对上的行
    choices_path = APP / "user-choices.tsv"
    if choices_path.exists():
        ours = {(row[0], row[1]) for row in rows(PACK / "choices.tsv") if len(row) >= 2}
        lines = choices_path.read_text(encoding="utf-8-sig").splitlines()
        header = next((line for line in lines if line.startswith("#")), "")
        kept = [line for line in lines if line.strip() and not line.startswith("#")]
        kept = [
            line
            for line in kept
            if len(line.split("\t")) < 2 or (line.split("\t")[0], line.split("\t")[1]) not in ours
        ]
        choices_path.write_text(
            (header + "\n" if header else "") + "\n".join(kept) + ("\n" if kept else ""),
            encoding="utf-8",
        )
        print(f"已从 {choices_path.name} 删除预置选择")

    # 4. 配置还原
    config_path = APP / "config.toml"
    if config_path.exists():
        config = config_path.read_text(encoding="utf-8")
        if "font_before" in state:
            before = state.get("font_before") or ""
            config = set_config_value(config, "general", "font", f'"{before}"')
        if "predict_enabled_before" in state:
            before = state.get("predict_enabled_before") or "true"
            config = set_config_value(config, "predict", "enabled", before)
        before_language = state.get("learning_language_before")
        if before_language:
            config = set_config_value(
                config, "general", "learning_language", '"%s"' % before_language
            )
        config_path.write_text(config, encoding="utf-8")
        print("已还原配置（字体 / 云兜底 / 学习语言）")

    kill_server()
    if state.get("settings_patched"):
        print("注意：设置程序的“越南语→藏文”显示名补丁还在；")
        print("     以管理员运行 tools\\restore_label_elevated.ps1 可还原原版设置程序。")
    print("卸载完成；切走再切回输入法即可生效。")


if __name__ == "__main__":
    main()
