# DaytradeTrendPullback - starker 1h-Trend, Kauf wenn ein kurzer 5m-Ruecksetzer endet; grosses Ziel, lange Haltezeit
import sys
from pathlib import Path

from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeTrendPullback(DaytradeMomentum):
    stop_mult = 2.0
    target_mult = 5.0
    hold_minutes = 480

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        back_up = (dataframe["rsi"] > 40) & (dataframe["rsi"].shift(1) <= 40)
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"])
            & (dataframe["close_1h"] > dataframe["ema50_1h"])
            & dataframe["rsi_1h"].between(55, 70)
            & (dataframe["btc_ok"] == 1)
            & back_up,
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["close_1h"] < dataframe["ema50_1h"], "exit_long"] = 1
        return dataframe
