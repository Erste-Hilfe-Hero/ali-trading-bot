# DaytradeRelStrength - 5m: Coin steigt in den letzten 4h deutlich staerker als BTC, Einstieg beim EMA-Kreuz
import sys
from pathlib import Path

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeRelStrength(DaytradeMomentum):
    rs_edge = DecimalParameter(0.005, 0.03, default=0.01, decimals=3, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["rs_btc_ret"] = 0.0
        if self.dp:
            btc = self.dp.get_pair_dataframe("BTC/USDT", self.timeframe)
            if not btc.empty:
                btc = btc[["date", "close"]].rename(columns={"close": "rs_btc_close"})
                dataframe = dataframe.merge(btc, on="date", how="left")
                dataframe["rs_btc_ret"] = dataframe["rs_btc_close"].ffill().pct_change(48)
        dataframe["rs_ret"] = dataframe["close"].pct_change(48)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross = (dataframe["ema9"] > dataframe["ema21"]) & (dataframe["ema9"].shift(1) <= dataframe["ema21"].shift(1))
        stronger = dataframe["rs_ret"] > dataframe["rs_btc_ret"] + self.rs_edge.value
        dataframe.loc[(dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1) & cross & stronger & (dataframe["volume"] > 0), "enter_long"] = 1
        return dataframe
