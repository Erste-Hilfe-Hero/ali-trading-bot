# DaytradeMeanRevertEdge3 - Wide35 (Stop 3,5 ATR) mit Mindestabstand 1 %; aus der Gewinner/Verlierer-Auswertung 2026-10-26
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from DaytradeMeanRevertPro24Wide35 import DaytradeMeanRevertPro24Wide35  # noqa: E402


class DaytradeMeanRevertEdge3(DaytradeMeanRevertPro24Wide35):
    min_gap = 0.01
