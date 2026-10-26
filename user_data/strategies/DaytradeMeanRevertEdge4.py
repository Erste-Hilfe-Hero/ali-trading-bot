# DaytradeMeanRevertEdge4 - Wide35 (Stop 3,5 ATR) mit Mindestabstand 1 % und strengem Einstieg; aus der Gewinner/Verlierer-Auswertung 2026-10-26
import sys
from pathlib import Path

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMeanRevertPro24Wide35 import DaytradeMeanRevertPro24Wide35  # noqa: E402


class DaytradeMeanRevertEdge4(DaytradeMeanRevertPro24Wide35):
    min_gap = 0.01
    bb_dev = DecimalParameter(1.8, 2.8, default=2.8, decimals=1, space="buy")
    rsi_max_entry = IntParameter(20, 38, default=22, space="buy")
