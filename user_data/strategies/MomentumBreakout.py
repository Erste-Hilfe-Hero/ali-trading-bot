# MomentumBreakout – aggressive Trendfolge mit harten Stops
#
# Idee: Nur kaufen, wenn (1) der Gesamtmarkt (BTC) im Aufwärtstrend ist,
# (2) der Coin selbst im Trend ist und (3) er mit erhöhtem Volumen
# aus seiner 24h-Spanne ausbricht. Verluste werden hart begrenzt,
# Gewinner werden per Trailing-Stop laufen gelassen.

from functools import reduce

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, merge_informative_pair


class MomentumBreakout(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "1h"
    can_short = False

    # Harte Verlustgrenze pro Trade
    stoploss = -0.08

    # Gewinner laufen lassen, ab +6 % mit 3 % Abstand nachziehen
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.06
    trailing_only_offset_is_reached = True

    # Feste Gewinnmitnahme nur bei sehr großen Moves
    minimal_roi = {"0": 0.30}

    process_only_new_candles = True
    startup_candle_count = 210
    use_exit_signal = True

    # Stop-Loss direkt auf der Börse platzieren (greift auch, wenn der Bot offline ist)
    order_types = {
        "entry": "market",
        "exit": "market",
        "stoploss": "market",
        "stoploss_on_exchange": True,
    }

    breakout_window = IntParameter(12, 48, default=24, space="buy")
    volume_factor = DecimalParameter(1.0, 3.0, default=1.5, decimals=1, space="buy")
    rsi_max = IntParameter(65, 85, default=75, space="buy")

    @property
    def protections(self):
        return [
            # 3 Stop-Losses in 24h -> 24h Pause
            {"method": "StoplossGuard", "lookback_period_candles": 24, "trade_limit": 3,
             "stop_duration_candles": 24, "only_per_pair": False},
            # 15 % Drawdown in 7 Tagen -> 48h Pause
            {"method": "MaxDrawdown", "lookback_period_candles": 168, "trade_limit": 5,
             "stop_duration_candles": 48, "max_allowed_drawdown": 0.15},
            {"method": "CooldownPeriod", "stop_duration_candles": 2},
            # Coin mit 2 Verlust-Trades in 72h -> 48h gesperrt
            {"method": "LowProfitPairs", "lookback_period_candles": 72, "trade_limit": 2,
             "stop_duration_candles": 48, "required_profit": 0.0},
        ]

    def informative_pairs(self):
        return [("BTC/USDT", self.timeframe)]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["vol_avg"] = dataframe["volume"].rolling(20).mean()
        for w in self.breakout_window.range:
            dataframe[f"hh_{w}"] = dataframe["high"].rolling(w).max().shift(1)

        if self.dp:
            btc = self.dp.get_pair_dataframe("BTC/USDT", self.timeframe)
            btc["ema200"] = ta.EMA(btc, timeperiod=200)
            btc["ema50"] = ta.EMA(btc, timeperiod=50)
            btc = btc[["date", "close", "ema50", "ema200"]].rename(
                columns={"close": "btc_close", "ema50": "btc_ema50", "ema200": "btc_ema200"})
            dataframe = merge_informative_pair(dataframe, btc, self.timeframe, self.timeframe, ffill=True)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        w = self.breakout_window.value
        conditions = [
            # Marktfilter: BTC im Aufwärtstrend
            dataframe["btc_close_1h"] > dataframe["btc_ema200_1h"],
            dataframe["btc_ema50_1h"] > dataframe["btc_ema200_1h"],
            # Coin im Trend
            dataframe["close"] > dataframe["ema50"],
            dataframe["ema50"] > dataframe["ema200"],
            # Ausbruch über das Hoch der letzten w Stunden mit Volumen
            dataframe["close"] > dataframe[f"hh_{w}"],
            dataframe["volume"] > dataframe["vol_avg"] * self.volume_factor.value,
            # nicht schon völlig überkauft
            dataframe["rsi"] < self.rsi_max.value,
            dataframe["volume"] > 0,
        ]
        dataframe.loc[reduce(lambda a, b: a & b, conditions), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Trend gebrochen: Schlusskurs fällt unter die EMA20
        dataframe.loc[
            (dataframe["close"] < dataframe["ema20"]) & (dataframe["volume"] > 0),
            "exit_long",
        ] = 1
        return dataframe
