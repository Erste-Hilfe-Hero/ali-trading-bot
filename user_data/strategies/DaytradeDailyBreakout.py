# DaytradeDailyBreakout - 15m: Ausbruch ueber das Hoch des Vortags (UTC) mit Volumen, BTC stabil; bis 24h halten
import sys
from pathlib import Path

from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeDailyBreakout(DaytradeMomentum):
    timeframe = "15m"
    stop_mult = 2.5
    target_mult = 8.0
    hold_minutes = 1440

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        day = dataframe["date"].dt.floor("D")
        daily_high = dataframe.groupby(day)["high"].max()
        dataframe["prev_day_high"] = day.map(daily_high.shift(1))
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        first_break = (dataframe["close"] > dataframe["prev_day_high"]) & (dataframe["close"].shift(1) <= dataframe["prev_day_high"])
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"]) & first_break & (dataframe["btc_ok"] == 1)
            & (dataframe["volume"] > dataframe["vol_avg"] * 1.5),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["close"] < dataframe["prev_day_high"] * 0.985, "exit_long"] = 1
        return dataframe
