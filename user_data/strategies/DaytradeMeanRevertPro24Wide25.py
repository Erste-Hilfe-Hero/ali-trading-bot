# DaytradeMeanRevertPro24Wide25 – wie MeanRevertPro24, aber weiterer Stop (2,5 ATR); Auswertung 2026-10-26: Stop-Loss kostet fast alles
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from DaytradeMeanRevertPro24 import DaytradeMeanRevertPro24  # noqa: E402


class DaytradeMeanRevertPro24Wide25(DaytradeMeanRevertPro24):
    stop_mult = 2.5
    target_mult = 4.5
