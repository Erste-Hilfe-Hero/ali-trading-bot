# DaytradeCapitulation - Ausverkaufskerze: sehr hohes Volumen, langer Docht nach unten, Schluss in der oberen Haelfte
import sys
from pathlib import Path

from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeCapitulation(DaytradeMomentum):
    stop_mult = 1.5
    target_mult = 4.0
    hold_minutes = 240

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        rng = (dataframe["high"] - dataframe["low"]).clip(lower=1e-12)
        wick = dataframe[["open", "close"]].min(axis=1) - dataframe["low"]
        dataframe.loc[
            (dataframe["volume"] > dataframe["vol_avg"] * 4)
            & (wick / rng > 0.6)
            & ((dataframe["close"] - dataframe["low"]) / rng > 0.5)
            & (dataframe["rsi"].shift(1) < 30)
            & (dataframe["close_1h"] > dataframe["ema200_1h"]),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["close"] < dataframe["low"].shift(1).rolling(3).min(), "exit_long"] = 1
        return dataframe
