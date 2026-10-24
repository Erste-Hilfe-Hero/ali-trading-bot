# DaytradeMeanRevertBtc – MeanRevert mit Markt-Waechter: nur kaufen, wenn BTC steigt und nicht gerade abstuerzt
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from DaytradeMeanRevert import DaytradeMeanRevert  # noqa: E402


class DaytradeMeanRevertBtc(DaytradeMeanRevert):
    guard_btc_trend = True
    guard_btc_crash = 0.015
