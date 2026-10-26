# DaytradeTripleScreen - nach Elder: 1h-Trend hoch, 15m kurz ueberverkauft, Kauf erst beim Bruch des letzten Hochs
import sys
from pathlib import Path

from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeTripleScreen(DaytradeMomentum):
    timeframe = "15m"
    stop_mult = 2.0
    target_mult = 6.0
    hold_minutes = 720

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        was_oversold = dataframe["m_stoch_k"].shift(1).rolling(4).min() < 20
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["close_1h"] > dataframe["ema50_1h"]) & (dataframe["rsi_1h"] > 50)
            & was_oversold & (dataframe["close"] > dataframe["high"].shift(1))
            & (dataframe["btc_ok"] == 1),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["close_1h"] < dataframe["ema50_1h"], "exit_long"] = 1
        return dataframe
