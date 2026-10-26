# DaytradeBtcDip - BTC faellt in einer Stunde stark, starke Coins werden mit runtergezogen -> Erholung kaufen
import sys
from pathlib import Path

from pandas import DataFrame

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeBtcDip(DaytradeMomentum):
    stop_mult = 2.0
    target_mult = 4.0
    hold_minutes = 240

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"])
            & (dataframe["btc_chg1h"] < -0.015)
            & (dataframe["rsi"] < 30)
            # erste gruene Kerze nach dem Abverkauf
            & (dataframe["close"] > dataframe["open"]),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["rsi"] > 65, "exit_long"] = 1
        return dataframe
