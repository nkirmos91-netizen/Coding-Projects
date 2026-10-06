"""Ranked results page: one self-contained HTML file."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hidden Orderblock Scan</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
/* Layout: summary line, filter bar, one dense ranked table that scrolls sideways on phones */
:root{--bg:#f4f5f7;--panel:#ffffff;--fg:#16191d;--muted:#5f6670;--line:#dde1e6;--bear:#b8501c;--bull:#1a78a8;
--touch:#a87b00;--hover:#eef1f4;--sans:"IBM Plex Sans",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f1114;--panel:#161a1e;--fg:#e6e8eb;--muted:#9097a0;--line:#262b31;
--bear:#e0763d;--bull:#4aa8db;--touch:#e8b931;--hover:#1c2126;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0f1114;--panel:#161a1e;--fg:#e6e8eb;--muted:#9097a0;--line:#262b31;--bear:#e0763d;--bull:#4aa8db;
--touch:#e8b931;--hover:#1c2126;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 var(--sans)}
.wrap{max-width:1280px;margin:0 auto;padding-inline:16px;padding-block:24px 40px;display:grid;gap:16px}
h1{margin:0;font-size:1.35rem;font-weight:600;text-wrap:balance}
.meta{color:var(--muted);font-size:.85rem}
.filters{display:flex;flex-wrap:wrap;gap:10px;align-items:end}
.filters label{display:grid;gap:3px;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
select,input{height:34px;font:14px var(--sans);color:var(--fg);background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:6px 8px;min-width:0}
input[type=search]{width:12rem}
select:focus-visible,input:focus-visible,th:focus-visible{outline:2px solid var(--bull);outline-offset:1px}
.count{margin-left:auto;color:var(--muted);font-size:.85rem}
.tablewrap{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th,td{padding:7px 10px;text-align:left;white-space:nowrap;border-bottom:1px solid var(--line)}
th{font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:500;cursor:pointer;user-select:none;position:sticky;top:0;background:var(--panel)}
th[aria-sort=descending]::after{content:" ↓"}th[aria-sort=ascending]::after{content:" ↑"}
td.num{text-align:right;font-family:var(--mono);font-size:.86rem}
tbody tr:hover{background:var(--hover)}
.dir{display:inline-block;width:3.2em;font-weight:600}
.bear{color:var(--bear)}.bull{color:var(--bull)}
.hid{font-family:var(--mono);font-weight:600}
.pill{display:inline-block;font-size:.72rem;padding:1px 7px;border-radius:999px;border:1px solid currentColor;margin-right:4px}
.p-touched{color:var(--touch)}.p-forming{color:var(--bull)}.p-testing{color:var(--bear)}
a{color:inherit;text-decoration-color:var(--line);text-underline-offset:3px}
a:hover{text-decoration-color:currentColor}
.sym{font-weight:600}.sub{color:var(--muted);font-size:.8rem}
.empty{padding:28px;text-align:center;color:var(--muted)}
</style>
</head>
<body>
<main class="wrap">
  <div>
    <h1>Hidden Orderblock Scan</h1>
    <div class="meta">__META__</div>
  </div>
  <div class="filters">
    <label for="f-market">Market<select id="f-market"><option value="">All</option></select></label>
    <label for="f-dir">Direction<select id="f-dir"><option value="">All</option><option value="Bear">Bearish</option><option value="Bull">Bullish</option></select></label>
    <label for="f-tf">Timeframe<select id="f-tf"><option value="">All</option></select></label>
    <label for="f-hidden">Min hidden<select id="f-hidden"><option value="1">1x</option><option value="2">2x</option><option value="3">3x</option><option value="4">4x+</option></select></label>
    <label for="f-touched">Touched<select id="f-touched"><option value="">Include</option><option value="no">Exclude</option></select></label>
    <label for="f-q">Search<input id="f-q" type="search" placeholder="Symbol or name"></label>
    <span class="count" id="count"></span>
  </div>
  <div class="tablewrap">
    <table>
      <thead><tr>
        <th data-k="rank" tabindex="0">#</th><th data-k="symbol" tabindex="0">Symbol</th><th data-k="tf" tabindex="0">TF</th>
        <th data-k="dir" tabindex="0">Dir</th><th data-k="hidden" tabindex="0">Hidden</th><th data-k="bot" tabindex="0">Zone</th>
        <th data-k="dist" tabindex="0">Dist %</th><th data-k="body" tabindex="0">Body %</th><th data-k="zone_date" tabindex="0">Formed</th>
        <th data-k="status" tabindex="0">Status</th><th data-k="score" tabindex="0">Score</th>
      </tr></thead>
      <tbody id="rows"></tbody>
    </table>
  </div>
</main>
<script>
const ROWS = __ROWS__;
const TF_DAYS = t => { const m = /^(\d*)([DWM])$/.exec(t); const n = +(m[1] || 1); return n * ({D:1, W:7, M:30.44})[m[2]]; };
const $ = id => document.getElementById(id);
const fmt = v => { if (v == null) return ""; const a = Math.abs(v); return a >= 1000 ? v.toFixed(2) : a >= 1 ? v.toPrecision(6).replace(/\.?0+$/, "") : v.toPrecision(4); };
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"})[c]);
let sortKey = "score", sortDir = -1;

for (const m of [...new Set(ROWS.map(r => r.market))].sort()) $("f-market").add(new Option(m, m));
for (const t of [...new Set(ROWS.map(r => r.tf))].sort((a, b) => TF_DAYS(a) - TF_DAYS(b))) $("f-tf").add(new Option(t, t));

function status(r) { return [r.forming && "forming", r.testing && "testing", r.touched && "touched"].filter(Boolean); }

function render() {
  const market = $("f-market").value, dir = $("f-dir").value, tf = $("f-tf").value;
  const minH = +$("f-hidden").value, noTouch = $("f-touched").value === "no", q = $("f-q").value.trim().toLowerCase();
  let rows = ROWS.filter(r => (!market || r.market === market) && (!dir || r.dir === dir) && (!tf || r.tf === tf)
    && r.hidden >= minH && !(noTouch && r.touched)
    && (!q || r.symbol.toLowerCase().includes(q) || (r.name || "").toLowerCase().includes(q)));
  const key = sortKey === "tf" ? r => TF_DAYS(r.tf) : sortKey === "status" ? r => status(r).join() : r => r[sortKey];
  rows.sort((a, b) => { const x = key(a), y = key(b); return (x > y ? 1 : x < y ? -1 : 0) * sortDir; });
  $("rows").innerHTML = rows.length ? rows.map(r => `<tr>
    <td class="num">${r.rank}</td>
    <td><a class="sym" href="${esc(r.tv_url)}" target="_blank" rel="noopener">${esc(r.symbol)}</a> <span class="sub">${esc(r.name || "")} · ${esc(r.exchange)}</span></td>
    <td>${esc(r.tf)}</td>
    <td><span class="dir ${r.dir === "Bear" ? "bear" : "bull"}">${r.dir}</span></td>
    <td class="hid">${r.hidden}x</td>
    <td class="num">${fmt(r.bot)} – ${fmt(r.top)}</td>
    <td class="num">${r.dist.toFixed(2)}</td>
    <td class="num">${Math.round(r.body)}</td>
    <td>${esc(r.zone_date)}</td>
    <td>${status(r).map(s => `<span class="pill p-${s}">${s}</span>`).join("")}</td>
    <td class="num">${r.score.toFixed(2)}</td></tr>`).join("") : `<tr><td colspan="11" class="empty">No zones match these filters.</td></tr>`;
  $("count").textContent = `${rows.length} of ${ROWS.length} zones`;
  document.querySelectorAll("th").forEach(th => th.setAttribute("aria-sort", th.dataset.k === sortKey ? (sortDir > 0 ? "ascending" : "descending") : "none"));
}

document.querySelectorAll("th").forEach(th => {
  const go = () => { const k = th.dataset.k; if (sortKey === k) sortDir = -sortDir; else { sortKey = k; sortDir = ["symbol","rank","dist"].includes(k) ? 1 : -1; } render(); };
  th.addEventListener("click", go);
  th.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
});
["f-market","f-dir","f-tf","f-hidden","f-touched","f-q"].forEach(id => $(id).addEventListener("input", render));
render();
</script>
</body>
</html>
"""


def write(rows: list[dict], path: str | Path, meta: str) -> Path:
    rows = sorted(rows, key=lambda r: -r["score"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    page = (TEMPLATE.replace("__META__", html.escape(meta))
            .replace("__ROWS__", json.dumps(rows, separators=(",", ":")).replace("</", "<\\/")))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")
    return path


def scan_meta(n_symbols: int, timeframes: list[str], errors: int, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    s = f"Scanned {n_symbols} symbols on {len(timeframes)} timeframes · {now:%d %b %Y %H:%M} UTC"
    return s + (f" · {errors} symbols failed (see console)" if errors else "")
