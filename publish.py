# -*- coding: utf-8 -*-
"""发布层：质量闸门 -> 增量比对 -> 产出 App 可拉取的 latest.json / manifest.json。

设计要点：
  1. 坏数据绝不覆盖好数据。任何一个源突然归零、或总量骤降，都要整体判失败。
  2. version 只由 events 内容决定，内容没变 App 就不用重新下载。
  3. 发布目标可插拔：默认写本地 public/（供 GitHub 托管），配了 R2 环境变量就额外上传。
"""
import argparse
import collections
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
CST = timezone(timedelta(hours=8))

# GitHub Actions 会自动注入 GITHUB_REPOSITORY；本地跑时用默认值。
# 端点表随 manifest 下发给 App，以后加 R2 / 换域名都不用改客户端。
REPO = os.environ.get("GITHUB_REPOSITORY", "serra006/sh-expo")
OWNER = REPO.split("/")[0]
NAME = REPO.split("/")[-1]
PAGES_BASE = "https://%s.github.io/%s/public" % (OWNER, NAME)
ENDPOINTS = [
    PAGES_BASE,
    "https://cdn.jsdelivr.net/gh/%s@main/public" % REPO,
    "https://raw.githubusercontent.com/%s/main/public" % REPO,
]


def stamp():
    return datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")


def today_str():
    return datetime.now(CST).strftime("%Y-%m-%d")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def dump(path, obj, pretty=False):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        else:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")


def source_counts(events):
    return dict(collections.Counter(e.get("source", "?") for e in events))


def merge_dev(payload):
    """把人工维护的开发者大会并入展会数据。

    放在发布层而不是 fetch.py：这类活动没有稳定的机器可读源，靠人工清单维护，
    和展会抓取是两条完全独立的链路，混在一起改反而容易互相牵连。
    已结束的活动直接剔除，口径与展会一致（App 只展示未结束的）。
    """
    path = os.path.join(ROOT, "data", "dev_events.json")
    if not os.path.exists(path):
        return 0, []
    try:
        devs = load(path).get("events") or []
    except (ValueError, OSError) as e:
        print("[WARN] dev_events.json 读取失败，跳过开发者大会：%s" % e)
        return 0, []

    today = datetime.now(CST).date()

    def status_of(e):
        try:
            s = datetime.strptime(str(e.get("start"))[:10], "%Y-%m-%d").date()
            en = datetime.strptime(str(e.get("end") or e.get("start"))[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return "upcoming"
        if today < s:
            return "upcoming"
        return "past" if today > en else "ongoing"

    events = payload.get("events") or []
    known = set(e.get("id") for e in events)
    added, dropped = [], []
    for e in devs:
        st = status_of(e)
        if st == "past":
            dropped.append(e.get("name", "?"))
            continue
        if e.get("id") in known:
            continue
        e["status"] = st
        e["kind_type"] = "dev"
        added.append(e)

    if added:
        payload["events"] = events + added
        payload["count"] = len(payload["events"])
    return len(added), dropped


def validate(payload, prev, min_ratio, min_count, max_age_hours):
    """返回问题列表；空列表表示可以发布。"""
    problems = []
    events = payload.get("events") or []
    n = len(events)

    # fetch.py 静默失败时不会改写文件，旧数据会被当成新数据发布，这里按时间戳拦住
    try:
        t = datetime.strptime((payload.get("updated") or "")[:19],
                              "%Y-%m-%d %H:%M:%S").replace(tzinfo=CST)
        age_h = (datetime.now(CST) - t).total_seconds() / 3600.0
        if age_h > max_age_hours:
            problems.append("数据时间过旧：%.1f 小时前（上限 %s 小时），疑似抓取失败"
                            % (age_h, max_age_hours))
        elif age_h < -1:
            problems.append("数据时间晚于当前时间，检查时区设置")
    except ValueError:
        problems.append("updated 字段缺失或格式异常")

    if n < min_count:
        problems.append("场次过少：%d 条，低于下限 %d" % (n, min_count))

    for e in events:
        if not all(e.get(k) for k in ("id", "name", "start")):
            problems.append("存在缺少 id / name / start 的条目")
            break

    today = today_str()
    if not any(e.get("status") in ("upcoming", "ongoing") or
               (e.get("end", "") or "") >= today for e in events):
        problems.append("没有任何未结束的展会，疑似只抓到了历史数据")

    if prev:
        pn = prev.get("count") or len(prev.get("events") or [])
        if pn and n < pn * min_ratio:
            problems.append("场次骤降：%d → %d（低于 %d%%），拒绝覆盖上一版"
                            % (pn, n, int(min_ratio * 100)))
        ps = source_counts(prev.get("events") or [])
        ns = source_counts(events)
        for src, cnt in ps.items():
            if cnt >= 3 and ns.get(src, 0) == 0:
                problems.append("数据源 %s 从 %d 场变成 0 场，疑似站点改版" % (src, cnt))

    return problems


def build(payload, prev):
    events = payload["events"]
    version = hashlib.sha256(canon(events)).hexdigest()[:12]

    prev_events = (prev or {}).get("events") or []
    prev_ids = set(e.get("id") for e in prev_events)
    cur_ids = set(e.get("id") for e in events)
    new_ids = [e["id"] for e in events if e["id"] not in prev_ids] if prev else []
    removed = len(prev_ids - cur_ids) if prev else 0

    latest = {
        "updated": payload.get("updated") or stamp(),
        "city": payload.get("city", "上海"),
        "count": len(events),
        "version": version,
        "generated_at": stamp(),
        "new_count": len(new_ids),
        "new_ids": new_ids[:100],
        "removed_count": removed,
        "sources": source_counts(events),
        "events": events,
    }
    raw = canon(latest)
    manifest = {
        "version": version,
        "count": len(events),
        "new_count": len(new_ids),
        "updated": latest["updated"],
        "generated_at": latest["generated_at"],
        "latest_bytes": len(raw),
        "latest_sha256": hashlib.sha256(raw).hexdigest(),
        "endpoints": ENDPOINTS,
    }
    return latest, manifest


def upload_r2(files):
    """files: [(本地路径, 对象键, Cache-Control)]；未配置时静默跳过。"""
    keys = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")
    cfg = {k: os.environ.get(k) for k in keys}
    if not all(cfg.values()):
        return "跳过（未配置 R2 环境变量）"
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        return "跳过（boto3 未安装）"

    s3 = boto3.client(
        "s3",
        endpoint_url="https://%s.r2.cloudflarestorage.com" % cfg["R2_ACCOUNT_ID"],
        aws_access_key_id=cfg["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=cfg["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )
    for local, key, cache in files:
        s3.upload_file(
            local, cfg["R2_BUCKET"], key,
            ExtraArgs={"ContentType": "application/json; charset=utf-8",
                       "CacheControl": cache},
        )
    return "已上传 %d 个对象到 R2/%s" % (len(files), cfg["R2_BUCKET"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=os.path.join(ROOT, "data", "events_active.json"))
    ap.add_argument("--public", default=os.path.join(ROOT, "public"))
    ap.add_argument("--snapshots", default=os.path.join(ROOT, "data", "snapshots"))
    ap.add_argument("--min-ratio", type=float, default=0.70)
    ap.add_argument("--min-count", type=int, default=30)
    ap.add_argument("--max-age", type=float, default=3.0,
                    help="数据时间戳最长允许滞后多少小时（默认 3，CI 抓取后应为 0）")
    ap.add_argument("--force", action="store_true", help="跳过质量闸门（仅人工排障用）")
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()

    prev_path = os.path.join(args.public, "latest.json")
    health_path = os.path.join(args.public, "health.json")
    prev = load(prev_path) if os.path.exists(prev_path) else None
    payload = load(args.input)
    added_dev, dropped_dev = merge_dev(payload)
    events = payload.get("events") or []
    if added_dev or dropped_dev:
        print("[DEV] 开发者大会：并入 %d 场，剔除已结束 %d 场"
              % (added_dev, len(dropped_dev)))

    problems = [] if args.force else validate(
        payload, prev, args.min_ratio, args.min_count, args.max_age)
    if problems:
        dump(health_path, {
            "ok": False, "checked_at": stamp(),
            "prev_version": (prev or {}).get("version", ""),
            "prev_count": (prev or {}).get("count", 0),
            "attempt_count": len(events), "problems": problems,
        }, pretty=True)
        print("[BLOCK] 质量闸门未通过，保留上一版：")
        for p in problems:
            print("   -", p)
        return 1

    latest, manifest = build(payload, prev)
    latest_path = os.path.join(args.public, "latest.json")
    manifest_path = os.path.join(args.public, "manifest.json")
    dump(latest_path, latest)
    dump(manifest_path, manifest, pretty=True)

    snap = os.path.join(args.snapshots, today_str() + ".json")
    dump(snap, payload)

    note = "跳过（--no-upload）" if args.no_upload else upload_r2([
        (manifest_path, "manifest.json", "public, max-age=60"),
        (latest_path, "latest.json", "public, max-age=300"),
        (snap, "snapshots/%s.json" % today_str(), "public, max-age=86400"),
    ])

    dump(health_path, {
        "ok": True, "checked_at": stamp(),
        "version": latest["version"], "count": latest["count"],
        "new_count": latest["new_count"], "removed_count": latest["removed_count"],
        "sources": latest["sources"], "publish": note,
    }, pretty=True)

    changed = (not prev) or prev.get("version") != latest["version"]
    print("[OK] version=%s count=%d 新增=%d 移除=%d 变化=%s"
          % (latest["version"], latest["count"], latest["new_count"],
             latest["removed_count"], "是" if changed else "否"))
    print("     manifest %d B / latest %d B" %
          (os.path.getsize(manifest_path), os.path.getsize(latest_path)))
    print("     " + note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
