"""Build higher-timeframe candles (2D, 5D, 1W, 3W, 1M, 12M ...) from daily candles.

Multi-period candles must start on the same dates TradingView uses, or bodies and FVGs
come out different. TradingView restarts the count every calendar year:
  * nD: groups of n daily candles, counted from the symbol's first daily candle of the
    year (calendar days for crypto, trading days for stocks; holidays have no candle).
  * nW: groups of n weeks (Monday to Sunday), counted from the first week that starts in
    the year (the first Monday on or after 1 January).
  * nM: calendar-aligned (3M starts Jan, Apr, Jul, Oct; 12M starts in January).
The last group of a year is cut short at the year end.
Checked against TradingView: NFLX 2W (21 Jun, 6 Jul, 19 Jul 2021 and 28 Sep 2026),
MSFT/EURUSD/NZDUSD 3W (5 Oct 2026), SOL 7D (1 Oct 2026), MSFT 2D-5D (Oct 2026, and the
5D candle starting Mon 31 Aug 2026 over Labor Day).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from .engine import Bar

DAY_MS = 86_400_000
_TF = re.compile(r"^(\d*)([DWM])$")


def parse_tf(tf: str) -> tuple[int, str]:
    m = _TF.match(tf.strip().upper())
    if not m:
        raise ValueError(f"Unsupported timeframe {tf!r}: use forms like 1D, 4D, 1W, 3W, 1M, 12M")
    return int(m.group(1) or 1), m.group(2)


def tf_days(tf: str) -> float:
    n, unit = parse_tf(tf)
    return n * {"D": 1, "W": 7, "M": 30.44}[unit]


def tv_interval(tf: str) -> str:
    """TradingView chart URL interval code."""
    n, unit = parse_tf(tf)
    return unit if n == 1 else f"{n}{unit}"


def _monday(t: int) -> int:
    """Day number (days since 1970-01-01) of the Monday of t's week."""
    day = t // DAY_MS
    return day - (day + 3) % 7  # 1970-01-01 was a Thursday


def _first_monday(year: int) -> int:
    """Day number of the first Monday on or after 1 January."""
    jan1 = (datetime(year, 1, 1, tzinfo=timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)).days
    return jan1 + (-(jan1 + 3)) % 7


def _year(t: int) -> int:
    return datetime.fromtimestamp(t / 1000, timezone.utc).year


def resample(daily: list[Bar], tf: str, now_ms: int, daily_live: bool = False, **_ignored) -> tuple[list[Bar], bool]:
    """Group daily candles into `tf` candles, the way TradingView does.

    Returns (candles, last_is_live). The last candle is live if its period has not
    finished yet or it contains a still-open daily candle.
    """
    n, unit = parse_tf(tf)
    if not daily:
        return [], False
    if n == 1 and unit == "D":
        return list(daily), daily_live

    keys: list[tuple[int, int]] = []
    if unit == "D":
        year, k = None, 0
        for b in daily:
            y = _year(b.t)
            k = k + 1 if y == year else 0
            year = y
            keys.append((y, k // n))
    elif unit == "W":
        for b in daily:
            mon = _monday(b.t)
            y = _year(mon * DAY_MS)  # a week belongs to the year its Monday is in
            keys.append((y, (mon - _first_monday(y)) // 7 // n))
    else:
        for b in daily:
            d = datetime.fromtimestamp(b.t / 1000, timezone.utc)
            keys.append((d.year, (d.month - 1) // n))

    out: list[Bar] = []
    counts: list[int] = []
    cur_key = None
    for b, k in zip(daily, keys):
        if k != cur_key:
            out.append(b)
            counts.append(1)
            cur_key = k
        else:
            last = out[-1]
            out[-1] = Bar(t=last.t, o=last.o, h=max(last.h, b.h), l=min(last.l, b.l), c=b.c)
            counts[-1] += 1

    y, k = keys[-1]
    year_end = int(datetime(y + 1, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    if unit == "D":
        unfinished = counts[-1] < n and now_ms < year_end
    elif unit == "W":
        group_end = (_first_monday(y) + (k + 1) * n * 7) * DAY_MS
        unfinished = now_ms < min(group_end, (_first_monday(y + 1)) * DAY_MS)
    else:
        m = (k + 1) * n
        end = datetime(y + 1, 1, 1, tzinfo=timezone.utc) if m >= 12 else datetime(y, m + 1, 1, tzinfo=timezone.utc)
        unfinished = now_ms < int(end.timestamp() * 1000)
    return out, daily_live or unfinished
