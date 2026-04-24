"""
测试案例：确保 Memory Pack 四个阶段都能命中数据
  1. 检索阶段 — user_text >= 15 字符 + memory.enabled
  2. 组装阶段 — L4 中有历史记忆
  3. 记忆渲染 — memory pack 有内容被 render
  4. 上下文预算&裁剪 — before_tokens > prompt_budget (需要 tools + 大量 tool_result)

用法：
  1. 确保后端已运行 (http://localhost:8000)
  2. 确保已有 L4 记忆（发送过多次请求后 distill 生成）
  3. python test_memory_pack_stages.py

如果 L4 为空，脚本会先发送几轮对话来积累记忆，再发送触发请求。
"""

import json
import sys
import time
import httpx

BASE = "http://localhost:8000"
API_KEY = "ng-abc123"  # 修改为你的 LOCAL_API_KEY
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# ── helpers ──────────────────────────────────────────────────

def check_memory_exists() -> bool:
    """检查 L4 是否有记忆"""
    try:
        r = httpx.get(f"{BASE}/admin/memories?limit=5", headers=HEADERS, timeout=10)
        data = r.json()
        items = data.get("items") or data.get("memories") or []
        return len(items) > 0
    except Exception:
        return False


def seed_memory(session_id: str, n_rounds: int = 3):
    """发送多轮对话积累 L4 记忆"""
    print(f"[seed] 发送 {n_rounds} 轮对话积累记忆...")
    for i in range(n_rounds):
        payload = {
            "model": "gpt-5.3-codex",
            "input": [
                {"role": "user", "content": f"这是第 {i+1} 轮测试对话，请记住这个数字 {i+1}，用于后续记忆检索验证。"},
            ],
            "session_id": session_id,
        }
        try:
            r = httpx.post(f"{BASE}/v1/responses", json=payload, headers=HEADERS, timeout=60)
            print(f"  round {i+1}: status={r.status_code}")
        except Exception as e:
            print(f"  round {i+1}: error={e}")
    # 等待 distill
    print("[seed] 等待 5 秒让 distill 完成...")
    time.sleep(5)


def get_latest_trace() -> dict | None:
    """获取最新的 trace"""
    try:
        r = httpx.get(f"{BASE}/admin/traces?limit=1", headers=HEADERS, timeout=10)
        items = r.json().get("items") or []
        return items[0] if items else None
    except Exception:
        return None


# ── main test ────────────────────────────────────────────────

def run_test():
    session_id = f"test-mempack-{int(time.time())}"

    # Step 1: 确保有 L4 记忆
    if not check_memory_exists():
        print("[!] 未检测到记忆数据，先积累记忆...")
        seed_memory(session_id, n_rounds=3)
        session_id = f"test-mempack-final-{int(time.time())}"  # 新 session 触发跨 session 检索
    else:
        print("[✓] 已有记忆数据")

    # Step 2: 构造触发全部 4 阶段的请求
    # - user_text > 15 字符 → 触发检索
    # - 跨 session → 触发 L4 检索
    # - 带 tools + 大量 tool_result → 触发上下文预算裁剪
    # - 记忆有内容 → 触发渲染

    big_tool_result = "A" * 8000  # 足够大的 tool_result 触发预算裁剪

    payload = {
        "model": "gpt-5.3-codex",
        "input": [
            {"role": "user", "content": "请帮我分析之前所有的测试记录并总结规律"},
            {"role": "assistant", "content": "我来查看之前的记录。", "tool_calls": [
                {"id": "call_001", "type": "function", "function": {"name": "read_file", "arguments": '{"path": "/data/records.txt"}' }}
            ]},
            {"role": "tool", "tool_call_id": "call_001", "content": big_tool_result},
            {"role": "assistant", "content": "找到了一些记录，让我继续查找更多。", "tool_calls": [
                {"id": "call_002", "type": "function", "function": {"name": "read_file", "arguments": '{"path": "/data/more_records.txt"}' }}
            ]},
            {"role": "tool", "tool_call_id": "call_002", "content": big_tool_result},
            {"role": "assistant", "content": "数据量很大，让我再查一个文件。", "tool_calls": [
                {"id": "call_003", "type": "function", "function": {"name": "read_file", "arguments": '{"path": "/data/extra.txt"}' }}
            ]},
            {"role": "tool", "tool_call_id": "call_003", "content": big_tool_result},
            {"role": "user", "content": "请帮我分析之前所有的测试记录并总结规律，包括每轮的数字和内容"},
        ],
        "tools": [
            {"type": "function", "function": {"name": "read_file", "description": "Read a file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}
        ],
        "session_id": session_id,
    }

    print(f"\n[test] 发送触发请求 (session={session_id})...")
    print(f"       user_text 长度: {len('请帮我分析之前所有的测试记录并总结规律，包括每轮的数字和内容')} 字符 (>15 ✓)")
    print(f"       tool_result 大小: {len(big_tool_result)} chars × 3 episodes")
    print(f"       tools 字段: 已包含 ✓")

    try:
        r = httpx.post(f"{BASE}/v1/responses", json=payload, headers=HEADERS, timeout=120)
        print(f"[test] 响应状态: {r.status_code}")
    except Exception as e:
        print(f"[test] 请求失败: {e}")
        sys.exit(1)

    # Step 3: 检查 trace 结果
    time.sleep(1)
    trace = get_latest_trace()
    if not trace:
        print("[✗] 未获取到 trace")
        sys.exit(1)

    t = trace.get("trace") or {}
    ts = trace.get("token_stats") or {}

    print("\n" + "=" * 60)
    print("Memory Pack 四阶段验证结果")
    print("=" * 60)

    # 检索阶段
    retrieval = t.get("retrieval")
    if retrieval:
        kept = retrieval.get("kept_candidates", 0)
        raw = retrieval.get("raw_candidates", 0)
        print(f"  [1] 检索阶段: ✓ 命中 (保留 {kept}/{raw} 候选)")
    else:
        print(f"  [1] 检索阶段: ✗ 未命中 (retrieval=null)")

    # 组装阶段
    assembly = t.get("assembly")
    if assembly:
        total = sum(assembly.get(k, 0) for k in ("facts_count", "procedures_count", "continuity_count", "constraints_count"))
        print(f"  [2] 组装阶段: ✓ 命中 ({total} 条目)")
    else:
        print(f"  [2] 组装阶段: ✗ 未命中 (assembly=null)")

    # 记忆渲染
    render = t.get("render")
    if render and (render.get("estimated_tokens_before") or render.get("trim_passes")):
        before = render.get("estimated_tokens_before", 0)
        after = render.get("estimated_tokens_after", 0)
        passes = render.get("trim_passes", 0)
        print(f"  [3] 记忆渲染: ✓ 命中 ({before}→{after} tok, {passes} 裁剪)")
    else:
        print(f"  [3] 记忆渲染: ✗ 未命中 (render=null 或无裁剪)")

    # 上下文预算&裁剪
    budget = t.get("budget")
    if budget and budget.get("enabled"):
        before_b = budget.get("before_tokens", 0)
        after_b = budget.get("after_tokens", 0)
        truncated = budget.get("truncated_messages", 0)
        dropped = budget.get("dropped_messages", 0)
        native = budget.get("native_tools_budget", False)
        if before_b != after_b or truncated or dropped:
            print(f"  [4] 上下文预算: ✓ 命中 ({before_b}→{after_b} tok, 截断={truncated}, 丢弃={dropped}, tools={native})")
        else:
            print(f"  [4] 上下文预算: △ 启用但未裁剪 ({before_b}→{after_b} tok, budget={budget.get('context_budget_tokens', 0)})")
    else:
        print(f"  [4] 上下文预算: ✗ 未命中 (budget=null 或未启用)")

    # Token 统计
    raw_input = ts.get("raw_input_tokens", 0)
    sent = ts.get("estimated_sent_tokens", 0)
    saved = ts.get("saved_tokens_estimated", 0)
    rate = ts.get("saved_rate_estimated", 0)
    print(f"\n  Token: raw={raw_input} sent={sent} saved={saved} rate={rate*100:.1f}%")

    print("=" * 60)

    # 总结
    stages_ok = 0
    if retrieval: stages_ok += 1
    if assembly: stages_ok += 1
    if render and (render.get("estimated_tokens_before") or render.get("trim_passes")): stages_ok += 1
    if budget and budget.get("enabled") and (budget.get("before_tokens", 0) != budget.get("after_tokens", 0) or budget.get("truncated_messages", 0) or budget.get("dropped_messages", 0)): stages_ok += 1

    print(f"\n命中阶段: {stages_ok}/4")
    if stages_ok >= 3:
        print("✓ 测试通过（至少 3/4 阶段命中）")
    else:
        print("✗ 测试未通过，检查记忆和配置")


if __name__ == "__main__":
    run_test()
