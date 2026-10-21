# -*- coding: utf-8 -*-
"""生成本地补丁版青简设置程序：把“学习语言”下拉里的“越南语”显示名换成“藏文”。

青简的语言枚举是写死的，无法通过配置新增；这里做等长 UTF-8 替换：
“越南语”（9 字节）→ “藏文”+3 个空格（9 字节），不改变程序结构。
底层语言仍是 vi，注释写入 user-glossary-vi.tsv。

用法（在 tibetan/ 目录下）：
  python tools/patch_settings_label.py
然后把 dist/qingjian-settings-vi-tibetan.exe 备份并覆盖安装目录里的
C:\\Program Files\\Qingjian\\qingjian-settings.exe（需要管理员，见
tools/apply_label_admin.ps1）。
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Qingjian" / "qingjian-settings.exe"
OUT = ROOT / "dist" / "qingjian-settings-vi-tibetan.exe"
OLD = "越南语".encode("utf-8")
NEW = "藏文".encode("utf-8") + b"   "


def main() -> None:
    if not SRC.is_file():
        raise SystemExit(f"找不到青简设置程序：{SRC}")
    data = SRC.read_bytes()
    count = data.count(OLD)
    if count == 0:
        backup = ROOT / "backup" / "qingjian-settings.exe.orig"
        if backup.is_file():
            data = backup.read_bytes()
            count = data.count(OLD)
            print(f"当前安装的已是补丁版，改用备份生成：{backup}")
    if count == 0:
        raise SystemExit("没有找到“越南语”标签，青简可能已升级或已经打过补丁。")
    patched = data.replace(OLD, NEW)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(patched)
    print(f"已生成 {OUT}（替换 {count} 处，文件大小不变：{len(patched)} 字节）")
    print("下一步：以管理员运行 tools/apply_label_admin.ps1，把补丁版覆盖到安装目录。")


if __name__ == "__main__":
    main()
