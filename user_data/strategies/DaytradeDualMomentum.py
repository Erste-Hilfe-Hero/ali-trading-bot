# DaytradeDualMomentum - 5m: kurzer und langer Schwung positiv, Einstieg beim Ruecksetzer an die EMA21
import sys
from pathlib import Path

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeDualMomentum(DaytradeMomentum):

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        roc_short = dataframe["close"].pct_change(12)
        roc_long = dataframe["close"].pct_change(48)
        touch = (dataframe["low"] <= dataframe["ema21"]) & (dataframe["close"] > dataframe["ema21"])
        dataframe.loc[(dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & (roc_short > 0) & (roc_long > 0) & touch, "enter_long"] = 1
        return dataframe
