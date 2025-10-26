#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 `notes/` 目录结构自动更新首页 `notes/index.md`、生成总索引 `notes/all-notes.md`，
并为每个分类目录自动生成/更新其 `index.md`。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Sequence, Tuple

# -----------------------------
# 路径常量
# -----------------------------
ROOT = Path(__file__).resolve().parent
NOTES_DIR = ROOT / "notes"
INDEX_PATH = NOTES_DIR / "index.md"
ALL_NOTES_PATH = NOTES_DIR / "all-notes.md"
MKDOCS_PATH = ROOT / "mkdocs.yml"

# -----------------------------
# 文案模板
# -----------------------------
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

# -----------------------------
# 数据结构
# -----------------------------
class Category(NamedTuple):
    """记录分类名称、目录路径及索引文件相对路径。"""
    title: str
    directory: Path
    index_rel_path: str


# -----------------------------
# 工具函数
# -----------------------------
def md_escape(text: str) -> str:
    """最小化 Markdown 转义，避免标题中出现括号、方括号等导致语法歧义。"""
    return (
        text.replace("\\", "\\\\")
        .replace("*", "\\*")
        .replace("_", "\\_")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("#", "\\#")
    )


def rel_url(*parts: str) -> str:
    """使用原样相对路径（不做 URL 编码），避免中文文件名被百分号编码。"""
    return "/".join(parts)


def write_if_changed(path: Path, content: str) -> None:
    """仅在内容变化时写入，避免产生无意义的 CI diff。"""
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if old != content:
        path.write_text(content, encoding="utf-8")


# -----------------------------
# mkdocs.yml 导航提取
# -----------------------------
def _extract_category_nav_by_regex(mkdocs_text: str) -> List[Tuple[str, str]]:
    """正则回退方案：从 mkdocs.yml 中提取“分类”块内的 (title, path)。"""
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
            break

        entry_match = entry_re.match(line)
        if entry_match:
            title = entry_match.group("title").strip()
            path = entry_match.group("path").strip()
            nav_entries.append((title, path))

    return nav_entries


def extract_category_nav(mkdocs_text: str) -> List[Tuple[str, str]]:
    """
    首选 YAML 解析；若 PyYAML 不可用或结构异常，则回退到正则解析。
    返回 [(title, path), ...]
    """
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(mkdocs_text) or {}
        nav = data.get("nav", [])
        for item in nav:
            if isinstance(item, dict) and "分类" in item:
                cats = item["分类"]
                result: List[Tuple[str, str]] = []
                for entry in cats or []:
                    if isinstance(entry, dict) and len(entry) == 1:
                        [(title, path)] = entry.items()
                        result.append((str(title), str(path)))
                return result
        return []
    except Exception:
        return _extract_category_nav_by_regex(mkdocs_text)


# -----------------------------
# 分类收集与渲染
# -----------------------------
def read_category_title(index_file: Path) -> str:
    """读取子目录 `index.md` 的首个 H1 作为分类名称；失败则用目录名。"""
    for line in index_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("# ").strip()
    return index_file.parent.name


# 放在常量区附近
USE_H1_TITLES = False  # ← 设为 False：显示文件名；设为 True：显示 H1（若有）
_H1_RE = re.compile(r"^#\s+(.+)$")
def read_note_title(note_file: Path) -> str:
    """根据开关决定标题来源：False=文件名，True=文内首个 H1 回退到文件名。"""
    if not USE_H1_TITLES:
        return note_file.stem
    try:
        for line in note_file.read_text(encoding="utf-8").splitlines():
            m = _H1_RE.match(line.strip())
            if m:
                return m.group(1).strip()
    except Exception:
        pass
    return note_file.stem


def gather_categories(nav_entries: Sequence[Tuple[str, str]]) -> List[Category]:
    """根据 mkdocs 导航与目录实际情况列出分类。"""
    categories: List[Category] = []
    seen_dirs = set()

    # 先按 mkdocs.yml 的顺序
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

    # 再补全 notes/ 下存在但未在 nav 中出现的分类目录
    remaining_dirs = sorted(
        (
            d
            for d in NOTES_DIR.iterdir()
            if d.is_dir()
            and (d / "index.md").exists()
            and d.name not in seen_dirs
        ),
        key=lambda p: p.name.lower(),
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
    return f"- [{md_escape(title)}]({rel_url(*path.split('/'))})：{description}"


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


# -----------------------------
# “全部笔记索引”生成（一级扫描）
# -----------------------------
def build_all_notes_sections(categories: Sequence[Category]) -> List[str]:
    """按分类生成全部笔记的 Markdown 段落（仅扫描分类目录下的一级 .md 文件）。"""
    sections: List[str] = []

    for category in categories:
        note_files = sorted(
            (
                path
                for path in category.directory.glob("*.md")
                if path.name.lower() != "index.md"
            ),
            key=lambda p: p.name.lower(),
        )

        if not note_files:
            continue

        sections.append(f"## {md_escape(category.title)}")

        for note_file in note_files:
            title = md_escape(read_note_title(note_file))
            rel_path = rel_url(category.directory.name, note_file.name)
            sections.append(f"- [{title}]({rel_path})")

        sections.append("")

    return sections


def render_all_notes(categories: Sequence[Category]) -> str:
    parts: List[str] = [ALL_NOTES_TITLE, "", ALL_NOTES_INTRO, ""]
    sections = build_all_notes_sections(categories)
    parts.extend(sections)
    return "\n".join(parts).rstrip() + "\n"


# -----------------------------
# 分类目录 index.md 生成/更新
# -----------------------------
def build_category_index(category: Category) -> str:
    """为每个分类目录生成 index.md 内容（自动列出该分类下的笔记）。"""
    files = sorted(
        (f for f in category.directory.glob("*.md") if f.name.lower() != "index.md"),
        key=lambda p: p.name.lower(),
    )
    parts: List[str] = [f"# {md_escape(category.title)}", ""]
    parts.append("> 本目录列出该分类下的全部原始笔记，方便在站点导航中快速定位。")
    parts.append("> 本页由脚本自动生成，列出该分类下的所有笔记。")
    parts.append("")
    if not files:
        parts.append("_（暂无条目）_")
        parts.append("")
        return "\n".join(parts).rstrip() + "\n"

    for f in files:
        title = md_escape(read_note_title(f))
        parts.append(f"- [{title}]({rel_url(f.name)})")
    parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def update_category_indexes(categories: Sequence[Category]) -> None:
    for cat in categories:
        index_file = cat.directory / "index.md"
        content = build_category_index(cat)
        write_if_changed(index_file, content)


# -----------------------------
# 主流程
# -----------------------------
def main() -> None:
    # 基本存在性检查
    if not MKDOCS_PATH.exists():
        print(f"[ERROR] mkdocs.yml 不存在：{MKDOCS_PATH}", file=sys.stderr)
        sys.exit(1)
    if not NOTES_DIR.exists():
        print(f"[ERROR] notes 目录不存在：{NOTES_DIR}", file=sys.stderr)
        sys.exit(1)

    mkdocs_text = MKDOCS_PATH.read_text(encoding="utf-8")

    # 1) 提取导航分类
    nav_entries = extract_category_nav(mkdocs_text)

    # 2) 聚合分类（顺序优先遵循 mkdocs.yml，再补 notes/ 中存在但未配置的）
    categories = gather_categories(nav_entries)

    # 3) 生成总首页与“全部笔记”
    category_entries = build_category_entries(categories)
    index_content = render_index(category_entries)
    all_notes_content = render_all_notes(categories)
    write_if_changed(INDEX_PATH, index_content)
    write_if_changed(ALL_NOTES_PATH, all_notes_content)

    # 4) 生成/更新每个分类目录的 index.md
    update_category_indexes(categories)

    print("[OK] 已更新：")
    print(" -", INDEX_PATH)
    print(" -", ALL_NOTES_PATH)
    for c in categories:
        print(" -", c.directory / "index.md")


if __name__ == "__main__":
    main()
