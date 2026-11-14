# -*- coding: utf-8 -*-
"""把人工维护的开发者大会（data/dev_events.json）合并进当日活跃数据。

设计要点：
  1. 不改 fetch.py 的抓取逻辑，只在它产出 events_active.json 之后追加，
     展会那条链路出问题也不会被这里牵连。
  2. 已结束的活动自动剔除，和展会口径一致（App 只展示未结束的）。
  3. 合并后重新算 status，App 的「进行中 / 一周内」筛选对两类活动都成立。
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
CST = timezone(timedelta(hours=8))
ACTIVE = os.path.join(ROOT, "data", "events_active.json")
DEV = os.path.join(ROOT, "data", "dev_events.json")


def today():
    return datetime.now(CST).date()


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")


def status_of(start, end, t):
    d = lambda s: datetime.strptime(s[:10], "%Y-%m-%d").date()
    try:
        s, e = d(start), d(end or start)
    except (ValueError, TypeError):
        return "upcoming"
    if t < s:
        return "upcoming"
    if t > e:
        return "past"
    return "ongoing"


def main():
    if not os.path.exists(DEV):
        print("[SKIP] 没有 data/dev_events.json")
        return 0
    if not os.path.exists(ACTIVE):
        print("[FAIL] 缺少 data/events_active.json，请先跑 fetch.py")
        return 1

    payload = load(ACTIVE)
    expo = payload.get("events") or []
    dev_all = load(DEV).get("events") or []
    t = today()

    dev, dropped = [], []
    for e in dev_all:
        st = status_of(e.get("start"), e.get("end"), t)
        if st == "past":
            dropped.append(e.get("name", "?"))
            continue
        e["status"] = st
        e["kind_type"] = "dev"
        dev.append(e)

    known = set(e.get("id") for e in expo)
    fresh = [e for e in dev if e.get("id") not in known]

    merged = expo + fresh
    payload["events"] = merged
    payload["count"] = len(merged)
    dump(ACTIVE, payload)

    print("[OK] 合并开发者大会：%d 场（展会 %d + 大会 %d），剔除已结束 %d 场"
          % (len(merged), len(expo), len(fresh), len(dropped)))
    for name in dropped:
        print("     - 已结束：%s" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
