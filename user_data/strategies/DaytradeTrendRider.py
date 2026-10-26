# DaytradeTrendRider - Einstieg wie Momentum, aber ohne festes Ziel: Gewinnsicherung ab +1,5R, bis zu 12h halten
import sys
from pathlib import Path

from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeTrendRider(DaytradeMomentum):
    stop_mult = 2.0
    target_mult = 50.0
    hold_minutes = 720

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["close_1h"] < dataframe["ema50_1h"], "exit_long"] = 1
        return dataframe
