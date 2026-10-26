# DaytradeFearBuy - gegen die Masse: bei grosser Angst (Fear & Greed < 25) ueberverkaufte Coins kaufen, bis 24h halten
import sys
from pathlib import Path

from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeFearBuy(DaytradeMomentum):
    timeframe = "15m"
    stop_mult = 3.0
    target_mult = 8.0
    hold_minutes = 1440

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        if not self.guard._fng:
            self.guard.load_fng()
        dataframe["fng"] = dataframe["date"].map(lambda d: self.guard.fng(d.to_pydatetime())).astype(float)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["fng"] < 25) & (dataframe["rsi_1h"] < 32)
            & (dataframe["rsi"] > 30) & (dataframe["rsi"].shift(1) <= 30),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["rsi_1h"] > 60, "exit_long"] = 1
        return dataframe
