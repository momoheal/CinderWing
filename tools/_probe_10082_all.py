"""汇总所有 10082 interaction_ask_block 的状态取值，校准 WAITING 判定。"""
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
    if not isinstance(t, dict):
        continue
    for rid, v in (t.get("receivedMessages", {}) or {}).items():
        ex = v.get("extra", {}) or {}
        for i, cb in enumerate(ex.get("content_blocks_v2", []) or []):
            if cb.get("block_type") != 10082:
                continue
            ask = (cb.get("content", {}) or {}).get(
                "interaction_ask_block", {}) or {}
            qs = ask.get("questions", []) or []
            ans = [(q.get("question_id"),
                    (q.get("answer") or {}).get("status"),
                    list((q.get("answer") or {}).keys())) for q in qs]
            real = src._is_real_agent_task(t)
            print(f"task={tid[:8]} real_agent={real} blk_finish={cb.get('is_finish')}"
                  f" outer_status={ask.get('status')} answers={ans}")
            print("   proc_text:",
                  (ask.get("thinking_content") or {}).get(
                      "processing_status_text"))
