# DaytradeMacdCross - MACD kreuzt seine Signallinie unter der Nulllinie nach oben, im 1h-Aufwaertstrend
import sys
from pathlib import Path

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeMacdCross(DaytradeMomentum):
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        macd = ta.MACD(dataframe)
        dataframe["mc_macd"] = macd["macd"]
        dataframe["mc_signal"] = macd["macdsignal"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross = (dataframe["mc_macd"] > dataframe["mc_signal"]) & (dataframe["mc_macd"].shift(1) <= dataframe["mc_signal"].shift(1))
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & cross & (dataframe["mc_macd"] < 0) & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross_down = (dataframe["mc_macd"] < dataframe["mc_signal"]) & (dataframe["mc_macd"].shift(1) >= dataframe["mc_signal"].shift(1))
        dataframe.loc[cross_down, "exit_long"] = 1
        return dataframe
