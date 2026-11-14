# Personal-Panchang
Panchang, Hora, Nakshatra, Yoga, etc
Personal Panchang

A free, private-ish daily panchang for iPhone: a web page (installable like an app), a Home Screen / Lock Screen
widget, and a notification at every hora change. No Mac, no Apple developer account, no paid services.

| Piece | What it does | Runs on |
|---|---|---|
| `generator/` | Computes tithi, nakshatra, yoga, karana, vara, sunrise/sunset, Rahu Kaal, Yamaganda, Gulika, Abhijit, Brahma Muhurta, 24 horas, ratings and a daily briefing from Swiss Ephemeris | GitHub Actions (daily) |
| `docs/` | The page: live current hora, panchang now, briefing, best/avoid windows, all horas | GitHub Pages |
| `scriptable/PanchangWidget.js` | Widget with live countdown (small / medium / large / Lock Screen) | Scriptable app (free) |
| `generator/notify.py` | Queues tomorrow's hora alerts + a morning briefing as *scheduled* ntfy messages | GitHub Actions (daily) |

```
GitHub Action (daily, ~8 PM)  ->  generate.py -> docs/data.json -> GitHub Pages   (page + widget read this)
                              ->  notify.py   -> ntfy.sh (scheduled for tomorrow) -> ntfy iOS app -> your lock screen
```

## Setup (about 15 minutes)

1. **Create a GitHub repo** (public; Pages on private repos needs a paid plan) and push this folder to `main`.
2. **Edit `config.json`**: `place`, `lat`, `lon`, `tz`. Optional: `birth.nakshatra` (e.g. `"Rohini"`) and
   `birth.moon_sign` (e.g. `"Vrishabha"`) switch on Tarabala/Chandrabala in the ratings.
   The repo and page are public, so use a nearby point if you don't want your exact location out there
   (the page only shows coordinates rounded to ~1 km). Or leave `config.json` generic and set the repo
   secrets `PANCHANG_LAT` / `PANCHANG_LON` instead; they override the file.
3. **Enable Pages**: repo Settings > Pages > Source = **GitHub Actions**.
4. **Pick a notification topic**: invent a long random string (e.g. `panchang-7f3k9x2m4q8w`). Anyone who knows it
   can read it, so treat it like a password. Add it as repo secret **`NTFY_TOPIC`**. Optional variable
   **`SITE_URL`** = your Pages URL (tapping a notification opens it).
5. **Run it once**: Actions > "Daily panchang" > Run workflow. First tick **send_test** to confirm a notification
   arrives, then run it again normally. It also runs by itself every day.
6. **iPhone**
   - Install **ntfy** from the App Store, add subscription = your topic (server `ntfy.sh`), allow notifications.
   - Open your Pages URL in Safari > Share > **Add to Home Screen** (this is the "app").
   - Install **Scriptable**, new script, paste `scriptable/PanchangWidget.js`, set `DATA_URL` to
     `https://<you>.github.io/<repo>/data.json`. Then Home Screen > + > Scriptable > choose size > Edit Widget > pick the script.
     Lock Screen: add a Scriptable widget (inline / rectangular / circular).

The workflow's cron is in UTC (`0 1 * * *` = 8 PM EST / 9 PM EDT). If you are in another timezone, change it to
land in the *evening* of your local day: the notifier queues the **next** local calendar day.

## Customising

- **Notifications** (`config.json` > `notify`): `horas` = `"all"`, `"highlights"` (Favorable, Good, Avoid only) or `"off"`;
  `active_from` / `active_until` limit hora alerts to waking hours; `briefing_time` sets the morning briefing.
- **Ratings** are transparent. Each hora starts from its planet, then adds/subtracts for the nakshatra type, planetary
  friendship with the nakshatra lord, tithi type, challenging yoga, Vishti karana, Rahu Kaal / Yamaganda / Gulika,
  Abhijit and (optional) Tarabala/Chandrabala. Tap "Why?" on the page to see every term. Weights live in
  `generator/knowledge.py` (`SCORE`); all the traditional tables are in that file too.
- **Ayanamsa / sunrise definition**: `ayanamsa` = `lahiri` | `raman` | `krishnamurti`; `sun_disc` = `upper` (default) or `center`.

## Verification (`python tests/verify.py`)

2,181 checks, all passing when this was built:
- **Astronomical anchor:** Amavasya ends within 3 s of the published 12 Aug 2026 new moon (conjunction ~17:36:41 UTC).
- **Independent implementation:** the `vedic-panchang` PyPI library agrees on all 225 tithi/nakshatra/yoga numbers and on
  216/225 end times (worst agreeing difference 0.8 s). Where they differ, our values sit exactly on the segment boundary and
  the library's do not (it mishandles the 360 -> 0 degree wrap, mislabels some karanas, and returns the next day's sunrise when
  sunrise is before 05:30 IST). Karana names are checked against the traditional per-tithi table.
- **Sunrise/sunset:** Sun centre at 0.833 degrees below the horizon at the reported times (Toronto, Mumbai, Delhi, Sydney, Reykjavik).
- **Structure:** 24 contiguous horas, Chaldean order, day-to-day continuity, Rahu/Yama/Gulika/Abhijit formulas, DST-change days.

## Known limits (please read)

- **Not tested here:** the live ntfy delivery, the GitHub Actions run and the Scriptable widget on a real iPhone could not be
  exercised from the build environment (the widget logic was run against stubbed Scriptable APIs; the notifier was dry-run).
  Use the workflow's `send_test` option first, and tell me what breaks.
- **ntfy**: scheduled messages can be set 10 seconds to 3 days ahead; ntfy.sh applies rate limits (the script retries on
  HTTP 429). Running the notifier twice for the same date queues duplicates. If the daily job is skipped (GitHub occasionally
  delays or drops scheduled runs) you can run it manually with a `schedule_date`.
- **Widget refresh** is controlled by iOS: the countdown ticks live, but the hora label can lag a few minutes after a change.
- **Guidance, not prediction.** Rules are commonly cited Jyotish/Muhurta conventions; lineages differ. Observances
  (Ekadashi, Vinayaka Chaturthi, Sankashti, Pradosha ...) use one conventional reference time each; confirm festival dates in a local calendar.
- Polar latitudes (Sun never rises/sets) are not supported.

## Local use

```
pip install -r requirements.txt
python generator/generate.py                 # writes docs/data.json
python -m http.server -d docs 8000           # open http://localhost:8000
python generator/notify.py --dry-run         # preview tomorrow's notifications
python tests/verify.py
```
Swiss Ephemeris is AGPL-3.0 (free for this personal use; if you ever publish a modified service, the AGPL applies).
