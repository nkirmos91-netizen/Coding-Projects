# Hidden Orderblock Scanner

Finds **hidden orderblocks**: clean candle bodies that price has only ever skipped over inside Fair Value Gaps. Each FVG that covers the whole body adds one level of "hidden" (1x, 2x, 3x …). The more hidden, the stronger the zone.

## Definition

For a candidate candle **Z**, the body is the range between its open and close:

1. Z's colour must match the **first** FVG that hides it (see 3). On the chart and in the scanner, a zone above price is shown as **bearish** (resistance) and below price as **bullish** (support).
2. The candle straight after Z may cross the body only by closing beyond its far side (the move away). If its wick goes back into the body, the zone is mitigated.
3. After that, every candle **M** that trades into the body must be an FVG candle that crosses the **whole** body. It is confirmed when M closes:
   - Bearish: `low[M-1] >= bodyTop` and `low[M] <= bodyBottom`
   - Bullish: `high[M-1] <= bodyBottom` and `high[M] >= bodyTop`
   - The candle after M must leave the gap open: after a bearish FVG candle its high must stay below the body (`high[M+1] <= bodyBottom`), after a bullish one its low must stay above (`low[M+1] >= bodyTop`). Otherwise there was no FVG (for example, just a wick through the body) and the zone is mitigated.
   - While M is still open, the zone shows as **forming** (dashed border).
   - The **first** covering FVG must be the same colour as Z; that makes it 1x hidden. An opposite-colour first FVG invalidates the zone.
   - After that, every further covering FVG of either colour adds **+1 hidden**.
4. Any other wick or body that enters the zone mitigates it (takes the liquidity), and it is removed.
   - **Touch buffer** (default 5% of the body height): a wick that only reaches into the outer 5% from either edge is allowed. The zone stays valid but is marked **touched** (yellow border, "touched" in its label).
   - **Fresh only** (default on): touched zones, and zones price is trading into right now, are hidden. Turn it off to see them labelled.
5. Body quality: tiny bodies with big wicks are filtered out. A body that is about 50% of the candle range is ideal.
6. Junk filter: the body must be at least **0.15× the 14-candle ATR**, so zones that are tiny next to the surrounding candles are skipped (e.g. BKNG 2W 120.93–121.98, about 0.1×).

Detection only uses candles from the chart's own timeframe.

## Pine indicator (`pine/hidden_orderblocks.pine`)

1. In TradingView, open **Pine Editor**, paste the file in, and click **Add to chart**.
2. Zones are drawn from the zone candle to the right edge of the chart.
   - Each zone is labelled `<hidden>x <timeframe>`, for example `3x 4D`.
   - Fill is darker the more hidden a zone is.
   - "testing" means the current candle is trading into the zone.
3. The table lists the visible zones ranked by hidden count, then by distance from price.
   - Zones are shown regardless of age or distance from price.
4. Three alerts are available:
   - hidden OB formed or gained a level
   - price tapping a hidden OB
   - hidden OB mitigated

### Reference examples (should match)

| Chart | Zone | Expected |
|---|---|---|
| CADJPY 4D (OANDA) | ~113.64 – 113.96 (Jul 2026) | 3x bearish |
| LINKUSDT.P 1W (Binance) | ~8.38 – 8.825 (Jul 2026) | 1x bullish, touched (hidden when Fresh only is on) |
| SOLUSDT.P 7D (Bybit) | ~89.2 – 91.0 (May 2026) | 1x bullish (body ~17% of range) |
| HYPEUSDT.P 5D (Bybit) | ~24.0 – 24.7 (Jan 2026) | 1x bullish (~74% below price) |
| EURUSD 5D (OANDA) | ~1.1525 – 1.1555 (Aug 2026) | 1x bearish |
| NZDUSD 3W (FXCM) | ~0.6640 – 0.6705 (early 2022) | 1x bearish |

## Roadmap

- [x] Pine indicator to confirm the detection matches what's seen on charts
- [x] Python scanner (`scanner/`): crypto and stocks on 1D–12M, ranked page
- [ ] Scanner: FXCM connection for FX, commodities and indices
- [x] Scanner: multi-day/week candle start dates matched to TradingView (crypto, US stocks)
- [ ] Scanner: ASX and XETRA 2D–5D candle start dates
