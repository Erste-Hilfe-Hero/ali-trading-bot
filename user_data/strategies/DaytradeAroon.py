# DaytradeAroon - 5m: Aroon-Up steigt ueber 70, Aroon-Down unter 30 (neuer Aufwaertstrend)
import sys
from pathlib import Path

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeAroon(DaytradeMomentum):

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        aroon = ta.AROON(dataframe, timeperiod=25)
        dataframe["aroon_up"] = aroon["aroonup"]
        dataframe["aroon_down"] = aroon["aroondown"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        up = (dataframe["aroon_up"] > 70) & (dataframe["aroon_up"].shift(1) <= 70)
        dataframe.loc[(dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & up & (dataframe["aroon_down"] < 30), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["aroon_down"] > dataframe["aroon_up"], "exit_long"] = 1
        return dataframe
