# Watcher: poll the live Doubao Work IndexedDB and log mainTaskDataMap stage transitions.
# Usage: python watch_tasks.py <work_dir> [interval_seconds] [rounds]
import json, shutil, time, sys, pathlib
from ccl_chromium_reader.ccl_chromium_indexeddb import WrappedIndexDB

SRC = pathlib.Path(r"C:\Users\admin\AppData\Local\DoubaoWork\User Data\Default\IndexedDB")
WORK = pathlib.Path(sys.argv[1])
interval = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 120
LD, BL = WORK / "leveldb", WORK / "blob"


def snapshot():
    if LD.exists():
        shutil.rmtree(LD, ignore_errors=True)
    if BL.exists():
        shutil.rmtree(BL, ignore_errors=True)
    shutil.copytree(SRC / "chrome_doubaowork-chat_0.indexeddb.leveldb", LD)
    blob_src = SRC / "chrome_doubaowork-chat_0.indexeddb.blob"
    if blob_src.exists():
        shutil.copytree(blob_src, BL)


def read_stages():
    w = WrappedIndexDB(LD, BL if BL.exists() else None)
    out = {}
    for dbid in w.database_ids:
        if dbid.name != "samantha-web":
            continue
        db = w[dbid.dbid_no]
        for rec in db["store"].iterate_records(errors_to_stdout=True):
            state = rec.value.get("state") if isinstance(rec.value, dict) else None
            tmap = state.get("mainTaskDataMap") if isinstance(state, dict) else None
            if isinstance(tmap, dict):
                for tid, t in tmap.items():
                    entry = {"stage": t.get("stage")}
                    q = t.get("requestQuery", {})
                    msgs = q.get("syncTask", {}).get("messages", [])
                    if msgs:
                        blocks = msgs[0].get("content_block", [])
                        for b in blocks:
                            txt = b.get("content", {}).get("text_block", {}).get("text")
                            if txt:
                                entry["query"] = txt[:40]
                    out[tid] = entry
    return out


prev = None
for _ in range(rounds):
    try:
        snapshot()
        cur = read_stages()
    except Exception as e:
        print(time.strftime("%H:%M:%S"), "ERR", repr(e), flush=True)
        time.sleep(interval)
        continue
    if cur != prev:
        print(time.strftime("%H:%M:%S"), json.dumps(cur, ensure_ascii=False), flush=True)
        prev = cur
    time.sleep(interval)
print("WATCHER_DONE")
