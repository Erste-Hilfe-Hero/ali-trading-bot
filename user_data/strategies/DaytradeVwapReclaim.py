# DaytradeVwapReclaim - 5m: Kurs springt mit Volumen von unten ueber den Tages-VWAP
import sys
from pathlib import Path

import talib.abstract as ta
from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeVwapReclaim(DaytradeMomentum):
    # Schnelle Gewinnmitnahme: kleine Ziele, die mit der Zeit sinken
    minimal_roi = {"0": 0.012, "20": 0.007, "45": 0.004, "90": 0.0}

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross = (dataframe["close"] > dataframe["vwap"]) & (dataframe["close"].shift(1) <= dataframe["vwap"].shift(1))
        dataframe.loc[(dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & cross & (dataframe["volume"] > dataframe["vol_avg"] * 1.5), "enter_long"] = 1
        return dataframe
