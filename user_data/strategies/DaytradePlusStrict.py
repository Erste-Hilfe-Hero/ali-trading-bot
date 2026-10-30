# DaytradePlusStrict - DaytradePlus mit dem strengen Einstieg und Stop von Edge7 (ungesehen +0,77 $ am 26.10.)
import sys
from pathlib import Path

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradePlus import DaytradePlus  # noqa: E402


class DaytradePlusStrict(DaytradePlus):
    bb_dev = DecimalParameter(1.8, 2.8, default=2.8, decimals=1, space="buy")
    rsi_max_entry = IntParameter(20, 38, default=22, space="buy")
    stop_mult = 5.0
    target_mult = 7.0
