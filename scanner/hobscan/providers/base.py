from __future__ import annotations

import time
from dataclasses import dataclass

import requests

from ..engine import Bar

DAY_MS = 86_400_000


@dataclass
class Instrument:
    symbol: str  # provider symbol, e.g. SOLUSDT or BHP.AX
    market: str  # "Crypto", "Stocks", "FX"
    name: str
    tv_symbol: str  # TradingView symbol, e.g. BYBIT:SOLUSDT.P
    exchange: str = ""
    market_cap_usd: float | None = None
    volume_usd: float | None = None


def get_json(url: str, params: dict | None = None, tries: int = 4, timeout: float = 20):
    """GET with retries and back-off for rate limits and network errors."""
    delay = 2.0
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} from {url}")
            r.raise_for_status()
            return r.json()
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError):
            if attempt == tries - 1:
                raise
            time.sleep(delay)
            delay *= 2


def daily_is_live(last: Bar, now_ms: int) -> bool:
    """A UTC-aligned daily candle is still open until 24h after it started."""
    return now_ms < last.t + DAY_MS
