## 环境现状

- 项目入口为 `nexus_gate_core.py:1-3`，实际应用由 `nexusgate.app:create_app()` 构建。
- 当前网关是一个 FastAPI + LiteLLM 聚合层，已经对三类接口做统一收口：
  - OpenAI Chat Completions：`nexusgate/app.py:103-127`
  - OpenAI Responses：`nexusgate/app.py:129-180`
  - Anthropic Messages：`nexusgate/app.py:182-209`
- 现有“记忆”并非独立 skill runtime，而是一个在请求前后被动调用的 `MemoryManager`：
  - 初始化：`nexusgate/app.py:51-58`
  - 请求前召回：`nexusgate/app.py:78-90`
  - 请求后归档/蒸馏：
    - chat completions：`nexusgate/app.py:99-101`
    - responses：`nexusgate/app.py:174-179` 或 passthrough 回调 `157-162`
- 现有五层记忆只有“命名/文件结构”意义上的雏形，不是完整分层 pipeline：
  - `nexusgate/memory/layers.py:13-40` 仅有 `BaseMemoryLayer` 和 5 个空子类骨架。
  - 真正工作的逻辑都集中在 `nexusgate/memory/manager.py`。

---

## 关键发现

### 1. 当前记忆注入链路非常直接：在上游请求前拼一个 system context

关键路径：

1. 提取会话与最新用户问题  
   - `session_id = _resolve_session_id(req)`：`nexusgate/app.py:79`
   - `user_query = _extract_latest_user_query(req.messages)`：`nexusgate/app.py:80`

2. 拉取记忆头部  
   - `memory_context = memory.get_memory(session_id, user_query)`：`nexusgate/app.py:82`

3. 把记忆直接塞进 system message  
   - 元规则：`L0_META_RULES`：`nexusgate/app.py:20-23`
   - `<nexus_context>` 注入：`nexusgate/app.py:83-87`

4. 再把增强后的 messages 交给 LiteLLM  
   - `litellm.completion(**kwargs)`：`nexusgate/app.py:91-97`

这说明 **“session memory recall” 的最小接入点已经天然存在**：  
`MemoryManager.get_memory()` / `build_memory_header()` 就是召回 skill 的等价插槽。

---

### 2. 当前 MemoryManager 实际只实现了 L0/L1/L2/L4 的部分能力，L3 基本未落地

`nexusgate/memory/manager.py` 中可确认：

- L0：SOP 文本加载并摘取前 12 行进 header  
  - `load_l0_sop()`：`157-158`
  - `build_memory_header()`：`199-207`
- L1：全局索引文件
  - `l1_path`：`110`
  - `load_l1_index()`：`170-171`
  - L1 upsert 同步文件：`253-256`
- L2：事实层
  - `l2_path`：`111`
  - `load_l2_facts()`：`173-181`
  - L2 upsert 同步文件：`256-257`
- L3：只有目录与 `load_l3_doc()`，没有自动写入、分类、召回专门策略
  - `l3_dir`：`104-105`
  - `load_l3_doc()`：`183-188`
- L4：会话归档最完整
  - `archive_session()`：`282-293`
  - `distill_to_l4()`：`294-295`
  - `start_memory_update()` 先归档：`297-300`
  - JSONL 持久化：`330-341`
  - 重启后回灌：`343-368`

因此，**当前所谓“五层记忆嵌入”更准确说是：**
- 注入时：L0 + L1 + 检索到的 L1/L2/L3/L4
- 写回时：主要写 L4，成功时补少量 L2/L1 指针
- L3 / layer objects 还没有成为真正的编排中心

---

### 3. 现有召回模型更像“统一检索头”，不是“session memory recall skill”

当前召回由 `build_memory_header()` 完成：`199-207`

其结构是：

- L0 摘要
- `<memory_index>`：L1 全量索引文件
- `<relevant_memory>`：从 store 查询 `["L1", "L2", "L3", "L4"]`

检索入口：
- `query_memory()`：`190-197`
- 底层查询：
  - Chroma 模式：`61-73`
  - fallback 内存列表模式：`75-86`

特点：
- 优点：非常容易插入，改动面小。
- 局限：
  1. 没有把“本 session 最近上下文”与“跨 session 历史证据”显式区分。
  2. 没有输出“verified facts / unknowns / next step snapshot”的结构化结果。
  3. 对 session recall 的排序较粗糙，fallback 里只是子串命中 `score=2/1`：`82-84`。
  4. 没有单独的 recall policy，如“优先最近相关 session，再补全局事实”。

这与已读的 “Session Memory Recall” skill 成功标准有明显映射关系：  
它要求识别 prior session evidence、重建可信摘要、区分 verified facts / unknowns、给 continuation-ready snapshot。  
而当前 NexusGate 只做到“塞一个相关记忆块”，还没做到“结构化 recall skill”。

---

### 4. Responses API 是最适合接入 memory skill 的主通道

`/v1/responses` 处理逻辑比 chat completions 更像 agent runtime：

- 可 raw passthrough 到第三方兼容上游：`151-163`
- 注释明确强调保留 tool-calling 语义：`149-150`
- 请求完成后通过 `start_memory_update()` 做归档/写回：`174-179`

这意味着如果要支持“工具式 memory skill / session recall 能力”，**最合适的主接入面是 `responses_api()`**，原因：

1. Responses 语义更适配多轮工具链和 agent loop。
2. passthrough 分支已经预留了“完成回调”钩子。
3. 未来若把 memory 做成显式工具，而不是静态 system 注入，Responses API 更容易承载。

---

### 5. 最小改动接入方案：先把 session recall 做成“结构化 header builder”，不要先碰 layers.py

#### 推荐最小方案（Phase 1）

只改动两个核心点：

1. 在 `MemoryManager` 内新增一个更明确的 session recall 构建函数  
   例如：
   - `build_session_recall(session_id, query) -> str`
   - 或把 `build_memory_header()` 重构为输出更结构化的块

2. 在 `app.py::_run_completion()` 继续沿用当前 system 注入方式  
   仅把：
   - `memory.get_memory(session_id, user_query)`  
   替换为  
   - 更结构化的 recall 输出

#### 为什么这是最小改动
- 不改 API 面。
- 不改 LiteLLM 调用协议。
- 不改现有持久化。
- 不依赖 `layers.py` 先成熟。
- chat / responses / anthropic 三个入口可自动收益，因为它们都走 `_run_completion()`。

#### 建议的输出结构
可把当前 `<nexus_context>` 内文本升级为：

```xml
<nexus_context>
  <verified_facts>
  ...
  </verified_facts>
  <relevant_prior_sessions>
  ...
  </relevant_prior_sessions>
  <working_assumptions>
  ...
  </working_assumptions>
  <unknowns>
  ...
  </unknowns>
  <continuation_snapshot>
  ...
  </continuation_snapshot>
</nexus_context>
```

其中：
- `verified_facts`：优先来自 L2，辅以有 evidence 的 L4 片段
- `relevant_prior_sessions`：来自 L4，按 session/query 相关性排序
- `working_assumptions`：仅在代码可推导但未证实时输出
- `unknowns`：明确列缺失信息
- `continuation_snapshot`：一句话概括“上次做到哪、下一步是什么”

这最贴近 Session Memory Recall skill 的目标，而且仍然只是“prompt shaping”。

---

### 6. 若要进一步演进，再把 memory skill 从“隐式注入”升级为“显式能力”

#### Phase 2：在 `responses_api()` 中引入显式 recall skill
可选方式：

- 方式 A：预处理型  
  在请求进入上游前，先执行 recall 生成结构化 memory block，再并入 input/messages。
- 方式 B：工具型  
  对 agent 暴露一个内部工具，例如 `recall_session_memory(query, session_id)`，由模型按需调用。

更推荐先 A 后 B：
- A 的确定性更高，兼容现有实现。
- B 需要设计工具 schema、tool result 格式、回灌链路，改动更大。

---

### 7. `layers.py` 当前不适合作为第一落点

虽然文件名显示有五层抽象：`nexusgate/memory/layers.py:13-40`，但现实是：

- `enrich()` 没有被 app 主链路调用
- `persist()` 没有接入写回路径
- 五个 layer 子类都没有任何策略实现

所以如果现在把“session memory recall / memory skill”硬塞进 `layers.py`：
- 会引入第二套抽象，但主流程仍在 `MemoryManager`
- 会产生“代码结构看似更优雅，实际调用不到”的问题

**结论：第一阶段应以 `MemoryManager` 为中心接入。**
等 recall 逻辑稳定，再考虑把 manager 中的策略下沉到各 layer。

---

### 8. 当前写回策略能支撑 session recall，但证据质量一般

当前写回：

- 所有会话都进 L4 归档：`282-295`
- 结果看起来成功时，额外写：
  - L2：`会话结果: ...`：`301-308`
  - L1：`recent_success -> L2`：`309-315`

优点：
- session recall 至少有材料可取，尤其是 L4。
- 重启后还能从 `archive.jsonl` 回灌：`343-368`

问题：
1. L2 写入内容太泛化，通常只是“会话结果: ...”，未提炼成稳定事实。
2. L1 指针内容固定为 `recent_success -> L2`，信息量很低。
3. `validate_memory_write()` 的 evidence 校验较弱，更多是关键词门禁：`160-168`。
4. 没有把“上次关键文件/关键命令/失败原因/下一步”抽成 continuation snapshot。

这意味着：  
**接入 recall skill 时，最先收益的不是改检索，而是改“L4 → 可复用摘要”的提炼格式。**

---

## 可插入记忆 skill 的位置

### 位置 A：`nexusgate/app.py:_run_completion()` 前置召回
- 行号：`78-90`
- 作用：统一覆盖 chat / responses / anthropic 三类入口
- 适合：最小改动的“隐式 recall”
- 建议优先级：最高

### 位置 B：`nexusgate/app.py:responses_api()` 中 passthrough 前
- 行号：`143-165`
- 作用：在保留 Codex/tool-calling 语义前提下插入 recall
- 适合：agent 化、工具化演进
- 建议优先级：中高

### 位置 C：`nexusgate/memory/manager.py:build_memory_header()` / `get_memory()`
- 行号：`199-213`
- 作用：当前真正的召回构造器
- 适合：把 recall skill 逻辑集中在 memory 侧
- 建议优先级：最高

### 位置 D：`nexusgate/memory/manager.py:start_memory_update()`
- 行号：`297-315`
- 作用：改进 session 结束后的摘要蒸馏
- 适合：提升 recall 质量
- 建议优先级：最高（与 C 配套）

### 位置 E：`nexusgate/memory/layers.py`
- 行号：`13-40`
- 作用：未来抽象层
- 适合：第二阶段重构
- 建议优先级：低

---

## 最小改动接入方案

### 方案目标
在不改外部 API、不引入新基础设施、不重做 layers 抽象的前提下，把现有 memory 注入升级成“session memory recall”。

### 建议步骤

1. **增强写回摘要**
   - 在 `start_memory_update()` 中，不只写原始 L4 和“会话结果”。
   - 额外提炼：
     - 本次确认的稳定事实
     - 改过/涉及的文件
     - 已完成事项
     - 未完成事项/下一步
   - 仍然落在 L2/L4，先不引入复杂新层。

2. **增强召回组织**
   - 在 `build_memory_header()` 中分块输出：
     - verified facts
     - prior relevant sessions
     - unknowns
     - continuation snapshot

3. **调整检索策略**
   - 查询时优先：
     1. 当前 `session_id` 的 L4/L2
     2. 其他 session 的高相关 L4
     3. 全局 L1/L2
   - 而不是简单把四层混查后平铺。

4. **保留现有 `_run_completion()` 调用方式**
   - 这样三类 API 自动继承 recall 能力。

### 预期收益
- 代码改动集中在 `MemoryManager`，风险最小。
- 现有测试可以较容易扩展。
- 可在后续平滑演进成显式 memory tool。

---

## 风险 / 不确定点

1. **SOP 实际内容未完整展开**
   - 已知系统提示要求在读取记忆/SOP时关注靠后关键点，但当前可见代码里 `MemoryManager` 只截取 SOP 前 12 行：`199-200`。
   - 如果真实 SOP 后半段包含重要写回规则，当前实现可能根本没有把这些规则传给模型。

2. **Responses passthrough 分支可能绕开一部分增强逻辑**
   - 虽然完成后有 `on_complete` 回调：`157-162`
   - 但请求前的 memory 注入方式与 `_run_completion()` 分支并不完全一致，后续若做显式 skill，要检查 passthrough 前是否有统一增强入口。

3. **`_extract_latest_user_query()` 可能不足以表达复杂 input**
   - 见 `nexusgate/app.py:257-260` 及 manager 内 `224-232`
   - 对多模态/工具消息/结构化 input 的 query 抽取可能不稳定，影响 recall 相关性。

4. **测试覆盖目前只验证基础行为，不验证 recall 质量**
   - `tests/test_memory_manager.py` 只验证：
     - evidence 校验
     - header 包含 section
     - enrich 注入
     - L4 archive / reload
   - 没有验证“跨 session 召回排序、verified/unknown 分离、continuation snapshot”。
   - 接入 recall skill 后需新增针对性测试。

5. **`layers.py` 与 `manager.py` 双轨结构存在未来维护风险**
   - 现在真实逻辑在 manager，抽象名义在 layers。
   - 若后续继续叠功能而不收敛，容易出现“看上去五层，实际上单体 manager”的分裂。

---

## 结论

对于 NexusGate，这个需求最合理的理解不是“从零接一个 memory skill 系统”，而是：

**把现有 `MemoryManager.get_memory()` 升级为更像 Session Memory Recall 的结构化召回器，并把 `start_memory_update()` 升级为更利于 continuation 的摘要蒸馏器。**

最小改动主线应放在：

- `nexusgate/memory/manager.py:199-213`
- `nexusgate/memory/manager.py:297-315`
- `nexusgate/app.py:78-90`

而不是优先改：

- `nexusgate/memory/layers.py:13-40`

因为当前真正被主链路调用的就是 `MemoryManager`，这里改动最小、收益最大、兼容现有三类 API 入口。若后续需要把 recall 变成显式 agent skill，再优先从 `responses_api()` 演进。