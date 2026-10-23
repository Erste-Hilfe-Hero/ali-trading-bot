# DaytradeSqueeze1m - Regeln von DaytradeSqueeze auf 1m-Kerzen: schnelle Trades
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from DaytradeSqueeze import DaytradeSqueeze  # noqa: E402


class DaytradeSqueeze1m(DaytradeSqueeze):
    timeframe = "1m"
