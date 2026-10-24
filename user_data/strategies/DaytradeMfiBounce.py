# DaytradeMfiBounce - 5m: Geldfluss-Index (MFI) steigt wieder ueber 20, im Aufwaertstrend
import sys
from pathlib import Path

import talib.abstract as ta
from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeMfiBounce(DaytradeMomentum):
    # Schnelle Gewinnmitnahme: kleine Ziele, die mit der Zeit sinken
    minimal_roi = {"0": 0.012, "20": 0.007, "45": 0.004, "90": 0.0}

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        up = (dataframe["m_mfi"] > 20) & (dataframe["m_mfi"].shift(1) <= 20)
        dataframe.loc[(dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & up & (dataframe["close"] > dataframe["ema50"]), "enter_long"] = 1
        return dataframe
