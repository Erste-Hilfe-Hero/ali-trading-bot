# DaytradeParabolicSar - 5m: Parabolic SAR springt unter den Kurs, im Aufwaertstrend
import sys
from pathlib import Path

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeParabolicSar(DaytradeMomentum):

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["sar"] = ta.SAR(dataframe, acceleration=0.02, maximum=0.2)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        flip = (dataframe["sar"] < dataframe["close"]) & (dataframe["sar"].shift(1) > dataframe["close"].shift(1))
        dataframe.loc[(dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & flip & (dataframe["adx"] > 20), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["sar"] > dataframe["close"], "exit_long"] = 1
        return dataframe
