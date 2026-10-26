# DaytradeBtcDip - BTC faellt in einer Stunde stark, starke Coins werden mit runtergezogen -> Erholung kaufen
import sys
from pathlib import Path

from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeBtcDip(DaytradeMomentum):
    stop_mult = 2.0
    target_mult = 4.0
    hold_minutes = 240
    btc_drop = DecimalParameter(0.005, 0.03, default=0.015, decimals=3, space="buy")
    dip_rsi = IntParameter(20, 40, default=30, space="buy")
    exit_rsi = IntParameter(55, 80, default=65, space="buy")

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"])
            & (dataframe["btc_chg1h"] < -self.btc_drop.value)
            & (dataframe["rsi"] < self.dip_rsi.value)
            # erste gruene Kerze nach dem Abverkauf
            & (dataframe["close"] > dataframe["open"]),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["rsi"] > self.exit_rsi.value, "exit_long"] = 1
        return dataframe
