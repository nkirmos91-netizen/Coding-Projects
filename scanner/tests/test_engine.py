from hobscan.engine import Params, detect
from hobscan.samples import CADJPY_4D, EURUSD_3W, EURUSD_3W_REJECTED, HYPE_5D, LINK_1W, SOL_7D


def zone(found, bot):
    return next((f for f in found if abs(f.zone.bot - bot) < 1e-9), None)


def test_cadjpy_3x_with_mixed_colour_fvgs():
    f = zone(detect(CADJPY_4D), 113.64)
    assert f and f.hidden == 3 and f.zone.bear and not f.touched


def test_eurusd_3w_wick_back_in_and_opposite_first_fvg_rejected():
    assert zone(detect(EURUSD_3W_REJECTED), 1.0574) is None


def test_eurusd_3w_valid_1x():
    f = zone(detect(EURUSD_3W), 1.1417)
    assert f and f.hidden == 1 and f.zone.bear


def test_eurusd_3w_forming_while_fvg_candle_open():
    f = zone(detect(EURUSD_3W[:6], last_is_live=True), 1.1417)
    assert f and f.hidden == 1 and f.forming


def test_link_touched_within_buffer():
    f = zone(detect(LINK_1W), 8.381)
    assert f and f.hidden == 1 and f.touched and not f.zone.bear


def test_link_wick_past_buffer_mitigates():
    deeper = LINK_1W[:3] + [LINK_1W[3].__class__(LINK_1W[3].t, 8.378, 8.43, 8.0, 8.18)] + LINK_1W[4:]
    assert zone(detect(deeper), 8.381) is None


def test_link_no_buffer_mitigates():
    assert zone(detect(LINK_1W, Params(touch_buffer_pct=0)), 8.381) is None


def test_sol_small_body_passes_10pct_but_not_20pct():
    assert zone(detect(SOL_7D), 89.2).hidden == 1
    assert zone(detect(SOL_7D, Params(min_body_pct=20)), 89.2) is None


def test_hype_far_from_price_still_found():
    f = zone(detect(HYPE_5D), 24.0)
    assert f and f.hidden == 1


def test_later_wick_into_body_mitigates():
    from hobscan.engine import Bar
    tap = Bar(CADJPY_4D[-1].t + 1, 110.7, 113.8, 110.6, 111.0)
    assert zone(detect(CADJPY_4D + [tap]), 113.64) is None


def test_live_candle_tapping_is_testing_not_removed():
    from hobscan.engine import Bar
    tap = Bar(CADJPY_4D[-1].t + 1, 110.7, 113.8, 110.6, 111.0)
    f = zone(detect(CADJPY_4D + [tap], last_is_live=True), 113.64)
    assert f and f.testing and f.hidden == 3
