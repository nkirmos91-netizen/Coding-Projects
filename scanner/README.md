# Hidden Orderblock Scanner

Scans markets on daily-and-higher timeframes for hidden orderblocks and writes one
ranked page (`output/hob_scan.html`). The detection rules are the same as the
TradingView indicator in `../pine/hidden_orderblocks.pine` (see the main README).

## Markets and data

| Market | Source | Filter (editable in `config.toml`) |
|---|---|---|
| Crypto | Bybit (or Binance) USDT perpetuals; market cap from CoinGecko | market cap ≥ $100m and perp 24h volume ≥ $50m; zones within 50% of price |
| Stocks: NYSE, NASDAQ, ASX, XETR | Yahoo Finance | market cap ≥ $150m and 10-day average daily traded value ≥ $15m (USD); zones within 30% of price |
| FX, commodities, indices | FXCM | **not connected yet** |

All timeframes (1D, 2D, 3D, 4D, 5D, 1W, 2W, 3W, 1M, 2M, 3M, 6M, 12M) are built from daily candles.

## Ranking

`score = timeframe weight × hidden count × body quality`, ×0.85 if touched.

- Timeframe weight: 1D = 1, 1W ≈ 3.8, 1M ≈ 5.9, 3M ≈ 7.5, 12M ≈ 9.5
- Body quality: 1.0 when the body is 50% of the candle range, down to 0.5

The page sorts by any column and filters by market, direction, timeframe, minimum
hidden count and touched. Each symbol links to its TradingView chart on that timeframe.

## Run it

Needs Python 3.11 or newer.

```
cd scanner
pip install -r requirements.txt
cp config.example.toml config.toml
python -m hobscan demo                     # example page, no internet needed
python -m hobscan scan --limit 20          # quick test: first 20 symbols per market
python -m hobscan scan                     # full scan
```

Then open `output/hob_scan.html` in a browser.

Bybit and Binance block some countries (including the US), so run it from a
location they serve.

## Compare candles with TradingView

```
python -m hobscan candles MSFT 5D
python -m hobscan candles SOLUSDT 3D
```

Prints the scanner's last few candles (start date, open, high, low, close).
Hover the same candles on TradingView to check they match.

## Still to do

- Match ASX and XETRA 2D–5D candles to TradingView (they are skipped until then).
  Crypto and US stocks are matched on every timeframe.
- FXCM connection for FX, commodities and indices.

## Tests

```
pip install pytest
python -m pytest
```
