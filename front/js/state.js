(function (w) {
  const NAV = [
    { id: "dashboard", label: "全局监控控制面板", title: "全局监控控制面板", desc: "状态卡、路由监控、token 使用与节省、异常告警四区布局。" },
    { id: "upstream", label: "上游配置", title: "上游配置", desc: "TARGET_* 与 LLMAPI_* 分区，清晰显示当前生效配置。" },
    { id: "memory", label: "记忆中心", title: "记忆中心", desc: "分层树 + 列表 + 详情面板，支持搜索筛选与导出。" },
    { id: "pack", label: "MemoryPack 预览", title: "MemoryPack 预览", desc: "命中条目、trim 报告、保留与裁剪差异可视化。" },
    { id: "trace", label: "请求追踪", title: "请求追踪", desc: "追踪 route/fallback/trim/grounding/rewrite 与最终响应。" },
    { id: "clients", label: "客户端接入", title: "客户端接入", desc: "OpenAI SDK、curl、Codex/Claude 接入示例。" },
  ];

  const state = {
    apiBase: localStorage.getItem("nexusgate_api_base") || ((location.protocol.startsWith("http") ? location.origin : "http://127.0.0.1:8000")),
    apiKey: localStorage.getItem("nexusgate_api_key") || "",
    activeView: "dashboard",
    config: null,
    health: null,
    memories: [],
    traces: [],
    errors: {},
    selectedMemoryId: "",
    selectedTraceId: "",
    memoryLayer: "ALL",
    memoryQuery: "",
  };

  const escapeHtml = (text) => String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");

  const json = (v) => escapeHtml(JSON.stringify(v ?? {}, null, 2));
  const short = (text, n = 60) => String(text || "").length > n ? `${String(text).slice(0, n)}...` : String(text || "");
  const fmtTs = (sec) => sec ? new Date(Number(sec) * 1000).toLocaleString("zh-CN", { hour12: false }) : "";

  const apiFetch = async (path) => {
    const headers = { "Content-Type": "application/json" };
    if (state.apiKey.trim()) headers.Authorization = `Bearer ${state.apiKey.trim()}`;
    const resp = await fetch(`${state.apiBase}${path}`, { headers });
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}: ${(await resp.text()).slice(0, 180)}`);
    return resp.json();
  };

  const tokenStats = (trace) => (trace && trace.token_stats) || {
    estimated_prompt_tokens: 0,
    estimated_sent_tokens: 0,
    prompt_tokens: 0,
    completion_tokens: 0,
    total_tokens: 0,
    saved_tokens_estimated: 0,
    saved_tokens_actual: 0,
    saved_rate_estimated: 0,
    saved_rate_actual: 0,
    usage_source: "estimate_only",
  };

  w.NexusUI = { NAV, state, escapeHtml, json, short, fmtTs, apiFetch, tokenStats };
})(window);
