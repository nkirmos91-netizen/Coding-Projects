"""Hidden orderblock detection.

A straight port of pine/hidden_orderblocks.pine. Keep the two in step: any rule
change made in one must be made in the other.

Rules for a candidate candle Z (body = open..close):
  * Z's colour sets the zone: bearish candle = bearish zone, bullish = bullish.
  * The candle straight after Z may cross the body only by closing beyond its
    far side (the move away). Closing inside the touch buffer marks it touched.
  * Every later candle M that reaches into the body is judged when it closes:
      - M crosses the whole body as an FVG candle -> hidden += 1
          bearish: low[M-1] >= top - buf and close[M] <= bot + buf
          bullish: high[M-1] <= bot + buf and close[M] >= top - buf
        The FIRST such FVG must be the zone's colour; after that either colour counts.
        The candle after M must leave the gap open (bearish: high <= bot + buf,
        bullish: low >= top - buf), or the zone is mitigated.
      - M only reaches the outer touch buffer -> allowed, zone marked touched
      - anything else -> mitigated (zone removed)
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
    min_body_atr: float = 0.15  # body as a multiple of the 14-candle ATR (drops "junk" zones)
    touch_buffer_pct: float = 5.0  # % of body height allowed at each edge
    min_hidden: int = 1
    fresh_only: bool = True  # drop zones that were touched or are being traded into now


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
    gap_dir: int = 0  # +1 / -1: last candle was a bearish / bullish FVG candle; next must leave the gap open
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


def gap_filled(z: Zone, b: Bar, buf_pct: float) -> bool:
    """Whether candle `b`, right after an FVG candle, closed the gap over the body."""
    buf = (z.top - z.bot) * buf_pct / 100
    return b.h > z.bot + buf if z.gap_dir > 0 else b.l < z.top - buf


def judge(z: Zone, i: int, b: Bar, prev: Bar, buf_pct: float) -> str:
    """What candle `b` at index `i` does to zone `z`."""
    if i <= z.idx or not (b.h > z.bot and b.l < z.top):
        return NONE
    buf = (z.top - z.bot) * buf_pct / 100
    if i == z.idx + 1:
        # The move away: it may only cross the body by closing beyond the far side.
        if (b.c <= z.top - buf) if z.bear else (b.c >= z.bot + buf):
            return KILL
        if (b.c <= z.top) if z.bear else (b.c >= z.bot):
            return TOUCH
        return NONE
    if b.h > z.bot + buf and b.l < z.top - buf:
        # The FVG candle's body must carry price through: it closes (or, while open,
        # trades) beyond the far side. A wick through the body doesn't count.
        bear_cov = prev.l >= z.top - buf and b.c <= z.bot + buf
        bull_cov = prev.h <= z.bot + buf and b.c >= z.top - buf
        same = (bear_cov and z.bear) or (bull_cov and not z.bear)
        if same or ((bear_cov or bull_cov) and z.hidden > 0):
            return FVG_BEAR if bear_cov else FVG_BULL
        return KILL
    return TOUCH


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
                if z.gap_dir:
                    filled = gap_filled(z, b, params.touch_buffer_pct)
                    z.gap_dir = 0
                    if filled:
                        continue
                v = judge(z, i, b, prev, params.touch_buffer_pct)
                if v == KILL:
                    continue
                if v in FVG:
                    z.hidden += 1
                    z.gap_dir = 1 if v == FVG_BEAR else -1
                    z.fvg_times.append(b.t)
                elif v == TOUCH:
                    z.touched = True
                keep.append(z)
            active = keep
        rng = b.h - b.l
        body = abs(b.c - b.o)
        if (rng > 0 and body > 0 and body / rng * 100 >= params.min_body_pct
                and (atr is None or body >= params.min_body_atr * atr)):
            active.append(Zone(idx=i, t=b.t, top=max(b.o, b.c), bot=min(b.o, b.c),
                               bear=b.c < b.o, body_pct=body / rng * 100))

    found = []
    live = bars[-1] if last_is_live and len(bars) >= 2 else None
    for z in active:
        v = judge(z, len(closed), live, closed[-1], params.touch_buffer_pct) if live else NONE
        if live and z.gap_dir and gap_filled(z, live, params.touch_buffer_pct):
            continue  # the open candle already filled the gap: there was no FVG
        forming = v in FVG
        hidden = z.hidden + (1 if forming else 0)
        touched = z.touched or v == TOUCH
        if params.fresh_only and (touched or v == KILL):
            continue
        if hidden >= params.min_hidden:
            found.append(Found(zone=z, hidden=hidden, forming=forming,
                               testing=v == KILL, touched=touched))
    return found
