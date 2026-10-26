# DaytradeAsiaRange - Spanne der Asien-Sitzung (0-7 UTC); Kauf beim Ausbruch nach oben zur Europa-Eroeffnung (7-12 UTC)
import sys
from pathlib import Path

from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeAsiaRange(DaytradeMomentum):
    timeframe = "15m"
    stop_mult = 2.0
    target_mult = 6.0
    hold_minutes = 600

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        day = dataframe["date"].dt.floor("D")
        hour = dataframe["date"].dt.hour
        asia = dataframe["high"].where(hour < 7)
        dataframe["asia_high"] = asia.groupby(day).transform("max")
        dataframe["hour"] = hour
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        first_break = (dataframe["close"] > dataframe["asia_high"]) & (dataframe["close"].shift(1) <= dataframe["asia_high"])
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"]) & first_break & dataframe["hour"].between(7, 11)
            & (dataframe["btc_ok"] == 1) & (dataframe["volume"] > dataframe["vol_avg"] * 1.3),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["close"] < dataframe["asia_high"] * 0.99, "exit_long"] = 1
        return dataframe
