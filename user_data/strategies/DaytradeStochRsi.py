# DaytradeStochRsi - Stoch-RSI kreuzt im ueberverkauften Bereich nach oben, im Aufwaertstrend
import sys
from pathlib import Path

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeStochRsi(DaytradeMomentum):
    stoch_low = IntParameter(10, 30, default=20, space="buy")

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        k, d = dataframe["m_stoch_k"], dataframe["m_stoch_d"]
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1)
            & (k > d) & (k.shift(1) <= d.shift(1)) & (k.shift(1) < self.stoch_low.value)
            & (dataframe["close"] > dataframe["ema50"]),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["m_stoch_k"] > 85) & (dataframe["m_stoch_k"] < dataframe["m_stoch_d"]), "exit_long"] = 1
        return dataframe
