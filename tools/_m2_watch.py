# M2 lifecycle capture: poll live DoubaoWork IndexedDB, log every task
# stage transition and dump full task objects for field mapping.
# Usage: python _m2_watch.py <work_dir> [interval] [rounds]
import contextlib
import io
import json
import pathlib
import shutil
import sys
import time

from ccl_chromium_reader.ccl_chromium_indexeddb import WrappedIndexDB

SRC = pathlib.Path(
    r"C:\Users\admin\AppData\Local\DoubaoWork\User Data\Default\IndexedDB")
WORK = pathlib.Path(sys.argv[1])
interval = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 150
LD, BL = WORK / "leveldb", WORK / "blob"
DUMP_DIR = WORK / "dumps"
DUMP_DIR.mkdir(parents=True, exist_ok=True)


def snapshot():
    if LD.exists():
        shutil.rmtree(LD, ignore_errors=True)
    if BL.exists():
        shutil.rmtree(BL, ignore_errors=True)
    shutil.copytree(SRC / "chrome_doubaowork-chat_0.indexeddb.leveldb", LD)
    blob_src = SRC / "chrome_doubaowork-chat_0.indexeddb.blob"
    if blob_src.exists():
        shutil.copytree(blob_src, BL)


def read_tasks():
    w = WrappedIndexDB(LD, BL if BL.exists() else None)
    out = {}
    for dbid in w.database_ids:
        if dbid.name != "samantha-web":
            continue
        db = w[dbid.dbid_no]
        with contextlib.redirect_stdout(io.StringIO()):  # silence decode noise
            recs = list(db["store"].iterate_records(
                errors_to_stdout=False,
                bad_deserializer_data_handler=lambda key, record: None))
        for rec in recs:
            state = rec.value.get("state") if isinstance(rec.value, dict) else None
            tmap = state.get("mainTaskDataMap") if isinstance(state, dict) else None
            if isinstance(tmap, dict):
                out.update(tmap)
    return out


def brief(t):
    b = {"stage": t.get("stage") if isinstance(t, dict) else None}
    q = t.get("requestQuery", {}) if isinstance(t, dict) else {}
    st = q.get("syncTask", {}) if isinstance(q, dict) else {}
    opt = st.get("option", {}) if isinstance(st, dict) else {}
    gtp = opt.get("general_task_param") if isinstance(opt, dict) else None
    b["agent"] = bool(gtp)
    msgs = st.get("messages", []) if isinstance(st, dict) else []
    for m in msgs[:1]:
        for blk in m.get("content_block", []):
            txt = blk.get("content", {}).get("text_block", {}).get("text")
            if txt:
                b["query"] = txt[:30]
                break
    sm = t.get("sentMessages", {}) or {}
    rm = t.get("receivedMessages", {}) or {}
    def est(v):
        ex = v.get("extra", {}) or {}
        return ex.get("status", v.get("status"))
    b["sent"] = sorted((est(v), v.get("contentStatus")) for v in sm.values())
    recv, block_types, finals = [], [], []
    for v in rm.values():
        ex = v.get("extra", {}) or {}
        recv.append((ex.get("status", v.get("status")),
                     v.get("contentStatus"), ex.get("stage", v.get("stage"))))
        ff = ex.get("final_status")
        if isinstance(ff, dict) and ff.get("message"):
            finals.append(ff.get("message"))
        for cb in ex.get("content_blocks_v2", []) or []:
            if cb.get("block_type") not in block_types:
                block_types.append(cb.get("block_type"))
        ext2 = ex.get("ext", {}) or {}
        if ext2.get("is_finish"):
            b["finish"] = ext2.get("is_finish")
    b["recv"] = sorted(recv)
    b["blocks"] = block_types
    if finals:
        b["final"] = sorted(set(finals))
    return b


seen_full = set()
prev = {}
for rnd in range(rounds):
    try:
        snapshot()
        cur = read_tasks()
    except Exception as e:
        print(time.strftime("%H:%M:%S"), "ERR", repr(e)[:160], flush=True)
        time.sleep(interval)
        continue
    curb = {}
    for tid, t in cur.items():
        bb = brief(t)
        curb[tid] = bb
        if tid not in seen_full:
            seen_full.add(tid)
            print(time.strftime("%H:%M:%S"), "NEW TASK", tid,
                  json.dumps(bb, ensure_ascii=False), flush=True)
            try:
                (DUMP_DIR / f"{tid}.json").write_text(
                    json.dumps(t, ensure_ascii=False, indent=1, default=str),
                    encoding="utf-8")
            except Exception as e:
                print("  dump failed", repr(e)[:120], flush=True)
        pb = prev.get(tid)
        if pb is not None and pb != bb:
            print(time.strftime("%H:%M:%S"), "UPDATE", tid[:8],
                  json.dumps(bb, ensure_ascii=False), flush=True)
            try:
                (DUMP_DIR / f"{tid}_state{len(list(DUMP_DIR.glob(tid[:8]+'*')))}.json").write_text(
                    json.dumps(t, ensure_ascii=False, indent=1, default=str),
                    encoding="utf-8")
            except Exception:
                pass
    gone = [t for t in prev if t not in curb]
    for tid in gone:
        print(time.strftime("%H:%M:%S"), "REMOVED", tid[:8], flush=True)
    prev = curb
    time.sleep(interval)
print("WATCHER_DONE")
