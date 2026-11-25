"""把 白话版.md 编译成 白话版.pdf。

路线：Markdown -> HTML -> Chrome(headless) 打印 PDF。
不依赖 pandoc / LaTeX；仅依赖 markdown 与 playwright，以及本机 Chrome。

用法：python build_pdf.py
输出：白话版.html、白话版.pdf（与本脚本同目录）
"""

import re
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SRC = HERE / "白话版.md"
HTML = HERE / "白话版.html"
PDF = HERE / "白话版.pdf"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

CSS = """
body {
  font-family: "Microsoft YaHei", "SimSun", "Segoe UI", sans-serif;
  font-size: 10.5pt;
  line-height: 1.6;
  color: #222;
}
h1 { font-size: 20pt; margin: 0 0 2pt 0; text-align: center; }
h2 { font-size: 15pt; margin: 18pt 0 6pt 0; border-bottom: 1px solid #bbb; padding-bottom: 4pt; }
h3 { font-size: 12pt; margin: 14pt 0 5pt 0; }
p  { margin: 5pt 0; text-align: justify; }
blockquote { margin: 6pt 0; padding: 4pt 10pt; background: #f6f6f6; color: #555; font-size: 9.5pt; }
hr { border: none; border-top: 1px solid #ddd; margin: 14pt 0; }
ul, ol { margin: 5pt 0 5pt 18pt; }
li { margin: 2pt 0; }
table { border-collapse: collapse; width: 100%; font-size: 9pt; margin: 8pt 0; }
th, td { border: 1px solid #ccc; padding: 3pt 5pt; text-align: center; vertical-align: middle; }
th { background: #f0f0f0; font-weight: 600; }
tr { page-break-inside: avoid; }
img { max-width: 100%; display: block; margin: 8pt auto 2pt auto; }
.caption { font-size: 9pt; color: #555; text-align: center; margin: 2pt 0 10pt 0; }
.math {
  font-family: "Cambria Math", "Times New Roman", serif;
  font-size: 12pt;
  text-align: center;
  margin: 7pt 0;
}
.math sub { font-size: 8pt; }
.math sup { font-size: 8pt; }
strong { font-weight: 600; }
"""


def latex_to_html(expr: str) -> str:
    """把本文用到的少量 LaTeX 公式转成可读的 HTML。"""
    s = expr.strip()
    s = re.sub(r"\\mathrm\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\left\|", "|", s)
    s = re.sub(r"\\right\|", "|", s)
    s = re.sub(r"\\left\(", "(", s)
    s = re.sub(r"\\right\)", ")", s)
    s = re.sub(r"_\{([^{}]*)\}", r"<sub>\1</sub>", s)
    s = re.sub(r"\^\{([^{}]*)\}", r"<sup>\1</sup>", s)
    s = re.sub(r"\\([A-Za-z]+)", r"\1", s)
    return s


def main() -> None:
    text = SRC.read_text(encoding="utf-8")

    # 1) 取出 $$...$$ 块公式，先换成占位符
    formulas: list[str] = []

    def stash(match: re.Match) -> str:
        formulas.append(latex_to_html(match.group(1)))
        return f"%%MATH{len(formulas) - 1}%%"

    text = re.sub(r"\$\$(.+?)\$\$", stash, text, flags=re.S)

    # 2) 图注整行改成专用段落，避免整段中文变斜体
    text = re.sub(r"^\*图 (.+?)\*$", r'<p class="caption">图 \1</p>', text, flags=re.M)

    # 3) Markdown -> HTML（启用表格）
    body = markdown.markdown(text, extensions=["tables"])

    # 4) 还原公式
    for i, formula in enumerate(formulas):
        body = body.replace(f"%%MATH{i}%%", f'<div class="math">{formula}</div>')

    html = (
        "<!DOCTYPE html>\n<html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        f"<title>白话版</title><style>{CSS}</style></head><body>{body}</body></html>\n"
    )
    HTML.write_text(html, encoding="utf-8")

    # 5) Chrome 打印 PDF
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True, executable_path=str(CHROME), args=["--disable-gpu"]
        )
        page = browser.new_page()
        page.goto(HTML.as_uri(), wait_until="load")
        page.pdf(
            path=str(PDF),
            format="A4",
            print_background=True,
            margin={"top": "18mm", "bottom": "18mm", "left": "16mm", "right": "16mm"},
        )
        browser.close()

    print(f"OK: {PDF}")


if __name__ == "__main__":
    main()
