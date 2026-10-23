# DaytradeRsi2 - Connors RSI(2): kurzer Ausverkauf im Aufwaertstrend, Verkauf bei Erholung
import sys
from pathlib import Path

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeRsi2(DaytradeMomentum):
    rsi2_entry = IntParameter(3, 15, default=8, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["rsi2"] = ta.RSI(dataframe, timeperiod=2)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1)
            & (dataframe["close"] > dataframe["ema200"])
            & (dataframe["rsi2"] < self.rsi2_entry.value)
            & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["rsi2"] > 70) | (dataframe["close"] > dataframe["ema21"]), "exit_long"] = 1
        return dataframe
