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
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.exchange import timeframe_to_minutes
from freqtrade.persistence import Trade
from freqtrade.strategy import (BooleanParameter, DecimalParameter, IntParameter, IStrategy,
                                informative, stoploss_from_absolute)

sys.path.append(str(Path(__file__).parent))
from market_guard import MarketGuard  # noqa: E402

logger = logging.getLogger(__name__)

USER_DATA = Path(__file__).resolve().parent.parent
RISK_FILE = USER_DATA / "daytrade-risk.json"
KILL_FILE = USER_DATA / "KILL"

DEFAULT_RISK = {
    "risk_per_trade": 0.005,
    "max_stake_ratio": 0.2,
    "daily_loss_limit": 0.02,
    "daily_profit_target": 0.0,
    "max_trades_per_day": 50,
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

    # Einstiegsfilter, per ./daytrade.sh hyperopt optimierbar
    adx_min = IntParameter(15, 35, default=20, space="buy")
    rsi_low = IntParameter(40, 60, default=50, space="buy")
    rsi_high = IntParameter(60, 80, default=70, space="buy")
    vol_factor = DecimalParameter(1.0, 2.5, default=1.3, decimals=1, space="buy")
    # Zusatz-Werkzeuge: aus, bis das Selbstlernen (learn) zeigt, dass sie auf ungesehenen Daten helfen
    use_macd = BooleanParameter(default=False, space="buy")      # MACD-Histogramm steigt
    use_obv = BooleanParameter(default=False, space="buy")       # Kaufvolumen (OBV) ueber seinem Schnitt
    use_mfi = BooleanParameter(default=False, space="buy")       # Geldfluss (MFI) > 50
    use_rsi_1h = BooleanParameter(default=False, space="buy")    # 1h-RSI > 50
    use_not_stretched = BooleanParameter(default=False, space="buy")  # Kurs noch unter oberem Bollinger-Band
    use_stoch = BooleanParameter(default=False, space="buy")     # Stoch-RSI K ueber D
    # Markt-Waechter wie bei Profi-Daytradern; Unterklassen schalten sie ein (0/None = aus)
    guard_fng_min = 0          # kein Kauf, wenn Fear & Greed (Vortag) darunter liegt
    guard_btc_trend = False    # kein Kauf, wenn BTC auf 15m unter seiner EMA50 liegt
    guard_btc_crash = 0.0      # kein Kauf, wenn BTC in der letzten Stunde mehr als so viel gefallen ist
    guard_hours = None         # (von, bis) in UTC: nur zu aktiven Handelszeiten kaufen
    # Stop/Ziel/Haltezeit je Strategie (None = Wert aus daytrade-risk.json); das Risiko pro Trade bleibt gleich,
    # weil die Positionsgroesse sich nach dem Stop-Abstand richtet
    stop_mult = None
    target_mult = None
    hold_minutes = None

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
        self.live = self.config["runmode"].value in ("live", "dry_run")
        self.guard = MarketGuard(self.live)
        if self.guard_fng_min:
            self.guard.load_fng()
        self._journal_day = None

    def informative_pairs(self):
        return [("BTC/USDT", "15m")]

    @informative("1h")
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema9"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema21"] = ta.EMA(dataframe, timeperiod=21)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["vol_avg"] = dataframe["volume"].rolling(30).mean()
        dataframe["m_macd_hist"] = ta.MACD(dataframe)["macdhist"]
        dataframe["m_obv"] = ta.OBV(dataframe)
        dataframe["m_obv_ema"] = ta.EMA(dataframe["m_obv"], timeperiod=20)
        dataframe["m_mfi"] = ta.MFI(dataframe, timeperiod=14)
        dataframe["m_bb_upper"] = dataframe["close"].rolling(20).mean() + 2 * dataframe["close"].rolling(20).std()
        stoch = ta.STOCHRSI(dataframe, timeperiod=14, fastk_period=3, fastd_period=3)
        dataframe["m_stoch_k"] = stoch["fastk"]
        dataframe["m_stoch_d"] = stoch["fastd"]

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
                btc["btc_chg1h"] = btc["close"] / btc["close"].shift(4) - 1
                # 15m-Kerze erst nach ihrem Schluss verwenden
                btc["date"] = btc["date"] + timedelta(minutes=15)
                dataframe = dataframe.merge(btc[["date", "btc_ok", "btc_chg1h"]], on="date", how="left")
                dataframe["btc_ok"] = dataframe["btc_ok"].ffill().fillna(0)
                dataframe["btc_chg1h"] = dataframe["btc_chg1h"].ffill().fillna(0)
        if "btc_ok" not in dataframe:
            dataframe["btc_ok"] = 1
            dataframe["btc_chg1h"] = 0.0
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross_up = (dataframe["ema9"] > dataframe["ema21"]) & (
            dataframe["ema9"].shift(1) <= dataframe["ema21"].shift(1))
        extra = dataframe["close"] > 0
        if self.use_macd.value:
            extra &= dataframe["m_macd_hist"] > dataframe["m_macd_hist"].shift(1)
        if self.use_obv.value:
            extra &= dataframe["m_obv"] > dataframe["m_obv_ema"]
        if self.use_mfi.value:
            extra &= dataframe["m_mfi"] > 50
        if self.use_rsi_1h.value:
            extra &= dataframe["rsi_1h"] > 50
        if self.use_not_stretched.value:
            extra &= dataframe["close"] < dataframe["m_bb_upper"]
        if self.use_stoch.value:
            extra &= dataframe["m_stoch_k"] > dataframe["m_stoch_d"]
        dataframe.loc[
            extra
            & (dataframe["ema50_1h"] > dataframe["ema200_1h"])
            & (dataframe["close_1h"] > dataframe["ema50_1h"])
            & (dataframe["btc_ok"] == 1)
            & cross_up
            & (dataframe["close"] > dataframe["vwap"])
            & (dataframe["close"] > dataframe["ema50"])
            & (dataframe["adx"] > self.adx_min.value)
            & (dataframe["rsi"].between(self.rsi_low.value, self.rsi_high.value))
            & (dataframe["volume"] > dataframe["vol_avg"] * self.vol_factor.value)
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

    def _rp(self, key: str) -> float:
        own = {"atr_stop_mult": self.stop_mult, "atr_target_mult": self.target_mult,
               "max_trade_minutes": self.hold_minutes}[key]
        return self.risk[key] if own is None else own

    def _entry_atr(self, pair: str, trade: Trade) -> float | None:
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df.empty:
            return None
        signal_time = trade.open_date_utc - timedelta(minutes=timeframe_to_minutes(self.timeframe))
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
        r = atr * self._rp("atr_stop_mult")
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
        if atr and current_rate >= trade.open_rate + atr * self._rp("atr_target_mult"):
            return "atr_target"
        if current_time - trade.open_date_utc > timedelta(minutes=self._rp("max_trade_minutes")):
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
        stop_dist = atr * self._rp("atr_stop_mult") / current_rate
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
        if self.guard_hours and not (self.guard_hours[0] <= current_time.hour < self.guard_hours[1]):
            return False
        if self.guard_btc_trend or self.guard_btc_crash:
            df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if not df.empty:
                last = df.iloc[-1]
                if self.guard_btc_trend and last["btc_ok"] != 1:
                    return False
                if self.guard_btc_crash and last["btc_chg1h"] < -self.guard_btc_crash:
                    return False
        if self.guard.block_reason(pair, current_time, self.guard_fng_min):
            return False
        return True

    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        # Trade-Tagebuch: jeden Abend 19 UTC (21 Uhr deutsche Sommerzeit) per Telegram
        if not self.live or current_time.hour != 19 or self._journal_day == current_time.date():
            return
        self._journal_day = current_time.date()
        start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        trades = Trade.get_trades_proxy(is_open=False, close_date=start)
        lines = [f"Tagebuch {current_time:%d.%m.} ({self.__class__.__name__})"]
        for t in trades:
            lines.append(f"{t.pair} {t.open_date_utc:%H:%M}-{t.close_date_utc:%H:%M} "
                         f"{(t.close_profit or 0) * 100:+.2f}% ({t.close_profit_abs or 0:+.2f} $) {t.exit_reason}")
        total = sum(t.close_profit_abs or 0 for t in trades)
        wins = sum(1 for t in trades if (t.close_profit_abs or 0) > 0)
        lines.append(f"{len(trades)} Trades, {wins} im Plus, gesamt {total:+.2f} $")
        self.dp.send_msg("\n".join(lines), always_send=True)

