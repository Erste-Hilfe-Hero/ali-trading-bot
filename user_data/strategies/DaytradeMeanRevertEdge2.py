# DaytradeMeanRevertEdge2 - Wide35 (Stop 3,5 ATR) mit Haltezeit 90 min; aus der Gewinner/Verlierer-Auswertung 2026-10-26
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from DaytradeMeanRevertPro24Wide35 import DaytradeMeanRevertPro24Wide35  # noqa: E402


class DaytradeMeanRevertEdge2(DaytradeMeanRevertPro24Wide35):
    hold_minutes = 90
