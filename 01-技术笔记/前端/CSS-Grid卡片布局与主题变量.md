---
title: CSS-Grid卡片布局与主题变量
created: 2026-09-15
updated: 2026-09-15
tags: [CSS, Grid, 前端]
source: 原创
---

# CSS-Grid卡片布局与主题变量

## 概述

本文档总结纯 CSS 实现响应式卡片网格与主题色管理两个实用模式（源自知识库说明网页 demo_zsk 的实践）：`repeat(auto-fit, minmax())` 免媒体查询网格、CSS 自定义属性主题。适用于后台首页、导航页、文档站等卡片式布局场景。

## 正文

核心结论：**卡片网格用 `grid-template-columns: repeat(auto-fit, minmax(250px, 1fr))` 一行解决响应式；主题色全部收敛到 `:root` 的自定义属性，换主题只改一处。**

### 免媒体查询的响应式网格

```css
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 14px;
}
```

- `minmax(250px, 1fr)`：每列最窄 250px、最宽均分剩余空间；
- `auto-fit`：容器够宽放几列放几列，窄了自动换行，**不需要写任何 @media 查询**；
- 与 `auto-fill` 的区别：`auto-fill` 会保留空轨道，`auto-fit` 会把空轨道折叠进 `1fr`，卡片少的场景（如 3 张卡占满整行）用 `auto-fit` 效果更好。

### 自定义属性做主题

```css
:root {
  --bg: #f6f7f9;
  --surface: #ffffff;
  --border: #e3e6ea;
  --text: #1f2933;
  --text-soft: #5f6b7a;
  --accent: #2563eb;
  --accent-soft: #eff4ff;
  --radius: 10px;
}

.cat-count {
  background: var(--accent-soft);
  color: var(--accent);
  border-radius: var(--radius);
}
```

要点：

- 颜色语义化命名（`--surface` 面、`--text-soft` 次要文字），而不是 `--blue` 这类色值命名，换主题时语义不变；
- 同一色系派生色（`--accent-soft`）与主色成对定义，保证浅色背景与文字色始终配套；
- 圆角、阴影等尺寸值同样收入变量，整站风格一处调整。

### 卡片微交互

```css
.cat-card { transition: transform 0.15s ease, box-shadow 0.15s ease; }
.cat-card:hover { transform: translateY(-2px); }
.cat-card.dimmed { opacity: 0.4; }
```

- hover 只动 `transform` 与 `opacity`（合成层属性），不触发布局重排；
- `dimmed` 这类状态类由 JS 按搜索结果增删，CSS 只负责状态外观，职责分离。

### 中文场景字体栈

```css
font-family: -apple-system, "Segoe UI", "PingFang SC", "Hiragino Sans GB",
             "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
```

西文字体在前、中文字体在后，各平台自动回退：macOS 命中苹方、Windows 命中微软雅黑、Linux 命中 Noto 黑体。

### 关键点

- `repeat(auto-fit, minmax())` 是卡片网格首选，免媒体查询；
- 主题值收敛到 `:root` 自定义属性，语义化命名 + 派生色成对定义；
- 动画只碰 `transform/opacity`；状态类由 JS 控制、CSS 呈现。

## 总结

这两个模式覆盖了展示型页面的绝大部分布局与主题需求，全程零依赖。后续做暗色主题时，只需新增一组变量值（如 `[data-theme="dark"]` 选择器下重定义），组件样式无需改动。

## 参考

- MDN：[grid-template-columns](https://developer.mozilla.org/zh-CN/docs/Web/CSS/grid-template-columns)、[使用 CSS 自定义属性](https://developer.mozilla.org/zh-CN/docs/Web/CSS/Using_CSS_custom_properties)
