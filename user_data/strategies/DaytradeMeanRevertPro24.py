# DaytradeMeanRevertPro24 – wie MeanRevertPro, aber rund um die Uhr (ohne Zeitfenster), Ali 2026-10-26
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from DaytradeMeanRevertPro import DaytradeMeanRevertPro  # noqa: E402


class DaytradeMeanRevertPro24(DaytradeMeanRevertPro):
    guard_hours = None
