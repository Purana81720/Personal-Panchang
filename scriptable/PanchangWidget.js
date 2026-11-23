// Panchang widget for the Scriptable app (free, iOS).
// Shows the current hora with a live countdown, today's tithi / nakshatra / yoga / karana,
// and the next hora. Works as a Home Screen widget (small, medium, large) and as a
// Lock Screen widget (inline, rectangular, circular).
//
// SETUP: 1) Install Scriptable. 2) Create a new script, paste this file.
//        3) Set DATA_URL below (or put the URL in the widget's "Parameter" field).
//        4) Long-press Home Screen > + > Scriptable > pick size > Edit Widget > choose this script.

const DATA_URL = "https://purana81720.github.io/Personal-Panchang/data.json";

const CACHE_FILE = "panchang-data.json";
const C = {
  bg1: "#1a2050", bg2: "#0b0e1d", text: "#eef0fb", muted: "#9aa2cf", accent: "#f2a33a",
  Favorable: "#5fd6a0", Good: "#6cc4ee", Neutral: "#b4b9dc", Caution: "#f2b24a", Avoid: "#f26d7d",
};
const ICON = { Favorable: "✦", Good: "✓", Neutral: "–", Caution: "▲", Avoid: "✕" };

// ---------- data ----------
async function loadData() {
  const url = ((args && args.widgetParameter) || "").trim() || DATA_URL;
  const fm = FileManager.local();
  const path = fm.joinPath(fm.documentsDirectory(), CACHE_FILE);
  try {
    const req = new Request(url + (url.includes("?") ? "&" : "?") + "t=" + Date.now());
    req.timeoutInterval = 15;
    const data = await req.loadJSON();
    if (!data || !data.days) throw new Error("bad data");
    fm.writeString(path, JSON.stringify(data));
    return { data, offline: false };
  } catch (e) {
    if (fm.fileExists(path)) return { data: JSON.parse(fm.readString(path)), offline: true };
    throw e;
  }
}

function pickNow(data, nowSec) {
  const days = data.days;
  let day = days.find(d => d.sunrise <= nowSec && nowSec < d.next_sunrise);
  const covered = !!day;
  if (!day) day = nowSec < days[0].sunrise ? days[0] : days[days.length - 1];
  const all = days.flatMap(d => d.horas);
  let i = all.findIndex(h => h.start <= nowSec && nowSec < h.end);
  if (i < 0) i = nowSec < all[0].start ? 0 : all.length - 1;
  const seg = arr => arr.find(s => s.start <= nowSec && nowSec < s.end) || arr[arr.length - 1];
  return {
    day, covered, hora: all[i], next: all[i + 1],
    tithi: seg(day.tithi), nak: seg(day.nakshatra), yoga: seg(day.yoga), karana: seg(day.karana),
    active: day.windows.filter(w => w.start <= nowSec && nowSec < w.end),
  };
}

// ---------- formatting ----------
function makeFmt(tz) {
  const f = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", timeZone: tz });
  return ts => f.format(new Date(ts * 1000));
}

// ---------- drawing helpers ----------
function txt(parent, s, size, color, bold, opts) {
  const t = parent.addText(String(s));
  t.font = bold ? Font.boldSystemFont(size) : Font.systemFont(size);
  t.textColor = new Color(color || C.text);
  if (opts && opts.lines) t.lineLimit = opts.lines;
  t.minimumScaleFactor = (opts && opts.scale) || 0.8;
  return t;
}
function timer(parent, endSec, size, color) {
  const d = parent.addDate(new Date(endSec * 1000));
  d.applyTimerStyle();
  d.font = Font.boldMonospacedSystemFont(size);
  d.textColor = new Color(color || C.text);
  return d;
}
function ratingLine(parent, rating, size) {
  return txt(parent, `${ICON[rating] || ""} ${rating}`, size, C[rating], true);
}
function warnLine(ctx, fmt) {
  const w = ctx.active.find(x => x.kind === "avoid");
  if (w) return { text: `▲ ${w.label}${w.clip_end ? " (active)" : " until " + fmt(w.end)}`, color: C.Caution };
  const g = ctx.active.find(x => x.key === "abhijit");
  if (g) return { text: `✦ ${g.label} until ${fmt(g.end)}`, color: C.Favorable };
  return null;
}

// ---------- widgets ----------
function buildSmall(w, ctx, fmt) {
  w.setPadding(12, 12, 12, 12);
  const top = w.addStack(); top.centerAlignContent();
  txt(top, ctx.hora.glyph, 26, C.accent, true);
  top.addSpacer(8);
  const col = top.addStack(); col.layoutVertically();
  txt(col, `${ctx.hora.planet} hora`, 15, C.text, true, { lines: 1, scale: 0.7 });
  ratingLine(col, ctx.hora.rating, 12);
  w.addSpacer(8);
  timer(w, ctx.hora.end, 24, C.text);
  txt(w, `until ${fmt(ctx.hora.end)}`, 11, C.muted, false, { lines: 1 });
  w.addSpacer();
  const wl = warnLine(ctx, fmt);
  if (wl) txt(w, wl.text, 10.5, wl.color, true, { lines: 1, scale: 0.7 });
  txt(w, `${ctx.tithi.name} · ${ctx.nak.name}`, 11, C.muted, false, { lines: 1, scale: 0.65 });
}

function infoRow(parent, label, value, until, fmt) {
  const r = parent.addStack(); r.centerAlignContent();
  const ls = r.addStack(); ls.size = new Size(62, 0);
  txt(ls, label, 11, C.muted, false, { lines: 1 });
  txt(r, value, 13, C.text, true, { lines: 1, scale: 0.7 });
  if (until) { r.addSpacer(4); txt(r, `→ ${fmt(until)}`, 11, C.muted, false, { lines: 1 }); }
}

function buildMedium(w, ctx, fmt, large) {
  w.setPadding(14, 14, 14, 14);
  const row = w.addStack();
  const left = row.addStack(); left.layoutVertically();
  const head = left.addStack(); head.centerAlignContent();
  txt(head, ctx.hora.glyph, 30, C.accent, true);
  head.addSpacer(8);
  const hc = head.addStack(); hc.layoutVertically();
  txt(hc, `${ctx.hora.planet} hora`, 17, C.text, true, { lines: 1, scale: 0.7 });
  ratingLine(hc, ctx.hora.rating, 12.5);
  left.addSpacer(6);
  timer(left, ctx.hora.end, 26, C.text);
  txt(left, `until ${fmt(ctx.hora.end)}`, 11.5, C.muted, false, { lines: 1 });
  if (ctx.next) {
    left.addSpacer(6);
    txt(left, `Next ${ctx.next.glyph} ${ctx.next.planet}`, 12, C.text, true, { lines: 1, scale: 0.7 });
    txt(left, `${fmt(ctx.next.start)} · ${ctx.next.rating}`, 11, C[ctx.next.rating], false, { lines: 1, scale: 0.7 });
  }
  row.addSpacer(12);
  const right = row.addStack(); right.layoutVertically();
  infoRow(right, "Tithi", `${ctx.tithi.paksha[0]}. ${ctx.tithi.name}`, ctx.tithi.end, fmt);
  right.addSpacer(3);
  infoRow(right, "Nakshatra", ctx.nak.name, ctx.nak.end, fmt);
  right.addSpacer(3);
  infoRow(right, "Yoga", ctx.yoga.name, ctx.yoga.end, fmt);
  right.addSpacer(3);
  infoRow(right, "Karana", ctx.karana.name, ctx.karana.end, fmt);
  const wl = warnLine(ctx, fmt);
  if (wl) { right.addSpacer(5); txt(right, wl.text, 11.5, wl.color, true, { lines: 1, scale: 0.7 }); }

  if (large) {
    w.addSpacer(10);
    const b = ctx.day.briefing;
    txt(w, b.headline, 14, C.accent, true, { lines: 2 });
    w.addSpacer(6);
    txt(w, "Best windows", 11, C.muted, true);
    (b.best_windows.length ? b.best_windows : [{ label: "None in waking hours", start: 0, end: 0 }]).forEach(x => {
      txt(w, x.end ? `${x.label}  ${fmt(x.start)}–${fmt(x.end)}` : x.label, 12.5, C.Favorable, false, { lines: 1 });
    });
    w.addSpacer(6);
    txt(w, "Avoid starting things", 11, C.muted, true);
    b.avoid_windows.slice(0, 4).forEach(x => {
      txt(w, `${x.label}  ${x.when}`, 12.5, C.Caution, false, { lines: 1 });
    });
    w.addSpacer();
    txt(w, ctx.hora.summary, 11, C.muted, false, { lines: 4, scale: 0.8 });
  }
}

function buildAccessory(w, ctx, fmt, family) {
  if (family === "accessoryInline") {
    txt(w, `${ctx.hora.glyph} ${ctx.hora.planet} · until ${fmt(ctx.hora.end)}`, 12, C.text, false, { lines: 1 });
  } else if (family === "accessoryCircular") {
    const s = w.addStack(); s.layoutVertically(); s.centerAlignContent();
    txt(s, ctx.hora.glyph, 22, C.text, true);
    txt(s, ICON[ctx.hora.rating] || "", 11, C.text, true);
  } else {
    txt(w, `${ctx.hora.glyph} ${ctx.hora.planet} hora · ${ctx.hora.rating}`, 13, C.text, true, { lines: 1, scale: 0.7 });
    txt(w, `until ${fmt(ctx.hora.end)}`, 12, C.text, false, { lines: 1 });
    txt(w, `${ctx.tithi.name} · ${ctx.nak.name}`, 12, C.text, false, { lines: 1, scale: 0.65 });
  }
}

function buildError(w, msg) {
  w.setPadding(12, 12, 12, 12);
  txt(w, "Panchang", 14, C.accent, true);
  txt(w, msg, 11, C.muted, false, { lines: 6 });
}

async function build() {
  const w = new ListWidget();
  const family = (config && config.widgetFamily) || "medium";
  const accessory = family.startsWith("accessory");
  if (!accessory) {
    const g = new LinearGradient();
    g.colors = [new Color(C.bg1), new Color(C.bg2)];
    g.locations = [0, 1];
    w.backgroundGradient = g;
  }
  try {
    const { data, offline } = await loadData();
    const nowSec = Math.floor(Date.now() / 1000);
    const ctx = pickNow(data, nowSec);
    const fmt = makeFmt(data.meta.tz);
    if (!ctx.covered) {
      accessory ? txt(w, "Panchang data out of date", 12, C.text) : buildError(w, "Data is out of date. Check the daily GitHub Action.");
    } else if (accessory) {
      buildAccessory(w, ctx, fmt, family);
    } else if (family === "small") {
      buildSmall(w, ctx, fmt);
    } else {
      buildMedium(w, ctx, fmt, family === "large" || family === "extraLarge");
    }
    if (offline && !accessory) { w.addSpacer(2); txt(w, "offline copy", 9, C.muted); }
    // iOS decides the real refresh time; this asks for one at the next hora change.
    const next = Math.min(ctx.hora.end, nowSec + 15 * 60);
    w.refreshAfterDate = new Date(Math.max(next, nowSec + 60) * 1000);
  } catch (e) {
    accessory ? txt(w, "Panchang: no data", 12, C.text) : buildError(w, `Could not load data.\n${e.message || e}\nCheck DATA_URL in the script.`);
    w.refreshAfterDate = new Date(Date.now() + 10 * 60 * 1000);
  }
  return w;
}

const widget = await build();
if (config.runsInWidget) {
  Script.setWidget(widget);
} else {
  await widget.presentMedium();
}
Script.complete();
