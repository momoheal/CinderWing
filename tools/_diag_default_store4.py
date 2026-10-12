"""诊断 v4：手动走 blob 解析链路，定位 default store 失败点。"""
import io
import traceback
from pathlib import Path

from ccl_chromium_reader.ccl_chromium_indexeddb import (
    WrappedIndexDB, IndexedDb, IdbKey, _le_varint_from_bytes)

ld = Path(r"C:\Users\admin\AppData\Local\Temp\cinderwing_idb\leveldb")
bl = Path(r"C:\Users\admin\AppData\Local\Temp\cinderwing_idb\blob")
w = WrappedIndexDB(ld, bl)
raw = w._raw_db

prefix = IndexedDb.make_prefix(1, 1, 1)
needle = "default-chat-im-protocol-store".encode("utf-16-be")
recs = [r for r in raw._fetched_records
        if r.key.startswith(prefix) and needle in r.key
        and str(r.state) == "KeyState.Live"]
recs.sort(key=lambda r: r.seq)
rec = recs[-1]
print("newest seq", rec.seq, "vlen", len(rec.value))

raw_key = rec.key[len(prefix):]
print("raw_key tail:", raw_key.hex()[:80])
_, varint_raw = _le_varint_from_bytes(rec.value)
buf = rec.value[len(varint_raw):]
print("envelope:", buf.hex())
# ff 11 01 <size varint> <index varint>
assert buf[0] == 0xff and buf[1] == 0x11 and buf[2] == 0x01
size, v1 = _le_varint_from_bytes(buf[3:])
index, v2 = _le_varint_from_bytes(buf[3 + len(v1):])
print("blob size", size, "blob index", index)

try:
    info = raw.get_blob_info(1, 1, raw_key, index)
    print("blob info:", info)
except KeyError as e:
    print("get_blob_info KeyError:", e)
    info = None

if info is not None:
    p = bl / "1" / f"{info.blob_number >> 8:02x}" / f"{info.blob_number:x}"
    print("expected path:", p, "exists:", p.exists())
    try:
        f = raw.get_blob(1, 1, raw_key, index)
        data = f.read()
        print("blob bytes:", len(data), "head:", data[:16].hex())
    except Exception:
        traceback.print_exc()
