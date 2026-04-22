# Front 目录说明

这是 NexusGate 运维型前端控制面板（实时版）。

## 文件
- `index.html`：页面入口
- `styles.css`：视觉系统与响应式布局
- `js/state.js`：全局状态、工具函数、API 请求封装
- `js/views.js`：6 个页面视图渲染
- `js/main.js`：加载流程、事件绑定、数据刷新
- `design-flow.md`：前端设计流程

## 打开方式
推荐通过后端静态挂载访问：`http://127.0.0.1:8000/admin/ui/`。

## 当前范围
- 已实现 6 个核心页面：Dashboard、上游配置、记忆中心、MemoryPack 预览、请求追踪、客户端接入
- 已对接实时接口：`GET /admin/config`、`GET /admin/memories`、`GET /admin/traces`
- Dashboard 已包含 token 使用量、节省量、节省率可视化（estimate / upstream usage 标识）

## 备注
- 配置写入、连接测试、模型拉取、记忆编辑/回滚仍是 UI 入口，待后端可写 API 后接通。
