"""NYSE, NASDAQ, ASX and XETRA stocks from Yahoo Finance (free).

The universe comes from Yahoo's screener, filtered by market cap and average daily
traded value (both converted to USD). Daily candles are split-adjusted but not
dividend-adjusted, which matches TradingView's default.
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from ..engine import Bar
from .base import Instrument

# Yahoo exchange codes per exchange name used in the config.
YAHOO_CODES = {"NYSE": ["NYQ"], "NASDAQ": ["NMS", "NGM", "NCM"], "ASX": ["ASX"], "XETR": ["GER"]}
TV_PREFIX = {"NYQ": "NYSE", "NMS": "NASDAQ", "NGM": "NASDAQ", "NCM": "NASDAQ", "ASX": "ASX", "GER": "XETR"}
# Local close time per TradingView prefix, to tell whether today's daily candle is still open.
SESSIONS = {"NYSE": ("America/New_York", 16, 0), "NASDAQ": ("America/New_York", 16, 0),
            "ASX": ("Australia/Sydney", 16, 12), "XETR": ("Europe/Berlin", 17, 35)}


def tv_symbol(yahoo_symbol: str, yahoo_exchange: str) -> str:
    prefix = TV_PREFIX[yahoo_exchange]
    sym = yahoo_symbol.split(".")[0] if prefix in ("ASX", "XETR") else yahoo_symbol.replace("-", ".")
    return f"{prefix}:{sym}"


def _date_ms(ts) -> int:
    return int(datetime(ts.year, ts.month, ts.day, tzinfo=timezone.utc).timestamp() * 1000)


def _usd_rates(currencies: set[str]) -> dict[str, float]:
    import yfinance as yf

    rates = {"USD": 1.0}
    for cur in currencies - {"USD"}:
        try:
            rates[cur] = float(yf.Ticker(f"{cur}USD=X").fast_info["lastPrice"])
        except Exception:
            pass
    return rates


class Stocks:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def instruments(self) -> list[Instrument]:
        import yfinance as yf
        from yfinance import EquityQuery

        min_cap = float(self.cfg.get("min_market_cap_usd", 150e6))
        min_vol = float(self.cfg.get("min_volume_usd", 15e6))
        codes = [c for ex in self.cfg.get("exchanges", list(YAHOO_CODES)) for c in YAHOO_CODES[ex]]
        # Loose pre-filter (screener values may be in local currency); exact USD check below.
        query = EquityQuery("and", [EquityQuery("is-in", ["exchange", *codes]),
                                    EquityQuery("gt", ["intradaymarketcap", min_cap * 0.5])])
        quotes, offset = [], 0
        while True:
            res = yf.screen(query, offset=offset, size=250, sortField="intradaymarketcap", sortAsc=False)
            batch = res.get("quotes", [])
            quotes += batch
            offset += len(batch)
            if not batch or offset >= res.get("total", 0):
                break

        rates = _usd_rates({q.get("currency", "USD") for q in quotes})
        out = []
        for q in quotes:
            rate = rates.get(q.get("currency", "USD"))
            ex = q.get("exchange")
            if rate is None or ex not in TV_PREFIX:
                continue
            cap = (q.get("marketCap") or 0) * rate
            vol = (q.get("averageDailyVolume10Day") or 0) * (q.get("regularMarketPrice") or 0) * rate
            if cap < min_cap or vol < min_vol:
                continue
            out.append(Instrument(symbol=q["symbol"], market="Stocks",
                                  name=q.get("shortName") or q.get("longName") or q["symbol"],
                                  tv_symbol=tv_symbol(q["symbol"], ex), exchange=TV_PREFIX[ex],
                                  market_cap_usd=cap, volume_usd=vol))
        return out

    def prefetch(self, instruments: list[Instrument]) -> None:
        """Download daily history for many symbols at once (much faster than one by one)."""
        import yfinance as yf

        self._cache: dict[str, list[Bar]] = {}
        syms = [i.symbol for i in instruments]
        for k in range(0, len(syms), 50):
            chunk = syms[k:k + 50]
            df = yf.download(chunk, period="max", interval="1d", auto_adjust=False, actions=False,
                             group_by="ticker", threads=True, progress=False)
            for s in chunk:
                try:
                    d = df[s].dropna(subset=["Open", "High", "Low", "Close"])
                except KeyError:
                    continue
                # Key each candle by its local trading date at 00:00 UTC so weeks and months
                # group correctly for every exchange (Sydney midnight is the previous UTC day).
                self._cache[s] = [Bar(_date_ms(ts), float(r.Open), float(r.High), float(r.Low), float(r.Close))
                                  for ts, r in zip(d.index, d.itertuples())]

    def daily(self, inst: Instrument, now_ms: int) -> tuple[list[Bar], bool]:
        bars = getattr(self, "_cache", {}).get(inst.symbol, [])
        if not bars:
            return [], False
        tz, hh, mm = SESSIONS[inst.exchange]
        now = datetime.fromtimestamp(now_ms / 1000, ZoneInfo(tz))
        last_day = datetime.fromtimestamp(bars[-1].t / 1000, ZoneInfo("UTC")).date()
        live = last_day >= now.date() and (now.hour, now.minute) < (hh, mm)
        return bars, live
