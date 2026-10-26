# DaytradeBreakout4h - Ausbruch ueber das 4h-Hoch mit doppeltem Volumen im starken Trend; Gewinner laufen lassen
import sys
from pathlib import Path

from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeBreakout4h(DaytradeMomentum):
    stop_mult = 2.0
    target_mult = 6.0
    hold_minutes = 600

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["hh48"] = dataframe["high"].rolling(48).max().shift(1)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"])
            & (dataframe["btc_ok"] == 1)
            & (dataframe["close"] > dataframe["hh48"])
            & (dataframe["volume"] > dataframe["vol_avg"] * 2)
            & (dataframe["adx"] > 25),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["close"] < dataframe["ema50"], "exit_long"] = 1
        return dataframe
