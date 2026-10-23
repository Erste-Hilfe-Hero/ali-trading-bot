# DaytradeWilliamsR - 5m: Williams %R steigt aus dem ueberverkauften Bereich (-80), im Aufwaertstrend
import sys
from pathlib import Path

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeWilliamsR(DaytradeMomentum):

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["willr"] = ta.WILLR(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        up = (dataframe["willr"] > -80) & (dataframe["willr"].shift(1) <= -80)
        dataframe.loc[(dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & up & (dataframe["close"] > dataframe["ema50"]), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["willr"] > -10, "exit_long"] = 1
        return dataframe
