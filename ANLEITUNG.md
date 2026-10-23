# Ali Trading Bot – Freqtrade auf dem Contabo-VPS

## Was der Bot macht
Strategie **MomentumBreakout** auf 1h-Kerzen für BTC, ETH, SOL, DOGE, PEPE, WIF, BONK:

- **Kaufen** nur, wenn BTC im Aufwärtstrend ist (über EMA200), der Coin selbst im Trend ist (EMA50 > EMA200) und mit erhöhtem Volumen über das 24h-Hoch ausbricht.
- **Verkaufen**, wenn der Kurs unter die EMA20 fällt, der Trailing-Stop greift (ab +6 % Gewinn mit 3 % Abstand) oder bei +30 %.
- **Stop-Loss -8 %** pro Trade, direkt auf Binance platziert (greift auch, wenn der Bot offline ist).
- **Schutzschalter:** 3 Stop-Losses in 24h → 24h Pause. 15 % Drawdown in 7 Tagen → 48h Pause.
- Max. 3 Trades gleichzeitig à 30 USDT.

## Backtest (15.10.2025 – 16.10.2026, 100 USDT Start, inkl. Gebühren)
| | Bot | Markt (Ø der 7 Coins) |
|---|---|---|
| Ergebnis | **+3,0 %** | **-52,9 %** |
| Trades | 179 | – |
| Trefferquote | 32 % | – |
| Max. Drawdown | -13,3 % | – |
| Bester / schlechtester Trade | +12,7 % / -8,1 % | – |

Ehrlich gelesen: Der Bot hat in einem Jahr, in dem die Coins im Schnitt die Hälfte verloren haben, das Kapital gehalten. Einen statistisch belegten Vorteil hat er **nicht** (Profit-Faktor 1,05, p-Wert 0,82). Er ist ein Risiko-Werkzeug, keine Gelddruckmaschine. Vergangene Ergebnisse garantieren nichts.

## Einrichtung

### 1. API-Key für den Sub-Account `bot_virtual`
Binance → Sub-Account → API Management → beim Sub-Account `bot_virtual` einen API-Key erstellen.
- ✅ Enable Reading, ✅ Enable Spot & Margin Trading
- ❌ **Withdrawals AUS**, ❌ Margin, ❌ Futures
- ✅ **IP-Beschränkung** auf die IP deines Contabo-VPS
- Dann USDT auf `bot_virtual` überweisen (z. B. 100 USDT).

> Der Agent-Account (UID …221) bleibt für Claude im Chat. Der Bot bekommt einen eigenen Topf. So kommen sich beide nicht in die Quere.

### 2. Telegram-Bot
- In Telegram `@BotFather` → `/newbot` → Token kopieren.
- `@userinfobot` schreiben → deine Chat-ID kopieren.

### 3. Auf dem VPS
```bash
# Docker installieren (falls noch nicht da)
curl -fsSL https://get.docker.com | sh

# Ordner hochladen (z. B. mit scp) oder entpacken, dann:
cd ali-trading-bot
cp .env.example .env
nano .env        # Keys, Telegram eintragen, DRY_RUN=true lassen
docker compose up -d
docker compose logs -f   # prüfen, ob er läuft
```

### 4. Steuern über Telegram
| Befehl | Was es macht |
|---|---|
| `/status` | offene Trades |
| `/profit` | Gesamtgewinn |
| `/balance` | Kontostand |
| `/daily` | Gewinn pro Tag |
| `/stopentry` | keine neuen Käufe mehr |
| `/forceexit all` | alles verkaufen |
| `/stop` | Bot anhalten |

### 5. Live schalten
Erst nach **mindestens 1–2 Wochen Testmodus**, wenn die Telegram-Meldungen Sinn ergeben:
`FREQTRADE__DRY_RUN=false` in der `.env`, dann `docker compose up -d`.

## Steuer-Hinweis (Deutschland)
Jeder Verkauf innerhalb eines Jahres nach Kauf ist steuerpflichtig. Mit `/profit` und einem Export aus Binance (Blockpit, CoinTracking) behältst du den Überblick. Keine Steuerberatung.

## Daytrader (zweiter Bot, 5m-Kerzen)
Handelt dieselben Coins wie der Hauptbot (Top 50 nach Volumen, gleiche Filter und Sperrliste; der Backtest nutzt eine feste Liste von 30 liquiden Coins in `config-daytrade-backtest.json`, weil Freqtrade die Volumen-Liste im Backtest nicht kann).

Strategie **DaytradeMomentum**: kauft nur, wenn der Coin auf 1h im Aufwärtstrend ist und BTC auf 15m nicht fällt, und zwar wenn auf 5m EMA9 über EMA21 kreuzt, der Kurs über dem Tages-VWAP liegt und das Volumen erhöht ist.

- **Stop:** 1,5 × ATR unter Einstieg, auf Binance platziert. Ab +1R wird der Stop auf Einstand gezogen.
- **Ziel:** 3 × ATR (Chance/Risiko 1:2). Spätestens nach 3 Stunden wird verkauft.
- **Positionsgröße:** so berechnet, dass ein Stop 0,5 % des Kapitals kostet, max. 25 % des Kapitals pro Trade.
- **Tagesverlust-Limit:** ab -2 % realisiertem Verlust (UTC-Tag) keine neuen Trades.
- **Schutzschalter:** 4 Stops in 2h → 2h Pause, 5 % Drawdown in 24h → 12h Pause.
- Alle Werte in `user_data/daytrade-risk.json`, nach Änderung `./daytrade.sh start`.

Läuft in einem eigenen Container (`ali-daytrade`) mit eigener Datenbank, der Hauptbot bleibt unberührt. Telegram ist aus, weil ein Telegram-Token nur von einem Bot genutzt werden kann (für den Daytrader einen zweiten Bot bei @BotFather anlegen).

| Befehl | Was es macht |
|---|---|
| `./daytrade.sh start` | starten (Testmodus) |
| `./daytrade.sh status` | Container und letzte Logzeilen |
| `./daytrade.sh kill` | **Kill-Switch:** keine neuen Trades, offene werden verkauft |
| `./daytrade.sh unkill` | Kill-Switch aus |
| `./daytrade.sh stop` | Container anhalten |
| `./daytrade.sh backtest 30` | Backtest über die letzten 30 Tage |

Echtgeld: in `.env.daytrade` die Binance-Keys eintragen und `FREQTRADE__DRY_RUN=false` setzen, dann `./daytrade.sh start`. Erst nach einer sauberen Testphase.
