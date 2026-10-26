# DaytradeNr7 - engste Kerze der letzten 7 (Ruhe vor dem Ausbruch), Kauf beim Bruch ihres Hochs im Trend
import sys
from pathlib import Path

from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeNr7(DaytradeMomentum):
    stop_mult = 1.5
    target_mult = 4.5
    hold_minutes = 300

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        rng = dataframe["high"] - dataframe["low"]
        dataframe["nr7"] = (rng <= rng.rolling(7).min()).astype(int)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"])
            & (dataframe["close_1h"] > dataframe["ema50_1h"])
            & (dataframe["btc_ok"] == 1)
            & (dataframe["nr7"].shift(1) == 1)
            & (dataframe["close"] > dataframe["high"].shift(1))
            & (dataframe["close"] > dataframe["ema50"]),
            "enter_long",
        ] = 1
        return dataframe
