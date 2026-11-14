# -*- coding: utf-8 -*-
"""本地调试用：把 data/dev_events.json 合并进 data/events_active.json 并回写。

注意：CI 流水线不调用本脚本，线上实际走的是 publish.py 里的 merge_dev()。
这里直接复用同一个函数，避免两处规则分叉——之前就是因为各写一份，
出现过「改了清单线上不生效」的问题。

用法：
    python dev_merge.py          # 合并并覆盖 data/events_active.json
    python publish.py --force    # 正式发布（内部会自动再合一次，幂等）
"""
import json
import os
import sys

from publish import CST, merge_dev

ROOT = os.path.dirname(os.path.abspath(__file__))
ACTIVE = os.path.join(ROOT, "data", "events_active.json")


def main():
    if not os.path.exists(ACTIVE):
        print("[FAIL] 缺少 data/events_active.json，请先跑 fetch.py")
        return 1

    with open(ACTIVE, encoding="utf-8") as f:
        payload = json.load(f)

    before = len(payload.get("events") or [])
    added, dropped = merge_dev(payload)

    with open(ACTIVE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")

    dev = sum(1 for e in payload["events"] if e.get("kind_type") == "dev")
    print("[OK] 合并后 %d 场（原 %d + 新增大会 %d），其中开发者大会 %d 场"
          % (len(payload["events"]), before, added, dev))
    for name in dropped:
        print("     - 已结束：%s" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
