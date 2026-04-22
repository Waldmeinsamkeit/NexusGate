(function (w) {
  const U = w.NexusUI;
  const { state, NAV, escapeHtml, json, short, fmtTs, tokenStats } = U;

  const selectedMemory = () => state.memories.find((x) => x.memory_id === state.selectedMemoryId) || state.memories[0] || null;
  const selectedTrace = () => state.traces.find((x) => x.request_id === state.selectedTraceId) || state.traces[0] || null;

  const renderBadges = () => {
    const el = document.getElementById("global-badges");
    const fallback = state.traces.reduce((a, b) => a + Number(b.fallback_count || 0), 0);
    const provider = state.config?.target?.provider || "unknown";
    const model = state.config?.target?.default_model || provider;
    el.innerHTML = `<span class="badge">provider: ${escapeHtml(provider)}</span><span class="badge">model: ${escapeHtml(model)}</span><span class="badge warn">fallback: ${fallback}</span>`;
  };

  const renderNav = () => {
    const nav = document.getElementById("nav");
    nav.innerHTML = NAV.map((n) => `<button class="nav-btn ${state.activeView === n.id ? "active" : ""}" data-view="${n.id}">${n.label}</button>`).join("");
  };

  const renderConn = () => {
    document.getElementById("conn").innerHTML = `
      <div class="conn-row">
        <p class="muted">API 连接</p>
        <input id="api-base" value="${escapeHtml(state.apiBase)}" placeholder="http://127.0.0.1:8000" />
        <input id="api-key" value="${escapeHtml(state.apiKey)}" placeholder="local api key" />
        <button id="save-conn">保存连接</button>
        <button class="primary" id="reload-conn">刷新数据</button>
      </div>
      <p id="conn-status" class="status">连接尚未验证</p>
    `;
  };

  const dashboard = () => {
    const traces = state.traces;
    const totalReq = traces.length;
    const avgLatency = totalReq ? Math.round(traces.reduce((n, t) => n + Number(t.latency_ms || 0), 0) / totalReq) : 0;
    const fallback = traces.reduce((n, t) => n + Number(t.fallback_count || 0), 0);
    const trim = traces.filter((t) => t.has_trim).length;
    const rewrite = traces.filter((t) => String(t.trace?.grounding?.degrade_action || "").includes("degrade")).length;
    const unsupported = totalReq ? traces.reduce((n, t) => n + Number(t.unsupported_ratio || 0), 0) / totalReq : 0;
    const tokens = traces.map(tokenStats);
    const saved = tokens.reduce((n, s) => n + Number(s.saved_tokens_estimated || 0), 0);
    const sent = tokens.reduce((n, s) => n + Number(s.estimated_sent_tokens || 0), 0);
    const base = tokens.reduce((n, s) => n + Number(s.estimated_prompt_tokens || 0), 0);
    const rate = base ? (saved / base) : 0;
    const series = traces.slice(0, 24).reverse().map((t) => tokenStats(t).saved_rate_estimated || 0);
    const spark = (series.length ? series : [0.1]).map((v) => `<span style="height:${Math.max(6, Math.round(v * 120) + 8)}px"></span>`).join("");

    return `
      <div class="grid">
        <article class="card panel kpi"><p class="muted">服务状态</p><p class="metric">${escapeHtml(state.health?.status || "unknown")}</p></article>
        <article class="card panel kpi"><p class="muted">请求量</p><p class="metric">${totalReq}</p></article>
        <article class="card panel kpi"><p class="muted">平均延迟</p><p class="metric">${avgLatency}ms</p></article>
        <article class="card panel kpi"><p class="muted">fallback</p><p class="metric">${fallback}</p></article>

        <article class="card panel left"><h3>请求与路由监控</h3><div class="stack" style="margin-top:8px"><div class="node">trim 次数：${trim}</div><div class="node">rewrite 次数：${rewrite}</div><div class="node">unsupported_ratio：${unsupported.toFixed(3)}</div><div class="node">默认上游：${escapeHtml(state.health?.upstream || "")}</div></div></article>

        <article class="card panel mid"><h3>Token 使用与节省可视化</h3><div class="stack" style="margin-top:8px"><div class="node">原始估算 token：${base}</div><div class="node">实际发送估算 token：${sent}</div><div class="node">节省 token：${saved}</div><div class="node">节省率：${(rate * 100).toFixed(1)}%</div></div><div class="spark">${spark}</div><p class="muted" style="margin-top:8px">口径：estimated_prompt_tokens / estimated_sent_tokens；若上游回传 usage，则 trace 中 usage_source=upstream_usage。</p></article>

        <article class="card panel right"><h3>异常与告警</h3><div class="flow" style="margin-top:8px">${traces.slice(0, 5).map((t) => `<div class="node">${escapeHtml(t.request_id)} | fallback=${Number(t.fallback_count || 0)} | trim=${t.has_trim ? "yes" : "no"}</div>`).join("") || '<div class="node">暂无告警</div>'}</div></article>
      </div>`;
  };

  const upstream = () => {
    const target = state.config?.target || {};
    const legacy = state.config?.legacy_llmapi || {};
    const eff = state.config?.effective || {};
    return `<div class="grid"><article class="card panel half"><h3>区域 A：主配置（TARGET_*）</h3><div class="stack" style="margin-top:8px"><div class="node">TARGET_PROVIDER: ${escapeHtml(target.provider || "")}</div><div class="node">TARGET_BASE_URL: ${escapeHtml(target.base_url || "")}</div><div class="node">TARGET_API_KEY: ${escapeHtml(target.api_key_masked || "")}</div><div class="node">DEFAULT_MODEL: ${escapeHtml(target.default_model || "")}</div></div><div class="actions"><button>保存配置（待接）</button><button>测试连接（待接）</button><button>拉取模型列表（待接）</button></div></article><article class="card panel half"><h3>区域 B：旧版兼容配置</h3><div class="stack" style="margin-top:8px"><div class="node">LLMAPI_BASE_URL: ${escapeHtml(legacy.base_url || "")}</div><div class="node">LLMAPI_API_KEY: ${escapeHtml(legacy.api_key_masked || "")}</div><div class="node">LLMAPI_MODEL_PREFIX: ${escapeHtml(legacy.model_prefix || "")}</div><div class="node">LLMAPI_PROVIDER_PREFIX: ${escapeHtml(legacy.provider_prefix || "")}</div></div><div class="actions"><button>迁移到 TARGET_*（待接）</button><button>导入 .env（待接）</button><button>导出 .env（待接）</button></div></article><article class="card panel"><h3>当前实际生效配置</h3><pre style="margin-top:8px">${json(eff)}</pre></article></div>`;
  };

  const memory = () => {
    const sel = selectedMemory();
    const rows = state.memories.map((m) => `<tr class="${sel?.memory_id === m.memory_id ? "is-active" : ""}" data-memory-id="${escapeHtml(m.memory_id)}"><td>${escapeHtml(m.memory_id)}</td><td>${escapeHtml(m.layer)}</td><td>${escapeHtml(short(m.content, 44))}</td><td>${escapeHtml(m.memory_type || "")}</td><td>${escapeHtml(m.source || "")}</td><td>${escapeHtml(m.session_id || "-")}</td><td>${escapeHtml((m.tags || []).join(","))}</td><td>${Number(m.confidence || 0).toFixed(2)}</td><td>${escapeHtml(m.updated_at || m.created_at || "")}</td><td>${m.archived ? "archived" : "active"}</td></tr>`).join("");
    return `<div class="grid"><article class="card panel quarter"><h3>分层树</h3><div class="stack" style="margin-top:8px"><button data-layer="ALL">全部</button><button data-layer="L1">L0/constraints</button><button data-layer="L2">facts</button><button data-layer="L3">procedures</button><button data-layer="L4">continuity</button></div></article><article class="card panel half"><h3>记忆列表</h3><div class="actions"><input id="memory-q" value="${escapeHtml(state.memoryQuery)}" placeholder="搜索记忆" /><button id="memory-search" class="primary">搜索</button><button id="export-json">导出JSON</button><button id="export-md">导出Markdown</button></div><div class="table-wrap" style="margin-top:8px"><table><thead><tr><th>id</th><th>layer</th><th>title</th><th>kind</th><th>source</th><th>session</th><th>tags</th><th>confidence</th><th>updated_at</th><th>status</th></tr></thead><tbody>${rows || '<tr><td colspan="10">暂无数据</td></tr>'}</tbody></table></div></article><article class="card panel quarter"><h3>详情面板</h3><pre style="margin-top:8px">${json(sel || {})}</pre><div class="actions"><button>单条编辑（待接）</button><button>批量编辑（待接）</button><button>归档（待接）</button><button>禁用（待接）</button><button>回滚（待接）</button></div></article></div>`;
  };

  const pack = () => {
    const t = selectedTrace();
    const tr = t?.trace || {};
    const r = tr.render || {};
    const kept = [...(r.retained_fact_ids || []), ...(r.retained_procedure_ids || []), ...(r.retained_continuity_ids || []), ...(r.retained_constraint_ids || [])];
    const drop = r.dropped_blocks || r.dropped_block_ids || [];
    return `<div class="grid"><article class="card panel third"><h3>命中记忆条目</h3><pre style="margin-top:8px">${json(tr.retrieval || {})}</pre></article><article class="card panel third"><h3>结构化MemoryPack</h3><pre style="margin-top:8px">${json(tr.assembly || {})}</pre></article><article class="card panel third"><h3>provider渲染结果</h3><pre style="margin-top:8px">${json(tr.routing || {})}</pre></article><article class="card panel half"><h3>trim report</h3><pre style="margin-top:8px">${json(r)}</pre></article><article class="card panel half"><h3>trim前后差异</h3><div class="stack" style="margin-top:8px"><div class="node">保留条目：${escapeHtml(kept.join(",") || "(empty)")}</div><div class="node">裁剪条目：${escapeHtml(drop.join(",") || "(empty)")}</div><div class="node">trim chars：${Number(r.trimmed_total_chars || 0)}</div></div></article></div>`;
  };

  const trace = () => {
    const sel = selectedTrace();
    const rows = state.traces.map((t) => `<tr class="${sel?.request_id === t.request_id ? "is-active" : ""}" data-trace-id="${escapeHtml(t.request_id)}"><td>${escapeHtml(t.request_id)}</td><td>${escapeHtml(t.session_id || "")}</td><td>${escapeHtml(t.provider || "")}</td><td>${escapeHtml(t.model || "")}</td><td>${Number(t.latency_ms || 0)}ms</td><td>${Number(t.fallback_count || 0)}</td><td>${t.has_trim ? "yes" : "no"}</td><td>${escapeHtml(String(t.trace?.grounding?.degrade_action || "none"))}</td><td>${Number(t.unsupported_ratio || 0).toFixed(3)}</td><td>${escapeHtml(fmtTs(t.created_at))}</td></tr>`).join("");
    return `<div class="grid"><article class="card panel half"><h3>请求追踪列表</h3><div class="table-wrap" style="margin-top:8px"><table><thead><tr><th>request_id</th><th>session</th><th>provider</th><th>model</th><th>latency</th><th>fallback</th><th>trim</th><th>rewrite</th><th>unsupported</th><th>time</th></tr></thead><tbody>${rows || '<tr><td colspan="10">暂无trace</td></tr>'}</tbody></table></div></article><article class="card panel half"><h3>链路详情</h3><div class="flow" style="margin-top:8px"><div class="node"><strong>original input</strong><pre style="margin-top:6px">${json({ session_id: sel?.session_id, api_style: sel?.api_style })}</pre></div><div class="node"><strong>route decision</strong><pre style="margin-top:6px">${json(sel?.trace?.routing || {})}</pre></div><div class="node"><strong>fallback chain</strong><pre style="margin-top:6px">${json(sel?.trace?.fallback || [])}</pre></div><div class="node"><strong>trim report</strong><pre style="margin-top:6px">${json(sel?.trace?.render || {})}</pre></div><div class="node"><strong>grounding summary</strong><pre style="margin-top:6px">${json(sel?.trace?.grounding || {})}</pre></div></div></article><article class="card panel"><h3>完整 trace JSON</h3><pre style="margin-top:8px">${json(sel || {})}</pre></article></div>`;
  };

  const clients = () => {
    const base = `${state.apiBase}/v1`;
    const model = state.config?.target?.provider || "auto";
    return `<div class="grid"><article class="card panel half"><h3>OpenAI SDK</h3><pre style="margin-top:8px">from openai import OpenAI
client = OpenAI(base_url="${escapeHtml(base)}", api_key="&lt;LOCAL_API_KEY&gt;")
resp = client.chat.completions.create(model="${escapeHtml(model)}", messages=[{"role":"user","content":"hello"}])</pre></article><article class="card panel half"><h3>curl</h3><pre style="margin-top:8px">curl ${escapeHtml(base)}/chat/completions \\
  -H "Authorization: Bearer &lt;LOCAL_API_KEY&gt;" \\
  -H "Content-Type: application/json" \\
  -d '{"model":"${escapeHtml(model)}","messages":[{"role":"user","content":"ping"}]}'</pre></article><article class="card panel third"><h3>Codex 接入</h3><pre style="margin-top:8px">[model_providers.OpenAI]
base_url = "${escapeHtml(base)}"
wire_api = "responses"
requires_openai_auth = false</pre></article><article class="card panel third"><h3>Claude 接入</h3><pre style="margin-top:8px">{"env":{"ANTHROPIC_BASE_URL":"${escapeHtml(state.apiBase)}","ANTHROPIC_AUTH_TOKEN":"&lt;LOCAL_API_KEY&gt;"}}</pre></article><article class="card panel third"><h3>接入状态</h3><div class="stack" style="margin-top:8px"><div class="node">Base URL: ${escapeHtml(base)}</div><div class="node">auth_mode: ${escapeHtml(state.health?.auth_mode || "unknown")}</div><div class="node">upstream_mode: ${escapeHtml(state.health?.upstream_mode || "unknown")}</div></div></article></div>`;
  };

  const renderViews = () => {
    document.getElementById("view-dashboard").innerHTML = dashboard();
    document.getElementById("view-upstream").innerHTML = upstream();
    document.getElementById("view-memory").innerHTML = memory();
    document.getElementById("view-pack").innerHTML = pack();
    document.getElementById("view-trace").innerHTML = trace();
    document.getElementById("view-clients").innerHTML = clients();
  };

  w.NexusViews = { renderNav, renderConn, renderBadges, renderViews, selectedMemory, selectedTrace };
})(window);
