"""Quality score: higher timeframe and more hidden rank higher; an even body/wick
split and an untouched body are tie-breakers."""

from __future__ import annotations

import math

from .resample import tf_days


def tf_weight(tf: str) -> float:
    # 1D = 1, 1W ~ 3.8, 1M ~ 5.9, 3M ~ 7.5, 12M ~ 9.5
    return 1 + math.log2(tf_days(tf))


def body_quality(body_pct: float) -> float:
    # 1.0 when body is 50% of the range (body and wicks even), down to 0.5 at the extremes.
    return 1 - abs(body_pct - 50) / 100


def score(tf: str, hidden: int, body_pct: float, touched: bool, touched_penalty: float) -> float:
    s = tf_weight(tf) * hidden * body_quality(body_pct)
    return s * touched_penalty if touched else s
