(async function (w) {
  const U = w.NexusUI;
  const V = w.NexusViews;
  const { state, NAV, apiFetch } = U;

  const setStatus = (text, bad) => {
    const el = document.getElementById("conn-status");
    if (!el) return;
    el.textContent = text;
    el.style.color = bad ? "var(--danger)" : "var(--muted)";
  };

  const switchView = (id) => {
    state.activeView = id;
    document.querySelectorAll(".view").forEach((n) => n.classList.remove("active"));
    document.getElementById(`view-${id}`)?.classList.add("active");
    const meta = NAV.find((x) => x.id === id) || NAV[0];
    document.getElementById("page-title").textContent = meta.title;
    document.getElementById("page-desc").textContent = meta.desc;
    V.renderNav();
  };

  const loadConfig = async () => {
    try {
      state.config = await apiFetch("/admin/config");
      state.health = state.config.health;
      state.errors.config = "";
    } catch (e) {
      state.errors.config = String(e.message || e);
    }
  };

  const loadMemories = async () => {
    try {
      const l = state.memoryLayer === "ALL" ? "" : `&layers=${encodeURIComponent(state.memoryLayer)}`;
      const q = state.memoryQuery.trim() ? `&query=${encodeURIComponent(state.memoryQuery.trim())}` : "";
      const res = await apiFetch(`/admin/memories?limit=120${l}${q}`);
      state.memories = res.items || [];
      if (!state.selectedMemoryId && state.memories[0]) state.selectedMemoryId = state.memories[0].memory_id;
      state.errors.memories = "";
    } catch (e) {
      state.errors.memories = String(e.message || e);
    }
  };

  const loadTraces = async () => {
    try {
      const res = await apiFetch("/admin/traces?limit=120");
      state.traces = res.items || [];
      if (!state.selectedTraceId && state.traces[0]) state.selectedTraceId = state.traces[0].request_id;
      state.errors.traces = "";
    } catch (e) {
      state.errors.traces = String(e.message || e);
    }
  };

  const saveConn = () => {
    state.apiBase = document.getElementById("api-base")?.value.trim() || state.apiBase;
    state.apiKey = document.getElementById("api-key")?.value.trim() || "";
    localStorage.setItem("nexusgate_api_base", state.apiBase);
    localStorage.setItem("nexusgate_api_key", state.apiKey);
    setStatus("连接参数已保存", false);
  };

  const download = (filename, text, type) => {
    const b = new Blob([text], { type });
    const url = URL.createObjectURL(b);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  let eventsBound = false;
  const bindDelegatedEvents = () => {
    if (eventsBound) return;
    eventsBound = true;

    document.getElementById("nav")?.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      const btn = target.closest("button[data-view]");
      if (!btn) return;
      const viewId = btn.getAttribute("data-view");
      if (!viewId) return;
      switchView(viewId);
    });

    document.addEventListener("click", async (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      const node = target.closest("button, tr");
      if (!node) return;

      if (node.id === "save-conn") {
        saveConn();
        return;
      }
      if (node.id === "reload-conn") {
        await refresh();
        return;
      }
      if (node.id === "memory-search") {
        state.memoryQuery = document.getElementById("memory-q")?.value || "";
        await refresh();
        switchView("memory");
        return;
      }
      if (node.id === "export-json") {
        download(`nexusgate-memories-${Date.now()}.json`, JSON.stringify(state.memories, null, 2), "application/json");
        return;
      }
      if (node.id === "export-md") {
        const lines = ["# NexusGate Memories", ""];
        state.memories.forEach((m) => {
          lines.push(`## ${m.memory_id} (${m.layer})`);
          lines.push(`- source: ${m.source || ""}`);
          lines.push(`- confidence: ${Number(m.confidence || 0).toFixed(2)}`);
          lines.push(`- updated_at: ${m.updated_at || m.created_at || ""}`);
          lines.push("");
          lines.push(m.content || "");
          lines.push("");
        });
        download(`nexusgate-memories-${Date.now()}.md`, lines.join("\n"), "text/markdown");
        return;
      }
      const layer = node.getAttribute("data-layer");
      if (layer) {
        state.memoryLayer = layer;
        await refresh();
        switchView("memory");
        return;
      }
      const memoryId = node.getAttribute("data-memory-id");
      if (memoryId) {
        state.selectedMemoryId = memoryId;
        V.renderViews();
        switchView("memory");
        return;
      }
      const traceId = node.getAttribute("data-trace-id");
      if (traceId) {
        state.selectedTraceId = traceId;
        V.renderViews();
        switchView("trace");
      }
    });
  };

  const refresh = async () => {
    await Promise.all([loadConfig(), loadMemories(), loadTraces()]);
    const fail = state.errors.config || state.errors.memories || state.errors.traces;
    V.renderBadges();
    V.renderViews();
    setStatus(fail ? "接口请求失败，请检查 API Base/API Key 或后端状态" : "接口连接正常，数据已刷新", Boolean(fail));
  };

  const init = async () => {
    V.renderNav();
    V.renderConn();
    V.renderBadges();
    bindDelegatedEvents();
    await refresh();
    switchView(state.activeView);
  };

  await init();
})(window);
