#!/usr/bin/env python3
"""
Generate docs/data.json: three Vedic days (yesterday, today, tomorrow) so the page and
widget can always find the current one, even between midnight and sunrise.

Usage:
    python generator/generate.py                 # today in the configured timezone
    python generator/generate.py --date 2026-11-13
    python generator/generate.py --out /tmp/data.json
Environment overrides (GitHub secrets, so nothing personal lives in this public repo):
  PANCHANG_LAT, PANCHANG_LON, PANCHANG_TZ            location (required unless set in config.json)
  PANCHANG_BIRTH_NAKSHATRA, PANCHANG_BIRTH_MOON_SIGN  birth Moon; used ONLY for private notifications,
                                                      never written to the public data.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from enrich import build_day  # noqa: E402
from panchang_core import Engine  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DISCLAIMER = ("Traditional Jyotish/Muhurta guidance computed from Swiss Ephemeris positions. "
              "Lineages differ; treat as guidance, not prediction or advice.")


def load_config(path=None, private=False):
    """private=True (notifier only) also applies the birth-chart secrets. The public site build never does."""
    cfg = json.loads(Path(path or ROOT / "config.json").read_text(encoding="utf-8"))
    env = os.environ
    if env.get("PANCHANG_LAT"):
        cfg["lat"] = float(env["PANCHANG_LAT"])
    if env.get("PANCHANG_LON"):
        cfg["lon"] = float(env["PANCHANG_LON"])
    if env.get("PANCHANG_PLACE"):
        cfg["place"] = env["PANCHANG_PLACE"]
    if env.get("PANCHANG_TZ"):
        cfg["tz"] = env["PANCHANG_TZ"]
    if private:
        birth = dict(cfg.get("birth") or {})
        if env.get("PANCHANG_BIRTH_NAKSHATRA"):
            birth["nakshatra"] = env["PANCHANG_BIRTH_NAKSHATRA"]
        if env.get("PANCHANG_BIRTH_MOON_SIGN"):
            birth["moon_sign"] = env["PANCHANG_BIRTH_MOON_SIGN"]
        cfg["birth"] = birth
    else:
        cfg["birth"] = {}          # the public page never carries personal (birth-based) guidance
    if cfg.get("lat") is None or cfg.get("lon") is None:
        sys.exit("Location not set: add the PANCHANG_LAT and PANCHANG_LON repository secrets "
                 "(or put lat/lon in config.json for a private copy).")
    return cfg


def make_engine(cfg):
    return Engine(cfg["lat"], cfg["lon"], cfg["tz"], cfg.get("ayanamsa", "lahiri"),
                  cfg.get("elevation_m", 0), cfg.get("sun_disc", "upper"))


def build_data(cfg, today: date, before=1, after=1, eng=None):
    eng = eng or make_engine(cfg)
    days = [build_day(eng, cfg, today + timedelta(days=i)) for i in range(-before, after + 1)]
    now = int(time.time())
    return {
        "meta": {
            "place": cfg.get("public_place", "Private location"),   # the site is public: no coordinates or city
            "tz": cfg["tz"], "ayanamsa": cfg.get("ayanamsa", "lahiri"),
            "generated_ts": now, "for_date": today.isoformat(),
            "engine": "Swiss Ephemeris (pyswisseph, Moshier)", "disclaimer": DISCLAIMER,
            "notify": cfg.get("notify", {}),
        },
        "days": days,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config")
    ap.add_argument("--date", help="civil date YYYY-MM-DD (default: today in configured tz)")
    ap.add_argument("--out", default=str(ROOT / "docs" / "data.json"))
    args = ap.parse_args()

    cfg = load_config(args.config)
    eng = make_engine(cfg)
    if args.date:
        today = date.fromisoformat(args.date)
    else:
        today = datetime.now(eng.tz).date()
    data = build_data(cfg, today, eng=eng)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size/1024:.0f} KB) for {today}")


if __name__ == "__main__":
    main()
