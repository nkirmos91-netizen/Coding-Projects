from datetime import date, datetime, timedelta, timezone

from hobscan.engine import Bar
from hobscan.resample import parse_tf, resample, tv_interval

DAY = 86_400_000


def ms(d):
    return int(datetime.fromisoformat(d).replace(tzinfo=timezone.utc).timestamp() * 1000)


def daily(start, n, weekdays_only=False, skip=()):
    out, d, k = [], date.fromisoformat(start), 0
    while len(out) < n:
        if not (weekdays_only and d.weekday() >= 5) and d.isoformat() not in skip:
            out.append(Bar(ms(d.isoformat()), 10 + k, 11 + k, 9 + k, 10.5 + k))
            k += 1
        d += timedelta(days=1)
    return out


def starts(bars):
    return [datetime.fromtimestamp(b.t / 1000, timezone.utc).strftime("%Y-%m-%d") for b in bars]


def test_parse_and_tv_interval():
    assert parse_tf("3W") == (3, "W") and parse_tf("D") == (1, "D")
    assert tv_interval("1D") == "D" and tv_interval("12M") == "12M"


def test_weeks_start_monday():
    d = daily("2026-01-05", 14)  # Monday
    w, live = resample(d, "1W", now_ms=ms("2026-02-01"))
    assert starts(w) == ["2026-01-05", "2026-01-12"]
    assert w[0].o == d[0].o and w[0].c == d[6].c and w[0].h == max(b.h for b in d[:7])
    assert not live


def test_nflx_2w_2021_matches_tradingview():
    # TradingView NFLX 2W: candles start Mon 21 Jun, Tue 6 Jul (5 Jul holiday), Mon 19 Jul 2021.
    d = daily("2021-06-01", 45, weekdays_only=True, skip={"2021-07-05"})
    got = starts(resample(d, "2W", now_ms=ms("2021-09-01"))[0])
    assert {"2021-06-21", "2021-07-06", "2021-07-19"} <= set(got)
    assert "2021-06-28" not in got


def test_2w_and_3w_2026_match_tradingview():
    d = daily("2026-09-01", 30, weekdays_only=True)
    assert "2026-09-28" in starts(resample(d, "2W", now_ms=ms("2026-10-07"))[0])  # NFLX / AMZN 2W
    assert "2026-10-05" in starts(resample(d, "3W", now_ms=ms("2026-10-07"))[0])  # MSFT / EURUSD / NZDUSD 3W


def test_crypto_7d_matches_tradingview():
    # BYBIT:SOLUSDT.P 7D: candle starts 2026-10-01 (day 273 of the year).
    d = daily("2026-01-01", 279)  # every day, Jan 1 .. Oct 6
    assert "2026-10-01" in starts(resample(d, "7D", now_ms=ms("2026-10-06"))[0])


def test_us_stock_multi_day_matches_tradingview():
    # MSFT: 2D and 4D start Oct 2, 3D Oct 5, 5D Sep 29 and Mon Aug 31 (Labor Day Sep 7 closed).
    holidays = {"2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19",
                "2026-07-03", "2026-09-07"}
    d = [b for b in daily("2026-01-01", 200, weekdays_only=True, skip=holidays) if b.t <= ms("2026-10-05")]
    now = ms("2026-10-06")
    assert starts(resample(d, "2D", now_ms=now)[0])[-1] == "2026-10-02"
    assert starts(resample(d, "4D", now_ms=now)[0])[-1] == "2026-10-02"
    assert starts(resample(d, "3D", now_ms=now)[0])[-1] == "2026-10-05"
    five = starts(resample(d, "5D", now_ms=now)[0])
    assert five[-1] == "2026-09-29" and "2026-08-31" in five


def test_count_restarts_each_year():
    d = daily("2025-12-25", 14)
    got = starts(resample(d, "3D", now_ms=ms("2026-02-01"))[0])
    assert "2026-01-01" in got  # a new group starts on the first candle of the year
    assert "2025-12-31" in got  # the last 2025 group is cut short


def test_quarters_calendar_aligned():
    d = daily("2025-11-01", 120)
    q, _ = resample(d, "3M", now_ms=ms("2026-06-01"))
    assert [s[:7] for s in starts(q)] == ["2025-11", "2026-01"]


def test_last_period_live_until_it_ends():
    d = daily("2026-03-02", 10)  # Mon 2 Mar .. Wed 11 Mar
    assert resample(d, "1W", now_ms=ms("2026-03-12"))[1]
    assert not resample(d, "1W", now_ms=ms("2026-03-16"))[1]
