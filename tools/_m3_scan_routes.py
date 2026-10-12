"""扫描豆包工作前端 bundle，寻找会话跳转路由/深度链接格式。"""
import os
import re

ROOT = r"C:\LenovoSoftstore\Install\doubaogongzuo\DoubaoWork\app\local_webcontents"

pats = {
    "chat_route": re.compile(rb'["\'`]/chat/[ -~]{0,80}'),
    "open_url_conv": re.compile(rb'.{60}open-url.{120}'),
}

seen = {k: set() for k in pats}
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
        for k, pat in pats.items():
            for m in pat.findall(b):
                s = m.decode("latin1", "replace")
                if s not in seen[k]:
                    seen[k].add((f, s))

for k, items in seen.items():
    print("====", k, len(items))
    for f, s in list(items)[:25]:
        print(f, "::", s[:200])
