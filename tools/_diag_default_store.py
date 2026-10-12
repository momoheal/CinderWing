"""诊断：为什么 default-chat-im-protocol-store 最新 live 版本反序列化失败。"""
import contextlib
import io
import traceback
from pathlib import Path

from ccl_chromium_reader.storage_formats import ccl_leveldb
from ccl_chromium_reader.ccl_chromium_indexeddb import WrappedIndexDB, IdbKey
from ccl_chromium_reader.serialization_formats import (
    ccl_blink_value_deserializer as bvd,
    ccl_v8_value_deserializer as v8d)

ld = Path(r"C:\Users\admin\AppData\Local\Temp\cinderwing_idb\leveldb")
bl = Path(r"C:\Users\admin\AppData\Local\Temp\cinderwing_idb\blob")
w = WrappedIndexDB(ld, bl)
raw = w._raw_db

cands = []
for rec in raw._fetched_records:
    if b"default-chat-im-protocol-store" in rec.key:
        cands.append(rec)
print("raw recs (any state)", len(cands))
cands.sort(key=lambda r: r.seq)
for rec in cands[-5:]:
    print("seq", rec.seq, "state", rec.state, "origin", rec.origin_file,
          "value len", len(rec.value))

rec = cands[-1]
buf = rec.value


def handler(k, b):
    print("BAD HANDLER, head bytes:", b[:12].hex())


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
            print("parsed OK", type(v))
        except Exception:
            traceback.print_exc()
except Exception:
    traceback.print_exc()
