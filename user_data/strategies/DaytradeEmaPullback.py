# DaytradeEmaPullback - 5m: im starken Trend (EMA9 > 21 > 50, ADX > 25) Kauf beim Ruecksetzer an die EMA21
import sys
from pathlib import Path

import talib.abstract as ta
from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeEmaPullback(DaytradeMomentum):
    # Schnelle Gewinnmitnahme: kleine Ziele, die mit der Zeit sinken
    minimal_roi = {"0": 0.012, "20": 0.007, "45": 0.004, "90": 0.0}

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        stack = (dataframe["ema9"] > dataframe["ema21"]) & (dataframe["ema21"] > dataframe["ema50"])
        touch = (dataframe["low"] <= dataframe["ema21"] * 1.001) & (dataframe["close"] > dataframe["ema21"]) & (dataframe["close"] > dataframe["open"])
        dataframe.loc[(dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & stack & touch & (dataframe["adx"] > 25), "enter_long"] = 1
        return dataframe
