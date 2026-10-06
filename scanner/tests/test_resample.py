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
