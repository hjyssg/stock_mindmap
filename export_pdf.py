#!/usr/bin/env python3
"""
把 notes/ 下所有 Markdown（排除 china/ 文件夹）合并成一个 PDF。
依赖：pip install fpdf2 markdown
"""

import os
import re
import markdown
from fpdf import FPDF
from fpdf.html import HTMLMixin

NOTES_DIR = "notes"
EXCLUDE_DIRS = {"china"}
OUTPUT_PDF = "notes_export.pdf"
FONT_PATH = r"C:\Windows\Fonts\simhei.ttf"   # Windows 自带黑体

# ── 收集 md 文件 ──────────────────────────────────────────────────────────
md_files = []
for root, dirs, files in os.walk(NOTES_DIR):
    dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS)
    for f in sorted(files):
        if f.endswith(".md"):
            md_files.append(os.path.join(root, f))

print(f"共找到 {len(md_files)} 个 Markdown 文件（已排除 china/）")


# ── 自定义 PDF 类 ─────────────────────────────────────────────────────────
class PDF(FPDF, HTMLMixin):
    pass


pdf = PDF(format="A4")
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_font("SimHei", style="", fname=FONT_PATH)
pdf.add_font("SimHei", style="B", fname=FONT_PATH)   # bold 也用同一字体
pdf.set_font("SimHei", size=11)


def clean_html(html: str) -> str:
    """移除 fpdf2 不支持的标签，保留基本结构。"""
    # 去掉 <hr>（fpdf2 不支持）
    html = re.sub(r"<hr\s*/?>", "<br/>", html, flags=re.IGNORECASE)
    # 去掉 class/style 属性（避免解析错误）
    html = re.sub(r'\s(class|style)="[^"]*"', "", html)
    return html


# ── 逐文件写入 PDF ────────────────────────────────────────────────────────
for i, filepath in enumerate(md_files):
    rel = os.path.relpath(filepath, NOTES_DIR)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()

    # Markdown → HTML
    body = markdown.markdown(
        content,
        extensions=["tables", "fenced_code", "nl2br"],
    )
    body = clean_html(body)

    pdf.add_page()

    # 文件路径小标题
    pdf.set_font("SimHei", size=8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 6, f"[{rel}]", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1)

    # 正文
    pdf.set_font("SimHei", size=11)
    try:
        pdf.write_html(body, tag_styles={
            "h1": {"font_size_pt": 18, "color": 0x222222},
            "h2": {"font_size_pt": 15, "color": 0x333333},
            "h3": {"font_size_pt": 13, "color": 0x444444},
            "p":  {"font_size_pt": 11},
        })
    except Exception as e:
        # 降级：直接输出纯文本
        pdf.set_font("SimHei", size=11)
        plain = re.sub(r"<[^>]+>", "", body)
        pdf.multi_cell(0, 7, plain)

    if i % 10 == 0:
        print(f"  进度：{i+1}/{len(md_files)}")

pdf.output(OUTPUT_PDF)
print(f"\n✅ 完成！已输出：{OUTPUT_PDF}")
