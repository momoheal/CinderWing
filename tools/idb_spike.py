# Spike: parse a snapshot of Doubao Work chat IndexedDB, dump task-related records.
# Usage: python idb_spike.py <snapshot_dir>
import json, sys, pathlib
from ccl_chromium_reader.ccl_chromium_indexeddb import WrappedIndexDB

snap = pathlib.Path(sys.argv[1])
blob = snap / "blob"
wrapper = WrappedIndexDB(snap / "leveldb", blob if blob.exists() else None)

for dbid in wrapper.database_ids:
    db = wrapper[dbid.dbid_no]
    print(f"\n### DATABASE id={dbid.dbid_no} name={dbid.name!r} origin={dbid.origin!r} "
          f"stores={list(db.object_store_names)}")
    for store_name in db.object_store_names:
        store = db[store_name]
        n = 0
        for rec in store.iterate_records(
                errors_to_stdout=True,
                bad_deserializer_data_handler=lambda k, v: print("  BAD RECORD", k)):
            n += 1
            k = str(rec.key)
            if "mainTaskDataMap" not in k and "Task" not in k:
                continue
            print(f"\n[{store_name}] KEY: {k} | type: {type(rec.value).__name__}")
            try:
                s = json.dumps(rec.value, default=str, ensure_ascii=False)
            except Exception as e:
                s = f"<unserialisable {e}: {rec.value!r}>"
            print("VAL:", s[:2000])
        print(f"  (store {store_name!r}: {n} records)")
