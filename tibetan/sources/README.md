# 源数据（不随仓库分发）

`pack/` 里已经是生成好的词库、注释和威利表，直接用不需要这里的文件。
只有想从零重跑 `tools/gen_wylie_table.py` 或 `tools/build_pack.py` 时才需要把源数据放到本目录。

## 词库反查源

- `藏汉词典.txt`（UTF-16，25,241 条）
  来源：[bmwj/Tibetan_information_processing](https://github.com/bmwj/Tibetan_information_processing)
  的 `T10_藏汉电子词典设计/藏汉词典.txt`。

## 威利表源

- `Classified.xls`（18,785 个音节的构件分解）
- `TibetTolatSyallcode.txt`（构件 → 拉丁）
  来源：同一仓库的 `T08_藏文转拉丁/`。

## 许可

上述数据在源仓库以 MIT 许可提供；词典正文的著作权归原编者/出版方。
本仓库不再分发原始词典文件，只分发根据它整理的词对与威利转写表，使用时请遵守源数据许可。
