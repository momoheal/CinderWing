"""探查当前快照里指定任务的真实字段（终态后记录形态、会话 id 位置）。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.task_source import DoubaoTaskSource


class _D:
    def notify(self, *a, **k):
        pass

    def update_progress(self, *a, **k):
        pass


src = DoubaoTaskSource(_D(), lambda *a: None, lambda *a: None)
src._snapshot()
tasks = src._read_tasks()
target = [t for t in tasks if t.startswith("cc7a5a40")]
assert target, "cc7a not found"
t = tasks[target[0]]

print("top keys:", list(t.keys()))
q = t.get("requestQuery", {})
st = q.get("syncTask", {})
print("syncTask keys:", list(st.keys()) if isinstance(st, dict) else type(st))
# 会话 id 可能在 syncTask 顶层
for k in ("conversation_id", "conversationId", "section_id", "last_section_id",
          "sessionId", "ext"):
    if isinstance(st, dict) and k in st:
        v = st[k]
        print("syncTask.", k, "=", (str(v)[:200] if k != "ext" else list(v.keys()) if isinstance(v, dict) else v))

for mid, v in (t.get("sentMessages", {}) or {}).items():
    print("--- sent msg keys:", list(v.keys()))
    for k in ("conversation_id", "section_id", "last_section_id", "status", "contentStatus"):
        if k in v:
            print("   ", k, "=", v[k])
    ex = v.get("extra", {}) or {}
    print("    extra keys:", list(ex.keys())[:40])
    for k in ("conversation_id", "section_id", "last_section_id"):
        if k in ex:
            print("    extra.", k, "=", ex[k])

for mid, v in (t.get("receivedMessages", {}) or {}).items():
    print("--- recv msg keys:", list(v.keys()))
    ex = v.get("extra", {}) or {}
    print("    extra keys:", list(ex.keys())[:40])
    ext2 = ex.get("ext", {}) or {}
    print("    ext keys:", list(ext2.keys())[:40] if isinstance(ext2, dict) else type(ext2))
    print("    is_finish:", ext2.get("is_finish"), "| reason:", ext2.get("mode_downgrade_reason"))
    print("    extra.status:", ex.get("status"), "stage:", ex.get("stage"),
          "contentStatus:", ex.get("contentStatus"))
    blocks = ex.get("content_blocks_v2", []) or []
    print("    n blocks:", len(blocks))
    # 终态标记可能在块或消息的别的字段；全局搜 is_finish
    s = json.dumps(v, ensure_ascii=False)
    import re
    hits = [m.start() for m in re.finditer(r'is_finish', s)]
    print("    is_finish occurrences:", len(hits))
    for h in hits[:6]:
        print("      ...", s[h:h + 40].replace("\n", " "))
