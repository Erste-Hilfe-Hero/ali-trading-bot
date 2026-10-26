# DaytradeSwing1h - 15m: Kurs kreuzt auf 1h ueber die EMA50 im Aufwaertstrend; wenige Trades, bis 24h halten
import sys
from pathlib import Path

from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeSwing1h(DaytradeMomentum):
    timeframe = "15m"
    stop_mult = 3.0
    target_mult = 9.0
    hold_minutes = 1440

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross = (dataframe["close_1h"] > dataframe["ema50_1h"]) & (dataframe["close_1h"].shift(4) <= dataframe["ema50_1h"].shift(4))
        dataframe.loc[(dataframe["ema50_1h"] > dataframe["ema200_1h"]) & cross & (dataframe["rsi_1h"] > 50) & (dataframe["btc_ok"] == 1), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["close_1h"] < dataframe["ema50_1h"] * 0.99, "exit_long"] = 1
        return dataframe
