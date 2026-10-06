from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .engine import Params


@dataclass
class Config:
    timeframes: list[str]
    anchor: str = "first"
    output: str = "output/hob_scan.html"
    params: Params = field(default_factory=Params)
    touched_penalty: float = 0.85
    crypto: dict = field(default_factory=dict)
    stocks: dict = field(default_factory=dict)
    fx: dict = field(default_factory=dict)


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
            touch_buffer_pct=det.get("touch_buffer_pct", 5),
            min_hidden=det.get("min_hidden", 1),
        ),
        touched_penalty=raw.get("ranking", {}).get("touched_penalty", 0.85),
        crypto=raw.get("crypto", {}),
        stocks=raw.get("stocks", {}),
        fx=raw.get("fx", {}),
    )
