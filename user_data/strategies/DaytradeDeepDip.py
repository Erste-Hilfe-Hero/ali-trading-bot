# DaytradeDeepDip - Coin liegt ueber 8 % unter seinem 3-Tage-Hoch, 1h stark ueberverkauft, langfristig noch im Trend
import sys
from pathlib import Path

from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeDeepDip(DaytradeMomentum):
    timeframe = "15m"
    stop_mult = 3.0
    target_mult = 6.0
    hold_minutes = 1440

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["hh72h"] = dataframe["high"].rolling(288).max()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] < dataframe["hh72h"] * 0.92)
            & (dataframe["close_1h"] > dataframe["ema200_1h"] * 0.97)
            & (dataframe["rsi_1h"] < 30)
            & (dataframe["close"] > dataframe["open"]) & (dataframe["rsi"] > dataframe["rsi"].shift(1)),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["rsi_1h"] > 55, "exit_long"] = 1
        return dataframe
