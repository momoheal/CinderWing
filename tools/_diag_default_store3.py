"""诊断 v3：复刻 iterate_records，对 default store 的失败记录打印真实异常。"""
import contextlib
import io
import traceback
from pathlib import Path

from ccl_chromium_reader.ccl_chromium_indexeddb import WrappedIndexDB, IndexedDb
from ccl_chromium_reader.serialization_formats import (
    ccl_blink_value_deserializer as bvd,
    ccl_v8_value_deserializer as v8d)

ld = Path(r"C:\Users\admin\AppData\Local\Temp\cinderwing_idb\leveldb")
bl = Path(r"C:\Users\admin\AppData\Local\Temp\cinderwing_idb\blob")
w = WrappedIndexDB(ld, bl)
raw = w._raw_db

# db 1 的 store 名 -> id
wdb = w[1]
print("stores:", list(wdb.object_store_names))
store_id = None
for sid, meta in raw.get_object_store_metadata(1).items() if False else []:
    pass

# 直接用 data 记录前缀枚举（store id 通常为 1）
prefix = IndexedDb.make_prefix(1, 1, 1)
needle = "default-chat-im-protocol-store".encode("utf-16-be")
recs = [r for r in raw._fetched_records
        if r.key.startswith(prefix) and needle in r.key
        and str(r.state) == "KeyState.Live"]
recs.sort(key=lambda r: r.seq)
print("live data recs:", len(recs))
if not recs:
    raise SystemExit("no live data recs")

from ccl_chromium_reader.ccl_chromium_indexeddb import (
    IdbKey, _le_varint_from_bytes)

blink_deserializer = bvd.BlinkV8Deserializer()
shown = 0
for rec in recs[::-1][:3]:
    print("\n=== seq", rec.seq, "origin", rec.origin_file.name,
          "vlen", len(rec.value))
    _, varint_raw = _le_varint_from_bytes(rec.value)
    val_idx = len(varint_raw)
    try:
        with contextlib.redirect_stdout(io.StringIO()) as cap:
            pre = raw.read_record_precursor(
                IdbKey(rec.key[len(prefix):]), 1, 1,
                rec.value[val_idx:],
                lambda k, b: print("envelope bad:", b[:12].hex()))
        out = cap.getvalue()
        if out.strip():
            print(out.strip())
        if pre is None:
            print("-> precursor None")
            continue
        ver, obj_raw, trailer, ext = pre
        print("blink ver", ver, "obj bytes", len(obj_raw.getvalue()), "ext", ext)
        d = v8d.Deserializer(obj_raw,
                             host_object_delegate=blink_deserializer.read)
        v = d.read()
        print("-> parsed OK:", type(v), list(v.keys()) if isinstance(v, dict)
              else str(v)[:200])
    except Exception:
        traceback.print_exc()
    shown += 1
