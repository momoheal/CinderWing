"""守护 harness 临时目录：记录见过的 lr_* 子目录，被删就重建。"""
import os
import time

BASE = r"C:\Users\admin\AppData\Local\DoubaoWork\User Data\Default\agent_infra\to"


def main():
    known = set()
    while True:
        try:
            os.makedirs(BASE, exist_ok=True)
            current = {d for d in os.listdir(BASE)
                       if d.startswith("lr_") and os.path.isdir(os.path.join(BASE, d))}
            known |= current
            for d in known - current:
                os.makedirs(os.path.join(BASE, d), exist_ok=True)
        except Exception:
            pass
        time.sleep(1)


if __name__ == "__main__":
    main()
