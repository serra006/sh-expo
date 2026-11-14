# -*- coding: utf-8 -*-
"""对现有数据补「参加入口」字段，不重新抓源站，保证场次数不变。

- events_active.json（当前 105 场）：补 website_kind + 探测官网预登记入口 + 票务搜索
- events.json（全量 714 场）：只补 website_kind 和票务搜索，不做网络探测
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from fetch import (  # noqa: E402
    link_kind, enrich_entry, is_ticketed, tickets_of,
)


def patch(path, probe):
    d = json.load(open(path, encoding="utf-8"))
    events = d.get("events", [])
    for e in events:
        e["website_kind"] = link_kind(e.get("website", ""))
        e.pop("signup", None)
        e.pop("tickets", None)

    if probe:
        events = enrich_entry(events)
    else:
        n = 0
        for e in events:
            if is_ticketed(e.get("name", ""), e.get("category", ""),
                           (e.get("admit") or {}).get("kind", "")):
                e["tickets"] = tickets_of(e.get("name", ""))
                n += 1
        print("[票务] %s 加票务入口 %d 场" % (os.path.basename(path), n))

    d["events"] = events
    d["count"] = len(events)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)

    official = sum(1 for e in events if e.get("website_kind") == "official")
    filing = sum(1 for e in events if e.get("website_kind") == "filing")
    signup = sum(1 for e in events if e.get("signup"))
    tick = sum(1 for e in events if e.get("tickets"))
    print("[完成] %s: %d 场 | 官网 %d | 备案页 %d | 有预登记入口 %d | 有票务 %d"
          % (os.path.basename(path), len(events), official, filing, signup, tick))


if __name__ == "__main__":
    patch(os.path.join(BASE, "data", "events_active.json"), probe=True)
    patch(os.path.join(BASE, "data", "events.json"), probe=False)
