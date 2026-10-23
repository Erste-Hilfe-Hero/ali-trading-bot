# DaytradeMomentum – Intraday-Trendfolge auf 5m-Kerzen (nur Long, Spot)
#
# Idee: Nur kaufen, wenn der Coin auf 1h im Aufwaertstrend ist und BTC nicht
# faellt. Einstieg auf 5m, wenn ein kurzer Ruecksetzer endet (EMA9 kreuzt EMA21
# nach oben, Kurs ueber dem Tages-VWAP, Volumen erhoeht). Jeder Trade hat einen
# ATR-Stop und ein ATR-Ziel (Chance/Risiko 1:2) und ist spaetestens nach
# max_trade_minutes zu.
#
# Risikosteuerung (alles in user_data/daytrade-risk.json einstellbar):
#   risk_per_trade      Anteil des Kapitals, der bei einem Stop verloren gehen darf
#   max_stake_ratio     maximale Positionsgroesse als Anteil des Kapitals
#   daily_loss_limit    realisierter Tagesverlust (UTC), ab dem keine neuen Trades mehr kommen
#   daily_profit_target realisierter Tagesgewinn, ab dem keine neuen Trades mehr kommen (0 = aus)
#   max_trades_per_day  Obergrenze neuer Trades pro UTC-Tag
# Kill-Switch: Datei user_data/KILL anlegen -> keine neuen Einstiege, offene
# Trades werden beim naechsten Durchlauf verkauft.

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, informative, stoploss_from_absolute

logger = logging.getLogger(__name__)

USER_DATA = Path(__file__).resolve().parent.parent
RISK_FILE = USER_DATA / "daytrade-risk.json"
KILL_FILE = USER_DATA / "KILL"

DEFAULT_RISK = {
    "risk_per_trade": 0.005,
    "max_stake_ratio": 0.25,
    "daily_loss_limit": 0.02,
    "daily_profit_target": 0.0,
    "max_trades_per_day": 20,
    "atr_stop_mult": 1.5,
    "atr_target_mult": 3.0,
    "max_trade_minutes": 180,
}


class DaytradeMomentum(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short = False

    # Notbremse, falls der ATR-Stop nicht berechnet werden kann
    stoploss = -0.03
    use_custom_stoploss = True
    minimal_roi = {"0": 100}
    trailing_stop = False

    process_only_new_candles = True
    startup_candle_count = 300
    use_exit_signal = True
    exit_profit_only = False

    order_types = {
        "entry": "market",
        "exit": "market",
        "stoploss": "market",
        "stoploss_on_exchange": True,
        "stoploss_on_exchange_interval": 60,
    }

    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 3},
            # 4 Stops in 2h ueber alle Coins -> 2h Pause
            {"method": "StoplossGuard", "lookback_period_candles": 24, "trade_limit": 4,
             "stop_duration_candles": 24, "only_per_pair": False},
            # Coin mit 2 Verlusten in 3h -> 3h gesperrt
            {"method": "LowProfitPairs", "lookback_period_candles": 36, "trade_limit": 2,
             "stop_duration_candles": 36, "required_profit": 0.0},
            # 5 % Drawdown in 24h -> 12h Pause
            {"method": "MaxDrawdown", "lookback_period_candles": 288, "trade_limit": 4,
             "stop_duration_candles": 144, "max_allowed_drawdown": 0.05},
        ]

    def bot_start(self, **kwargs) -> None:
        self.risk = dict(DEFAULT_RISK)
        if RISK_FILE.exists():
            self.risk.update(json.loads(RISK_FILE.read_text()))
        logger.info("DaytradeMomentum: Risiko-Einstellungen %s", self.risk)

    def informative_pairs(self):
        return [("BTC/USDT", "15m")]

    @informative("1h")
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema9"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema21"] = ta.EMA(dataframe, timeperiod=21)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["vol_avg"] = dataframe["volume"].rolling(30).mean()

        # VWAP, jeden UTC-Tag neu
        day = dataframe["date"].dt.floor("D")
        tp = (dataframe["high"] + dataframe["low"] + dataframe["close"]) / 3
        pv = (tp * dataframe["volume"]).groupby(day).cumsum()
        vv = dataframe["volume"].groupby(day).cumsum()
        dataframe["vwap"] = pv / vv

        if self.dp:
            btc = self.dp.get_pair_dataframe("BTC/USDT", "15m")
            if not btc.empty:
                btc["btc_ema50"] = ta.EMA(btc, timeperiod=50)
                btc["btc_ok"] = (btc["close"] > btc["btc_ema50"]).astype(int)
                # 15m-Kerze erst nach ihrem Schluss verwenden
                btc["date"] = btc["date"] + timedelta(minutes=15)
                dataframe = dataframe.merge(btc[["date", "btc_ok"]], on="date", how="left")
                dataframe["btc_ok"] = dataframe["btc_ok"].ffill().fillna(0)
        if "btc_ok" not in dataframe:
            dataframe["btc_ok"] = 1
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross_up = (dataframe["ema9"] > dataframe["ema21"]) & (
            dataframe["ema9"].shift(1) <= dataframe["ema21"].shift(1))
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"])
            & (dataframe["close_1h"] > dataframe["ema50_1h"])
            & (dataframe["btc_ok"] == 1)
            & cross_up
            & (dataframe["close"] > dataframe["vwap"])
            & (dataframe["close"] > dataframe["ema50"])
            & (dataframe["adx"] > 20)
            & (dataframe["rsi"].between(50, 70))
            & (dataframe["volume"] > dataframe["vol_avg"] * 1.3)
            & (dataframe["atr"] / dataframe["close"] > 0.002),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] < dataframe["ema21"]) & (dataframe["close"] < dataframe["vwap"]),
            "exit_long",
        ] = 1
        return dataframe

    def _entry_atr(self, pair: str, trade: Trade) -> float | None:
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df.empty:
            return None
        signal_time = trade.open_date_utc - timedelta(minutes=5)
        rows = df.loc[df["date"] <= signal_time]
        if rows.empty:
            return None
        return float(rows["atr"].iloc[-1])

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, after_fill: bool,
                        **kwargs) -> float | None:
        atr = self._entry_atr(pair, trade)
        if not atr:
            return None
        r = atr * self.risk["atr_stop_mult"]
        stop_price = trade.open_rate - r
        # Ab +1,5R einen halben R Gewinn sichern (Einstand allein frisst die Gebuehren)
        if current_rate >= trade.open_rate + 1.5 * r:
            stop_price = trade.open_rate + 0.5 * r
        return stoploss_from_absolute(stop_price, current_rate, is_short=False, leverage=trade.leverage)

    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float, **kwargs):
        if KILL_FILE.exists():
            return "kill_switch"
        atr = self._entry_atr(pair, trade)
        if atr and current_rate >= trade.open_rate + atr * self.risk["atr_target_mult"]:
            return "atr_target"
        if current_time - trade.open_date_utc > timedelta(minutes=self.risk["max_trade_minutes"]):
            return "time_exit"
        return None

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: float | None, max_stake: float,
                            leverage: float, entry_tag: str | None, side: str,
                            **kwargs) -> float:
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df.empty:
            return 0
        atr = float(df["atr"].iloc[-1])
        stop_dist = atr * self.risk["atr_stop_mult"] / current_rate
        capital = self.wallets.get_total_stake_amount()
        stake = capital * self.risk["risk_per_trade"] / max(stop_dist, 0.003)
        stake = min(stake, capital * self.risk["max_stake_ratio"], max_stake)
        if min_stake and stake < min_stake:
            return 0
        return stake

    def _day_stats(self, current_time: datetime) -> tuple[float, int]:
        start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        closed = Trade.get_trades_proxy(is_open=False, close_date=start)
        opened = [t for t in Trade.get_trades_proxy() if t.open_date_utc >= start]
        return sum(t.close_profit_abs or 0 for t in closed), len(opened)

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: str | None,
                            side: str, **kwargs) -> bool:
        if KILL_FILE.exists():
            logger.warning("Kill-Switch aktiv, kein Einstieg in %s", pair)
            return False
        capital = self.wallets.get_total_stake_amount()
        pnl, count = self._day_stats(current_time)
        if pnl <= -capital * self.risk["daily_loss_limit"]:
            logger.warning("Tagesverlust-Limit erreicht (%.2f), kein Einstieg in %s", pnl, pair)
            return False
        target = self.risk["daily_profit_target"]
        if target and pnl >= capital * target:
            logger.info("Tagesziel erreicht (%.2f), kein Einstieg in %s", pnl, pair)
            return False
        if count >= self.risk["max_trades_per_day"]:
            logger.info("Max. Trades pro Tag erreicht, kein Einstieg in %s", pair)
            return False
        return True
