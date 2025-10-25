# Stock Mindmap

个人笔记与思路整理仓库，并提供 MkDocs 生成的在线预览站点。

## 目录结构

- `notes/`：全部原始 Markdown 笔记，保持分类目录不变。
  - `index.md` 用于站点首页。
  - 各子目录的 `index.md` 自动列出该分类下的笔记清单。
- `research/`：深度研究（AI、经济等）。
- `prompts/`：各类 Prompt 和模板。
- `.github/workflows/`：GitHub Actions 配置，负责构建与发布文档站点。
- `mkdocs.yml`：MkDocs 站点配置文件。

## 快速开始

1. 安装依赖：
   ```bash
   pip install mkdocs mkdocs-material
   ```
2. 本地预览：
   ```bash
   mkdocs serve
   ```
   启动后访问 <http://127.0.0.1:8000/>。
3. 构建静态文件：
   ```bash
   mkdocs build
   ```

## GitHub Pages 发布

1. 提交更新后推送至默认分支，GitHub Actions 会自动运行 `Docs` 工作流，结果将部署到 `gh-pages` 分支。
2. 首次启用时，请在仓库 **Settings → Pages** 中将来源设置为 `gh-pages` 分支的根目录。
3. 部署完成后，访问：`https://<your-github-username>.github.io/stock_mindmap/`。

## 预览链接

- 在线站点（示例）：`https://<your-github-username>.github.io/stock_mindmap/`
- 如果尚未配置 GitHub Pages，可先在本地通过 `mkdocs serve` 预览。

这个 repo 用于记录学习、研究和投资思考，同时提供更友好的在线阅读体验。
