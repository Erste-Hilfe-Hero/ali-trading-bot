# DaytradeZScore - Kurs liegt statistisch extrem weit unter seinem 4h-Schnitt (z < -2,5) im Aufwaertstrend
import sys
from pathlib import Path

from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeZScore(DaytradeMomentum):
    stop_mult = 2.0
    target_mult = 4.0
    hold_minutes = 360

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        mean = dataframe["close"].rolling(48).mean()
        dataframe["z_mean"] = mean
        dataframe["z"] = (dataframe["close"] - mean) / dataframe["close"].rolling(48).std()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"])
            & (dataframe["z"] < -2.5)
            & ((dataframe["z_mean"] - dataframe["close"]) / dataframe["close"] > 0.008),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["z"] > 0.5, "exit_long"] = 1
        return dataframe
