# DaytradeBreakout – Ausbruch ueber das 2h-Hoch auf 5m, erbt Risiko und Kill-Switch von DaytradeMomentum
import sys
from pathlib import Path

from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeBreakout(DaytradeMomentum):
    # Kaufen, wenn der Kurs mit starkem Volumen ueber das Hoch der letzten lookback Kerzen steigt,
    # nur im 1h-Aufwaertstrend und wenn BTC nicht faellt.
    lookback = IntParameter(12, 48, default=24, space="buy")
    breakout_vol = DecimalParameter(1.5, 3.5, default=2.0, decimals=1, space="buy")

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        prev_high = dataframe["high"].rolling(self.lookback.value).max().shift(1)
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"])
            & (dataframe["btc_ok"] == 1)
            & (dataframe["close"] > prev_high)
            & (dataframe["close"].shift(1) <= prev_high.shift(1))
            & (dataframe["volume"] > dataframe["vol_avg"] * self.breakout_vol.value)
            & (dataframe["rsi"] < 80)
            & (dataframe["atr"] / dataframe["close"] > 0.003),
            "enter_long",
        ] = 1
        return dataframe
