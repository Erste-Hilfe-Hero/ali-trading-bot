# DaytradeSupertrend - Supertrend (ATR-Baender) dreht auf "aufwaerts"; Verkauf, wenn er wieder dreht
import sys
from pathlib import Path

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeSupertrend(DaytradeMomentum):
    st_mult = 3.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        hl2 = ((dataframe["high"] + dataframe["low"]) / 2).to_numpy()
        atr = ta.ATR(dataframe, timeperiod=10).to_numpy()
        close = dataframe["close"].to_numpy()
        upper = hl2 + self.st_mult * atr
        lower = hl2 - self.st_mult * atr
        up = np.ones(len(close), dtype=int)
        for i in range(1, len(close)):
            if np.isnan(atr[i - 1]):
                continue
            if close[i - 1] <= upper[i - 1]:
                upper[i] = min(upper[i], upper[i - 1])
            if close[i - 1] >= lower[i - 1]:
                lower[i] = max(lower[i], lower[i - 1])
            if up[i - 1] == 1:
                up[i] = 0 if close[i] < lower[i] else 1
            else:
                up[i] = 1 if close[i] > upper[i] else 0
        dataframe["st_up"] = up
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1)
            & (dataframe["st_up"] == 1) & (dataframe["st_up"].shift(1) == 0)
            & (dataframe["volume"] > dataframe["vol_avg"]),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["st_up"] == 0, "exit_long"] = 1
        return dataframe
