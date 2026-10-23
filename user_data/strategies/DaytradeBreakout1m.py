# DaytradeBreakout1m - Regeln von DaytradeBreakout auf 1m-Kerzen: schnelle Trades
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from DaytradeBreakout import DaytradeBreakout  # noqa: E402


class DaytradeBreakout1m(DaytradeBreakout):
    timeframe = "1m"
