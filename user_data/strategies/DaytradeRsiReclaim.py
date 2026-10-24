# DaytradeRsiReclaim - 5m: RSI steigt wieder ueber 30, Kurs ueber der EMA200 (Ausverkauf im Aufwaertstrend endet)
import sys
from pathlib import Path

import talib.abstract as ta
from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeRsiReclaim(DaytradeMomentum):
    # Schnelle Gewinnmitnahme: kleine Ziele, die mit der Zeit sinken
    minimal_roi = {"0": 0.012, "20": 0.007, "45": 0.004, "90": 0.0}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["rr_ema200"] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        up = (dataframe["rsi"] > 30) & (dataframe["rsi"].shift(1) <= 30)
        dataframe.loc[(dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & up & (dataframe["close"] > dataframe["rr_ema200"]), "enter_long"] = 1
        return dataframe
