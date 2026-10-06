"""USDT perpetuals from Bybit or Binance, filtered by CoinGecko market cap and the
perpetual's own 24h traded value."""

from __future__ import annotations

import re
import time

from ..engine import Bar
from .base import Instrument, daily_is_live, get_json

COINGECKO = "https://api.coingecko.com/api/v3/coins/markets"
BYBIT = "https://api.bybit.com"
BINANCE = "https://fapi.binance.com"

_MULT_PREFIX = re.compile(r"^(1000+|1M)(?=[A-Z])")
_MULT_SUFFIX = re.compile(r"(?<=[A-Z])1000+$")


def base_asset(symbol: str) -> str:
    """SOLUSDT -> SOL, 1000PEPEUSDT -> PEPE, SHIB1000USDT -> SHIB, 1INCHUSDT -> 1INCH."""
    base = symbol[:-4] if symbol.endswith("USDT") else symbol
    return _MULT_SUFFIX.sub("", _MULT_PREFIX.sub("", base))


def market_caps(min_usd: float) -> dict[str, float]:
    """Market cap by ticker symbol. Where tickers collide, the largest coin wins."""
    caps: dict[str, float] = {}
    page = 1
    while True:
        rows = get_json(COINGECKO, {"vs_currency": "usd", "order": "market_cap_desc",
                                    "per_page": 250, "page": page})
        if not rows:
            break
        for r in rows:
            cap = r.get("market_cap") or 0
            caps.setdefault(r["symbol"].upper(), cap)
        if (rows[-1].get("market_cap") or 0) < min_usd:
            break
        page += 1
        time.sleep(3)  # free tier rate limit
    return caps


class Bybit:
    name = "Bybit"

    def instruments(self) -> list[tuple[str, float]]:
        """(symbol, 24h traded value in USDT) for trading USDT perpetuals."""
        symbols, cursor = set(), ""
        while True:
            res = get_json(f"{BYBIT}/v5/market/instruments-info",
                           {"category": "linear", "limit": 1000, "cursor": cursor})["result"]
            for s in res["list"]:
                if (s.get("status") == "Trading" and s.get("quoteCoin") == "USDT"
                        and s.get("contractType") == "LinearPerpetual"):
                    symbols.add(s["symbol"])
            cursor = res.get("nextPageCursor") or ""
            if not cursor:
                break
        tickers = get_json(f"{BYBIT}/v5/market/tickers", {"category": "linear"})["result"]["list"]
        return [(t["symbol"], float(t.get("turnover24h") or 0)) for t in tickers if t["symbol"] in symbols]

    def daily(self, symbol: str) -> list[Bar]:
        bars: dict[int, Bar] = {}
        end = None
        while True:
            params = {"category": "linear", "symbol": symbol, "interval": "D", "limit": 1000}
            if end:
                params["end"] = end
            rows = get_json(f"{BYBIT}/v5/market/kline", params)["result"]["list"]  # newest first
            for r in rows:
                t = int(r[0])
                bars[t] = Bar(t, float(r[1]), float(r[2]), float(r[3]), float(r[4]))
            if len(rows) < 1000:
                break
            end = int(rows[-1][0]) - 1
        return [bars[t] for t in sorted(bars)]

    def tv_symbol(self, symbol: str) -> str:
        return f"BYBIT:{symbol}.P"


class Binance:
    name = "Binance"

    def instruments(self) -> list[tuple[str, float]]:
        info = get_json(f"{BINANCE}/fapi/v1/exchangeInfo")
        symbols = {s["symbol"] for s in info["symbols"]
                   if s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT"
                   and s.get("status") == "TRADING"}
        tickers = get_json(f"{BINANCE}/fapi/v1/ticker/24hr")
        return [(t["symbol"], float(t.get("quoteVolume") or 0)) for t in tickers if t["symbol"] in symbols]

    def daily(self, symbol: str) -> list[Bar]:
        bars: dict[int, Bar] = {}
        end = None
        while True:
            params = {"symbol": symbol, "interval": "1d", "limit": 1500}
            if end:
                params["endTime"] = end
            rows = get_json(f"{BINANCE}/fapi/v1/klines", params)  # oldest first
            for r in rows:
                t = int(r[0])
                bars[t] = Bar(t, float(r[1]), float(r[2]), float(r[3]), float(r[4]))
            if len(rows) < 1500:
                break
            end = int(rows[0][0]) - 1
        return [bars[t] for t in sorted(bars)]

    def tv_symbol(self, symbol: str) -> str:
        return f"BINANCE:{symbol}.P"


class Crypto:
    """Instruments passing the market-cap and volume filters, and their daily candles."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.ex = Binance() if cfg.get("exchange", "bybit").lower() == "binance" else Bybit()

    def instruments(self) -> list[Instrument]:
        min_cap = float(self.cfg.get("min_market_cap_usd", 100e6))
        min_vol = float(self.cfg.get("min_volume_usd", 50e6))
        caps = market_caps(min_cap)
        out = []
        for symbol, vol in self.ex.instruments():
            cap = caps.get(base_asset(symbol))
            if cap is None or cap < min_cap or vol < min_vol:
                continue
            out.append(Instrument(symbol=symbol, market="Crypto", name=base_asset(symbol),
                                  tv_symbol=self.ex.tv_symbol(symbol), exchange=self.ex.name,
                                  market_cap_usd=cap, volume_usd=vol))
        return sorted(out, key=lambda i: -(i.market_cap_usd or 0))

    def daily(self, inst: Instrument, now_ms: int) -> tuple[list[Bar], bool]:
        bars = self.ex.daily(inst.symbol)
        return bars, bool(bars) and daily_is_live(bars[-1], now_ms)
