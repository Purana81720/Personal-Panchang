#!/usr/bin/env python3
"""
Schedule hora-change notifications (plus a morning briefing) through ntfy.

ntfy (https://ntfy.sh) can deliver a message at a future time (delay between 10 seconds
and 3 days), so a daily job can queue the next day's alerts and your phone gets them even
though nothing is running on it. Install the free ntfy iOS app and subscribe to your topic.

Environment:
    NTFY_TOPIC    required (unless --dry-run). Use a long random string; anyone who knows it can read it.
    NTFY_SERVER   default https://ntfy.sh
    NTFY_TOKEN    optional access token (higher limits, reserved topic)
    SITE_URL      optional, opened when you tap a notification

Usage:
    python generator/notify.py --dry-run          # show what would be scheduled for tomorrow
    python generator/notify.py                    # schedule tomorrow (civil date in your timezone)
    python generator/notify.py --date 2026-11-14  # schedule a specific local date
    python generator/notify.py --test             # send one immediate test notification

Run it once per day. Running it twice for the same date schedules duplicates.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from enrich import fmt_range, fmt_time  # noqa: E402
from generate import load_config, make_engine  # noqa: E402
from enrich import build_day  # noqa: E402

MAX_DELAY = 3 * 86400 - 600   # ntfy allows at most 3 days ahead
MIN_DELAY = 20                # ntfy needs at least 10 seconds


def _hour(s, default):
    try:
        return int(str(s).split(":")[0]), int(str(s).split(":")[1]) if ":" in str(s) else 0
    except Exception:
        return default, 0


def plan(cfg, target: date, now: float):
    """Return a list of notifications [{ts, title, message, kind}] for the civil date `target`."""
    eng = make_engine(cfg)
    tz = eng.tz
    n = cfg.get("notify", {})
    mode = n.get("horas", "all")                      # "all" | "highlights" | "off"
    lo_h, _ = _hour(n.get("active_from", "06:00"), 6)
    hi_h, _ = _hour(n.get("active_until", "23:00"), 23)
    b_h, b_m = _hour(n.get("briefing_time", "07:00"), 7)

    day_start = datetime(target.year, target.month, target.day, tzinfo=tz).timestamp()
    day_end = datetime.combine(target + timedelta(days=1), datetime.min.time(), tzinfo=tz).timestamp()

    # The civil day straddles two Vedic days (hora 19-24 of the previous one run past midnight).
    days = [build_day(eng, cfg, target - timedelta(days=1)), build_day(eng, cfg, target)]
    out = []

    if mode != "off":
        for d in days:
            for h in d["horas"]:
                if not (day_start <= h["start"] < day_end):
                    continue
                hr = datetime.fromtimestamp(h["start"], tz).hour
                if not (lo_h <= hr < hi_h):
                    continue
                if mode == "highlights" and h["rating"] not in ("Favorable", "Good", "Avoid"):
                    continue
                lines = [f"{fmt_range(h['start'], h['end'], tz)} · {h['tithi']} · {h['nakshatra']}", h["tip"]]
                lines += [f"▲ {w}" for w in h["warnings"][:2]]
                out.append({"ts": h["start"], "kind": "hora",
                            "title": f"{h['glyph']} {h['planet']} hora · {h['rating']}",
                            "message": "\n".join(lines)})

    today = days[1]
    b_ts = datetime(target.year, target.month, target.day, b_h, b_m, tzinfo=tz).timestamp()
    brief = today["briefing"]
    body = brief["text"].split("\n", 1)[1] if "\n" in brief["text"] else brief["text"]
    if brief.get("personal"):
        body += "\n" + "\n".join(brief["personal"].values())
    out.append({"ts": b_ts, "kind": "briefing", "title": f"☀ {brief['headline']}", "message": body})

    out.sort(key=lambda x: x["ts"])
    return [x for x in out if now + MIN_DELAY <= x["ts"] <= now + MAX_DELAY]


# ---- ntfy -------------------------------------------------------------------
def _rfc2047(s: str) -> str:
    try:
        s.encode("ascii")
        return s
    except UnicodeEncodeError:
        return "=?UTF-8?B?" + base64.b64encode(s.encode("utf-8")).decode() + "?="


def _post(req, retries=5):
    wait = 3.0
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code == 429 or e.code >= 500:
                delay = float(e.headers.get("Retry-After", wait))
                time.sleep(min(delay, 60))
                wait *= 2
                continue
            return e.code, body
        except urllib.error.URLError:
            time.sleep(wait)
            wait *= 2
    return 0, "network error after retries"


def publish(server, topic, item, token=None, click=None, immediate=False):
    auth = {"Authorization": f"Bearer {token}"} if token else {}
    payload = {"topic": topic, "title": item["title"], "message": item["message"]}
    if click:
        payload["click"] = click
    if not immediate:
        payload["delay"] = str(int(item["ts"]))
    req = urllib.request.Request(server.rstrip("/") + "/", data=json.dumps(payload).encode("utf-8"),
                                 method="POST", headers={"Content-Type": "application/json", **auth})
    status, body = _post(req)
    if status == 200:
        return True, body
    # Fallback: header-style publishing (the other documented way to schedule).
    headers = {"Title": _rfc2047(item["title"]), **auth}
    if click:
        headers["Click"] = click
    if not immediate:
        headers["At"] = str(int(item["ts"]))
    req = urllib.request.Request(f"{server.rstrip('/')}/{topic}", data=item["message"].encode("utf-8"),
                                 method="POST", headers=headers)
    status2, body2 = _post(req)
    return status2 == 200, f"json: {status} {body[:120]} | headers: {status2} {body2[:120]}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config")
    ap.add_argument("--date", help="local civil date to schedule (default: tomorrow)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--test", action="store_true", help="send one immediate test notification and exit")
    args = ap.parse_args()

    cfg = load_config(args.config, private=True)
    server = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
    topic = os.environ.get("NTFY_TOPIC", "")
    token = os.environ.get("NTFY_TOKEN") or None
    click = os.environ.get("SITE_URL") or None

    if args.test:
        if not topic:
            sys.exit("NTFY_TOPIC is not set")
        ok, info = publish(server, topic, {"title": "☉ Panchang test", "message": "If you can read this, notifications work."},
                           token, click, immediate=True)
        print("sent" if ok else f"FAILED: {info}")
        sys.exit(0 if ok else 1)

    eng = make_engine(cfg)
    now = time.time()
    target = date.fromisoformat(args.date) if args.date else datetime.fromtimestamp(now, eng.tz).date() + timedelta(days=1)
    items = plan(cfg, target, now)
    print(f"{len(items)} notification(s) for {target} ({cfg['tz']})")

    if args.dry_run:
        for it in items:
            print(f"- {fmt_time(it['ts'], eng.tz):>8}  [{it['kind']}] {it['title']}")
            print("    " + it["message"].replace("\n", "\n    "))
        return
    if not topic:
        sys.exit("NTFY_TOPIC is not set (use --dry-run to preview)")

    failed = 0
    for it in items:
        ok, info = publish(server, topic, it, token, click)
        if not ok:
            failed += 1
            print(f"FAILED {fmt_time(it['ts'], eng.tz)} {it['title']}: {info}", file=sys.stderr)
        time.sleep(0.4)
    print(f"scheduled {len(items) - failed}/{len(items)}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
