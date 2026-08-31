/*
 * MathJax 配置（与 pymdownx.arithmatex (generic: true) 配合使用）。
 * 加载顺序：本文件需先于 MathJax 主体脚本加载。
 * 由 mkdocs-material 内置的 document$ 主题事件驱动，保证每次内容更新后重新排版公式。
 */
window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true,
    processEnvironments: true
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex"
  }
};

document$.subscribe(() => {
  MathJax.startup.output.clearCache();
  MathJax.typesetClear();
  MathJax.texReset();
  MathJax.typesetPromise();
});