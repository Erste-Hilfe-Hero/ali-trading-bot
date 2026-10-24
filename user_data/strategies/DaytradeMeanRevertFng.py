# DaytradeMeanRevertFng – MeanRevert mit Markt-Waechter: kein Kauf bei extremer Angst im Markt (Fear & Greed unter 25)
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from DaytradeMeanRevert import DaytradeMeanRevert  # noqa: E402


class DaytradeMeanRevertFng(DaytradeMeanRevert):
    guard_fng_min = 25
