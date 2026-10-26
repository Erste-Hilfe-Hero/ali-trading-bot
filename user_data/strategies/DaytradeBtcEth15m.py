# DaytradeBtcEth15m - Momentum-Regeln auf 15m nur fuer BTC und ETH (tiefster Markt, kleinster Spread)
import sys
from pathlib import Path

from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeBtcEth15m(DaytradeMomentum):
    timeframe = "15m"
    stop_mult = 2.0
    target_mult = 5.0
    hold_minutes = 720

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if metadata["pair"] not in ("BTC/USDT", "ETH/USDT"):
            dataframe["enter_long"] = 0
        return dataframe
