# DaytradeMajors - Momentum-Einstieg nur auf den grossen Coins (weniger Rauschen, enger Spread), laengere Haltezeit
import sys
from pathlib import Path

from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


MAJORS = {"BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "DOGE/USDT", "ADA/USDT", "LINK/USDT"}


class DaytradeMajors(DaytradeMomentum):
    stop_mult = 2.0
    target_mult = 5.0
    hold_minutes = 480

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if metadata["pair"] not in MAJORS:
            dataframe["enter_long"] = 0
        return dataframe
