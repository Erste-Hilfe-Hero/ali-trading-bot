# DaytradeVwapBounce - Kurs testet den Tages-VWAP von oben und dreht mit gruener Kerze wieder hoch
import sys
from pathlib import Path

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeVwapBounce(DaytradeMomentum):
    touch = DecimalParameter(0.000, 0.003, default=0.001, decimals=3, space="buy")

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1)
            & (dataframe["low"] <= dataframe["vwap"] * (1 + self.touch.value))
            & (dataframe["close"] > dataframe["vwap"])
            & (dataframe["close"] > dataframe["open"])
            & (dataframe["rsi"].between(40, 62))
            & (dataframe["volume"] > dataframe["vol_avg"]),
            "enter_long",
        ] = 1
        return dataframe
