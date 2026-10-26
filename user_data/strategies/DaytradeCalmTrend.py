# DaytradeCalmTrend - ruhiger, sauberer Trend (EMA9 > 21 > 50, ADX steigt, wenig Schwankung); lange laufen lassen
import sys
from pathlib import Path

from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeCalmTrend(DaytradeMomentum):
    timeframe = "15m"
    stop_mult = 2.5
    target_mult = 50.0
    hold_minutes = 1440

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        stack = (dataframe["ema9"] > dataframe["ema21"]) & (dataframe["ema21"] > dataframe["ema50"])
        new_stack = stack & ~stack.shift(1, fill_value=False)
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"]) & new_stack & (dataframe["adx"] > 20) & (dataframe["adx"] > dataframe["adx"].shift(4))
            & (dataframe["atr"] / dataframe["close"] < 0.012) & (dataframe["btc_ok"] == 1),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["ema21"] < dataframe["ema50"], "exit_long"] = 1
        return dataframe
