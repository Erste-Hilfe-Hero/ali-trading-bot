# DaytradeMeanRevertHours – MeanRevert mit Markt-Waechter: nur zu aktiven Handelszeiten (7-20 UTC, Europa und USA wach)
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from DaytradeMeanRevert import DaytradeMeanRevert  # noqa: E402


class DaytradeMeanRevertHours(DaytradeMeanRevert):
    guard_hours = (7, 20)
