# DaytradeMacdSlow - MACD mit 1h-Laengen auf 5m (144/312/108): seltene, grosse Trendwechsel statt Rauschen
import sys
from pathlib import Path

import talib.abstract as ta
from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeMacdSlow(DaytradeMomentum):
    stop_mult = 2.5
    target_mult = 7.0
    hold_minutes = 720

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        m = ta.MACD(dataframe, fastperiod=144, slowperiod=312, signalperiod=108)
        dataframe["ms_hist"] = m["macdhist"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["ms_hist"] > 0)
            & (dataframe["ms_hist"].shift(1) <= 0)
            & (dataframe["btc_ok"] == 1)
            & (dataframe["close"] > dataframe["ema50"]),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["ms_hist"] < 0) & (dataframe["ms_hist"].shift(1) >= 0), "exit_long"] = 1
        return dataframe
