# DaytradeSqueeze - Bollinger-Baender ziehen sich zusammen, dann Ausbruch nach oben mit Volumen
import sys
from pathlib import Path

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeSqueeze(DaytradeMomentum):
    squeeze_window = IntParameter(50, 200, default=100, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        mid = dataframe["close"].rolling(20).mean()
        std = dataframe["close"].rolling(20).std()
        dataframe["sq_upper"] = mid + 2 * std
        dataframe["sq_width"] = 4 * std / mid
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        w = self.squeeze_window.value
        was_tight = dataframe["sq_width"].shift(1) <= dataframe["sq_width"].rolling(w).quantile(0.2).shift(1)
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1)
            & was_tight
            & (dataframe["close"] > dataframe["sq_upper"])
            & (dataframe["volume"] > dataframe["vol_avg"] * 1.5),
            "enter_long",
        ] = 1
        return dataframe
