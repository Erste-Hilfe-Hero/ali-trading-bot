# DaytradeKeltner - Schluss ueber dem oberen Keltner-Kanal (EMA20 + 2 ATR) bei starkem Trend (ADX)
import sys
from pathlib import Path

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeKeltner(DaytradeMomentum):
    kc_adx = IntParameter(20, 35, default=25, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["kc_upper"] = ta.EMA(dataframe, timeperiod=20) + 2 * dataframe["atr"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        up = (dataframe["close"] > dataframe["kc_upper"]) & (dataframe["close"].shift(1) <= dataframe["kc_upper"].shift(1))
        dataframe.loc[(dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & up & (dataframe["adx"] > self.kc_adx.value), "enter_long"] = 1
        return dataframe
