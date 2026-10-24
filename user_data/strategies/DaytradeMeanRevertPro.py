# DaytradeMeanRevertPro – MeanRevert mit Markt-Waechter: alle Profi-Filter: BTC-Trend und Crash-Bremse, aktive Zeiten, Stimmung
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from DaytradeMeanRevert import DaytradeMeanRevert  # noqa: E402


class DaytradeMeanRevertPro(DaytradeMeanRevert):
    guard_btc_trend = True
    guard_btc_crash = 0.015
    guard_hours = (7, 20)
    guard_fng_min = 25
