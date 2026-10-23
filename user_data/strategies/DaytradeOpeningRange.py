# DaytradeOpeningRange - 5m: Ausbruch ueber das Hoch der ersten UTC-Stunde, nur bis 12:00 UTC
import sys
from pathlib import Path

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeOpeningRange(DaytradeMomentum):
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        day = dataframe["date"].dt.floor("D")
        first_hour = dataframe["date"].dt.hour < 1
        or_high = dataframe["high"].where(first_hour).groupby(day).cummax()
        dataframe["or_high"] = or_high.groupby(day).ffill()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        hour = dataframe["date"].dt.hour
        up = (dataframe["close"] > dataframe["or_high"]) & (dataframe["close"].shift(1) <= dataframe["or_high"].shift(1))
        dataframe.loc[(dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & up & (hour >= 1) & (hour < 12) & (dataframe["volume"] > dataframe["vol_avg"]), "enter_long"] = 1
        return dataframe
