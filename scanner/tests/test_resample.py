from datetime import datetime, timezone

from hobscan.engine import Bar
from hobscan.resample import parse_tf, resample, tv_interval

DAY = 86_400_000


def ms(d):
    return int(datetime.fromisoformat(d).replace(tzinfo=timezone.utc).timestamp() * 1000)


def daily(start, n):
    t0 = ms(start)
    return [Bar(t0 + i * DAY, 10 + i, 11 + i, 9 + i, 10.5 + i) for i in range(n)]


def test_parse_and_tv_interval():
    assert parse_tf("3W") == (3, "W") and parse_tf("D") == (1, "D")
    assert tv_interval("1D") == "D" and tv_interval("12M") == "12M"


def test_weeks_start_monday():
    d = daily("2026-01-01", 14)  # Thursday
    w, live = resample(d, "1W", now_ms=ms("2026-02-01"))
    assert [datetime.fromtimestamp(b.t / 1000, timezone.utc).strftime("%a %d") for b in w] == ["Thu 01", "Mon 05", "Mon 12"]
    assert w[1].o == d[4].o and w[1].c == d[10].c and w[1].h == max(b.h for b in d[4:11])
    assert not live


def test_quarters_calendar_aligned():
    d = daily("2025-11-01", 120)
    q, _ = resample(d, "3M", now_ms=ms("2026-06-01"))
    assert [datetime.fromtimestamp(b.t / 1000, timezone.utc).strftime("%Y-%m") for b in q] == ["2025-11", "2026-01"]


def test_last_period_live_until_it_ends():
    d = daily("2026-03-02", 10)  # Mon 2 Mar .. Wed 11 Mar
    _, live = resample(d, "1W", now_ms=ms("2026-03-12"))
    assert live
    _, live = resample(d, "1W", now_ms=ms("2026-03-16"))
    assert not live


def test_n_day_counts_from_first_candle():
    d = daily("2026-01-01", 11)
    b, live = resample(d, "5D", now_ms=ms("2026-02-01"))
    assert len(b) == 3 and b[0].c == d[4].c and live  # last group has 1 of 5 days


def test_3w_matches_tradingview_boundary():
    # TradingView: MSFT / EURUSD / NZDUSD 3W candles start on Monday 2026-10-05.
    d = daily("2026-09-14", 30)
    w, _ = resample(d, "3W", now_ms=ms("2026-10-14"))
    starts = [datetime.fromtimestamp(b.t / 1000, timezone.utc).strftime("%Y-%m-%d") for b in w]
    assert starts == ["2026-09-14", "2026-10-05"]


def test_crypto_7d_epoch_matches_tradingview():
    # TradingView BYBIT:SOLUSDT.P 7D: current candle starts 2026-10-01.
    d = daily("2026-09-20", 16)
    w, _ = resample(d, "7D", now_ms=ms("2026-10-06"), anchor="epoch")
    starts = [datetime.fromtimestamp(b.t / 1000, timezone.utc).strftime("%Y-%m-%d") for b in w]
    assert starts == ["2026-09-20", "2026-09-24", "2026-10-01"]


def test_us_stock_sessions_match_tradingview():
    # NYSE trading days Aug 24 - Oct 7 2026 (Labor Day Sep 7 closed). TradingView MSFT:
    # 2D and 4D start Oct 2, 3D starts Oct 5, 5D starts Sep 29 and Aug 31.
    dates = ([f"2026-08-{d:02d}" for d in range(24, 32)] + [f"2026-09-{d:02d}" for d in range(1, 31)]
             + [f"2026-10-{d:02d}" for d in range(1, 8)])
    sessions = [x for x in dates if datetime.fromisoformat(x).weekday() < 5 and x != "2026-09-07"]
    bars = [Bar(ms(x), 1, 2, 0.5, 1.5) for x in sessions if x <= "2026-10-05"]
    ref = ms("2026-09-22")
    def starts(tf):
        b, _ = resample(bars, tf, now_ms=ms("2026-10-06"), anchor="sessions", session_ref_ms=ref)
        return [datetime.fromtimestamp(x.t / 1000, timezone.utc).strftime("%Y-%m-%d") for x in b]
    assert starts("2D")[-1] == "2026-10-02" and starts("4D")[-1] == "2026-10-02"
    assert starts("3D")[-1] == "2026-10-05" and starts("5D")[-1] == "2026-09-29"
    assert "2026-08-31" in starts("5D") and "2026-09-08" in starts("5D")
