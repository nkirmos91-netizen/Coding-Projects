from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .engine import Params

# Days on which every 2D-5D candle starts on TradingView, per exchange (trading-day count).
DEFAULT_SESSION_REFS = {"Stocks": {"NYSE": "2026-09-22", "NASDAQ": "2026-09-22"}}
DEFAULT_ANCHORS = {"Crypto": "epoch", "Stocks": "sessions"}
DEFAULT_MAX_DISTANCE = {"Crypto": 50.0, "Stocks": 30.0}


@dataclass
class Config:
    timeframes: list[str]
    anchor: str = "first"  # fallback for markets without their own setting
    output: str = "output/hob_scan.html"
    params: Params = field(default_factory=Params)
    touched_penalty: float = 0.85
    crypto: dict = field(default_factory=dict)
    stocks: dict = field(default_factory=dict)
    fx: dict = field(default_factory=dict)

    def session_ref(self, market: str, exchange: str) -> str | None:
        """Reference day for anchor 'sessions' (a day on which every 2D-5D candle starts)."""
        section = {"Crypto": self.crypto, "Stocks": self.stocks, "FX": self.fx}.get(market, {})
        refs = section.get("session_refs", DEFAULT_SESSION_REFS.get(market, {}))
        return refs.get(exchange)

    def max_distance_pct(self, market: str) -> float | None:
        """Zones further than this % from current price are left out of the scan."""
        section = {"Crypto": self.crypto, "Stocks": self.stocks, "FX": self.fx}.get(market, {})
        return section.get("max_distance_pct", DEFAULT_MAX_DISTANCE.get(market))

    def anchor_for(self, market: str) -> str:
        """Where 2D-7D candles start: crypto counts calendar days, stocks count trading days."""
        section = {"Crypto": self.crypto, "Stocks": self.stocks, "FX": self.fx}.get(market, {})
        anchor = section.get("anchor", DEFAULT_ANCHORS.get(market, self.anchor))
        # Older configs used "first" for stocks, which doesn't match TradingView.
        return "sessions" if market == "Stocks" and anchor == "first" else anchor


def load(path: str | Path) -> Config:
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    det = raw.get("detection", {})
    return Config(
        timeframes=raw.get("timeframes", ["1D", "1W", "1M"]),
        anchor=raw.get("anchor", "first"),
        output=raw.get("output", "output/hob_scan.html"),
        params=Params(
            min_body_pct=det.get("min_body_pct", 10),
            min_body_atr=det.get("min_body_atr", 0.15),
            touch_buffer_pct=det.get("touch_buffer_pct", 5),
            min_hidden=det.get("min_hidden", 1),
            fresh_only=det.get("fresh_only", True),
        ),
        touched_penalty=raw.get("ranking", {}).get("touched_penalty", 0.85),
        crypto=raw.get("crypto", {}),
        stocks=raw.get("stocks", {}),
        fx=raw.get("fx", {}),
    )
