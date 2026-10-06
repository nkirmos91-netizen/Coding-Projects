from hobscan.cli import zones_for
from hobscan.config import Config
from hobscan.providers.base import Instrument
from hobscan.samples import HYPE_5D, SOL_7D


def inst(market):
    return Instrument(symbol="X", market=market, name="X", tv_symbol="X", exchange="Bybit")


def test_scanner_leaves_out_zones_too_far_from_price():
    cfg = Config(timeframes=["1D"])
    # HYPE zone is ~74% below price: past the 50% crypto limit.
    assert zones_for(inst("Crypto"), HYPE_5D, False, cfg, 0) == []
    # SOL zone is ~25% below price: kept for crypto (50%), kept for stocks (30%).
    assert len(zones_for(inst("Crypto"), SOL_7D, False, cfg, 0)) == 1
    cfg_tight = Config(timeframes=["1D"], crypto={"max_distance_pct": 20})
    assert zones_for(inst("Crypto"), SOL_7D, False, cfg_tight, 0) == []
