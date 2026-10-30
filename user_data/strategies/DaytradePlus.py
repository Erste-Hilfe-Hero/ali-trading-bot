# DaytradePlus - Wide35 plus die Bot-Punkte aus dem 100-Punkte-Plan (Ali 2026-10-30 "Setze 50 Punkte um")
# Neu gegenueber Wide35 (Nummern = Plan-Punkte):
#   4  Mindestabstand zum Ziel 1 %          16 Einstieg erst nach gruener Kerze unter dem Band
#   17 Coin 6h gesperrt nach Stop-Loss      18 2 Stops in 2h -> 2h Pause fuer alle Coins
#   19 Break-even ab +0,8 %                 20 Trailing ab +1,2 %
#   30 Volumen ueber dem Schnitt            31 hoechstens 3 offene Trades
#   39 hoechstens 10 Trades am Tag          42 halbe Position, wenn BTC unter EMA ~200h
#   45 halbe Position bei extremer Schwankung   84 -6 % in der Woche -> Pause bis Montag
#   7/8 live: kein Kauf bei Spread > 0,15 % oder Tagesvolumen < 20 Mio. $
#   3  live: Telegram-Warnung, wenn BNB fuer den Gebuehrenrabatt unter 1 $ faellt
# Risiko pro Trade, Tagesverlust-Stopp, Kill-Switch und 85-$-Grenze bleiben unveraendert.
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import stoploss_from_absolute

sys.path.append(str(Path(__file__).parent))
from DaytradeMeanRevertPro24Wide35 import DaytradeMeanRevertPro24Wide35  # noqa: E402

logger = logging.getLogger(__name__)


class DaytradePlus(DaytradeMeanRevertPro24Wide35):
    min_gap = 0.01
    max_open = 3
    max_day_trades = 10
    week_loss_limit = 0.06
    max_spread = 0.0015
    min_quote_volume = 20_000_000

    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 3},
            {"method": "StoplossGuard", "lookback_period_candles": 72, "trade_limit": 1,
             "stop_duration_candles": 72, "only_per_pair": True},
            {"method": "StoplossGuard", "lookback_period_candles": 24, "trade_limit": 2,
             "stop_duration_candles": 24, "only_per_pair": False},
            {"method": "LowProfitPairs", "lookback_period_candles": 36, "trade_limit": 2,
             "stop_duration_candles": 36, "required_profit": 0.0},
            {"method": "MaxDrawdown", "lookback_period_candles": 288, "trade_limit": 4,
             "stop_duration_candles": 144, "max_allowed_drawdown": 0.05},
        ]

    def bot_start(self, **kwargs) -> None:
        super().bot_start(**kwargs)
        self._bnb_day = None

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["vol20"] = dataframe["volume"].rolling(20).mean()
        dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"]
        dataframe["atr_pct_avg"] = dataframe["atr_pct"].rolling(288).mean()
        if self.dp:
            btc = self.dp.get_pair_dataframe("BTC/USDT", "15m")
            if not btc.empty:
                btc = btc.copy()
                btc["btc_bear"] = (btc["close"] < ta.EMA(btc, timeperiod=800)).astype(int)
                btc["date"] = btc["date"] + timedelta(minutes=15)
                dataframe = dataframe.merge(btc[["date", "btc_bear"]], on="date", how="left")
                dataframe["btc_bear"] = dataframe["btc_bear"].ffill().fillna(0)
        if "btc_bear" not in dataframe:
            dataframe["btc_bear"] = 0
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        lower = dataframe["bb_mid"] - dataframe["bb_std"] * self.bb_dev.value
        dipped = (dataframe["close"].shift(1) < lower.shift(1)) & (
            dataframe["rsi"].shift(1) < self.rsi_max_entry.value)
        dataframe.loc[
            (dataframe["ema50_1h"] > dataframe["ema200_1h"])
            & dipped
            & (dataframe["close"] > dataframe["open"])
            & (dataframe["close"] > dataframe["close"].shift(1))
            & ((dataframe["volume"] > dataframe["vol20"]) | (dataframe["volume"].shift(1) > dataframe["vol20"]))
            & ((dataframe["bb_mid"] - dataframe["close"]) / dataframe["close"] > self.min_gap),
            "enter_long",
        ] = 1
        return dataframe

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, after_fill: bool,
                        **kwargs) -> float | None:
        atr = self._entry_atr(pair, trade)
        if not atr:
            return None
        r = atr * self._rp("atr_stop_mult")
        stop_price = trade.open_rate - r
        if current_rate >= trade.open_rate * 1.008:
            stop_price = max(stop_price, trade.open_rate * 1.002)
        if current_rate >= trade.open_rate * 1.012:
            stop_price = max(stop_price, current_rate - 1.5 * atr)
        if current_rate >= trade.open_rate + 1.5 * r:
            stop_price = max(stop_price, trade.open_rate + 0.5 * r)
        return stoploss_from_absolute(stop_price, current_rate, is_short=False, leverage=trade.leverage)

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: float | None, max_stake: float,
                            leverage: float, entry_tag: str | None, side: str,
                            **kwargs) -> float:
        stake = super().custom_stake_amount(pair, current_time, current_rate, proposed_stake, min_stake,
                                            max_stake, leverage, entry_tag, side, **kwargs)
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if not stake or df.empty:
            return stake
        last = df.iloc[-1]
        if last["btc_bear"] == 1:
            stake /= 2
        if last["atr_pct"] > 2 * last["atr_pct_avg"]:
            stake /= 2
        if min_stake and stake < min_stake:
            return 0
        return stake

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: str | None,
                            side: str, **kwargs) -> bool:
        if not super().confirm_trade_entry(pair, order_type, amount, rate, time_in_force,
                                           current_time, entry_tag, side, **kwargs):
            return False
        if len(Trade.get_trades_proxy(is_open=True)) >= self.max_open:
            return False
        if self._day_stats(current_time)[1] >= self.max_day_trades:
            return False
        monday = (current_time - timedelta(days=current_time.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0)
        week = sum(t.close_profit_abs or 0 for t in Trade.get_trades_proxy(is_open=False, close_date=monday))
        if week <= -self.wallets.get_total_stake_amount() * self.week_loss_limit:
            logger.warning("Wochenverlust-Limit erreicht (%.2f), kein Einstieg in %s", week, pair)
            return False
        if self.live:
            t = self.dp.ticker(pair)
            if t.get("bid") and t.get("ask") and (t["ask"] - t["bid"]) / t["ask"] > self.max_spread:
                logger.info("Spread zu hoch bei %s, kein Einstieg", pair)
                return False
            if t.get("quoteVolume") and t["quoteVolume"] < self.min_quote_volume:
                logger.info("Zu wenig Volumen bei %s, kein Einstieg", pair)
                return False
        return True

    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        super().bot_loop_start(current_time, **kwargs)
        if not self.live or current_time.hour != 8 or self._bnb_day == current_time.date():
            return
        self._bnb_day = current_time.date()
        try:
            bnb = self.wallets.get_total("BNB") * self.dp.ticker("BNB/USDT")["last"]
        except Exception as e:
            logger.warning("BNB-Pruefung fehlgeschlagen: %s", e)
            return
        if bnb < 1:
            self.dp.send_msg(f"BNB nur noch {bnb:.2f} $: Gebuehrenrabatt faellt weg. Bitte 3-5 $ BNB nachkaufen.",
                             always_send=True)
