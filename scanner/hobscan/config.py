from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .engine import Params

DEFAULT_MAX_DISTANCE = {"Crypto": 50.0, "Stocks": 30.0}


@dataclass
class Config:
    timeframes: list[str]
    output: str = "output/hob_scan.html"
    params: Params = field(default_factory=Params)
    touched_penalty: float = 0.85
    crypto: dict = field(default_factory=dict)
    stocks: dict = field(default_factory=dict)
    fx: dict = field(default_factory=dict)

    def max_distance_pct(self, market: str) -> float | None:
        """Zones further than this % from current price are left out of the scan."""
        section = {"Crypto": self.crypto, "Stocks": self.stocks, "FX": self.fx}.get(market, {})
        return section.get("max_distance_pct", DEFAULT_MAX_DISTANCE.get(market))


def load(path: str | Path) -> Config:
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    det = raw.get("detection", {})
    return Config(
        timeframes=raw.get("timeframes", ["1D", "1W", "1M"]),
        output=raw.get("output", "output/hob_scan.html"),
        params=Params(
            min_body_pct=det.get("min_body_pct", 10),
            min_body_atr=det.get("min_body_atr", 0.15),
            touch_buffer_pct=det.get("touch_buffer_pct", 15),
            min_hidden=det.get("min_hidden", 1),
            fresh_only=det.get("fresh_only", True),
        ),
        touched_penalty=raw.get("ranking", {}).get("touched_penalty", 0.85),
        crypto=raw.get("crypto", {}),
        stocks=raw.get("stocks", {}),
        fx=raw.get("fx", {}),
    )
