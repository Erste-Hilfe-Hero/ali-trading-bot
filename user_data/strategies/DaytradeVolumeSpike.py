# DaytradeVolumeSpike - 1m: ploetzliche Volumen-Explosion mit gruener Kerze ueber dem VWAP, im Aufwaertstrend
import sys
from pathlib import Path

from pandas import DataFrame

from freqtrade.strategy import DecimalParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeVolumeSpike(DaytradeMomentum):
    timeframe = "1m"
    spike = DecimalParameter(2.5, 6.0, default=4.0, decimals=1, space="buy")

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"]) & (dataframe["btc_ok"] == 1)
            & (dataframe["volume"] > dataframe["vol_avg"] * self.spike.value)
            & (dataframe["close"] > dataframe["open"])
            & (dataframe["close"] > dataframe["vwap"])
            & (dataframe["rsi"] < 75),
            "enter_long",
        ] = 1
        return dataframe
