# 中文版：重建基准如何反转结论

本目录是英文稿（`../readkv_v2_tmlr_anonymous/`）的中文版本。它不是逐句直译：叙述顺序、段落组织与举例方式按中文论文的阅读习惯重写，但**数据、表格、区间与结论边界与英文版完全一致**——两张稿子共用同一份由 `reproduce.py` 生成的 `results.tex`，因此表格数字不可能出现分叉。

## 文件

- `main.tex` —— 中文稿（`ctex` + `fontset=fandol`，XeLaTeX 系引擎）
- `results.tex` —— 表格宏，与英文稿目录中的同名文件逐字节相同
- `figures/fig*_zh.pdf` —— 六张中文图（矢量）；同名 `.png` 为预览
- `figures/preview_zh.html` —— 六张图的中文图版，浏览器直接打开
- `main.pdf` —— 编译产物（10 页）

## 编译

    tectonic main.tex

或 `xelatex main`（两遍）。字体用 TeX Live 自带的 Fandol 宋体/黑体，不依赖系统字体，因此在离线或容器环境也能复现排版。若本机装了 ctex 全套，可把 `fontset=fandol` 换成 `fontset=windows` 用中易宋体。

## 图的生成

中文图不是另画一套，而是复用英文图的几何：`figures/zh_labels.py` 把每个要显示的字符串映射成中文，`figures/render_zh.py` 用 SimSun 渲染并输出 `*_zh.pdf`。这样换语言不会移动任何一个方框、标记或坐标轴。出图前会跑与英文版相同的检查：文字重叠、图例压数据、箭头穿框、最小字号 7 pt、灰度对比、以及**缺字（missing glyph）即失败**。

    cd ../readkv_v2_tmlr_anonymous/figures
    python render_zh.py        # 生成中文图并自检

## 数字从哪来

正文里出现的每个数值都可回溯到 `results.json` / `evaluation.json`，或由 `data/audit_2x2/` 的原始语料重算。写作过程中做过一次机械核对：中文稿里 54 个小数中，除 `\linespread` 与四条 arXiv 编号外，其余全部出现在英文稿或其表格中。
