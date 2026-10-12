# Spike v3: recursively locate mainTaskDataMap inside IndexedDB record VALUES.
# Usage: python idb_spike3.py <snapshot_dir>
import json, sys, pathlib
from ccl_chromium_reader.ccl_chromium_indexeddb import WrappedIndexDB

snap = pathlib.Path(sys.argv[1])
blob = snap / "blob"
wrapper = WrappedIndexDB(snap / "leveldb", blob if blob.exists() else None)


def walk_find(obj, target, path="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == target:
                yield path + "." + str(k), v
            yield from walk_find(v, target, path + "." + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_find(v, target, f"{path}[{i}]")


for dbid in wrapper.database_ids:
    db = wrapper[dbid.dbid_no]
    for store_name in db.object_store_names:
        store = db[store_name]
        for rec in store.iterate_records(
                errors_to_stdout=True,
                bad_deserializer_data_handler=lambda k, v: print("  BAD", k)):
            key_repr = repr(rec.key)
            found = list(walk_find(rec.value, "mainTaskDataMap"))
            if not found:
                continue
            print(f"\n### db={dbid.name!r} store={store_name!r} record_key={key_repr} "
                  f"value_type={type(rec.value).__name__}")
            for p, v in found:
                print(f"  mainTaskDataMap at {p} | entries={len(v) if isinstance(v, dict) else '?'}")
                try:
                    s = json.dumps(v, default=str, ensure_ascii=False)
                except Exception as e:
                    s = f"<err {e}: {v!r}>"
                print("  TASKMAP:", s[:4000])
