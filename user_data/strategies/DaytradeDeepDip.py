# DaytradeDeepDip - Coin liegt ueber 8 % unter seinem 3-Tage-Hoch, 1h stark ueberverkauft, langfristig noch im Trend
import sys
from pathlib import Path

from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeDeepDip(DaytradeMomentum):
    timeframe = "15m"
    stop_mult = 3.0
    target_mult = 6.0
    hold_minutes = 1440
    dip_pct = DecimalParameter(0.04, 0.15, default=0.08, decimals=2, space="buy")
    rsi1h_max = IntParameter(20, 40, default=30, space="buy")
    exit_rsi1h = IntParameter(45, 70, default=55, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["hh72h"] = dataframe["high"].rolling(288).max()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] < dataframe["hh72h"] * (1 - self.dip_pct.value))
            & (dataframe["close_1h"] > dataframe["ema200_1h"] * 0.97)
            & (dataframe["rsi_1h"] < self.rsi1h_max.value)
            & (dataframe["close"] > dataframe["open"]) & (dataframe["rsi"] > dataframe["rsi"].shift(1)),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["rsi_1h"] > self.exit_rsi1h.value, "exit_long"] = 1
        return dataframe
