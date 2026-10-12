"""探查 10082 interaction_ask_block 的完整结构（疑似 WAITING 信号）。"""
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
for tid, t in tasks.items():
    if not isinstance(t, dict) or not src._is_real_agent_task(t):
        continue
    for rid, v in (t.get("receivedMessages", {}) or {}).items():
        ex = v.get("extra", {}) or {}
        for i, cb in enumerate(ex.get("content_blocks_v2", []) or []):
            if cb.get("block_type") == 10082:
                name = src._query_text(t)[:40]
                cid, sid = src._conv_ids(t)
                print("=== task", tid, repr(name), "conv", cid, sid)
                print("block index", i, "is_finish", cb.get("is_finish"),
                      "parent", cb.get("parent_id"))
                print(json.dumps(cb.get("content", {}), ensure_ascii=False,
                                 indent=1)[:2500])
                ext2 = ex.get("ext", {}) or {}
                print("msg ext.is_finish:", ext2.get("is_finish"),
                      "permission_interact:",
                      ((t.get("requestQuery", {}) or {}).get("syncTask", {})
                       or {}).get("option", {}).get("permission_interact"))
