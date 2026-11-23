"""
Builds one "Vedic day" (sunrise to next sunrise): panchang elements with exact
change times, special windows, 24 horas with a transparent rating, and a briefing.
"""
from __future__ import annotations

from datetime import date, datetime

import knowledge as K

MIN_OVERLAP = 10 * 60  # seconds of overlap before a window "touches" a hora


def fmt_time(ts, tz) -> str:
    dt = datetime.fromtimestamp(ts, tz)
    return dt.strftime("%I:%M %p").lstrip("0")


def fmt_range(a, b, tz) -> str:
    return f"{fmt_time(a, tz)}–{fmt_time(b, tz)}"


def fmt_win(w, tz) -> str:
    """Human text for a window that may be clipped to the Vedic day."""
    if w.get("clip_start") and w.get("clip_end"):
        return "all day"
    if w.get("clip_start"):
        return f"until {fmt_time(w['end'], tz)}"
    if w.get("clip_end"):
        return f"from {fmt_time(w['start'], tz)}"
    return fmt_range(w["start"], w["end"], tz)


def overlap(a0, a1, b0, b1) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def dominant(segs, a, b):
    """Segment that covers most of [a, b]."""
    return max(segs, key=lambda s: overlap(s["start"], s["end"], a, b))


def containing(segs, t):
    for s in segs:
        if s["start"] <= t < s["end"]:
            return s
    return segs[-1] if t >= segs[-1]["end"] else segs[0]


# ---- annotate raw segments --------------------------------------------------
def _tithi_seg(s):
    d = K.tithi_info(s["idx"])
    d.update(start=int(round(s["start"])), end=int(round(s["end"])))
    return d


def _nak_seg(s, birth_nak):
    name, lord, group = K.NAKSHATRAS[s["idx"]]
    d = {"n": s["idx"] + 1, "name": name, "lord": lord, "group": group,
         "start": int(round(s["start"])), "end": int(round(s["end"]))}
    if birth_nak is not None:
        c = (s["idx"] - birth_nak) % 27 + 1
        tara = c % 9 or 9
        d["tara"] = {"n": tara, "name": K.TARA_NAMES[tara],
                     "good": None if tara == 1 else (tara not in K.TARA_BAD)}
    return d


def _yoga_seg(s):
    name = K.YOGA_NAMES[s["idx"]]
    return {"n": s["idx"] + 1, "name": name, "challenging": name in K.YOGA_CHALLENGING,
            "start": int(round(s["start"])), "end": int(round(s["end"]))}


def _karana_seg(s):
    name = K.karana_name(s["idx"])
    return {"n": s["idx"], "name": name, "vishti": name == "Vishti",
            "start": int(round(s["start"])), "end": int(round(s["end"]))}


def _sign_seg(s, birth_sign):
    sa, en = K.RASHI[s["idx"]]
    d = {"n": s["idx"] + 1, "name": sa, "english": en,
         "start": int(round(s["start"])), "end": int(round(s["end"]))}
    if birth_sign is not None:
        house = (s["idx"] - birth_sign) % 12 + 1
        d["chandra"] = {"house": house, "good": house in K.CHANDRA_GOOD_HOUSES}
    return d


# ---- scoring a single hora --------------------------------------------------
def score_hora(planet, tithi, nak, yoga, karana, sign, flags, vara_lord, waxing):
    reasons = []

    def add(text, delta):
        if delta:
            reasons.append({"t": text, "d": delta})
        else:
            reasons.append({"t": text, "d": 0})

    base = K.HORA[planet]["base"]
    if planet == "Moon":
        base = K.SCORE["waxing_moon_hora"] if waxing else 0
        add(f"Moon hora ({'waxing' if waxing else 'waning'} Moon)", base)
    else:
        add(f"{planet} hora is {'a gentle' if base > 0 else 'a demanding' if base < 0 else 'a neutral'} "
            f"time for new starts", base)
    score = base

    g = K.NAK_GROUP[nak["group"]]
    add(f"{nak['name']} is a {g['label']} ({nak['group']}) nakshatra", g["delta"])
    score += g["delta"]

    lord = nak["lord"]
    rel = K.FRIENDS.get(planet)
    if rel and lord in rel["friends"]:
        add(f"{planet} is friendly with {lord}, lord of {nak['name']}", K.SCORE["lord_friend"])
        score += K.SCORE["lord_friend"]
    elif rel and lord in rel["enemies"]:
        add(f"{planet} is at odds with {lord}, lord of {nak['name']}", K.SCORE["lord_enemy"])
        score += K.SCORE["lord_enemy"]
    elif planet == lord:
        add(f"{planet} hora matches the nakshatra lord", 1)
        score += 1

    tdelta = K.TITHI_CAT_INFO[tithi["category"]]["delta"]
    label = f"{tithi['paksha']} {tithi['name']}"
    if tithi["n"] == 30:
        add(f"{label} (new moon) is not for fresh starts", K.SCORE["amavasya"])
        score += K.SCORE["amavasya"]
    elif tdelta:
        add(f"{label} is a {tithi['category']} tithi", tdelta)
        score += tdelta

    if yoga["challenging"]:
        add(f"{yoga['name']} yoga is considered challenging", K.SCORE["yoga_challenging"])
        score += K.SCORE["yoga_challenging"]
    if karana["vishti"]:
        add("Vishti (Bhadra) karana: avoid new starts", K.SCORE["vishti"])
        score += K.SCORE["vishti"]

    for key, label_ in (("rahu_kaal", "Rahu Kaal"), ("yamaganda", "Yamaganda"), ("gulika", "Gulika Kaal")):
        if flags.get(key):
            add(f"Overlaps {label_}", K.SCORE[key])
            score += K.SCORE[key]
    if flags.get("abhijit"):
        if vara_lord == "Mercury":
            add("Abhijit Muhurta (not counted on Wednesdays)", 0)
        else:
            add("Overlaps Abhijit Muhurta, the midday auspicious window", K.SCORE["abhijit"])
            score += K.SCORE["abhijit"]

    tara = nak.get("tara")
    if tara and tara["good"] is True:
        add(f"Tarabala: {tara['name']} (favourable for you)", K.SCORE["tara_good"])
        score += K.SCORE["tara_good"]
    elif tara and tara["good"] is False:
        add(f"Tarabala: {tara['name']} (unfavourable for you)", K.SCORE["tara_bad"])
        score += K.SCORE["tara_bad"]
    ch = sign.get("chandra")
    if ch and ch["good"]:
        add(f"Chandrabala: Moon in your house {ch['house']} (supportive)", K.SCORE["chandra_good"])
        score += K.SCORE["chandra_good"]
    elif ch:
        add(f"Chandrabala: Moon in your house {ch['house']} (weak)", K.SCORE["chandra_bad"])
        score += K.SCORE["chandra_bad"]
    return score, reasons


def hora_summary(planet, rating, nak, warnings):
    info = K.HORA[planet]
    best, avoid = info["best"], info["avoid"]
    s1 = f"{planet} hora: {info['nature']}."
    if rating == "Favorable":
        s2 = f"A strong window, good for {best[0]}, plus {best[1]}."
    elif rating == "Good":
        s2 = f"A supportive window that suits {best[0]}, plus {best[1]}."
    elif rating == "Neutral":
        s2 = f"A neutral window; it suits {best[0]} best."
    elif rating == "Caution":
        s2 = f"Handle with care: favour routine or finishing tasks over new starts, and avoid {avoid[0]}."
    else:
        s2 = "A poor window for new beginnings: hold off on important starts, purchases and signatures."
    g = K.NAK_GROUP[nak["group"]]
    s3 = f"Moon in {nak['name']} ({g['label']}): {g['text']}."
    return " ".join([s1, s2, s3]), s2


# ---- the day ----------------------------------------------------------------
def build_day(eng, cfg, d: date) -> dict:
    tz = eng.tz
    birth = cfg.get("birth") or {}
    birth_nak = K.find_nakshatra(birth.get("nakshatra"))
    birth_sign = K.find_rashi(birth.get("moon_sign"))

    sr, ss, sr2 = eng.day_bounds(d)
    wd = datetime.fromtimestamp(sr, tz).weekday()
    vara_lord = K.DAY_LORD[wd]

    tithis = [_tithi_seg(s) for s in eng.tithi_segments(sr, sr2)]
    naks = [_nak_seg(s, birth_nak) for s in eng.nakshatra_segments(sr, sr2)]
    yogas = [_yoga_seg(s) for s in eng.yoga_segments(sr, sr2)]
    karanas = [_karana_seg(s) for s in eng.karana_segments(sr, sr2)]
    signs = [_sign_seg(s, birth_sign) for s in eng.moon_sign_segments(sr, sr2)]
    sun_idx = int(eng.sun(sr) // 30) % 12
    sun_sign = {"name": K.RASHI[sun_idx][0], "english": K.RASHI[sun_idx][1]}

    # special windows -------------------------------------------------------
    D = ss - sr
    part = D / 8.0

    def eighth(k):
        return sr + (k - 1) * part, sr + k * part

    windows = []

    def win(key, label, kind, a, b, note, clip_start=False, clip_end=False):
        windows.append({"key": key, "label": label, "kind": kind,
                        "start": int(round(a)), "end": int(round(b)), "note": note,
                        "clip_start": clip_start, "clip_end": clip_end})

    a, b = eighth(K.RAHU_PART[wd]); win("rahu_kaal", "Rahu Kaal", "avoid", a, b, "Avoid starting anything important")
    a, b = eighth(K.YAMA_PART[wd]); win("yamaganda", "Yamaganda", "avoid", a, b, "Not favourable for new beginnings")
    a, b = eighth(K.GULIKA_PART[wd]); win("gulika", "Gulika Kaal", "avoid", a, b, "Repeats easily: avoid starting things you cannot undo")
    win("abhijit", "Abhijit Muhurta", "good", sr + D * 7 / 15, sr + D * 8 / 15,
        "Midday auspicious window" + (" (traditionally not used on Wednesdays)" if vara_lord == "Mercury" else ""))
    win("brahma", "Brahma Muhurta", "good", sr - 96 * 60, sr - 48 * 60, "Quiet pre-dawn time for meditation and study")
    for k in karanas:
        if k["vishti"] and k["end"] > sr and k["start"] < sr2:
            win("vishti", "Vishti (Bhadra) karana", "avoid", max(k["start"], sr), min(k["end"], sr2),
                "Avoid new starts and auspicious work", k["start"] < sr, k["end"] > sr2)
    for y in yogas:
        if y["challenging"] and y["end"] > sr and y["start"] < sr2:
            win("yoga_bad", f"{y['name']} yoga", "avoid", max(y["start"], sr), min(y["end"], sr2),
                "Challenging yoga: go carefully with new starts", y["start"] < sr, y["end"] > sr2)
    windows.sort(key=lambda w: w["start"])
    wmap = {w["key"]: w for w in windows if w["key"] in ("rahu_kaal", "yamaganda", "gulika", "abhijit")}

    # horas ------------------------------------------------------------------
    start_idx = K.CHALDEAN.index(vara_lord)
    day_len = (ss - sr) / 12.0
    night_len = (sr2 - ss) / 12.0
    horas = []
    for n in range(24):
        if n < 12:
            a, b = sr + n * day_len, sr + (n + 1) * day_len
        else:
            a, b = ss + (n - 12) * night_len, ss + (n - 11) * night_len
        if n == 23:
            b = sr2
        planet = K.CHALDEAN[(start_idx + n) % 7]
        t_seg, n_seg = dominant(tithis, a, b), dominant(naks, a, b)
        y_seg, k_seg, s_seg = dominant(yogas, a, b), dominant(karanas, a, b), dominant(signs, a, b)
        flags = {k: overlap(w["start"], w["end"], a, b) >= MIN_OVERLAP for k, w in wmap.items()}
        waxing = t_seg["paksha"] == "Shukla"
        score, reasons = score_hora(planet, t_seg, n_seg, y_seg, k_seg, s_seg, flags, vara_lord, waxing)
        rating = K.rating_for(score)
        warnings = []
        for key in ("rahu_kaal", "yamaganda", "gulika"):
            if flags[key]:
                w = wmap[key]
                warnings.append(f"Overlaps {w['label']} ({fmt_range(w['start'], w['end'], tz)})")
        if k_seg["vishti"]:
            warnings.append("Vishti (Bhadra) karana")
        if y_seg["challenging"]:
            warnings.append(f"{y_seg['name']} yoga")
        summary, tip = hora_summary(planet, rating, n_seg, warnings)
        horas.append({
            "n": n + 1, "planet": planet, "glyph": K.GLYPH[planet], "day": n < 12,
            "start": int(round(a)), "end": int(round(b)),
            "score": score, "rating": rating, "reasons": reasons,
            "best": K.HORA[planet]["best"], "avoid": K.HORA[planet]["avoid"],
            "warnings": warnings, "abhijit": bool(flags["abhijit"]),
            "summary": summary, "tip": tip,
            "tithi": f"{t_seg['paksha']} {t_seg['name']}", "nakshatra": n_seg["name"],
        })

    mr = eng.moonrise_after(sr)
    moonrise = int(round(mr)) if mr is not None and mr < sr2 else None

    day = {
        "date": d.isoformat(),
        "vara": K.VARA[wd], "vara_sanskrit": K.VARA_SANSKRIT[wd], "vara_lord": vara_lord,
        "vara_info": K.VARA_INFO[vara_lord],
        "sunrise": int(round(sr)), "sunset": int(round(ss)), "next_sunrise": int(round(sr2)),
        "tithi": tithis, "nakshatra": naks, "yoga": yogas, "karana": karanas, "moon_sign": signs,
        "sun_sign": sun_sign, "moonrise": moonrise, "windows": windows, "horas": horas,
        "observances": observances(tithis, sr, ss, sr2, moonrise),
    }
    day["briefing"] = briefing(day, cfg, tz)
    return day


def observances(tithis, sr, ss, sr2, moonrise):
    """Indicative tithi-based observances. Each uses a conventional reference time
    (sunrise, midday, moonrise or midnight); regional rules vary, so confirm festival
    dates in a local calendar."""
    def at(t):
        return containing(tithis, t)["n"]

    out = []
    n_sunrise, n_midday, n_night = at(sr), at((sr + ss) / 2), at((ss + sr2) / 2)

    def add(name, note, basis):
        out.append({"name": name, "note": note, "basis": basis})

    if n_sunrise in (11, 26):
        add("Ekadashi", "Traditional fasting and discipline day; many keep it light on food.", "tithi at sunrise")
    if n_midday == 4:
        add("Vinayaka Chaturthi", "Ganesha observance (Shukla Chaturthi).", "tithi at midday")
    if moonrise and sr <= moonrise < sr2 and at(moonrise) == 19:
        add("Sankashti Chaturthi", "Ganesha observance, kept until moonrise (Krishna Chaturthi).", "tithi at moonrise")
    if n_night == 29:
        add("Masik Shivaratri", "Shiva observance, night of Krishna Chaturdashi.", "tithi at midnight")
    if n_sunrise == 15:
        add("Purnima", "Full moon: worship, charity and Satyanarayana puja are traditional.", "tithi at sunrise")
    if n_sunrise == 30:
        add("Amavasya", "New moon: ancestor remembrance and rest; not for fresh starts.", "tithi at sunrise")
    for t in tithis:
        if t["n"] in (13, 28) and overlap(t["start"], t["end"], ss, ss + 96 * 60) > 0:
            add("Pradosha", "Twilight after sunset: evening Shiva worship is traditional.", "tithi at twilight")
            break
    return out


def briefing(day, cfg, tz) -> dict:
    sr, sr2 = day["sunrise"], day["next_sunrise"]
    t = containing(day["tithi"], sr)
    nk = containing(day["nakshatra"], sr)
    yg = containing(day["yoga"], sr)
    kr = containing(day["karana"], sr)
    sg = containing(day["moon_sign"], sr)
    lord = day["vara_lord"]
    info = day["vara_info"]
    cat = K.TITHI_CAT_INFO[t["category"]]
    grp = K.NAK_GROUP[nk["group"]]
    tlabel = f"{t['paksha']} {t['name']}"

    energies = [
        {"title": f"{day['vara']} · {lord}",
         "text": f"Ruled by {lord}: {info['theme']}. Traditionally linked with {info['deity']}; colours {info['colors']}."},
        {"title": f"Tithi · {tlabel}",
         "text": f"A {t['category']} tithi, {cat['text']}."},
        {"title": f"Nakshatra · {nk['name']}",
         "text": f"Ruled by {nk['lord']} ({K.LORD_THEME[nk['lord']]}); a {grp['label']} star, {grp['text']}."},
        {"title": f"Yoga · {yg['name']}",
         "text": "Considered challenging: go carefully with new starts." if yg["challenging"]
                 else "No special caution; supportive background energy."},
        {"title": f"Moon in {sg['name']} ({sg['english']})",
         "text": f"Moon passes through the {sg['english']} sign; the Sun is in {day['sun_sign']['name']} ({day['sun_sign']['english']})."},
    ]
    if kr["vishti"]:
        energies.append({"title": "Karana · Vishti", "text": "Vishti (Bhadra) is active at sunrise: avoid new starts until it ends."})

    changes = []
    for key, label in (("tithi", "Tithi"), ("nakshatra", "Nakshatra"), ("yoga", "Yoga"), ("moon_sign", "Moon sign")):
        segs = day[key]
        for prev, nxt in zip(segs, segs[1:]):
            if sr < nxt["start"] < sr2:
                nm = f"{nxt['paksha']} {nxt['name']}" if key == "tithi" else nxt["name"]
                changes.append({"t": nxt["start"], "text": f"{label} becomes {nm} at {fmt_time(nxt['start'], tz)}"})
    changes.sort(key=lambda c: c["t"])

    # best / avoid windows (waking hours only)
    lo_h, hi_h = _active_hours(cfg)
    def waking(h):
        hr = datetime.fromtimestamp(h["start"], tz).hour
        return lo_h <= hr < hi_h
    cand = [h for h in day["horas"] if waking(h) and h["rating"] in ("Favorable", "Good")]
    cand.sort(key=lambda h: (-h["score"], h["start"]))
    best = sorted(cand[:3], key=lambda h: h["start"])
    best_windows = [{"label": f"{h['glyph']} {h['planet']} hora", "start": h["start"], "end": h["end"],
                     "rating": h["rating"], "note": h["best"][0]} for h in best]
    avoid_windows = [{"label": w["label"], "start": w["start"], "end": w["end"], "note": w["note"],
                      "when": fmt_win(w, tz)} for w in day["windows"] if w["kind"] == "avoid"]

    do = [f"Lean into {lord}'s themes: {info['theme']}.",
          f"{tlabel} ({t['category']} tithi) is good for {cat['do']}.",
          f"Moon in {nk['name']} ({grp['label']}) is good for {grp['do']}."]
    if best_windows:
        b0 = best_windows[0]
        do.append(f"Put your most important start in {b0['label']} ({fmt_range(b0['start'], b0['end'], tz)}).")
    ab = next((w for w in day["windows"] if w["key"] == "abhijit"), None)
    if ab and lord != "Mercury":
        do.append(f"Use Abhijit Muhurta ({fmt_range(ab['start'], ab['end'], tz)}) for anything you want to begin well.")
    br = next((w for w in day["windows"] if w["key"] == "brahma"), None)
    if br:
        do.append(f"Brahma Muhurta ({fmt_range(br['start'], br['end'], tz)}) is the quiet slot for meditation or study.")

    avoid = []
    rk = next((w for w in day["windows"] if w["key"] == "rahu_kaal"), None)
    if rk:
        avoid.append(f"Starting anything important in Rahu Kaal ({fmt_range(rk['start'], rk['end'], tz)}).")
    for key, label in (("yamaganda", "Yamaganda"), ("gulika", "Gulika Kaal")):
        w = next((w for w in day["windows"] if w["key"] == key), None)
        if w:
            avoid.append(f"{label} ({fmt_range(w['start'], w['end'], tz)}) for new beginnings.")
    for w in day["windows"]:
        if w["key"] == "vishti":
            avoid.append(f"New starts during Vishti karana ({fmt_win(w, tz)}).")
        if w["key"] == "yoga_bad":
            avoid.append(f"New ventures during {w['label']} ({fmt_win(w, tz)}).")
    if grp["delta"] < 0:
        when = f" until {fmt_time(nk['end'], tz)}" if nk["end"] < sr2 else ""
        avoid.append(f"New ventures{when} while the Moon is in {nk['name']} ({grp['label']} nakshatra).")
    if t["category"] == "Rikta" or t["n"] == 30:
        when = f" until {fmt_time(t['end'], tz)}" if t["end"] < sr2 else ""
        avoid.append(f"Auspicious beginnings{when} while {tlabel} lasts.")
    avoid.append(f"On {lord}'s day, go easy on {K.HORA[lord]['avoid'][0]}.")

    personal = None
    if nk.get("tara") or sg.get("chandra"):
        personal = {}
        if nk.get("tara"):
            tr = nk["tara"]
            personal["tara"] = f"Tarabala at sunrise: {tr['name']} ({'favourable' if tr['good'] else 'unfavourable' if tr['good'] is False else 'mixed'})"
        if sg.get("chandra"):
            ch = sg["chandra"]
            personal["chandra"] = f"Chandrabala at sunrise: Moon in your house {ch['house']} ({'supportive' if ch['good'] else 'weak'})"

    headline = f"{day['vara']} · {tlabel} · {nk['name']}"
    lines = [headline]
    for e in energies[:3]:
        lines.append(f"{e['title']}: {e['text']}")
    if best_windows:
        lines.append("Best: " + "; ".join(f"{w['label']} {fmt_range(w['start'], w['end'], tz)}" for w in best_windows))
    if rk:
        lines.append(f"Avoid starts: Rahu Kaal {fmt_range(rk['start'], rk['end'], tz)}")
    if day["observances"]:
        lines.append("Today: " + ", ".join(o["name"] for o in day["observances"]))
    return {
        "headline": headline, "energies": energies, "do": do, "avoid": avoid,
        "best_windows": best_windows, "avoid_windows": avoid_windows, "changes": changes,
        "personal": personal, "text": "\n".join(lines),
    }


def _active_hours(cfg):
    n = cfg.get("notify", {})
    def hh(s, default):
        try:
            return int(str(s).split(":")[0])
        except Exception:
            return default
    return hh(n.get("active_from", "06:00"), 6), hh(n.get("active_until", "23:00"), 23)
