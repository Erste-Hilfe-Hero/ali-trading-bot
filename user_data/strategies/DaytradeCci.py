# DaytradeCci - 5m: CCI kommt von unter -100 zurueck (Ruecksetzer endet), im Aufwaertstrend
import sys
from pathlib import Path

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeCci(DaytradeMomentum):
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["cci"] = ta.CCI(dataframe, timeperiod=20)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        up = (dataframe["cci"] > -100) & (dataframe["cci"].shift(1) <= -100)
        dataframe.loc[(dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & up & (dataframe["close"] > dataframe["ema50"]), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["cci"] > 150, "exit_long"] = 1
        return dataframe
