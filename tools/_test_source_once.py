"""离线一次性验证 task_source：对当前真实数据库快照跑一遍分类，打印结果。"""
import os
import sys

os.environ.setdefault("PYTHONPATH", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.task_source import DoubaoTaskSource


class _Dummy:
    def notify(self, *a, **k):
        print("  EVENT", a)

    def update_progress(self, *a, **k):
        pass


src = DoubaoTaskSource(_Dummy(), lambda *a: None, lambda *a: None)
src._snapshot()
tasks = src._read_tasks()
print("total records:", len(tasks))
for tid, t in tasks.items():
    if not isinstance(t, dict):
        continue
    real = src._is_real_agent_task(t)
    if not real:
        continue
    kind, pct, detail, ask = src._extract(t)
    name = src._query_text(t)[:30]
    cid, sid = src._conv_ids(t)
    print(f"{tid[:8]} kind={kind} pct={pct} detail={detail}")
    print(f"   name={name!r} conv={cid} sect={sid}")
