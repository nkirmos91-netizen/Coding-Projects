"""Build higher-timeframe candles (2D, 5D, 1W, 3W, 1M, 12M ...) from daily candles.

Multi-day and multi-week candles must start on the same dates TradingView uses, or
bodies and FVGs come out different. Months are calendar-aligned (3M starts Jan,
Apr, Jul, Oct; 12M starts in January). For nD and nW the anchor is configurable
until it has been checked against TradingView charts:
  * "first": count from the first candle in the symbol's history
  * "epoch": count from 1970-01-01 (weeks: from the Monday of that week)
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


def _month_index(t: int) -> int:
    d = datetime.fromtimestamp(t / 1000, tz=timezone.utc)
    return d.year * 12 + d.month - 1


def _month_start_ms(index: int) -> int:
    y, m = divmod(index, 12)
    return int(datetime(y, m + 1, 1, tzinfo=timezone.utc).timestamp() * 1000)


def _week_index(t: int) -> int:
    # 1970-01-01 was a Thursday; +3 days makes weeks start on Monday.
    return (t // DAY_MS + 3) // 7


def resample(daily: list[Bar], tf: str, now_ms: int, daily_live: bool = False,
             anchor: str = "first") -> tuple[list[Bar], bool]:
    """Group daily candles into `tf` candles.

    Returns (candles, last_is_live). The last candle is live if its period has not
    finished yet or it contains a still-open daily candle.
    """
    n, unit = parse_tf(tf)
    if not daily:
        return [], False
    if unit == "D" and n == 1:
        return list(daily), daily_live

    keys: list[int] = []
    if unit == "D":
        keys = [i // n if anchor == "first" else (b.t // DAY_MS) // n for i, b in enumerate(daily)]
    elif unit == "W":
        base = _week_index(daily[0].t) if anchor == "first" else 0
        keys = [(_week_index(b.t) - base) // n for b in daily]
    else:
        keys = [_month_index(b.t) // n for b in daily]

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

    last_key = keys[-1]
    if unit == "D":
        if anchor == "first":
            unfinished = counts[-1] < n
        else:
            unfinished = now_ms < (last_key + 1) * n * DAY_MS
    elif unit == "W":
        base = _week_index(daily[0].t) if anchor == "first" else 0
        end_week = base + (last_key + 1) * n
        unfinished = now_ms < (end_week * 7 - 3) * DAY_MS
    else:
        unfinished = now_ms < _month_start_ms((last_key + 1) * n)
    return out, daily_live or unfinished
