# DaytradeEmaRibbon - EMA 8/13/21/34/55 stehen frisch geordnet uebereinander (starker Trendbeginn)
import sys
from pathlib import Path

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeEmaRibbon(DaytradeMomentum):
    ribbon_adx = IntParameter(18, 35, default=25, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        for p in (8, 13, 34, 55):
            dataframe[f"r_ema{p}"] = ta.EMA(dataframe, timeperiod=p)
        dataframe["r_aligned"] = ((dataframe["r_ema8"] > dataframe["r_ema13"]) & (dataframe["r_ema13"] > dataframe["ema21"])
                                  & (dataframe["ema21"] > dataframe["r_ema34"]) & (dataframe["r_ema34"] > dataframe["r_ema55"])).astype(int)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1)
            & (dataframe["r_aligned"] == 1) & (dataframe["r_aligned"].shift(1) == 0)
            & (dataframe["adx"] > self.ribbon_adx.value),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["r_ema8"] < dataframe["ema21"], "exit_long"] = 1
        return dataframe
