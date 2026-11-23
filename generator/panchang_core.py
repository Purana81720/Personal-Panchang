"""
Panchang calculation core.

Everything is derived from Swiss Ephemeris (pyswisseph) positions of the Sun
and Moon: sidereal longitudes (Lahiri ayanamsa by default), sunrise and sunset.
Times are Unix timestamps (seconds, UTC) throughout; conversion to local time
only happens at the edges.

No network access, no API keys.
"""
from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import swisseph as swe

UNIX_JD0 = 2440587.5

AYANAMSA = {
    "lahiri": swe.SIDM_LAHIRI,
    "raman": swe.SIDM_RAMAN,
    "krishnamurti": swe.SIDM_KRISHNAMURTI,
}

NAK_UNIT = 360.0 / 27.0


def ts_to_jd(ts: float) -> float:
    return ts / 86400.0 + UNIX_JD0


class Engine:
    def __init__(self, lat, lon, tz, ayanamsa="lahiri", elevation=0.0, sun_disc="upper"):
        if ayanamsa not in AYANAMSA:
            raise ValueError(f"ayanamsa must be one of {sorted(AYANAMSA)}")
        self.lat = float(lat)
        self.lon = float(lon)
        self.elevation = float(elevation)
        self.tz = ZoneInfo(tz)
        self.tz_name = tz
        self.ayanamsa = ayanamsa
        self.sun_disc = sun_disc  # "upper" (default) or "center"
        swe.set_sid_mode(AYANAMSA[ayanamsa])
        # Built-in Moshier ephemeris: no data files needed, ~1 arcsec accuracy,
        # far better than needed for panchang (tithi/nakshatra boundaries to the second).
        self.flags = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

    # ---- positions -------------------------------------------------------
    def _lon(self, body, ts):
        return swe.calc_ut(ts_to_jd(ts), body, self.flags)[0][0] % 360.0

    def sun(self, ts):
        return self._lon(swe.SUN, ts)

    def moon(self, ts):
        return self._lon(swe.MOON, ts)

    def elong(self, ts):
        """Moon minus Sun, 0..360. 12 degrees = one tithi."""
        return (self.moon(ts) - self.sun(ts)) % 360.0

    def yoga_angle(self, ts):
        """Sun plus Moon (sidereal), 0..360. 13d20' = one yoga."""
        return (self.sun(ts) + self.moon(ts)) % 360.0

    # ---- sunrise / sunset ------------------------------------------------
    def _rise_set(self, ts_start, rise, body=swe.SUN):
        rsmi = swe.CALC_RISE if rise else swe.CALC_SET
        if self.sun_disc == "center" and body == swe.SUN:
            rsmi |= swe.BIT_DISC_CENTER | swe.BIT_NO_REFRACTION
        res, tret = swe.rise_trans(
            ts_to_jd(ts_start), body, rsmi,
            (self.lon, self.lat, self.elevation), 1013.25, 15.0, swe.FLG_MOSEPH,
        )
        if res != 0:
            return None
        return (tret[0] - UNIX_JD0) * 86400.0

    def sunrise_after(self, ts):
        t = self._rise_set(ts, True)
        if t is None:
            raise RuntimeError("Sun does not rise/set here on this date (polar day/night)")
        return t

    def sunset_after(self, ts):
        t = self._rise_set(ts, False)
        if t is None:
            raise RuntimeError("Sun does not rise/set here on this date (polar day/night)")
        return t

    def moonrise_after(self, ts):
        """Next moonrise after ts, or None (the Moon can skip a rise on some days)."""
        return self._rise_set(ts, True, swe.MOON)

    def local_midnight(self, d: date) -> float:
        return datetime.combine(d, time.min, tzinfo=self.tz).timestamp()

    def day_bounds(self, d: date):
        """Vedic day for civil date d: (sunrise, sunset, next sunrise) as timestamps."""
        sr = self.sunrise_after(self.local_midnight(d))
        ss = self.sunset_after(sr)
        sr2 = self.sunrise_after(ss)
        return sr, ss, sr2

    # ---- boundary search -------------------------------------------------
    @staticmethod
    def _cross(fn, boundary, lo, hi):
        """Time in [lo, hi] at which the increasing angle fn(t) passes `boundary`.
        Requires fn(lo) before and fn(hi) at/after the boundary, within 180 degrees."""
        def h(t):
            return ((fn(t) - boundary + 180.0) % 360.0) - 180.0
        for _ in range(55):
            mid = (lo + hi) / 2.0
            if h(mid) >= 0:
                hi = mid
            else:
                lo = mid
        return hi

    def segments(self, fn, unit, t0, t1, window_days):
        """Split an angle into `unit`-degree segments covering [t0, t1).
        Returns [{"idx", "start", "end"}]; first start may precede t0, last end may follow t1."""
        n = int(round(360.0 / unit))
        win = window_days * 86400.0
        a = fn(t0)
        i = int(a // unit) % n
        start = self._cross(fn, (i * unit) % 360.0, t0 - win, t0)
        out = []
        while True:
            end = self._cross(fn, ((i + 1) * unit) % 360.0, start, start + win)
            out.append({"idx": i, "start": start, "end": end})
            if end >= t1:
                break
            start = end
            i = (i + 1) % n
        return out

    # convenience wrappers
    def tithi_segments(self, t0, t1):
        return self.segments(self.elong, 12.0, t0, t1, 2.0)          # idx 0..29

    def nakshatra_segments(self, t0, t1):
        return self.segments(self.moon, NAK_UNIT, t0, t1, 2.0)       # idx 0..26

    def yoga_segments(self, t0, t1):
        return self.segments(self.yoga_angle, NAK_UNIT, t0, t1, 2.0)  # idx 0..26

    def karana_segments(self, t0, t1):
        return self.segments(self.elong, 6.0, t0, t1, 2.0)           # idx 0..59

    def moon_sign_segments(self, t0, t1):
        return self.segments(self.moon, 30.0, t0, t1, 4.0)           # idx 0..11
