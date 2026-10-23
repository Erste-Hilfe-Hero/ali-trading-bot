# DaytradeConfluence – jeder Einstieg prueft alle Signale gleichzeitig
#
# Neun Filter geben je einen Punkt: 1h-Trend, Kurs ueber 1h-EMA50, BTC stabil, MACD steigt,
# RSI im gesunden Bereich, Volumen erhoeht, Volatilitaet passend, Kurs ueber Tages-VWAP, ADX.
# Zwei Einstiegsarten:
#   momentum: EMA9 kreuzt EMA21 nach oben und mindestens min_score Punkte
#   pullback: im 1h-Trend unter das untere Bollinger-Band mit RSI ueberverkauft und
#             mindestens pullback_score Punkte aus den Filtern, die ein Ruecksetzer erfuellen kann
# Risiko, Positionsgroesse, Tageslimit und Kill-Switch kommen aus DaytradeMomentum.
import sys
from pathlib import Path

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMomentum import DaytradeMomentum  # noqa: E402


class DaytradeConfluence(DaytradeMomentum):
    min_score = IntParameter(5, 9, default=7, space="buy")
    pullback_score = IntParameter(2, 5, default=3, space="buy")
    bb_dev = DecimalParameter(1.8, 2.8, default=2.2, decimals=1, space="buy")
    rsi_pullback = IntParameter(20, 38, default=30, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        macd = ta.MACD(dataframe)
        dataframe["macd_hist"] = macd["macdhist"]
        dataframe["bb_mid"] = dataframe["close"].rolling(20).mean()
        dataframe["bb_std"] = dataframe["close"].rolling(20).std()
        atr_pct = dataframe["atr"] / dataframe["close"]

        dataframe["s_trend"] = (dataframe["ema50_1h"] > dataframe["ema200_1h"]).astype(int)
        dataframe["s_above_1h"] = (dataframe["close_1h"] > dataframe["ema50_1h"]).astype(int)
        dataframe["s_btc"] = (dataframe["btc_ok"] == 1).astype(int)
        dataframe["s_macd"] = (dataframe["macd_hist"] > dataframe["macd_hist"].shift(1)).astype(int)
        dataframe["s_rsi"] = dataframe["rsi"].between(45, 70).astype(int)
        dataframe["s_vol"] = (dataframe["volume"] > dataframe["vol_avg"] * 1.2).astype(int)
        dataframe["s_atr"] = atr_pct.between(0.002, 0.03).astype(int)
        dataframe["s_vwap"] = (dataframe["close"] > dataframe["vwap"]).astype(int)
        dataframe["s_adx"] = (dataframe["adx"] > 20).astype(int)
        dataframe["score"] = dataframe[["s_trend", "s_above_1h", "s_btc", "s_macd", "s_rsi",
                                        "s_vol", "s_atr", "s_vwap", "s_adx"]].sum(axis=1)
        dataframe["score_pullback"] = dataframe[["s_trend", "s_btc", "s_vol", "s_atr", "s_macd"]].sum(axis=1)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross_up = (dataframe["ema9"] > dataframe["ema21"]) & (
            dataframe["ema9"].shift(1) <= dataframe["ema21"].shift(1))
        momentum = cross_up & (dataframe["score"] >= self.min_score.value)
        lower = dataframe["bb_mid"] - dataframe["bb_std"] * self.bb_dev.value
        pullback = (
            (dataframe["s_trend"] == 1)
            & (dataframe["close"] < lower)
            & (dataframe["rsi"] < self.rsi_pullback.value)
            & ((dataframe["bb_mid"] - dataframe["close"]) / dataframe["close"] > 0.006)
            & (dataframe["score_pullback"] >= self.pullback_score.value)
        )
        dataframe.loc[momentum & (dataframe["volume"] > 0), ["enter_long", "enter_tag"]] = (1, "momentum")
        dataframe.loc[pullback & (dataframe["volume"] > 0), ["enter_long", "enter_tag"]] = (1, "pullback")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] < dataframe["ema21"]) & (dataframe["close"] < dataframe["vwap"]),
            ["exit_long", "exit_tag"],
        ] = (1, "trend_break")
        return dataframe

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        reason = super().custom_exit(pair, trade, current_time, current_rate, current_profit, **kwargs)
        if reason:
            return reason
        # Pullback-Trades verkaufen, sobald der Kurs zur Bollinger-Mitte zurueckkehrt
        if trade.enter_tag == "pullback":
            df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if not df.empty and current_rate > df["bb_mid"].iloc[-1]:
                return "pullback_target"
        return None

    def custom_stake_amount(self, pair, current_time, current_rate, proposed_stake, min_stake,
                            max_stake, leverage, entry_tag, side, **kwargs) -> float:
        # Einsatz nach Signalstaerke: volle Punktzahl 1,3x, Mindestpunktzahl 0,7x des Basis-Einsatzes
        stake = super().custom_stake_amount(pair, current_time, current_rate, proposed_stake,
                                            min_stake, max_stake, leverage, entry_tag, side, **kwargs)
        if not stake:
            return stake
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if entry_tag == "momentum" and not df.empty:
            lo = self.min_score.value
            factor = 0.7 + 0.6 * (df["score"].iloc[-1] - lo) / max(9 - lo, 1)
        else:
            factor = 1.0
        stake = min(stake * factor, max_stake)
        if min_stake and stake < min_stake:
            return min_stake if min_stake <= max_stake else 0
        return stake
