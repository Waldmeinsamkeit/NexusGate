# Front 目录说明

这是 NexusGate 管理台前端原型（静态版）。

## 文件
- `index.html`：页面入口
- `styles.css`：视觉系统与响应式布局
- `app.js`：导航、页面渲染、示例数据
- `design-flow.md`：前端设计流程

## 打开方式
直接用浏览器打开 `front/index.html`。

## 当前范围
- 已实现 6 个核心页面视图（单页切换）
- 数据为演示数据，尚未接后端 admin API

## 下一步建议
把 `app.js` 中的 mock 数据替换为：
- `GET /admin/config`
- `GET /admin/memories`
- `GET /admin/traces`
