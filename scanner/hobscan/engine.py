"""Hidden orderblock detection.

A straight port of pine/hidden_orderblocks.pine. Keep the two in step: any rule
change made in one must be made in the other.

Rules for a candidate candle Z (body = open..close):
  * Z's colour must match the first FVG that hides it. Zones above price are shown
    as bearish (resistance), below price as bullish (support).
  * The candle straight after Z may cross the body only by closing beyond its far
    side (the move away).
  * Every later candle M that reaches into the body is judged when it closes:
      - M is an FVG candle whose body carries price through the whole zone -> hidden += 1
          bearish: low[M-1] >= top - buf and close[M] <= bot + buf
          bullish: high[M-1] <= bot + buf and close[M] >= top - buf
        The FIRST such FVG must be the zone's colour; after that either colour counts.
      - anything else is a touch: its depth into the body (from the nearer edge) is
        added to a running total. The zone survives, marked touched, while the total
        of all touches stays within the touch buffer (default 15% of body height);
        past that it is mitigated. This also covers the candle after an FVG candle
        filling the gap.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Bar:
    t: int  # period open time, ms since epoch (UTC)
    o: float
    h: float
    l: float
    c: float


@dataclass
class Params:
    min_body_pct: float = 10.0  # body as % of candle range
    min_body_atr: float = 0.15  # 1x zones need a body of at least this x the 14-candle ATR ("junk" filter)
    touch_buffer_pct: float = 15.0  # total wick depth allowed into the body, % of body height
    min_hidden: int = 1
    fresh_only: bool = True  # drop zones price is trading into right now (touched zones stay)


@dataclass
class Zone:
    idx: int
    t: int
    top: float
    bot: float
    bear: bool
    body_pct: float
    hidden: int = 0
    touched: bool = False
    small: bool = False  # body < min_body_atr x ATR: only shown once hidden 2x or more
    eaten: float = 0.0  # total depth of all touches into the body so far
    fvg_times: list[int] = field(default_factory=list)


@dataclass
class Found:
    zone: Zone
    hidden: int  # includes a forming FVG on the live candle
    forming: bool  # the live candle is crossing the body as an FVG candle
    testing: bool  # the live candle is trading into the body (not as an FVG)
    touched: bool


NONE, TOUCH, FVG_BEAR, FVG_BULL, KILL = "none", "touch", "fvg_bear", "fvg_bull", "kill"
FVG = (FVG_BEAR, FVG_BULL)


def judge(z: Zone, i: int, b: Bar, prev: Bar, buf_pct: float) -> tuple[str, float]:
    """What candle `b` at index `i` does to zone `z`, and how deep it touched the body.

    Doesn't change `z`; the caller adds the depth to `z.eaten` for closed candles.
    """
    if i <= z.idx or not (b.h > z.bot and b.l < z.top):
        return NONE, 0.0
    buf = (z.top - z.bot) * buf_pct / 100
    if i == z.idx + 1:
        # The move away: it may only cross the body by closing beyond the far side.
        depth = max(0.0, z.top - b.c) if z.bear else max(0.0, b.c - z.bot)
        if depth == 0:
            return NONE, 0.0
        return (KILL if z.eaten + depth > buf else TOUCH), depth
    # The FVG candle's body must carry price through: it closes (or, while open,
    # trades) beyond the far side. A wick through the body doesn't count.
    bear_cov = prev.l >= z.top - buf and b.c <= z.bot + buf
    bull_cov = prev.h <= z.bot + buf and b.c >= z.top - buf
    same = (bear_cov and z.bear) or (bull_cov and not z.bear)
    if same or ((bear_cov or bull_cov) and z.hidden > 0):
        return (FVG_BEAR if bear_cov else FVG_BULL), 0.0
    # A touch: depth from the nearer edge, added to the running total.
    depth = min(z.top - max(b.l, z.bot), min(b.h, z.top) - z.bot)
    return (KILL if z.eaten + depth > buf else TOUCH), depth


def prev_clear(z: Zone, prev: Bar, buf_pct: float) -> bool:
    """Whether the candle before stayed out of the body, so the next one could still be an FVG candle."""
    buf = (z.top - z.bot) * buf_pct / 100
    return prev.l >= z.top - buf or prev.h <= z.bot + buf


def detect(bars: list[Bar], params: Params = Params(), last_is_live: bool = False) -> list[Found]:
    """Hidden orderblocks still valid at the end of `bars`.

    If `last_is_live`, the final bar is the still-open candle: it never becomes a
    candidate and can only mark zones as forming / testing / touched.
    """
    closed = bars[:-1] if last_is_live and bars else bars
    active: list[Zone] = []
    atr = None  # Wilder's ATR(14), same as TradingView's ta.atr(14)
    trs: list[float] = []
    for i, b in enumerate(closed):
        tr = b.h - b.l if i == 0 else max(b.h, closed[i - 1].c) - min(b.l, closed[i - 1].c)
        if atr is None:
            trs.append(tr)
            if len(trs) == 14:
                atr = sum(trs) / 14
        else:
            atr = (atr * 13 + tr) / 14
        if i >= 1:
            prev = closed[i - 1]
            keep = []
            for z in active:
                v, depth = judge(z, i, b, prev, params.touch_buffer_pct)
                if v == KILL:
                    continue
                if v in FVG:
                    z.hidden += 1
                    z.fvg_times.append(b.t)
                elif v == TOUCH:
                    z.touched = True
                    z.eaten += depth
                keep.append(z)
            active = keep
        rng = b.h - b.l
        body = abs(b.c - b.o)
        if rng > 0 and body > 0 and body / rng * 100 >= params.min_body_pct:
            active.append(Zone(idx=i, t=b.t, top=max(b.o, b.c), bot=min(b.o, b.c),
                               bear=b.c < b.o, body_pct=body / rng * 100,
                               small=atr is not None and body < params.min_body_atr * atr))

    found = []
    live = bars[-1] if last_is_live and len(bars) >= 2 else None
    for z in active:
        v = judge(z, len(closed), live, closed[-1], params.touch_buffer_pct)[0] if live else NONE
        if v == KILL and not prev_clear(z, closed[-1], params.touch_buffer_pct):
            continue  # the open candle is already past the allowance and can't become an FVG candle
        forming = v in FVG
        hidden = z.hidden + (1 if forming else 0)
        touched = z.touched or v == TOUCH
        if params.fresh_only and v == KILL:
            continue
        if z.small and hidden < 2:
            continue  # junk: tiny next to the surrounding candles and only 1x hidden
        if hidden >= params.min_hidden:
            found.append(Found(zone=z, hidden=hidden, forming=forming,
                               testing=v == KILL, touched=touched))
    return found
