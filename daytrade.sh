#!/usr/bin/env bash
# Daytrader steuern:
#   start | stop | kill | unkill | status | logs | report
#   backtest [tage] | check [tage] | hyperopt [tage] [epochen] | apply-params
#   paper | live
set -euo pipefail
cd "$(dirname "$0")"
DC="docker compose -f docker-compose.daytrade.yaml"
FT_IMG=freqtradeorg/freqtrade:stable
ENVF=.env.daytrade
MAIN_ENV="${MAIN_ENV:-$HOME/ali-trading-bot-src/.env}"
UD=/freqtrade/user_data
CFG="--config $UD/config-daytrade.json"
BT_CFG="$CFG --config $UD/config-daytrade-backtest.json"
PARAMS=user_data/strategies/DaytradeMomentum.json

set_env() {
  if grep -q "^$1=" "$ENVF"; then sed -i "s|^$1=.*|$1=$2|" "$ENVF"; else echo "$1=$2" >> "$ENVF"; fi
}
get_env() { grep "^$1=" "$ENVF" 2>/dev/null | cut -d= -f2- || true; }

ensure_env() {
  mkdir -p user_data/logs
  chmod -R a+rwX user_data 2>/dev/null || true
  if [ ! -f "$ENVF" ]; then
    echo "FREQTRADE__DRY_RUN=true" > "$ENVF"
    chmod 600 "$ENVF"
  fi
  # Web-Dashboard (FreqUI) und API, nur auf dem Server selbst erreichbar (Port 18081)
  if [ -z "$(get_env FREQTRADE__API_SERVER__PASSWORD)" ]; then
    set_env FREQTRADE__API_SERVER__ENABLED true
    set_env FREQTRADE__API_SERVER__LISTEN_IP_ADDRESS 0.0.0.0
    set_env FREQTRADE__API_SERVER__LISTEN_PORT 8080
    set_env FREQTRADE__API_SERVER__USERNAME ali
    set_env FREQTRADE__API_SERVER__PASSWORD "$(openssl rand -hex 16)"
    set_env FREQTRADE__API_SERVER__JWT_SECRET_KEY "$(openssl rand -hex 32)"
  fi
  # Telegram: eigener Bot-Token noetig (ein Token kann nur von einem Bot genutzt werden)
  if [ -n "${TG_TOKEN_DAYTRADE:-}" ] && [ -n "${TG_CHAT:-}" ]; then
    set_env FREQTRADE__TELEGRAM__TOKEN "$TG_TOKEN_DAYTRADE"
    set_env FREQTRADE__TELEGRAM__CHAT_ID "$TG_CHAT"
  fi
  if [ -n "$(get_env FREQTRADE__TELEGRAM__TOKEN)" ]; then
    set_env FREQTRADE__TELEGRAM__ENABLED true
  else
    set_env FREQTRADE__TELEGRAM__ENABLED false
  fi
}

api() {
  curl -fsS -u "ali:$(get_env FREQTRADE__API_SERVER__PASSWORD)" "http://127.0.0.1:18081/api/v1/$1"
}

download() {
  local days="$1"
  docker run --rm -v "$PWD/user_data:$UD" "$FT_IMG" download-data $BT_CFG -t 5m 15m 1h \
    --timerange "$(date -u -d "-$((days + 3)) days" +%Y%m%d)-"
}

mode() { [ "$(get_env FREQTRADE__DRY_RUN)" = "false" ] && echo "ECHTGELD" || echo "TESTMODUS"; }

case "${1:-status}" in
  start)
    ensure_env; rm -f user_data/KILL; $DC pull; $DC up -d --force-recreate
    echo "Modus: $(mode)" ;;
  stop)   $DC stop ;;
  kill)   touch user_data/KILL; echo "Kill-Switch aktiv: keine neuen Trades, offene werden verkauft." ;;
  unkill) rm -f user_data/KILL; echo "Kill-Switch aus." ;;
  status) $DC ps; echo "Modus: $(mode)"; tail -n 30 user_data/logs/daytrade.log 2>/dev/null || true ;;
  logs)   $DC logs -f --tail 100 ;;
  report)
    echo "Modus: $(mode)"; [ -f user_data/KILL ] && echo "Kill-Switch: AKTIV"
    echo "== Gewinn gesamt";   api profit | python3 -m json.tool
    echo "== Letzte 7 Tage";   api "daily?timescale=7" | python3 -m json.tool
    echo "== Offene Trades";   api status | python3 -m json.tool
    echo "== Kontostand";      api balance | python3 -c 'import json,sys; b=json.load(sys.stdin); print(b["total"], b["stake"])' ;;
  backtest)
    DAYS="${2:-30}"; ensure_env; download "$DAYS"
    docker run --rm -v "$PWD/user_data:$UD" "$FT_IMG" backtesting $BT_CFG --strategy DaytradeMomentum \
      --timerange "$(date -u -d "-${DAYS} days" +%Y%m%d)-" --breakdown day --cache none ;;
  hyperopt)
    # Optimiert auf den ersten 2/3 des Zeitraums, prueft danach auf dem letzten Drittel,
    # das der Optimierer nie gesehen hat. Ergebnis wird nur ein Vorschlag (apply-params).
    DAYS="${2:-90}"; EPOCHS="${3:-300}"; ensure_env; download "$DAYS"
    START=$(date -u -d "-${DAYS} days" +%Y%m%d)
    SPLIT=$(date -u -d "-$((DAYS / 3)) days" +%Y%m%d)
    [ -f "$PARAMS" ] && mv "$PARAMS" "$PARAMS.active"
    RUN="docker run --rm -v $PWD/user_data:$UD $FT_IMG"
    $RUN hyperopt $BT_CFG --strategy DaytradeMomentum --spaces buy --hyperopt-loss SharpeHyperOptLossDaily \
      -e "$EPOCHS" --timerange "${START}-${SPLIT}" -j 2
    echo "== Test auf ungesehenen Daten (${SPLIT} bis heute)"
    $RUN backtesting $BT_CFG --strategy DaytradeMomentum --timerange "${SPLIT}-" --cache none
    [ -f "$PARAMS" ] && mv "$PARAMS" "$PARAMS.candidate"
    [ -f "$PARAMS.active" ] && mv "$PARAMS.active" "$PARAMS"
    echo "Vorschlag gespeichert in $PARAMS.candidate. Uebernehmen mit: $0 apply-params" ;;
  check)
    # Prueft die Strategie auf Blick-in-die-Zukunft-Fehler (Lookahead) und instabile Indikatoren
    DAYS="${2:-30}"; ensure_env; download "$DAYS"
    TR="$(date -u -d "-${DAYS} days" +%Y%m%d)-"
    docker run --rm -v "$PWD/user_data:$UD" "$FT_IMG" lookahead-analysis $BT_CFG --strategy DaytradeMomentum --timerange "$TR"
    docker run --rm -v "$PWD/user_data:$UD" "$FT_IMG" recursive-analysis $BT_CFG --strategy DaytradeMomentum --timerange "$TR" ;;
  apply-params)
    [ -f "$PARAMS.candidate" ] || { echo "Kein Vorschlag vorhanden."; exit 1; }
    mv "$PARAMS.candidate" "$PARAMS"; echo "Parameter uebernommen. Neustart mit: $0 start" ;;
  paper)
    ensure_env; set_env FREQTRADE__DRY_RUN true; $DC up -d --force-recreate; echo "Modus: $(mode)" ;;
  live)
    ensure_env
    KEY=$(grep '^FREQTRADE__EXCHANGE__KEY=' "$MAIN_ENV" 2>/dev/null | cut -d= -f2- || true)
    SECRET=$(grep '^FREQTRADE__EXCHANGE__SECRET=' "$MAIN_ENV" 2>/dev/null | cut -d= -f2- || true)
    [ -z "$(get_env FREQTRADE__EXCHANGE__KEY)" ] && [ -n "$KEY" ] && set_env FREQTRADE__EXCHANGE__KEY "$KEY" && set_env FREQTRADE__EXCHANGE__SECRET "$SECRET"
    [ -n "$(get_env FREQTRADE__EXCHANGE__KEY)" ] || { echo "Kein Binance-Key gefunden (weder $ENVF noch $MAIN_ENV)."; exit 1; }
    set_env FREQTRADE__DRY_RUN false; rm -f user_data/KILL; $DC up -d --force-recreate; echo "Modus: $(mode)" ;;
  *) sed -n '2,5p' "$0"; exit 1 ;;
esac
