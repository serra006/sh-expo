# -*- coding: utf-8 -*-
"""用最新的 admission_of 规则重算已有数据的「参加办法」，不重新抓取源站。

改了公众号 / 通道文案后，让 data/*.json 立即跟上，
避免为了一个字段重跑三源抓取（会带来展会增删的额外波动）。
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from fetch import admission_of  # noqa: E402

CST = timezone(timedelta(hours=8))


def refit(rel_path, stamp):
    path = os.path.join(BASE, rel_path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    events = data.get("events") or []
    for e in events:
        e["admit"] = admission_of(
            e.get("name", ""), e.get("category", ""), e.get("official_type", ""))
    data["updated"] = stamp
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    print("%-26s %4d 场" % (rel_path, len(events)))


def main():
    stamp = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
    refit("data/events.json", stamp)
    refit("data/events_active.json", stamp)
    print("updated =", stamp)


if __name__ == "__main__":
    main()
