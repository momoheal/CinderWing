"""诊断 v2：解析最新 live default-chat 记录（86 字节）为何失败。"""
import contextlib
import io
import traceback
from pathlib import Path

from ccl_chromium_reader.ccl_chromium_indexeddb import WrappedIndexDB, IdbKey
from ccl_chromium_reader.serialization_formats import (
    ccl_blink_value_deserializer as bvd,
    ccl_v8_value_deserializer as v8d)

ld = Path(r"C:\Users\admin\AppData\Local\Temp\geoharbour_pet_idb\leveldb")
bl = Path(r"C:\Users\admin\AppData\Local\Temp\geoharbour_pet_idb\blob")
w = WrappedIndexDB(ld, bl)
raw = w._raw_db

needle = "default-chat-im-protocol-store".encode("utf-16-be")
hits = [r for r in raw._fetched_records if needle in r.key]
hits.sort(key=lambda r: r.seq)
live = [r for r in hits if str(r.state) == "KeyState.Live"]
print("total", len(hits), "live", len(live))
for rec in live[-4:]:
    print("seq", rec.seq, "origin", rec.origin_file.name,
          "vlen", len(rec.value), "head", rec.value[:16].hex())

rec = live[-1]
buf = rec.value
print("\n--- parse newest live ---")


def handler(k, b):
    print("BAD HANDLER head:", b[:16].hex())


try:
    with contextlib.redirect_stdout(io.StringIO()):
        pre = raw.read_record_precursor(
            IdbKey(b"default-chat-im-protocol-store"), 1, 1, buf[1:], handler)
    print("precursor:", None if pre is None else
          (pre[0], len(pre[1].getvalue()), pre[3]))
    if pre and pre[0] is not None:
        ver, obj_raw, trailer, ext = pre
        try:
            d = v8d.Deserializer(
                obj_raw, host_object_delegate=bvd.BlinkV8Deserializer().read)
            v = d.read()
            print("parsed OK", type(v), str(v)[:300])
        except Exception:
            traceback.print_exc()
except Exception:
    traceback.print_exc()
