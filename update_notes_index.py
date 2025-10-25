#!/usr/bin/env python3
"""根据 `notes/` 目录结构自动更新首页 `notes/index.md` 并生成总索引。"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Sequence, Tuple

ROOT = Path(__file__).resolve().parent
NOTES_DIR = ROOT / "notes"
INDEX_PATH = NOTES_DIR / "index.md"
ALL_NOTES_PATH = NOTES_DIR / "all-notes.md"
MKDOCS_PATH = ROOT / "mkdocs.yml"

INTRO = """# Stock Mindmap 笔记导览

> 本仓库的原始笔记全部保存在 `notes/` 目录。现已统一采用 [MkDocs](https://www.mkdocs.org/) + Material 主题生成静态站点，便于在线浏览与检索。
""".strip()

CATEGORIES_HEADING = "## 分类结构"

OUTRO = """
更多笔记会在原有文件结构下继续扩展，方便使用者在本地编辑或在线浏览时保持一致体验。

## 站点构建方式

- 站点生成器：MkDocs 1.x + Material 主题
- 笔记目录：直接引用 `notes/`，无需额外迁移
- GitHub Pages：通过自动化工作流发布到 `gh-pages` 分支

如需离线或自定义构建，可参考仓库根目录的 `README.md`。
""".strip()

ALL_NOTES_TITLE = "# 全部笔记索引"
ALL_NOTES_INTRO = (
    "> 自动汇总 `notes/` 目录下的所有 Markdown 文件，按分类列出，便于快速查找。"
)

CATEGORY_DESCRIPTIONS: Dict[str, str] = {
    "strategy": "行为心理、仓位管理与模型复盘相关的体系化思考。",
    "markets": "历史行情、黑天鹅事件、波动率分析等具体案例回顾。",
    "economy": "宏观指标、央行政策、全球经济演化笔记。",
    "china": "国内监管事件、产业政策与对外关系整理。",
    "personal_finance": "资产配置、税务与跨境资金管理经验。",
    "misc": "未归类的阅读摘录、科技趋势和灵感记录。",
}

PLACEHOLDER_DESCRIPTION = "（待补充简介）"


class Category(NamedTuple):
    """记录分类名称、目录路径及索引文件相对路径。"""

    title: str
    directory: Path
    index_rel_path: str


def extract_category_nav(mkdocs_text: str) -> List[Tuple[str, str]]:
    """从 mkdocs.yml 中提取分类导航的标题与路径。"""
    nav_entries: List[Tuple[str, str]] = []
    lines = mkdocs_text.splitlines()
    in_categories = False
    base_indent = 0

    indent_re = re.compile(r"^(?P<indent>\s*)-")
    entry_re = re.compile(r"^(?P<indent>\s*)-\s*(?P<title>[^:]+):\s*(?P<path>\S+)")

    for raw_line in lines:
        line = raw_line.rstrip()
        if not in_categories:
            match = re.match(r"^(?P<indent>\s*)-\s*分类\s*:\s*", line)
            if match:
                in_categories = True
                base_indent = len(match.group("indent"))
            continue

        if not line.strip():
            continue

        indent_match = indent_re.match(line)
        if indent_match:
            indent_len = len(indent_match.group("indent"))
            if indent_len <= base_indent:
                break
        else:
            # 非列表行，视为分类块结束
            break

        entry_match = entry_re.match(line)
        if entry_match:
            title = entry_match.group("title").strip()
            path = entry_match.group("path").strip()
            nav_entries.append((title, path))

    return nav_entries


def read_category_title(index_file: Path) -> str:
    """读取子目录 `index.md` 的首个标题作为分类名称。"""
    for line in index_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("# ")
    return index_file.parent.name


def gather_categories(nav_entries: Sequence[Tuple[str, str]]) -> List[Category]:
    """根据 mkdocs 导航与目录实际情况列出分类。"""

    categories: List[Category] = []
    seen_dirs = set()

    for title, rel_path in nav_entries:
        directory_name = rel_path.split("/")[0]
        directory_path = NOTES_DIR / directory_name
        if not directory_path.exists() or not directory_path.is_dir():
            continue
        categories.append(
            Category(
                title=title,
                directory=directory_path,
                index_rel_path=rel_path,
            )
        )
        seen_dirs.add(directory_name)

    remaining_dirs = sorted(
        (
            d
            for d in NOTES_DIR.iterdir()
            if d.is_dir()
            and (d / "index.md").exists()
            and d.name not in seen_dirs
        ),
        key=lambda p: p.name,
    )

    for directory in remaining_dirs:
        index_file = directory / "index.md"
        categories.append(
            Category(
                title=read_category_title(index_file),
                directory=directory,
                index_rel_path=f"{directory.name}/index.md",
            )
        )

    return categories


def format_category_entry(title: str, path: str, description: str) -> str:
    return f"- [{title}]({path})：{description}"


def build_category_entries(categories: Sequence[Category]) -> List[str]:
    entries: List[str] = []

    for category in categories:
        description = CATEGORY_DESCRIPTIONS.get(
            category.directory.name, PLACEHOLDER_DESCRIPTION
        )
        entries.append(
            format_category_entry(category.title, category.index_rel_path, description)
        )

    return entries


def render_index(entries: Iterable[str]) -> str:
    parts = [INTRO, "", CATEGORIES_HEADING, ""]
    parts.extend(entries)
    parts.extend(["", OUTRO])
    return "\n".join(parts).rstrip() + "\n"


def read_note_title(note_file: Path) -> str:
    """直接使用笔记文件名（不含扩展名）作为条目名称。"""

    return note_file.stem


def build_all_notes_sections(categories: Sequence[Category]) -> List[str]:
    """按分类生成全部笔记的 Markdown 段落。"""

    sections: List[str] = []

    for category in categories:
        note_files = sorted(
            (
                path
                for path in category.directory.glob("*.md")
                if path.name.lower() != "index.md"
            ),
            key=lambda p: p.name,
        )

        if not note_files:
            continue

        sections.append(f"## {category.title}")

        for note_file in note_files:
            title = read_note_title(note_file)
            rel_path = f"{category.directory.name}/{note_file.name}"
            sections.append(f"- [{title}]({rel_path})")

        sections.append("")

    return sections


def render_all_notes(categories: Sequence[Category]) -> str:
    parts: List[str] = [ALL_NOTES_TITLE, "", ALL_NOTES_INTRO, ""]
    sections = build_all_notes_sections(categories)
    parts.extend(sections)
    return "\n".join(parts).rstrip() + "\n"


def main() -> None:
    mkdocs_text = MKDOCS_PATH.read_text(encoding="utf-8")
    nav_entries = extract_category_nav(mkdocs_text)
    categories = gather_categories(nav_entries)

    category_entries = build_category_entries(categories)
    index_content = render_index(category_entries)
    all_notes_content = render_all_notes(categories)

    INDEX_PATH.write_text(index_content, encoding="utf-8")
    ALL_NOTES_PATH.write_text(all_notes_content, encoding="utf-8")


if __name__ == "__main__":
    main()
