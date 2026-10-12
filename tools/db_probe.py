# Read-only probe: scan Chromium LevelDB/.ldb files for task & cowork related strings.
import re, glob

targets = []
targets += glob.glob(r"C:\Users\admin\AppData\Local\DoubaoWork\User Data\Default\saman_shell_db_storage\*.ldb")
targets += glob.glob(r"C:\Users\admin\AppData\Local\DoubaoWork\User Data\Default\Local Storage\leveldb\*.ldb")
targets += glob.glob(r"C:\Users\admin\AppData\Local\DoubaoWork\User Data\Default\IndexedDB\chrome_doubaowork-chat_0.indexeddb.leveldb\*.ldb")
targets += glob.glob(r"C:\Users\admin\AppData\Local\DoubaoWork\User Data\Default\IndexedDB\chrome_doubao-office_0.indexeddb.leveldb\*.ldb")

kw = ['task', 'cowork', 'complete', 'collaborat', 'assign', '任务', '完成', '伙伴', '协作', '同事']
# ascii + valid utf-8 multibyte runs
pat = re.compile(rb'(?:[\x20-\x7e]|[\xc2-\xf4][\x80-\xbf]{2}){5,}')

for f in sorted(set(targets)):
    try:
        data = open(f, 'rb').read()
    except Exception as e:
        print(f"== {f} READ ERROR {e}")
        continue
    hits, seen = [], set()
    for m in pat.findall(data):
        try:
            t = m.decode('utf-8')
        except Exception:
            continue
        low = t.lower()
        if any(k.lower() in low for k in kw) and t not in seen:
            seen.add(t)
            hits.append(t)
    print(f"== {f} | {len(data)/1024:.0f}KB | hits={len(hits)}")
    for h in hits[:20]:
        print("   ", h[:220])
