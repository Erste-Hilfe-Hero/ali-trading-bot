#!/usr/bin/env bash
# Daytrader steuern: start | stop | kill | unkill | status | logs | backtest [tage]
set -euo pipefail
cd "$(dirname "$0")"
DC="docker compose -f docker-compose.daytrade.yaml"
FT_IMG=freqtradeorg/freqtrade:stable

ensure_env() {
  mkdir -p user_data/logs
  chmod -R a+rwX user_data 2>/dev/null || true
  if [ ! -f .env.daytrade ]; then
    # Binance-Zugang vom Hauptbot uebernehmen, Testmodus erzwingen, Telegram aus (ein Token kann nur ein Bot nutzen)
    grep -E '^FREQTRADE__EXCHANGE__(KEY|SECRET)=' .env 2>/dev/null > .env.daytrade || true
    echo "FREQTRADE__DRY_RUN=true" >> .env.daytrade
    chmod 600 .env.daytrade
  fi
}

case "${1:-status}" in
  start)  ensure_env; rm -f user_data/KILL; $DC pull; $DC up -d --force-recreate
          grep -q '^FREQTRADE__DRY_RUN=false' .env.daytrade && echo "Modus: ECHTGELD" || echo "Modus: TESTMODUS" ;;
  stop)   $DC stop ;;
  kill)   touch user_data/KILL; echo "Kill-Switch aktiv: keine neuen Trades, offene werden verkauft." ;;
  unkill) rm -f user_data/KILL; echo "Kill-Switch aus." ;;
  status) $DC ps; tail -n 30 user_data/logs/daytrade.log 2>/dev/null || true ;;
  logs)   $DC logs -f --tail 100 ;;
  backtest)
    DAYS="${2:-30}"
    ensure_env
    START=$(date -u -d "-$((DAYS + 3)) days" +%Y%m%d)
    BT=$(date -u -d "-${DAYS} days" +%Y%m%d)
    RUN="docker run --rm -v $PWD/user_data:/freqtrade/user_data $FT_IMG"
    $RUN download-data --config /freqtrade/user_data/config-daytrade.json --config /freqtrade/user_data/config-daytrade-backtest.json -t 5m 15m 1h --timerange "${START}-"
    $RUN backtesting --config /freqtrade/user_data/config-daytrade.json --config /freqtrade/user_data/config-daytrade-backtest.json --strategy DaytradeMomentum \
      --timerange "${BT}-" --breakdown day --cache none ;;
  *) echo "Benutzung: $0 start|stop|kill|unkill|status|logs|backtest [tage]"; exit 1 ;;
esac
