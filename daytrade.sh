#!/usr/bin/env bash
# Daytrader steuern:
#   start | stop | kill | unkill | status | logs | report
#   backtest [tage] [strategie] | select [tage] | suggest [tage] | use <strategie> | check [tage]
#   hyperopt [tage] [epochen] | apply-params | learn [tage] [epochen]
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
STRATEGIES="DaytradeMomentum DaytradeConfluence DaytradeMeanRevert DaytradeBreakout DaytradeTrend15m DaytradeRsi2 DaytradeVwapBounce DaytradeSqueeze DaytradeMacdCross DaytradeSupertrend DaytradeHeikinAshi DaytradeStochRsi DaytradeEmaRibbon"
STRAT_FILE=user_data/daytrade-strategy.txt
STRATEGY=$(cat "$STRAT_FILE" 2>/dev/null || echo DaytradeConfluence)
export DT_STRATEGY="$STRATEGY"
PARAMS="user_data/strategies/$STRATEGY.json"
RUN="docker run --rm -v $PWD/user_data:$UD $FT_IMG"

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

# Gesamtgewinn (Anteil) des letzten Backtests einer Strategie
last_profit() {
  docker run --rm -v "$PWD/user_data:$UD" --entrypoint python3 "$FT_IMG" -c \
    "from freqtrade.data.btanalysis import load_backtest_stats as l; print(l('$UD/backtest_results')['strategy']['$1']['profit_total'])"
}

bt() {  # bt <strategie> <timerange> [extra args]
  local st="$1" tr="$2"; shift 2
  $RUN backtesting $BT_CFG --strategy "$st" --timerange "$tr" --cache none "$@" 2>&1 | grep -vE " - INFO - |━━" | tail -45
  echo "ERGEBNIS $st: $(last_profit "$st")"
}

rank() {  # rank <tage>: testet alle Strategien, setzt BEST/BESTP/PCUR
  local days="$1" tr st p
  download "$days"; tr="$(date -u -d "-${days} days" +%Y%m%d)-"; BEST=""; BESTP=-9; PCUR=-9
  for st in $STRATEGIES; do
    bt "$st" "$tr" >/dev/null; p=$(last_profit "$st"); echo "$st: $p"
    if python3 -c "import sys; sys.exit(0 if $p > $BESTP else 1)"; then BEST=$st; BESTP=$p; fi
    [ "$st" = "$STRATEGY" ] && PCUR=$p
  done
}

mode() { [ "$(get_env FREQTRADE__DRY_RUN)" = "false" ] && echo "ECHTGELD" || echo "TESTMODUS"; }

case "${1:-status}" in
  start)
    ensure_env; rm -f user_data/KILL; $DC pull; $DC up -d --force-recreate
    echo "Modus: $(mode)" ;;
  stop)   $DC stop ;;
  kill)   touch user_data/KILL; echo "Kill-Switch aktiv: keine neuen Trades, offene werden verkauft." ;;
  unkill) rm -f user_data/KILL; echo "Kill-Switch aus." ;;
  status) $DC ps; echo "Modus: $(mode)  Strategie: $STRATEGY"; tail -n 30 user_data/logs/daytrade.log 2>/dev/null || true ;;
  logs)   $DC logs -f --tail 100 ;;
  report)
    echo "Modus: $(mode)  Strategie: $STRATEGY"; [ -f user_data/KILL ] && echo "Kill-Switch: AKTIV"
    [ -f user_data/daytrade-suggestion.txt ] && echo "VORSCHLAG: $(cat user_data/daytrade-suggestion.txt)"
    echo "== Gewinn gesamt";   api profit | python3 -m json.tool
    echo "== Letzte 7 Tage";   api "daily?timescale=7" | python3 -m json.tool
    echo "== Offene Trades";   api status | python3 -m json.tool
    echo "== Kontostand";      api balance | python3 -c 'import json,sys; b=json.load(sys.stdin); print(b["total"], b["stake"])' ;;
  backtest)
    DAYS="${2:-30}"; ST="${3:-$STRATEGY}"; ensure_env; download "$DAYS"
    bt "$ST" "$(date -u -d "-${DAYS} days" +%Y%m%d)-" --breakdown day ;;
  select)
    # Nur Rangliste, aendert nichts
    ensure_env; rank "${2:-30}"; echo "BESTE=$BEST GEWINN=$BESTP AKTIV=$STRATEGY GEWINN=$PCUR" ;;
  suggest)
    # Prueft alle Strategien und schreibt einen Vorschlag, wenn die beste im Plus und mindestens
    # 1 Prozentpunkt besser als die aktive ist. Gewechselt wird erst nach Alis Bestaetigung (use).
    ensure_env; rank "${2:-30}"
    MSG="$(date -u +%F) aktiv=$STRATEGY ($PCUR) beste=$BEST ($BESTP)"
    if [ "$BEST" != "$STRATEGY" ] && python3 -c "import sys; sys.exit(0 if $BESTP > max($PCUR, 0) + 0.01 else 1)"; then
      echo "$MSG" > user_data/daytrade-suggestion.txt; echo "VORSCHLAG: $MSG" | tee -a user_data/logs/learn.log
    else
      rm -f user_data/daytrade-suggestion.txt; echo "kein Wechsel: $MSG" | tee -a user_data/logs/learn.log
    fi ;;
  use)
    # use <strategie>: wechselt die aktive Strategie (nach Alis Bestaetigung), Modus bleibt
    case " $STRATEGIES " in *" ${2:-} "*) ;; *) echo "Unbekannte Strategie: ${2:-}"; exit 1 ;; esac
    echo "$2" > "$STRAT_FILE"; export DT_STRATEGY="$2"; rm -f user_data/daytrade-suggestion.txt
    $DC up -d --force-recreate; echo "Modus: $(mode)  Strategie: $2" ;;
  hyperopt)
    # Optimiert auf den ersten 2/3 des Zeitraums, prueft danach auf dem letzten Drittel,
    # das der Optimierer nie gesehen hat. Ergebnis wird nur ein Vorschlag (apply-params).
    DAYS="${2:-90}"; EPOCHS="${3:-300}"; ensure_env; download "$DAYS"
    START=$(date -u -d "-${DAYS} days" +%Y%m%d)
    SPLIT=$(date -u -d "-$((DAYS / 3)) days" +%Y%m%d)
    [ -f "$PARAMS" ] && mv "$PARAMS" "$PARAMS.active"
    $RUN hyperopt $BT_CFG --strategy "$STRATEGY" --spaces buy --hyperopt-loss SharpeHyperOptLossDaily \
      -e "$EPOCHS" --timerange "${START}-${SPLIT}" -j 2
    echo "== Test auf ungesehenen Daten (${SPLIT} bis heute)"
    bt "$STRATEGY" "${SPLIT}-"
    [ -f "$PARAMS" ] && mv "$PARAMS" "$PARAMS.candidate"
    [ -f "$PARAMS.active" ] && mv "$PARAMS.active" "$PARAMS"
    echo "Vorschlag gespeichert in $PARAMS.candidate. Uebernehmen mit: $0 apply-params" ;;
  check)
    # Prueft die Strategie auf Blick-in-die-Zukunft-Fehler (Lookahead) und instabile Indikatoren
    DAYS="${2:-30}"; ensure_env; download "$DAYS"
    TR="$(date -u -d "-${DAYS} days" +%Y%m%d)-"
    docker run --rm -v "$PWD/user_data:$UD" "$FT_IMG" lookahead-analysis $BT_CFG --strategy "$STRATEGY" --timerange "$TR"
    docker run --rm -v "$PWD/user_data:$UD" "$FT_IMG" recursive-analysis $BT_CFG --strategy "$STRATEGY" --timerange "$TR" ;;
  learn)
    # Selbstlernen: optimiert die Einstiegsfilter auf 2/3 der Daten und uebernimmt sie nur,
    # wenn sie auf dem letzten Drittel (ungesehen) besser sind als die aktuellen UND im Plus.
    # Risikowerte (daytrade-risk.json), Kill-Switch und "kein Hebel" fasst das nie an.
    DAYS="${2:-90}"; EPOCHS="${3:-300}"; ensure_env; download "$DAYS"
    START=$(date -u -d "-${DAYS} days" +%Y%m%d); SPLIT=$(date -u -d "-$((DAYS / 3)) days" +%Y%m%d)
    bt "$STRATEGY" "${SPLIT}-" >/dev/null; P0=$(last_profit "$STRATEGY")
    [ -f "$PARAMS" ] && cp "$PARAMS" "$PARAMS.active"
    $RUN hyperopt $BT_CFG --strategy "$STRATEGY" --spaces buy --hyperopt-loss SharpeHyperOptLossDaily \
      -e "$EPOCHS" --timerange "${START}-${SPLIT}" -j 2 2>&1 | grep -vE " - INFO - " | tail -20
    bt "$STRATEGY" "${SPLIT}-" >/dev/null; P1=$(last_profit "$STRATEGY")
    MSG="$(date -u +%F) $STRATEGY ungesehen: aktuell=$P0 neu=$P1"
    if python3 -c "import sys; sys.exit(0 if $P1 > max($P0, 0) else 1)"; then
      rm -f "$PARAMS.active"; echo "$MSG -> uebernommen" | tee -a user_data/logs/learn.log
      $DC up -d --force-recreate
    else
      if [ -f "$PARAMS.active" ]; then mv "$PARAMS.active" "$PARAMS"; else rm -f "$PARAMS"; fi
      echo "$MSG -> verworfen" | tee -a user_data/logs/learn.log
    fi ;;
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
