# DaytradeTrend15m – Momentum-Regeln auf 15m-Kerzen: weniger, groessere Trades, weniger Gebuehren
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeTrend15m(DaytradeMomentum):
    timeframe = "15m"
