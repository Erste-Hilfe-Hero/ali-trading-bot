# DaytradeStoch1m - 1m: Stochastik K kreuzt D unter 20 nach oben, im Aufwaertstrend
import sys
from pathlib import Path

import talib.abstract as ta
from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeStoch1m(DaytradeMomentum):
    timeframe = "1m"
    # Schnelle Gewinnmitnahme: kleine Ziele, die mit der Zeit sinken
    minimal_roi = {"0": 0.012, "20": 0.007, "45": 0.004, "90": 0.0}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        st = ta.STOCH(dataframe, fastk_period=14, slowk_period=3, slowd_period=3)
        dataframe["st_k"] = st["slowk"]
        dataframe["st_d"] = st["slowd"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        k, d = dataframe["st_k"], dataframe["st_d"]
        dataframe.loc[(dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & (k > d) & (k.shift(1) <= d.shift(1)) & (k.shift(1) < 20) & (dataframe["close"] > dataframe["ema50"]), "enter_long"] = 1
        return dataframe
