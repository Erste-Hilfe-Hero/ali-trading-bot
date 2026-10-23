# DaytradeHeikinAshi - Heikin-Ashi-Kerzen werden nach mehreren roten wieder gruen, im Aufwaertstrend
import sys
from pathlib import Path

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeHeikinAshi(DaytradeMomentum):
    red_before = IntParameter(2, 5, default=3, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        ha_close = ((dataframe["open"] + dataframe["high"] + dataframe["low"] + dataframe["close"]) / 4).to_numpy()
        o = dataframe["open"].to_numpy()
        ha_open = np.empty(len(o))
        ha_open[0] = o[0]
        for i in range(1, len(o)):
            ha_open[i] = (ha_open[i - 1] + ha_close[i - 1]) / 2
        dataframe["ha_green"] = (ha_close > ha_open).astype(int)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        n = self.red_before.value
        reds = (1 - dataframe["ha_green"]).shift(1).rolling(n).sum() == n
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & reds & (dataframe["ha_green"] == 1) & (dataframe["close"] > dataframe["ema50"]),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["ha_green"] == 0) & (dataframe["ha_green"].shift(1) == 0), "exit_long"] = 1
        return dataframe
