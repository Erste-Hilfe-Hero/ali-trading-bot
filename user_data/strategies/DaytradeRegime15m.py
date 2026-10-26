# DaytradeRegime15m - Momentum auf 15m, aber nur bei gutem Marktklima: BTC steigt, Fear & Greed >= 40, aktive Handelszeit
import sys
from pathlib import Path

from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeRegime15m(DaytradeMomentum):
    timeframe = "15m"
    stop_mult = 2.0
    target_mult = 5.0
    hold_minutes = 720
    guard_fng_min = 40
    guard_btc_trend = True
    guard_btc_crash = 0.01
    guard_hours = (7, 20)
