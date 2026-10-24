# DaytradeBbScalp1m - 1m: Kurs kommt von unter dem unteren Bollinger-Band zurueck, Verkauf an der Mitte
import sys
from pathlib import Path

import talib.abstract as ta
from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeBbScalp1m(DaytradeMomentum):
    timeframe = "1m"

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["bs_mid"] = dataframe["close"].rolling(20).mean()
        dataframe["bs_lower"] = dataframe["bs_mid"] - 2 * dataframe["close"].rolling(20).std()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        back_in = (dataframe["close"] > dataframe["bs_lower"]) & (dataframe["close"].shift(1) <= dataframe["bs_lower"].shift(1))
        dataframe.loc[(dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & back_in & ((dataframe["bs_mid"] - dataframe["close"]) / dataframe["close"] > 0.004), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["close"] > dataframe["bs_mid"], "exit_long"] = 1
        return dataframe
