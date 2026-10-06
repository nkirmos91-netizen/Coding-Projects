"""Command line: `python -m hobscan scan` or `python -m hobscan demo`."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from urllib.parse import quote

from . import report
from .config import Config, load
from .engine import Bar, Params, detect
from .providers.base import Instrument
from .rank import score
from .resample import resample, tv_interval


def zones_for(inst: Instrument, daily: list[Bar], daily_live: bool, cfg: Config, now_ms: int) -> list[dict]:
    rows = []
    for tf in cfg.timeframes:
        bars, live = resample(daily, tf, now_ms, daily_live, cfg.anchor)
        if len(bars) < 3:
            continue
        close = bars[-1].c
        for f in detect(bars, cfg.params, live):
            z = f.zone
            dist = (z.bot - close) / close * 100 if z.bear else (close - z.top) / close * 100
            rows.append({
                "symbol": inst.symbol, "name": inst.name, "market": inst.market, "exchange": inst.exchange,
                "tf": tf, "dir": "Bear" if z.bear else "Bull", "hidden": f.hidden,
                "bot": z.bot, "top": z.top, "dist": dist, "body": z.body_pct,
                "zone_date": datetime.fromtimestamp(z.t / 1000, timezone.utc).strftime("%Y-%m-%d"),
                "touched": f.touched, "forming": f.forming, "testing": f.testing,
                "score": score(tf, f.hidden, z.body_pct, f.touched, cfg.touched_penalty),
                "tv_url": f"https://www.tradingview.com/chart/?symbol={quote(inst.tv_symbol)}&interval={tv_interval(tf)}",
            })
    return rows


def run_scan(cfg: Config, markets: set[str], limit: int | None) -> None:
    from .providers.crypto import Crypto
    from .providers.stocks import Stocks

    sources = []
    if "crypto" in markets and cfg.crypto.get("enabled", True):
        sources.append(("Crypto", Crypto(cfg.crypto)))
    if "stocks" in markets and cfg.stocks.get("enabled", True):
        sources.append(("Stocks", Stocks(cfg.stocks)))
    if "fx" in markets and cfg.fx.get("enabled", False):
        print("FX (FXCM) is not connected yet; skipping.", file=sys.stderr)

    rows, scanned, errors = [], 0, 0
    now_ms = int(time.time() * 1000)
    for label, src in sources:
        print(f"{label}: finding symbols that pass the filters...")
        insts = src.instruments()
        if limit:
            insts = insts[:limit]
        print(f"{label}: {len(insts)} symbols")
        if hasattr(src, "prefetch"):
            src.prefetch(insts)
        for n, inst in enumerate(insts, 1):
            try:
                daily, live = src.daily(inst, now_ms)
                rows += zones_for(inst, daily, live, cfg, now_ms)
                scanned += 1
            except Exception as e:  # one bad symbol must not stop the scan
                errors += 1
                print(f"  {inst.symbol}: {e}", file=sys.stderr)
            if n % 25 == 0:
                print(f"  {n}/{len(insts)}")

    path = report.write(rows, cfg.output, report.scan_meta(scanned, cfg.timeframes, errors))
    print(f"{len(rows)} hidden orderblocks. Page: {path.resolve()}")


def run_demo(out: str) -> None:
    """Build the page from made-up candles shaped like the reference examples."""
    from .samples import SAMPLES

    cfg = Config(timeframes=["1D"], params=Params())
    rows = []
    now_ms = int(time.time() * 1000)
    for s in SAMPLES:
        inst = Instrument(symbol=s["symbol"], market=s["market"], name="example data",
                          tv_symbol=s["tv"], exchange=s["exchange"])
        for r in zones_for(inst, s["bars"], s.get("live", False), cfg, now_ms):
            r["tf"] = s["tf"]
            r["score"] = score(s["tf"], r["hidden"], r["body"], r["touched"], cfg.touched_penalty)
            r["tv_url"] = f"https://www.tradingview.com/chart/?symbol={quote(s['tv'])}&interval={tv_interval(s['tf'])}"
            rows.append(r)
    path = report.write(rows, out, "Example data only: made-up candles shaped like your reference charts")
    print(f"Demo page: {path.resolve()}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="hobscan", description="Hidden orderblock scanner")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="scan markets and write the ranked page")
    s.add_argument("--config", default="config.toml")
    s.add_argument("--markets", default="crypto,stocks,fx", help="comma list: crypto,stocks,fx")
    s.add_argument("--limit", type=int, help="only scan the first N symbols per market (for testing)")
    d = sub.add_parser("demo", help="write the page using example data")
    d.add_argument("--out", default="output/demo.html")
    a = p.parse_args(argv)
    if a.cmd == "scan":
        run_scan(load(a.config), set(a.markets.lower().split(",")), a.limit)
    else:
        run_demo(a.out)
