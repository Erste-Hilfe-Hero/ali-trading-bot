# DaytradeDonchian - Turtle-Ausbruch auf 5m: Kauf ueber dem 55-Kerzen-Hoch, Verkauf unter dem 20-Kerzen-Tief
import sys
from pathlib import Path

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeDonchian(DaytradeMomentum):

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        high55 = dataframe["high"].rolling(55).max().shift(1)
        dataframe.loc[(dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & (dataframe["close"] > high55) & (dataframe["volume"] > dataframe["vol_avg"]), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["close"] < dataframe["low"].rolling(20).min().shift(1), "exit_long"] = 1
        return dataframe
