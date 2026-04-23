# NexusGate 前端设计方案（方案 A：最快落地）

## 1. 目标

先做一个**能直接用于运维和调试的管理台**，不是聊天前端。

当前核心目标只有五件事：

1. 配置上游 API / Base URL / API Key / 默认模型
2. 管理 `TARGET_*` 与旧版 `LLMAPI_*` 配置
3. 可视化查看、编辑、提取、导出记忆
4. 看清请求路由、trim、fallback、grounding、rewrite 等运行过程
5. 可视化监控 token 使用量与节省量

---

## 2. 产品定位

NexusGate 前端第一版应定位为：

> **运维型全局监控控制面板**
> 用来配置、看记忆、查请求、做调试，并做全局运行态监控。

它要解决的不是“聊天好不好看”，而是下面这些实际问题：

- 当前到底连的是哪个上游？
- Base URL / API Key / 默认模型是什么？
- 这次请求注入了哪些记忆？
- 哪些记忆被 trim 了？
- 最终路由到了哪个 provider / model？
- 有没有 fallback / retry / rewrite / degrade？
- 为什么回答变保守，或者直接说“不知道”？

---

## 3. 技术选型

为了最快落地，推荐：

- **Next.js**
- **React**
- **TypeScript**
- **Tailwind CSS**
- **shadcn/ui**

补充建议：

- 表格：TanStack Table
- 请求缓存：TanStack Query
- 简单状态：Zustand
- JSON / Markdown 编辑：Monaco Editor
- 图表：ECharts

这套组合适合快速做后台管理台，不容易走偏。

---

## 4. 设计原则

### 4.1 配置要看得清

- `TARGET_*` 和 `LLMAPI_*` 必须分开展示
- 必须显示“当前实际生效配置”
- 旧版兼容配置不能偷偷生效，要明确标注

### 4.2 记忆要看得见

- 注入了什么
- 没注入什么
- 为什么没注入
- trim 前后差异

这些都要能直接看到。

### 4.3 调试要能追踪

前端必须能回答：

- 为什么选了这个 provider
- 为什么 fallback
- 为什么 rewrite
- 为什么 unsupported_ratio 高
- 为什么最终输出被降级

### 4.4 操作要可回滚

特别是记忆编辑：

- 支持归档
- 支持禁用
- 支持版本历史
- 支持回滚

---

## 5. 第一版建议页面

第一版先做 6 个页面就够了：

1. 全局监控控制面板（Dashboard）
2. 上游配置
3. 记忆中心
4. MemoryPack 预览
5. 请求追踪
6. 客户端接入

---

## 6. 重点页面设计

### 6.1 全局监控控制面板（Dashboard）

用于日常巡检和全局监控，建议展示：

- 服务状态
- 当前默认上游
- 当前默认模型
- 请求量
- 平均延迟
- fallback 次数
- trim 次数
- rewrite 次数
- unsupported_ratio 趋势
- token 使用量
- token 节省量
- token 节省率

建议控制面板按四个区域布局：

- 顶部：全局状态卡片
- 左侧：请求与路由监控
- 中部：token 使用与节省可视化
- 右侧：异常事件与最近 fallback / rewrite / trim 告警

token 可视化建议至少包含：

- 最近 1h / 24h / 7d 节省 token 趋势
- provider 维度节省量对比
- model 维度节省量对比
- 单次请求节省分布
- 节省量 Top 请求列表

补充建议：

- 图表旁明确统计口径：原始估算 token、实际发送 token、节省 token、节省率
- 区分“请求前估算”与“上游 usage 回传”两种数据来源
- 若上游不返回 usage，标记为 estimate，避免与真实计费混淆

---

### 6.2 上游配置页

这是第一优先级页面。

#### 目标

解决你最关心的：

- API Key
- Base URL
- 默认模型
- 当前到底用的是 `TARGET_*` 还是 `LLMAPI_*`

#### 页面分区

**区域 A：主配置（推荐）**

- `TARGET_PROVIDER`
- `TARGET_BASE_URL`
- `TARGET_API_KEY`
- `DEFAULT_MODEL`

**区域 B：旧版兼容配置**

- `LLMAPI_BASE_URL`
- `LLMAPI_API_KEY`
- `LLMAPI_MODEL_PREFIX`
- `LLMAPI_PROVIDER_PREFIX`

#### 核心功能

- 查看配置
- 编辑配置
- 保存配置
- 从 `.env` 导入
- 导出 `.env`
- 测试连接
- 拉取模型列表
- 显示连接延迟
- 将 `LLMAPI_*` 迁移到 `TARGET_*`

---

### 6.3 记忆中心

这是第二优先级页面。

#### 建议结构

**左侧：分层树**

- L0
- constraints
- procedures
- continuity
- facts

**中间：记忆列表**

建议列：

- id
- title
- layer
- kind
- source
- session_id
- tags
- confidence
- updated_at
- status

**右侧：详情面板**

- 完整内容
- 原始 JSON
- 来源
- 命中次数
- 最近命中时间
- 历史版本

#### 核心功能

- 搜索
- 筛选
- 单条编辑
- 批量编辑
- 合并重复记忆
- 归档
- 禁用
- 回滚
- 导出 Markdown / JSON

---

### 6.4 MemoryPack 预览

这个页面很重要，用来解释：

> 一次请求在发给模型前，记忆到底是怎么拼起来的。

建议展示：

- 命中的记忆条目
- 结构化 MemoryPack
- provider 渲染后的结果
- trim report
- trim 前后差异
- 哪些条目被保留
- 哪些条目被裁剪

---

### 6.5 请求追踪

这个页面决定 NexusGate 是否真的“可运营”。

建议展示：

- request_id
- session_id
- provider
- model
- latency
- fallback
- trim
- rewrite
- unsupported_ratio
- status

详情页建议包含：

- original input
- route decision
- selected provider / model
- fallback chain
- memory hit summary
- trim report
- grounding summary
- rewrite diff
- final response

---

### 6.6 Grounding / 安全调试

建议单独做一页，重点看：

- grounding_mode
- grounding_policy
- evidence blocks
- citation blocks
- unsupported claims
- unsupported_ratio
- rewrite 前后差异
- 是否触发 degrade

这个页面主要用来回答：

- 为什么模型这次突然保守
- 为什么说“不知道”
- 为什么某些内容被删掉

---

### 6.7 客户端接入页

帮助本地工具快速接入。

建议提供：

- OpenAI SDK 示例
- curl 示例
- Aider 接入说明
- Codex 接入说明
- Claude 接入说明
- 当前 Base URL 状态
- API Key 状态
- 一键复制配置

---

### 6.8 系统设置页

建议包含：

- `.env` 编辑
- 密钥管理
- 存储路径
- 调试开关
- 导入 / 导出配置

---

## 7. MVP 范围

如果只做最小可用版本，建议先上线这 5 个：

1. 上游配置
2. 记忆中心
3. MemoryPack 预览
4. 请求追踪
5. Markdown 导出

这样已经能覆盖：

- API / Base URL 配置
- `LLMAPI_*` 兼容展示
- 记忆可视化
- 记忆编辑
- 记忆导出
- 注入结果预览

---

## 8. 推荐后端接口

为了让前端真正可用，建议补 admin API。

### 配置

- `GET /admin/config`
- `PUT /admin/config`
- `POST /admin/config/test`
- `POST /admin/config/import-env`
- `POST /admin/config/export-env`
- `POST /admin/config/migrate-legacy`
- `GET /admin/config/models`

### 记忆

- `GET /admin/memories`
- `GET /admin/memories/:id`
- `POST /admin/memories`
- `PUT /admin/memories/:id`
- `DELETE /admin/memories/:id`
- `POST /admin/memories/batch`
- `POST /admin/memories/rollback`

### 预览 / 导出 / Trace

- `POST /admin/memory-pack/preview`
- `POST /admin/memories/extract`
- `POST /admin/export/md`
- `GET /admin/traces`
- `GET /admin/traces/:id`

---

## 9. 分阶段实施

### Phase 1：先做可用

- 上游配置
- 记忆中心
- MemoryPack 预览
- Markdown 导出
- 基础 Dashboard

### Phase 2：增强可观测性

- 请求追踪
- fallback 可视化
- trim report 可视化
- grounding 详情
- rewrite diff

### Phase 3：高级能力

- 记忆提取工作台
- 去重与合并
- 历史版本 / 回滚
- 多环境配置
- RBAC

---

## 10. 推荐前端管理台能力

如果你准备为 NexusGate 做前端，建议至少覆盖以下模块。

### 10.1 上游配置中心

目标：解决你当前最关心的“LLMAPI 的 API / Base URL 配置”。

建议字段：

- 配置名称
- Provider 类型
- Base URL
- API Key
- 默认模型
- 是否启用
- 是否作为默认上游
- 兼容模式（Target / LLMAPI Legacy）
- 连接测试按钮

建议行为：

- 新建配置默认保存为 `TARGET_*`
- 识别到 `LLMAPI_*` 时，以“旧版兼容配置”展示
- 支持 `.env` 导入 / 导出
- 支持连接测试、延迟检测、模型列表读取

---

### 10.2 记忆结构可视化

建议拆成四块：

1. **MemoryPack 预览**
   - 看本次请求实际命中的记忆
   - 看 provider 渲染结果
   - 看 trim 前后差异

2. **分层记忆浏览器**
   - 按 L0 / constraints / procedures / continuity / facts 展示
   - 支持搜索、筛选、排序
   - 支持按 session / topic / source 查看

3. **命中证据面板**
   - 展示回答依赖了哪些记忆
   - 展示 citations / evidence blocks
   - 展示 unsupported_ratio 和 rewrite

4. **历史演化视图**
   - 展示记忆如何从短期进入长期
   - 展示哪些被保留、裁剪、归档

---

### 10.3 记忆编辑器

建议支持：

- 单条编辑
- 批量标签修改
- 升/降级记忆层级
- 合并重复记忆
- 标记失效
- 回滚历史版本
- 锁定高置信事实
- 设置注入策略

---

### 10.4 记忆提取工作台

建议做成三栏：

- 左侧：原始文本
- 中间：候选记忆
- 右侧：写入结果

建议流程：

- 从对话提取
- 从日志提取
- 从代码仓库提取
- 人工审核后写入正式记忆库
- 支持置信度阈值与去重建议

---

### 10.5 Markdown 导出

建议支持：

- 导出某个 session 的记忆摘要
- 导出某个主题的 facts / procedures / constraints
- 导出某次 MemoryPack 结果
- 导出审计报告
- 导出系统配置快照

---

### 10.6 路由与回退可观测性

建议展示：

- 命中的 provider / model
- fallback chain
- same-provider retry
- context overflow
- rerender-only recovery
- 每次尝试耗时
- provider 健康趋势
- 错误类型分布

---

### 10.7 幻觉抑制 / grounding 调试台

建议展示：

- grounding_mode
- grounding_policy
- evidence blocks
- citation block
- unsupported_ratio
- rewrite / degrade
- 最终输出与原始输出差异

---

### 10.8 本地客户端接入页

建议提供：

- OpenAI SDK
- Aider
- Codex
- Claude
- 配置同步

---

## 11. 推荐前端信息架构

建议菜单结构：

- **概览 Dashboard**
  - 服务状态
  - 请求量
  - 错误率
  - fallback 次数

- **上游配置**
  - TARGET / LLMAPI 配置管理
  - API Key 管理
  - 连通性测试

- **记忆中心**
  - 记忆列表
  - 分层视图
  - 编辑器
  - 提取工作台
  - Markdown 导出

- **请求追踪**
  - 请求详情
  - 命中记忆
  - trim report
  - 路由决策
  - fallback 事件

- **安全与 grounding**
  - unsupported claims
  - rewrite 记录
  - 引用证据
  - 风险策略

- **客户端接入**
  - OpenAI SDK
  - Aider
  - Codex
  - Claude
  - 配置同步

- **系统设置**
  - `.env` 编辑
  - 密钥管理
  - 存储路径
  - 调试开关

---

## 12. 最终建议

第一版不要做复杂聊天界面。

优先把下面这些做好：

- 上游配置
- 记忆可视化
- 记忆编辑 / 提取 / 导出
- 请求追踪
- grounding 调试
- 客户端接入
- 系统设置

这才是 NexusGate 最快形成可用产品的路径。