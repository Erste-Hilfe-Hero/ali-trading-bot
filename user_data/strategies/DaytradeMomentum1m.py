# DaytradeMomentum1m - Regeln von DaytradeMomentum auf 1m-Kerzen: schnelle Trades
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeMomentum1m(DaytradeMomentum):
    timeframe = "1m"
