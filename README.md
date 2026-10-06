# Hidden Orderblock Scanner

Finds **hidden orderblocks**: clean candle bodies that price has only ever skipped over inside Fair Value Gaps. Each FVG that covers the whole body adds one level of "hidden" (1x, 2x, 3x …). The more hidden, the stronger the zone.

## Definition

For a candidate candle **Z**, the body is the range between its open and close:

1. Z's colour sets the zone: a bearish candle makes a **bearish** zone, a bullish candle a **bullish** one.
2. The candle straight after Z may cross the body only by closing beyond its far side (the move away). If its wick goes back into the body, the zone is mitigated.
3. After that, every candle **M** that trades into the body must be the middle candle of an FVG that covers the **whole** body:
   - Bearish FVG: `low[M-1] >= bodyTop` and `high[M+1] <= bodyBottom`
   - Bullish FVG: `high[M-1] <= bodyBottom` and `low[M+1] >= bodyTop`
   - The **first** covering FVG must be the same colour as Z; that makes it 1x hidden. An opposite-colour first FVG invalidates the zone.
   - After that, every further covering FVG of either colour adds **+1 hidden**.
4. Any other wick or body that enters the zone mitigates it (takes the liquidity), and it is removed.
5. Body quality: tiny bodies with big wicks are filtered out. A body that is about 50% of the candle range is ideal.

Detection only uses candles from the chart's own timeframe.

## Pine indicator (`pine/hidden_orderblocks.pine`)

1. In TradingView, open **Pine Editor**, paste the file in, and click **Add to chart**.
2. Zones are drawn from the zone candle to the right edge of the chart.
   - Each zone is labelled `<hidden>x <timeframe>`, for example `3x 4D`.
   - Fill is darker the more hidden a zone is.
   - "testing" means the current candle is trading into the zone.
3. Small numbered tags (1, 2, 3 …) mark the FVG candles that hide each zone.
4. The table lists the visible zones ranked by hidden count, then by distance from price.
5. Three alerts are available:
   - hidden OB formed or gained a level
   - price tapping a hidden OB
   - hidden OB mitigated
6. The data window shows the nearest bullish and bearish hidden count and distance, so the script can be used in TradingView's Pine Screener.

### Reference examples (should match)

| Chart | Zone | Expected |
|---|---|---|
| CADJPY 4D (OANDA) | ~113.64 – 113.96 (Jul 2026) | 3x bearish |
| EURUSD 5D (OANDA) | ~1.1525 – 1.1555 (Aug 2026) | 1x bearish |
| NZDUSD 3W (FXCM) | ~0.6640 – 0.6705 (early 2022) | 1x bearish |

## Roadmap

- [x] Pine indicator to confirm the detection matches what's seen on charts
- [ ] Python scanner: crypto, indices, commodities, stocks and FX, on timeframes from 4H to 12M
- [ ] Quality ranking: timeframe weight × hidden count × body quality
