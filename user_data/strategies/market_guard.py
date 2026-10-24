# Markt-Waechter: sagt dem Bot, wann er lieber nicht kauft (wie ein Daytrader vor dem Klick)
#   News       Schlagzeilen grosser Krypto-Seiten; Coin + Warnwort (Hack, Delisting, Klage ...) -> Coin gesperrt
#   Termine    wichtige US-Termine (Fed, Inflation, Arbeitsmarkt) -> Pause davor und danach
#   Stimmung   Fear & Greed Index unter fng_min -> keine Kaeufe (auch im Backtest, Tageswerte)
# News und Termine gibt es nur live (keine Historie), sie sperren nur und kaufen nie.
# Netzfehler sperren nichts: lieber normal weiterhandeln als wegen eines Timeouts still stehen.

import json
import logging
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

USER_DATA = Path(__file__).resolve().parent.parent
GUARD_FILE = USER_DATA / "market-guard.json"
FNG_CACHE = USER_DATA / "fng-history.json"

DEFAULT_GUARD = {
    "news": False,
    "news_block_hours": 6,
    "macro": False,
    "macro_before_min": 30,
    "macro_after_min": 60,
}

NEWS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://www.theblock.co/rss.xml",
    "https://bitcoinmagazine.com/.rss/full/",
]
BAD_WORDS = re.compile(
    r"\b(hack(ed)?|exploit(ed)?|drain(ed)?|delist(s|ed|ing)?|lawsuit|sue[sd]?|charged?|fraud|scam|"
    r"rug ?pull|insolven\w*|bankrupt\w*|halt(s|ed)?|suspend(s|ed)?|depeg\w*|plunge[sd]?|crash(es|ed)?|"
    r"breach|stolen|investigation)\b", re.I)
EXCHANGE_DOWN = re.compile(r"\bbinance\b.*\b(hack(ed)?|exploit|insolven\w*|withdrawals? (halt|suspend)\w*)", re.I)
MACRO_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"


def _get(url: str, timeout: int = 10) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 ali-daytrader"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


class MarketGuard:
    def __init__(self, live: bool):
        self.live = live
        self.cfg = dict(DEFAULT_GUARD)
        if GUARD_FILE.exists():
            self.cfg.update(json.loads(GUARD_FILE.read_text()))
        self._fng: dict[str, int] = {}
        self._headlines: list[tuple[datetime, str]] = []
        self._news_at = 0.0
        self._events: list[tuple[datetime, str]] = []
        self._macro_at = 0.0
        self._last_block: dict[str, str] = {}
        logger.info("Markt-Waechter: %s (live=%s)", self.cfg, live)

    # Stimmung ---------------------------------------------------------------
    def load_fng(self) -> None:
        try:
            data = json.loads(_get("https://api.alternative.me/fng/?limit=0&format=json", 20))["data"]
            self._fng = {datetime.fromtimestamp(int(d["timestamp"]), timezone.utc).strftime("%Y-%m-%d"):
                         int(d["value"]) for d in data}
            FNG_CACHE.write_text(json.dumps(self._fng))
        except Exception as e:
            logger.warning("Fear & Greed nicht abrufbar (%s), nutze Cache", e)
            if FNG_CACHE.exists():
                self._fng = json.loads(FNG_CACHE.read_text())

    def fng(self, when: datetime) -> int | None:
        if self.live and time.time() - getattr(self, "_fng_at", 0) > 3600:
            self._fng_at = time.time()
            self.load_fng()
        # der Wert eines Tages steht erst ab diesem Tag fest -> Vortag nutzen, kein Blick in die Zukunft
        return self._fng.get((when - timedelta(days=1)).strftime("%Y-%m-%d"))

    # News -------------------------------------------------------------------
    def _refresh_news(self) -> None:
        if time.time() - self._news_at < 600:
            return
        self._news_at = time.time()
        items = []
        for url in NEWS_FEEDS:
            try:
                root = ET.fromstring(_get(url))
                for it in root.iter("item"):
                    title = (it.findtext("title") or "").strip()
                    pub = it.findtext("pubDate")
                    try:
                        ts = datetime.strptime(pub.strip()[:25], "%a, %d %b %Y %H:%M:%S").replace(tzinfo=timezone.utc)
                    except Exception:
                        ts = datetime.now(timezone.utc)
                    items.append((ts, title))
            except Exception as e:
                logger.info("News-Feed %s nicht lesbar: %s", url, e)
        if items:
            self._headlines = items

    def news_block(self, coin: str, now: datetime) -> str | None:
        self._refresh_news()
        since = now - timedelta(hours=self.cfg["news_block_hours"])
        coin_re = re.compile(rf"(?<![A-Za-z]){re.escape(coin)}(?![A-Za-z])")
        for ts, title in self._headlines:
            if ts < since or not BAD_WORDS.search(title):
                continue
            if EXCHANGE_DOWN.search(title) or coin_re.search(title):
                return title
        return None

    # Termine ----------------------------------------------------------------
    def _refresh_macro(self) -> None:
        if time.time() - self._macro_at < 6 * 3600:
            return
        self._macro_at = time.time()
        try:
            events = []
            for e in json.loads(_get(MACRO_URL)):
                if e.get("country") == "USD" and e.get("impact") == "High":
                    events.append((datetime.fromisoformat(e["date"]).astimezone(timezone.utc), e["title"]))
            self._events = events
        except Exception as e:
            logger.info("Termin-Kalender nicht lesbar: %s", e)

    def macro_block(self, now: datetime) -> str | None:
        self._refresh_macro()
        for ts, title in self._events:
            if ts - timedelta(minutes=self.cfg["macro_before_min"]) <= now <= ts + timedelta(minutes=self.cfg["macro_after_min"]):
                return f"{title} {ts:%H:%M} UTC"
        return None

    # Gesamturteil -----------------------------------------------------------
    def block_reason(self, pair: str, now: datetime, fng_min: int) -> str | None:
        reason = None
        if fng_min:
            v = self.fng(now)
            if v is not None and v < fng_min:
                reason = f"Fear & Greed {v} < {fng_min}"
        if not reason and self.live and self.cfg["macro"]:
            m = self.macro_block(now)
            if m:
                reason = f"US-Termin: {m}"
        if not reason and self.live and self.cfg["news"]:
            n = self.news_block(pair.split("/")[0], now)
            if n:
                reason = f"News: {n}"
        if reason and self.live and self._last_block.get(pair) != reason:
            logger.warning("Markt-Waechter sperrt %s: %s", pair, reason)
        self._last_block[pair] = reason or ""
        return reason
