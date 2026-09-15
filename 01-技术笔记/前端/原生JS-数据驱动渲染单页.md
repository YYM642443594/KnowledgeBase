---
title: 原生JS-数据驱动渲染单页
created: 2026-09-15
updated: 2026-09-15
tags: [JavaScript, 前端]
source: 原创
---

# 原生JS-数据驱动渲染单页

## 概述

本文档总结在不引入框架、不使用构建工具的前提下，用原生 JavaScript 开发静态单页（以知识库说明网页 demo_zsk 为例）时的代码组织方式：数据与渲染分离、事件委托、搜索过滤。适用于内容会更新、但规模较小的展示型单页。

## 正文

核心结论：**内容全部放进一个全局数据对象，页面只写「读数据 → 生成 HTML → 一次性挂载」的渲染函数**。内容更新只改数据文件，渲染逻辑不动。

### 代码组织：为什么不用 ES Modules

目标场景是「双击 index.html 打开」（`file://` 协议）。ES Modules 在 `file://` 下因浏览器 CORS 策略无法跨脚本 `import`，控制台直接报错。因此采用普通脚本 + 全局变量：

```javascript
// data.js —— 只放数据，挂载到全局
var KB_DATA = {
  meta: { name: "个人知识库", /* ... */ },
  categories: [
    { id: "01-技术笔记", icon: "💻", desc: "…", docs: [/* … */] }
  ]
};

// main.js —— 只放渲染逻辑，IIFE 避免污染全局
(function () {
  "use strict";
  var data = window.KB_DATA;
  // renderMeta(); renderTree(); …
})();
```

脚本引入顺序保证依赖：`<script src="js/data.js">` 在 `<script src="js/main.js">` 之前。

### 渲染：字符串拼接 + 转义，代替逐个 createElement

小规模列表用字符串拼 HTML 后一次性 `innerHTML` 赋值，比循环 `createElement/appendChild` 简洁得多。注意两点：

1. 所有动态内容先经过 `esc()` 转义，防止内容里的 `< > & " '` 破坏结构；
2. 拼接结果整体赋一次 `innerHTML`，浏览器只解析一次，性能足够。

```javascript
function esc(str) {
  return String(str).replace(/[&<>"']/g, function (ch) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
  });
}
```

### 交互：事件委托与全量重渲染

- 搜索框监听 `input` 事件，每次输入调用 `renderDocs(keyword)` 全量重绘列表——几百条以内完全没有性能问题，不需要增量更新或虚拟 DOM；
- 全局快捷键（如 `/` 聚焦搜索框）直接绑在 `document` 的 `keydown` 上，用 `document.activeElement` 排除「正在输入」的情况，这是事件委托思想的典型应用；
- 重渲染函数保持**纯函数化**：传入关键词 → 输出 HTML，不持有中间状态，空态提示（「没有匹配的文档」）也作为渲染分支处理，不留悬空 DOM。

### 关键点

- 数据文件与渲染文件分离，是零构建前提下最小可行的「数据驱动」；
- `file://` 直接打开是硬需求时，放弃 ES Modules，用普通脚本 + 全局对象；
- 动态拼 HTML 必须转义；一次性 `innerHTML` 优于逐节点创建；
- 简单场景下全量重渲染 + 事件委托足够，不必提前优化。

## 总结

数据驱动的组织方式让「更新内容」和「修改逻辑」彻底解耦，配合零依赖可直接打开的形态，适合个人工具型页面。若数据量增长到数千条或需要路由，再考虑引入构建工具与框架，当前模式即到为止。

## 参考

- MDN：[innerHTML](https://developer.mozilla.org/zh-CN/docs/Web/API/Element/innerHTML)、[事件委托（事件冒泡）](https://developer.mozilla.org/zh-CN/docs/Learn/JavaScript/Building_blocks/Events#%E4%BA%8B%E4%BB%B6%E5%A7%94%E6%89%98)
