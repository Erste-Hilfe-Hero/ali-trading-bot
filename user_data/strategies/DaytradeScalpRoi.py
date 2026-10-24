# DaytradeScalpRoi - 5m: Momentum-Einstieg, aber schnelle kleine Gewinnmitnahme statt grossem ATR-Ziel
import sys
from pathlib import Path

import talib.abstract as ta
from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeScalpRoi(DaytradeMomentum):
    # Schnelle Gewinnmitnahme: kleine Ziele, die mit der Zeit sinken
    minimal_roi = {"0": 0.012, "20": 0.007, "45": 0.004, "90": 0.0}
    use_exit_signal = False
