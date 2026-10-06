"""Made-up candles shaped like the reference charts. Used by the tests and the demo page.
Each sequence is read off a screenshot: prices are approximate."""

from __future__ import annotations

from datetime import datetime, timezone

from .engine import Bar

DAY_MS = 86_400_000


def bars(rows: list[tuple[float, float, float, float]], start: str = "2026-01-05") -> list[Bar]:
    t0 = int(datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp() * 1000)
    return [Bar(t0 + i * DAY_MS, o, h, l, c) for i, (o, h, l, c) in enumerate(rows)]


# CADJPY 4D: bearish body 113.64-113.96 hidden by a bearish, a bullish and a bearish FVG -> 3x.
CADJPY_4D = bars([
    (113.0, 113.5, 112.9, 113.4), (113.96, 114.1, 113.5, 113.64), (113.64, 114.7, 113.6, 114.6),
    (114.6, 116.0, 114.6, 115.9), (115.9, 116.1, 115.4, 115.5), (115.5, 115.6, 112.3, 112.4),
    (112.4, 113.2, 112.2, 113.1), (113.1, 114.4, 113.0, 114.35), (114.35, 115.0, 114.1, 114.9),
    (114.9, 115.1, 114.65, 114.8), (114.8, 115.05, 112.9, 113.0), (113.0, 113.46, 111.2, 111.3),
    (111.3, 111.8, 110.4, 110.7)])

# EURUSD 3W (rejected): bearish body 1.0574-1.0706; the next candle wicks back in and the
# first FVG over it is bullish.
EURUSD_3W_REJECTED = bars([
    (1.08, 1.085, 1.065, 1.075), (1.0706, 1.075, 1.045, 1.0574), (1.0574, 1.0618, 1.035, 1.04),
    (1.04, 1.045, 1.02, 1.03), (1.03, 1.04, 1.015, 1.035), (1.035, 1.10, 1.034, 1.098),
    (1.098, 1.12, 1.08, 1.11), (1.11, 1.13, 1.10, 1.12)])

# EURUSD 3W (valid): bearish body 1.1417-1.1452 hidden by the September drop -> 1x.
EURUSD_3W = bars([
    (1.150, 1.152, 1.133, 1.1452), (1.1452, 1.1466, 1.1326, 1.1417), (1.1417, 1.153, 1.1354, 1.1528),
    (1.1546, 1.170, 1.150, 1.1677), (1.1671, 1.169, 1.1568, 1.1597), (1.1597, 1.1600, 1.1210, 1.1248),
    (1.1248, 1.1261, 1.1161, 1.1226)])

# LINK 1W: bullish body 8.381-8.825, a wick ~3.4% into it, then a bullish FVG -> 1x touched.
LINK_1W = bars([
    (8.1, 8.65, 8.0, 8.38), (8.381, 8.84, 8.26, 8.825), (8.825, 8.92, 7.9, 8.378),
    (8.378, 8.396, 8.0, 8.18), (8.18, 12.2, 8.16, 12.0), (12.0, 14.3, 11.2, 13.9)])

# SOL 7D: bullish body 89.2-91.0 with long wicks (body ~17% of range) -> 1x.
SOL_7D = bars([
    (88.0, 92.0, 86.0, 89.0), (89.2, 98.3, 87.6, 91.0), (91.0, 93.6, 85.5, 86.2),
    (86.2, 87.9, 83.0, 84.0), (84.0, 85.0, 70.0, 72.0), (72.0, 76.0, 68.0, 75.6),
    (75.6, 87.4, 74.0, 85.3), (85.3, 103.0, 84.5, 101.9), (101.9, 104.0, 97.3, 100.3),
    (100.3, 121.0, 95.7, 120.9)])

# HYPE 5D: bullish body 24.0-24.67 hidden by a bullish FVG, now ~74% below price -> 1x.
HYPE_5D = bars([
    (25.5, 26.5, 23.8, 24.0), (24.0, 26.96, 23.07, 24.67), (24.67, 26.13, 20.7, 20.84),
    (20.84, 23.73, 20.4, 22.1), (22.1, 31.5, 21.9, 30.8), (30.8, 36.0, 27.4, 35.0),
    (35.0, 95.24, 34.0, 94.28)])

SAMPLES = [
    {"symbol": "CADJPY", "market": "FX", "exchange": "FXCM", "tv": "FXCM:CADJPY", "tf": "4D", "bars": CADJPY_4D},
    {"symbol": "EURUSD", "market": "FX", "exchange": "FXCM", "tv": "FXCM:EURUSD", "tf": "3W", "bars": EURUSD_3W},
    {"symbol": "LINKUSDT", "market": "Crypto", "exchange": "Binance", "tv": "BINANCE:LINKUSDT.P", "tf": "1W", "bars": LINK_1W},
    {"symbol": "SOLUSDT", "market": "Crypto", "exchange": "Bybit", "tv": "BYBIT:SOLUSDT.P", "tf": "7D", "bars": SOL_7D},
    {"symbol": "HYPEUSDT", "market": "Crypto", "exchange": "Bybit", "tv": "BYBIT:HYPEUSDT.P", "tf": "5D", "bars": HYPE_5D},
    # Same EURUSD sequence cut off while the September drop is still the open candle -> forming.
    {"symbol": "EURUSD", "market": "FX", "exchange": "FXCM", "tv": "FXCM:EURUSD", "tf": "2W",
     "bars": EURUSD_3W[:6], "live": True},
]
