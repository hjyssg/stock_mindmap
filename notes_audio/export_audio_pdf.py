#!/usr/bin/env python3
"""
把 notes_audio/ 下所有 Markdown 合并成一个 PDF，每篇一个书签章节。
依赖：pip install fpdf2 markdown
"""

import os
import re
import markdown
from fpdf import FPDF
from fpdf.enums import XPos, YPos

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOTES_DIR = BASE_DIR
OUTPUT_PDF = os.path.join(BASE_DIR, "个人经济学笔记_听书版.pdf")
FONT_PATH = r"C:\Windows\Fonts\simhei.ttf"

md_files = sorted(
    os.path.join(NOTES_DIR, f)
    for f in os.listdir(NOTES_DIR)
    if f.endswith(".md")
)
print(f"共找到 {len(md_files)} 篇")

pdf = FPDF(format="A4")
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_font("SimHei", style="", fname=FONT_PATH)
pdf.add_font("SimHei", style="B", fname=FONT_PATH)
pdf.set_font("SimHei", size=12)


def strip_emoji(text):
    return re.sub(
        r"[\U00010000-\U0010ffff\u2600-\u27BF\u2300-\u23FF"
        r"\u2B50-\u2B55\u2702-\u27B0\uFE00-\uFE0F\u200d\u2640-\u2642]+",
        "", text,
    )


def clean_html(html):
    html = re.sub(r"<hr\s*/?>", "<br/>", html, flags=re.IGNORECASE)
    html = re.sub(r'\s(class|style)="[^"]*"', "", html)
    return html


def get_title(filepath, content):
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return strip_emoji(line[2:].strip())
    return strip_emoji(os.path.splitext(os.path.basename(filepath))[0])


for filepath in md_files:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()

    title = get_title(filepath, content)
    body = markdown.markdown(content, extensions=["nl2br"])
    body = clean_html(body)

    pdf.add_page()
    pdf.start_section(title, level=0)

    pdf.set_font("SimHei", size=12)
    try:
        pdf.write_html(body, tag_styles={
            "h1": {"font_size_pt": 20, "color": 0x111111},
            "h2": {"font_size_pt": 16, "color": 0x333333},
            "p":  {"font_size_pt": 12},
        })
    except Exception:
        plain = strip_emoji(re.sub(r"<[^>]+>", "", body))
        pdf.multi_cell(0, 8, plain)

pdf.output(OUTPUT_PDF)
print(f"完成！已输出：{OUTPUT_PDF}")
