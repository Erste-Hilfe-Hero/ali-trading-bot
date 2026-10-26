# DaytradeLeader15m - Coin ist in 24h deutlich staerker als BTC; Kauf beim Ruecksetzer an die EMA21 (15m)
import sys
from pathlib import Path

from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeLeader15m(DaytradeMomentum):
    timeframe = "15m"
    stop_mult = 2.0
    target_mult = 6.0
    hold_minutes = 720

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["chg24h"] = dataframe["close"] / dataframe["close"].shift(96) - 1
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        touch = (dataframe["low"] <= dataframe["ema21"]) & (dataframe["close"] > dataframe["ema21"])
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["chg24h"] > 0.05) & (dataframe["btc_ok"] == 1)
            & touch & (dataframe["rsi"].between(45, 65)),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["close"] < dataframe["ema50"], "exit_long"] = 1
        return dataframe
