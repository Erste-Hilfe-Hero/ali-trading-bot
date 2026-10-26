# DaytradeRsiDivergence - Kurs macht ein tieferes Tief, der RSI aber ein hoeheres (Verkaeufer werden schwaecher)
import sys
from pathlib import Path

from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeRsiDivergence(DaytradeMomentum):
    stop_mult = 1.5
    target_mult = 4.0
    hold_minutes = 300

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        prev_low = dataframe["low"].shift(3).rolling(12).min()
        prev_rsi = dataframe["rsi"].shift(3).rolling(12).min()
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"])
            & (dataframe["low"] < prev_low)
            & (dataframe["rsi"] > prev_rsi + 5)
            & (prev_rsi < 30)
            & (dataframe["close"] > dataframe["open"]),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["rsi"] > 70, "exit_long"] = 1
        return dataframe
