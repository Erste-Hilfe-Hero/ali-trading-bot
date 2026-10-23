# DaytradeIchimoku - 5m: Kurs ueber der Wolke, Tenkan kreuzt Kijun nach oben
import sys
from pathlib import Path

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeIchimoku(DaytradeMomentum):

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        mid = lambda n: (dataframe["high"].rolling(n).max() + dataframe["low"].rolling(n).min()) / 2  # noqa: E731
        dataframe["ich_tenkan"] = mid(9)
        dataframe["ich_kijun"] = mid(26)
        # Wolke wird 26 Kerzen nach vorn geschoben, nutzt also nur alte Daten
        dataframe["ich_span_a"] = ((dataframe["ich_tenkan"] + dataframe["ich_kijun"]) / 2).shift(26)
        dataframe["ich_span_b"] = mid(52).shift(26)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cloud_top = dataframe[["ich_span_a", "ich_span_b"]].max(axis=1)
        cross = (dataframe["ich_tenkan"] > dataframe["ich_kijun"]) & (dataframe["ich_tenkan"].shift(1) <= dataframe["ich_kijun"].shift(1))
        dataframe.loc[(dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & cross & (dataframe["close"] > cloud_top), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["close"] < dataframe["ich_kijun"], "exit_long"] = 1
        return dataframe
