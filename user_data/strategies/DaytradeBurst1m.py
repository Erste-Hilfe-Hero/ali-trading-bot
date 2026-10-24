# DaytradeBurst1m - 1m: drei gruene Kerzen in Folge mit steigendem Volumen, Kurs ueber VWAP
import sys
from pathlib import Path

import talib.abstract as ta
from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeBurst1m(DaytradeMomentum):
    timeframe = "1m"
    # Schnelle Gewinnmitnahme: kleine Ziele, die mit der Zeit sinken
    minimal_roi = {"0": 0.012, "20": 0.007, "45": 0.004, "90": 0.0}

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        green = dataframe["close"] > dataframe["open"]
        three = green & green.shift(1) & green.shift(2)
        vol_up = (dataframe["volume"] > dataframe["volume"].shift(1)) & (dataframe["volume"].shift(1) > dataframe["volume"].shift(2))
        dataframe.loc[(dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & three & vol_up & (dataframe["close"] > dataframe["vwap"]) & (dataframe["rsi"] < 75), "enter_long"] = 1
        return dataframe
