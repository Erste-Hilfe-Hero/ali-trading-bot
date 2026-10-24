# DaytradeBtcLeader - 5m: BTC macht einen kraeftigen Schritt nach oben, der Coin ist noch nicht mitgezogen
import sys
from pathlib import Path

import talib.abstract as ta
from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeBtcLeader(DaytradeMomentum):
    # Schnelle Gewinnmitnahme: kleine Ziele, die mit der Zeit sinken
    minimal_roi = {"0": 0.012, "20": 0.007, "45": 0.004, "90": 0.0}

    def informative_pairs(self):
        return [("BTC/USDT", "15m"), ("BTC/USDT", "5m")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["bl_btc_ret"] = 0.0
        if self.dp:
            btc = self.dp.get_pair_dataframe("BTC/USDT", "5m")
            if not btc.empty:
                btc = btc[["date", "close", "open"]].rename(columns={"close": "bl_c", "open": "bl_o"})
                dataframe = dataframe.merge(btc, on="date", how="left")
                dataframe["bl_btc_ret"] = (dataframe["bl_c"] / dataframe["bl_o"] - 1).fillna(0)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        own = dataframe["close"] / dataframe["open"] - 1
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & (dataframe["bl_btc_ret"] > 0.003) & (own < dataframe["bl_btc_ret"] / 2)
            & (metadata["pair"] != "BTC/USDT"),
            "enter_long",
        ] = 1
        return dataframe
