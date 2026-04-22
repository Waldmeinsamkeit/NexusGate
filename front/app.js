const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", title: "Dashboard", desc: "查看服务状态、请求趋势与关键风险指标。" },
  { id: "upstream", label: "上游配置", title: "上游配置", desc: "分区展示 TARGET_* 与 LLMAPI_*，并显示当前实际生效配置。" },
  { id: "memory", label: "记忆中心", title: "记忆中心", desc: "按层级浏览记忆，支持搜索筛选、详情和导出入口。" },
  { id: "pack", label: "MemoryPack 预览", title: "MemoryPack 预览", desc: "解释记忆注入、trim 前后差异与 provider 渲染结果。" },
  { id: "trace", label: "请求追踪", title: "请求追踪", desc: "追踪 route/fallback/trim/grounding/rewrite 全链路。" },
  { id: "clients", label: "客户端接入", title: "客户端接入", desc: "提供 OpenAI SDK、curl 与本地接入指引。" },
];

const state = {
  apiBase: localStorage.getItem("nexusgate_api_base") || inferDefaultApiBase(),
  apiKey: localStorage.getItem("nexusgate_api_key") || "",
  config: null,
  health: null,
  memories: [],
  traces: [],
  errors: {},
  activeView: "dashboard",
  selectedMemoryId: "",
  selectedTraceId: "",
  memoryLayerFilter: "ALL",
  memorySearch: "",
};

const navRoot = document.getElementById("nav");

function inferDefaultApiBase() {
  if (location.protocol === "http:" || location.protocol === "https:") {
    return location.origin;
  }
  return "http://127.0.0.1:8000";
}

function escapeHtml(text) {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function toPrettyJson(value) {
  return escapeHtml(JSON.stringify(value ?? {}, null, 2));
}

function formatTs(sec) {
  if (!sec) return "";
  const d = new Date(Number(sec) * 1000);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("zh-CN", { hour12: false });
}

function short(text, len = 64) {
  const raw = String(text || "").trim();
  if (!raw) return "";
  return raw.length > len ? `${raw.slice(0, len)}...` : raw;
}

async function apiFetch(path) {
  const url = `${state.apiBase}${path}`;
  const headers = { "Content-Type": "application/json" };
  if (state.apiKey.trim()) {
    headers.Authorization = `Bearer ${state.apiKey.trim()}`;
  }
  const resp = await fetch(url, { headers });
  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`${resp.status} ${resp.statusText}: ${body.slice(0, 220)}`);
  }
  return resp.json();
}

function activeNavMeta() {
  return NAV_ITEMS.find((item) => item.id === state.activeView) || NAV_ITEMS[0];
}

function renderNav() {
  navRoot.innerHTML = NAV_ITEMS.map((item) => (
    `<button class="nav-btn ${item.id === state.activeView ? "active" : ""}" data-view="${item.id}">${item.label}</button>`
  )).join("");
}

function switchView(viewId) {
  state.activeView = viewId;
  document.querySelectorAll(".view").forEach((node) => node.classList.remove("active"));
  document.getElementById(`view-${viewId}`)?.classList.add("active");

  const meta = activeNavMeta();
  document.getElementById("page-title").textContent = meta.title;
  document.getElementById("page-desc").textContent = meta.desc;
  renderNav();
}

function renderConnectionPanel() {
  const panel = document.getElementById("connection-panel");
  panel.innerHTML = `
    <div class="connection-row">
      <p class="muted">API 连接</p>
      <input id="conn-api-base" value="${escapeHtml(state.apiBase)}" placeholder="http://127.0.0.1:8000" />
      <input id="conn-api-key" value="${escapeHtml(state.apiKey)}" placeholder="local api key" />
      <button id="conn-save">保存连接</button>
      <button class="primary" id="conn-reload">刷新数据</button>
    </div>
    <p id="conn-status" class="status-line">连接尚未验证</p>
  `;

  panel.querySelector("#conn-save")?.addEventListener("click", () => {
    state.apiBase = panel.querySelector("#conn-api-base")?.value.trim() || inferDefaultApiBase();
    state.apiKey = panel.querySelector("#conn-api-key")?.value.trim() || "";
    localStorage.setItem("nexusgate_api_base", state.apiBase);
    localStorage.setItem("nexusgate_api_key", state.apiKey);
    setConnStatus("连接参数已保存", false);
  });

  panel.querySelector("#conn-reload")?.addEventListener("click", async () => {
    await refreshDataAndRender();
  });
}

function setConnStatus(message, isError) {
  const node = document.getElementById("conn-status");
  if (!node) return;
  node.textContent = message;
  node.style.color = isError ? "var(--danger)" : "var(--muted)";
}

async function loadConfig() {
  try {
    state.config = await apiFetch("/admin/config");
    state.health = state.config.health;
    state.errors.config = "";
  } catch (err) {
    state.errors.config = String(err.message || err);
  }
}

async function loadMemories() {
  try {
    const q = state.memorySearch.trim();
    const layer = state.memoryLayerFilter === "ALL" ? "" : `&layers=${encodeURIComponent(state.memoryLayerFilter)}`;
    const query = q ? `&query=${encodeURIComponent(q)}` : "";
    const data = await apiFetch(`/admin/memories?limit=120${layer}${query}`);
    state.memories = data.items || [];
    if (!state.selectedMemoryId && state.memories[0]) {
      state.selectedMemoryId = state.memories[0].memory_id;
    }
    state.errors.memories = "";
  } catch (err) {
    state.errors.memories = String(err.message || err);
  }
}

async function loadTraces() {
  try {
    const data = await apiFetch("/admin/traces?limit=80");
    state.traces = data.items || [];
    if (!state.selectedTraceId && state.traces[0]) {
      state.selectedTraceId = state.traces[0].request_id;
    }
    state.errors.traces = "";
  } catch (err) {
    state.errors.traces = String(err.message || err);
  }
}

async function loadAllData() {
  await Promise.all([loadConfig(), loadMemories(), loadTraces()]);
  const hasErr = state.errors.config || state.errors.memories || state.errors.traces;
  setConnStatus(hasErr ? "接口请求失败，请检查 API Base/API Key 或后端服务状态" : "接口连接正常，数据已刷新", Boolean(hasErr));
}

function currentMemory() {
  return state.memories.find((row) => row.memory_id === state.selectedMemoryId) || state.memories[0] || null;
}

function currentTrace() {
  return state.traces.find((row) => row.request_id === state.selectedTraceId) || state.traces[0] || null;
}

function renderGlobalBadges() {
  const root = document.getElementById("global-badges");
  const provider = state.config?.target?.provider || "unknown";
  const model = state.config?.target?.default_model || state.config?.target?.provider || "unknown";
  const fallback = state.traces.reduce((sum, row) => sum + Number(row.fallback_count || 0), 0);
  root.innerHTML = `
    <span class="badge">provider: ${escapeHtml(provider)}</span>
    <span class="badge">model: ${escapeHtml(model)}</span>
    <span class="badge warn">fallback: ${fallback}</span>
  `;
}

function renderDashboard() {
  const traceCount = state.traces.length;
  const fallbackCount = state.traces.reduce((sum, row) => sum + Number(row.fallback_count || 0), 0);
  const trimCount = state.traces.reduce((sum, row) => sum + (row.has_trim ? 1 : 0), 0);
  const rewriteCount = state.traces.reduce((sum, row) => {
    const action = row.trace?.grounding?.degrade_action || row.trace?.grounding?.action || "";
    return sum + (String(action).includes("degrade") ? 1 : 0);
  }, 0);
  const unsupportedValues = state.traces.slice(0, 12).reverse().map((row) => Number(row.unsupported_ratio || 0));
  const unsupportedAvg = unsupportedValues.length
    ? unsupportedValues.reduce((sum, n) => sum + n, 0) / unsupportedValues.length
    : 0;

  const spark = unsupportedValues.length
    ? unsupportedValues.map((n) => `<span style="height:${Math.max(8, Math.round(n * 100) + 8)}px"></span>`).join("")
    : '<span style="height:10px"></span>';

  document.getElementById("view-dashboard").innerHTML = `
    <div class="grid">
      <article class="panel card-soft kpi"><p class="muted">服务状态</p><p class="kpi-num">${escapeHtml(state.health?.status || "unknown")}</p></article>
      <article class="panel card-soft kpi"><p class="muted">请求量（窗口）</p><p class="kpi-num">${traceCount}</p></article>
      <article class="panel card-soft kpi"><p class="muted">fallback 次数</p><p class="kpi-num">${fallbackCount}</p></article>
      <article class="panel card-soft kpi"><p class="muted">trim 次数</p><p class="kpi-num">${trimCount}</p></article>

      <article class="panel card-soft half">
        <h3>运行概览</h3>
        <div class="actions-row muted" style="margin-top:10px">
          <span>默认上游：${escapeHtml(state.health?.upstream || "")}</span>
          <span>模式：${escapeHtml(state.health?.upstream_mode || "")}</span>
          <span>rewrite/degrade：${rewriteCount}</span>
        </div>
        <div class="sparkline">${spark}</div>
        <p class="muted" style="margin-top:8px">unsupported_ratio 均值：${unsupportedAvg.toFixed(3)}</p>
      </article>

      <article class="panel card-soft half">
        <h3>巡检建议</h3>
        <div class="trace-flow" style="margin-top:10px">
          <div class="trace-box">优先检查 fallback 突增请求对应模型与上游健康。</div>
          <div class="trace-box">若 unsupported_ratio 升高，复核 grounding policy 与 citation 数据质量。</div>
          <div class="trace-box">trim 高频时关注 MemoryPack 预算和上下文窗口。</div>
        </div>
      </article>
    </div>
  `;
}

function renderUpstream() {
  const target = state.config?.target || {};
  const legacy = state.config?.legacy_llmapi || {};
  const effective = state.config?.effective || {};

  document.getElementById("view-upstream").innerHTML = `
    <div class="grid">
      <article class="panel card-soft half">
        <h3>区域 A：主配置（推荐）</h3>
        <div style="margin-top:10px" class="trace-flow">
          <div class="trace-box"><strong>TARGET_PROVIDER</strong><p class="muted">${escapeHtml(target.provider || "")}</p></div>
          <div class="trace-box"><strong>TARGET_BASE_URL</strong><p class="muted">${escapeHtml(target.base_url || "")}</p></div>
          <div class="trace-box"><strong>TARGET_API_KEY</strong><p class="muted">${escapeHtml(target.api_key_masked || "")}</p></div>
          <div class="trace-box"><strong>DEFAULT_MODEL</strong><p class="muted">${escapeHtml(target.default_model || "")}</p></div>
        </div>
        <div class="actions-row">
          <button>保存配置（待接 PUT /admin/config）</button>
          <button>测试连接（待接 POST /admin/config/test）</button>
          <button>拉取模型列表（待接 /admin/config/models）</button>
        </div>
      </article>

      <article class="panel card-soft half">
        <h3>区域 B：旧版兼容配置</h3>
        <div style="margin-top:10px" class="trace-flow">
          <div class="trace-box"><strong>LLMAPI_BASE_URL</strong><p class="muted">${escapeHtml(legacy.base_url || "")}</p></div>
          <div class="trace-box"><strong>LLMAPI_API_KEY</strong><p class="muted">${escapeHtml(legacy.api_key_masked || "")}</p></div>
          <div class="trace-box"><strong>LLMAPI_MODEL_PREFIX</strong><p class="muted">${escapeHtml(legacy.model_prefix || "")}</p></div>
          <div class="trace-box"><strong>LLMAPI_PROVIDER_PREFIX</strong><p class="muted">${escapeHtml(legacy.provider_prefix || "")}</p></div>
        </div>
        <div class="actions-row">
          <button>迁移到 TARGET_*（待接）</button>
          <button>导入 .env（待接）</button>
          <button>导出 .env（待接）</button>
        </div>
      </article>

      <article class="panel card-soft">
        <h3>当前实际生效配置</h3>
        <pre style="margin-top:10px">${toPrettyJson(effective)}</pre>
      </article>
    </div>
  `;
}

function renderMemory() {
  const selected = currentMemory();
  const rows = state.memories.map((row) => {
    const active = row.memory_id === selected?.memory_id ? "is-active" : "";
    return `
      <tr class="${active}" data-memory-id="${escapeHtml(row.memory_id)}">
        <td>${escapeHtml(row.memory_id)}</td>
        <td>${escapeHtml(row.layer)}</td>
        <td>${escapeHtml(short(row.content, 50))}</td>
        <td>${escapeHtml(row.memory_type || "")}</td>
        <td>${escapeHtml(row.source || "")}</td>
        <td>${escapeHtml(row.session_id || "-")}</td>
        <td>${escapeHtml((row.tags || []).join(", "))}</td>
        <td>${Number(row.confidence || 0).toFixed(2)}</td>
        <td>${escapeHtml(row.updated_at || row.created_at || "")}</td>
        <td>${row.archived ? "archived" : "active"}</td>
      </tr>
    `;
  }).join("");

  document.getElementById("view-memory").innerHTML = `
    <div class="grid">
      <article class="panel card-soft quarter">
        <h3>分层树</h3>
        <div class="tree" style="margin-top:10px">
          <button data-layer="ALL">全部</button>
          <button data-layer="L1">L0/L1 constraints</button>
          <button data-layer="L2">facts</button>
          <button data-layer="L3">procedures</button>
          <button data-layer="L4">continuity</button>
        </div>
      </article>

      <article class="panel card-soft half">
        <h3>记忆列表</h3>
        <div class="actions-row">
          <input id="memory-search" placeholder="搜索 content/source/tag" value="${escapeHtml(state.memorySearch)}" />
          <button id="memory-search-btn" class="primary">搜索</button>
          <button id="memory-export-json">导出 JSON</button>
          <button id="memory-export-md">导出 Markdown</button>
        </div>
        <div class="table-wrap" style="margin-top:10px">
          <table>
            <thead>
              <tr><th>id</th><th>layer</th><th>title</th><th>kind</th><th>source</th><th>session_id</th><th>tags</th><th>confidence</th><th>updated_at</th><th>status</th></tr>
            </thead>
            <tbody>${rows || '<tr><td colspan="10">暂无数据</td></tr>'}</tbody>
          </table>
        </div>
      </article>

      <article class="panel card-soft quarter">
        <h3>详情面板</h3>
        <p class="muted" style="margin-top:8px">memory_id: ${escapeHtml(selected?.memory_id || "")}</p>
        <pre style="margin-top:10px">${toPrettyJson(selected || {})}</pre>
        <div class="actions-row">
          <button>单条编辑（待接）</button>
          <button>批量编辑（待接）</button>
          <button>归档（待接）</button>
          <button>禁用（待接）</button>
          <button>回滚（待接）</button>
        </div>
      </article>
    </div>
  `;

  document.querySelectorAll("button[data-layer]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      state.memoryLayerFilter = btn.getAttribute("data-layer") || "ALL";
      await loadMemories();
      renderMemory();
    });
  });

  document.querySelectorAll("tr[data-memory-id]").forEach((tr) => {
    tr.addEventListener("click", () => {
      state.selectedMemoryId = tr.getAttribute("data-memory-id") || "";
      renderMemory();
    });
  });

  document.getElementById("memory-search-btn")?.addEventListener("click", async () => {
    state.memorySearch = document.getElementById("memory-search")?.value || "";
    await loadMemories();
    renderMemory();
  });

  document.getElementById("memory-export-json")?.addEventListener("click", () => {
    downloadText(`nexusgate-memories-${Date.now()}.json`, JSON.stringify(state.memories, null, 2), "application/json");
  });

  document.getElementById("memory-export-md")?.addEventListener("click", () => {
    const lines = ["# Memories", ""];
    state.memories.forEach((row) => {
      lines.push(`## ${row.memory_id} (${row.layer})`);
      lines.push(`- source: ${row.source || ""}`);
      lines.push(`- confidence: ${Number(row.confidence || 0).toFixed(2)}`);
      lines.push(`- updated_at: ${row.updated_at || row.created_at || ""}`);
      lines.push("");
      lines.push(row.content || "");
      lines.push("");
    });
    downloadText(`nexusgate-memories-${Date.now()}.md`, lines.join("\n"), "text/markdown");
  });
}

function renderPack() {
  const trace = currentTrace();
  const traceObj = trace?.trace || {};
  const render = traceObj.render || {};
  const retained = [
    ...(render.retained_fact_ids || []),
    ...(render.retained_procedure_ids || []),
    ...(render.retained_continuity_ids || []),
    ...(render.retained_constraint_ids || []),
  ];
  const dropped = render.dropped_blocks || render.dropped_block_ids || [];

  document.getElementById("view-pack").innerHTML = `
    <div class="grid">
      <article class="panel card-soft third">
        <h3>命中记忆条目</h3>
        <pre style="margin-top:10px">${toPrettyJson(traceObj.retrieval || {})}</pre>
      </article>
      <article class="panel card-soft third">
        <h3>结构化 MemoryPack</h3>
        <pre style="margin-top:10px">${toPrettyJson(traceObj.assembly || {})}</pre>
      </article>
      <article class="panel card-soft third">
        <h3>provider 渲染结果</h3>
        <pre style="margin-top:10px">${toPrettyJson(traceObj.routing || {})}</pre>
      </article>

      <article class="panel card-soft half">
        <h3>trim report</h3>
        <pre style="margin-top:10px">${toPrettyJson(render)}</pre>
      </article>

      <article class="panel card-soft half">
        <h3>trim 前后差异</h3>
        <div class="trace-flow" style="margin-top:10px">
          <div class="trace-box"><strong>保留条目</strong><p class="muted">${escapeHtml(retained.join(", ") || "(empty)")}</p></div>
          <div class="trace-box"><strong>裁剪条目</strong><p class="muted">${escapeHtml(dropped.join(", ") || "(empty)")}</p></div>
          <div class="trace-box"><strong>裁剪字符数</strong><p class="muted">${escapeHtml(String(render.trimmed_total_chars || 0))}</p></div>
        </div>
      </article>
    </div>
  `;
}

function renderTrace() {
  const selected = currentTrace();
  const rows = state.traces.map((row) => {
    const active = row.request_id === selected?.request_id ? "is-active" : "";
    return `
      <tr class="${active}" data-trace-id="${escapeHtml(row.request_id)}">
        <td>${escapeHtml(row.request_id)}</td>
        <td>${escapeHtml(row.session_id || "")}</td>
        <td>${escapeHtml(row.provider || "")}</td>
        <td>${escapeHtml(row.model || "")}</td>
        <td>${escapeHtml(row.status || "")}</td>
        <td>${Number(row.fallback_count || 0)}</td>
        <td>${row.has_trim ? "yes" : "no"}</td>
        <td>${escapeHtml(String(row.trace?.grounding?.degrade_action || "none"))}</td>
        <td>${Number(row.unsupported_ratio || 0).toFixed(3)}</td>
        <td>${escapeHtml(formatTs(row.created_at))}</td>
      </tr>
    `;
  }).join("");

  document.getElementById("view-trace").innerHTML = `
    <div class="grid">
      <article class="panel card-soft half">
        <h3>请求追踪列表</h3>
        <div class="table-wrap" style="margin-top:10px">
          <table>
            <thead>
              <tr><th>request_id</th><th>session_id</th><th>provider</th><th>model</th><th>status</th><th>fallback</th><th>trim</th><th>rewrite</th><th>unsupported_ratio</th><th>time</th></tr>
            </thead>
            <tbody>${rows || '<tr><td colspan="10">暂无 trace</td></tr>'}</tbody>
          </table>
        </div>
      </article>

      <article class="panel card-soft half">
        <h3>详情链路</h3>
        <div class="trace-flow" style="margin-top:10px">
          <div class="trace-box"><strong>original input</strong><pre style="margin-top:8px">${toPrettyJson({ session_id: selected?.session_id, api_style: selected?.api_style })}</pre></div>
          <div class="trace-box"><strong>route decision</strong><pre style="margin-top:8px">${toPrettyJson(selected?.trace?.routing || {})}</pre></div>
          <div class="trace-box"><strong>fallback chain</strong><pre style="margin-top:8px">${toPrettyJson(selected?.trace?.fallback || [])}</pre></div>
          <div class="trace-box"><strong>memory hit summary</strong><pre style="margin-top:8px">${toPrettyJson(selected?.trace?.retrieval || {})}</pre></div>
          <div class="trace-box"><strong>trim report</strong><pre style="margin-top:8px">${toPrettyJson(selected?.trace?.render || {})}</pre></div>
          <div class="trace-box"><strong>grounding summary</strong><pre style="margin-top:8px">${toPrettyJson(selected?.trace?.grounding || {})}</pre></div>
        </div>
      </article>

      <article class="panel card-soft">
        <h3>完整 trace JSON</h3>
        <pre style="margin-top:10px">${toPrettyJson(selected || {})}</pre>
      </article>
    </div>
  `;

  document.querySelectorAll("tr[data-trace-id]").forEach((tr) => {
    tr.addEventListener("click", () => {
      state.selectedTraceId = tr.getAttribute("data-trace-id") || "";
      renderTrace();
      renderPack();
    });
  });
}

function renderClients() {
  const base = `${state.apiBase}/v1`;
  const model = state.config?.target?.provider || "auto";
  document.getElementById("view-clients").innerHTML = `
    <div class="grid">
      <article class="panel card-soft half">
        <h3>OpenAI SDK</h3>
        <pre style="margin-top:10px">from openai import OpenAI

client = OpenAI(
    base_url="${escapeHtml(base)}",
    api_key="&lt;LOCAL_API_KEY&gt;"
)

resp = client.chat.completions.create(
    model="${escapeHtml(model)}",
    messages=[{"role": "user", "content": "hello"}]
)
print(resp.choices[0].message.content)</pre>
      </article>

      <article class="panel card-soft half">
        <h3>curl</h3>
        <pre style="margin-top:10px">curl ${escapeHtml(base)}/chat/completions \\
  -H "Authorization: Bearer &lt;LOCAL_API_KEY&gt;" \\
  -H "Content-Type: application/json" \\
  -d '{"model":"${escapeHtml(model)}","messages":[{"role":"user","content":"ping"}]}'</pre>
      </article>

      <article class="panel card-soft third">
        <h3>Codex 接入</h3>
        <pre style="margin-top:10px">[model_providers.OpenAI]
name = "OpenAI"
base_url = "${escapeHtml(base)}"
wire_api = "responses"
requires_openai_auth = false</pre>
      </article>

      <article class="panel card-soft third">
        <h3>Claude 接入</h3>
        <pre style="margin-top:10px">{
  "env": {
    "ANTHROPIC_BASE_URL": "${escapeHtml(state.apiBase)}",
    "ANTHROPIC_AUTH_TOKEN": "&lt;LOCAL_API_KEY&gt;"
  }
}</pre>
      </article>

      <article class="panel card-soft third">
        <h3>接入检查</h3>
        <div class="trace-flow" style="margin-top:10px">
          <div class="trace-box">Base URL：${escapeHtml(base)}</div>
          <div class="trace-box">本地鉴权：${escapeHtml(state.health?.auth_mode || "unknown")}</div>
          <div class="trace-box">上游模式：${escapeHtml(state.health?.upstream_mode || "unknown")}</div>
        </div>
      </article>
    </div>
  `;
}

function downloadText(filename, text, mime) {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function renderAllViews() {
  renderGlobalBadges();
  renderDashboard();
  renderUpstream();
  renderMemory();
  renderPack();
  renderTrace();
  renderClients();
}

async function refreshDataAndRender() {
  await loadAllData();
  renderAllViews();
}

function bindGlobalEvents() {
  navRoot.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const viewId = target.getAttribute("data-view");
    if (!viewId) return;
    switchView(viewId);
  });
}

async function init() {
  renderNav();
  renderConnectionPanel();
  bindGlobalEvents();
  await refreshDataAndRender();
  switchView(state.activeView);
}

init();
