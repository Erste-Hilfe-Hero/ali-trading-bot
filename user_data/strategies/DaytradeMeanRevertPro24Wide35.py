# DaytradeMeanRevertPro24Wide35 – wie MeanRevertPro24, aber weiterer Stop (3,5 ATR); Auswertung 2026-10-26: Stop-Loss kostet fast alles
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from DaytradeMeanRevertPro24 import DaytradeMeanRevertPro24  # noqa: E402


class DaytradeMeanRevertPro24Wide35(DaytradeMeanRevertPro24):
    stop_mult = 3.5
    target_mult = 5.5
