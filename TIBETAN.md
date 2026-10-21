# 青简 · 藏文适配分支

这个 fork 在 `tibetan/` 下附带了一套**藏文输入适配包**：

- 打中文拼音，候选仍是中文；高亮候选下方显示**藏文 + 威利转写**。
- 「设置 → 通用 → 学习语言」下拉里增加 **藏文**（替换“越南语”，日语保留）。
- 26,876 条中文 → 藏文 + 威利；18,774 个音节的威利转写表。

完整安装说明见 [tibetan/README.md](tibetan/README.md)。

```text
zangwen  →  1 藏文      （下方）བོད་ཡིག  bod yig
xiexie   →  1 谢谢      （下方）ཐུགས་རྗེ་ཆེ  thugs rje che
```

## 快速安装

```powershell
cd tibetan
python tools/selfcheck.py
python tools/install_pack.py --mode annotation --annotations tibetan --lang vi --set-language
python tools/patch_settings_label.py
# 然后右键“以管理员身份运行” tools\apply_label_admin.ps1
```

## 与上游的关系

适配包**没有改动青简的 Rust 源码**，全部走青简自带的扩展点（用户词库、个人释义表、
学习选择、候选窗字体）。要把它变成上游的原生语言，需要在
`crates/qingjian-core/src/candidate/language.rs` 里新增 `Language::Tibetan`（以及
`LEARNING_LANGUAGES`、释义表文件、设置页），并重新编译各平台外壳。

数据来源与许可见 [tibetan/README.md](tibetan/README.md) 末尾。
