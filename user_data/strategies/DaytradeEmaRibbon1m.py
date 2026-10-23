# DaytradeEmaRibbon1m - Regeln von DaytradeEmaRibbon auf 1m-Kerzen: schnelle Trades
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from DaytradeEmaRibbon import DaytradeEmaRibbon  # noqa: E402


class DaytradeEmaRibbon1m(DaytradeEmaRibbon):
    timeframe = "1m"
