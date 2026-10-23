# DaytradeMeanRevert – Ruecksetzer-Kauf auf 5m, erbt Risiko und Kill-Switch von DaytradeMomentum
import sys
from pathlib import Path

from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeMeanRevert(DaytradeMomentum):
    # Ruecksetzer-Kauf: im 1h-Aufwaertstrend kaufen, wenn der Kurs auf 5m unter das untere
    # Bollinger-Band faellt und ueberverkauft ist; verkaufen, sobald er zur Mitte zurueckkehrt.
    # Risiko, Positionsgroesse, Tageslimit und Kill-Switch kommen aus DaytradeMomentum.
    bb_dev = DecimalParameter(1.8, 2.8, default=2.2, decimals=1, space="buy")
    rsi_max_entry = IntParameter(20, 38, default=30, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["bb_mid"] = dataframe["close"].rolling(20).mean()
        dataframe["bb_std"] = dataframe["close"].rolling(20).std()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        lower = dataframe["bb_mid"] - dataframe["bb_std"] * self.bb_dev.value
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"])
            & (dataframe["close"] < lower)
            & (dataframe["rsi"] < self.rsi_max_entry.value)
            & (dataframe["volume"] > 0)
            # genug Abstand zur Mitte, damit sich der Trade nach Gebuehren lohnt
            & ((dataframe["bb_mid"] - dataframe["close"]) / dataframe["close"] > 0.006),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["close"] > dataframe["bb_mid"], "exit_long"] = 1
        return dataframe
