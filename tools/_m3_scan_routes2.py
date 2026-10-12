"""扫描 section/thread 路由拼接与 open-url 内层 URL 协议。"""
import os
import re

ROOT = r"C:\LenovoSoftstore\Install\doubaogongzuo\DoubaoWork\app\local_webcontents"

patterns = [
    re.compile(rb'.{50}/thread/["\'`].{0,80}'),
    re.compile(rb'.{40}/thread/\.concat\([ -~]{0,120}'),
    re.compile(rb'section_id=[ -~]{0,80}'),
    re.compile(rb'.{30}section_id.{0,30}searchParams.{0,120}'),
    re.compile(rb'doubaowork-chat/chat[ -~]{0,100}'),
]

seen = [set() for _ in patterns]
for dp, _, fs in os.walk(ROOT):
    for f in fs:
        if not f.endswith(".js"):
            continue
        p = os.path.join(dp, f)
        try:
            if os.path.getsize(p) > 30_000_000:
                continue
            b = open(p, "rb").read()
        except Exception:
            continue
        for k, pat in enumerate(patterns):
            for m in pat.findall(b):
                s = m.decode("latin1", "replace")
                key = (f, s[:180])
                if key not in seen[k]:
                    seen[k].add(key)

for k, items in enumerate(seen):
    print("====", patterns[k].pattern[:40], len(items))
    for f, s in list(items)[:12]:
        print(f, "::", s)
