#!/usr/bin/env bash
# Ali Trading Bot – Ein-Befehl-Installation für den VPS
set -euo pipefail

REPO="https://github.com/Erste-Hilfe-Hero/ali-trading-bot.git"
BRANCH="main"
SRC="$HOME/ali-trading-bot-src"
DIR="$SRC"

echo "== Ali Trading Bot Installation =="

# 1. Docker installieren, falls nicht vorhanden
if ! command -v docker >/dev/null 2>&1; then
  echo "-> Installiere Docker ..."
  curl -fsSL https://get.docker.com | sh
fi
if ! command -v git >/dev/null 2>&1; then
  echo "-> Installiere git ..."
  (apt-get update -y && apt-get install -y git) || (sudo apt-get update -y && sudo apt-get install -y git)
fi

# 2. Code holen oder aktualisieren
if [ -d "$SRC/.git" ]; then
  echo "-> Aktualisiere Bot ..."
  git -C "$SRC" pull --ff-only
else
  echo "-> Lade Bot ..."
  git clone --depth 1 -b "$BRANCH" "$REPO" "$SRC"
fi
cd "$DIR"

# Immer die frisch geholte Version aus dem Repo ausfuehren, nicht eine evtl. veraltete Download-Kopie
if [ -z "${ALI_REEXEC:-}" ]; then
  export ALI_REEXEC=1
  exec bash "$DIR/install.sh" "$@"
fi

mkdir -p user_data/logs
# Container laeuft intern als anderer Benutzer -> Schreibrechte fuer user_data
chmod -R a+rwX user_data 2>/dev/null || true

# 3. .env anlegen (nur beim ersten Mal)
if [ ! -f .env ]; then
  cp .env.example .env
  chmod 600 .env
fi

set_env() {
  if grep -q "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env; else echo "$1=$2" >> .env; fi
}

# Telegram: aus Umgebung (GitHub-Secrets) oder interaktiv, falls noch nicht gesetzt
if [ -z "${TG_TOKEN:-}" ] && ! grep -q '^FREQTRADE__TELEGRAM__TOKEN=.' .env; then
  echo "Telegram einrichten (Enter drücken zum Überspringen):"
  read -r -p "  Telegram-Bot-Token von @BotFather: " TG_TOKEN < /dev/tty || true
  read -r -p "  Deine Chat-ID von @userinfobot:    " TG_CHAT < /dev/tty || true
fi
if [ -n "${TG_TOKEN:-}" ] && [ -n "${TG_CHAT:-}" ]; then
  set_env FREQTRADE__TELEGRAM__TOKEN "$TG_TOKEN"
  set_env FREQTRADE__TELEGRAM__CHAT_ID "$TG_CHAT"
  echo "-> Telegram eingerichtet"
fi
if grep -q '^FREQTRADE__TELEGRAM__TOKEN=.' .env; then
  set_env FREQTRADE__TELEGRAM__ENABLED true
else
  set_env FREQTRADE__TELEGRAM__ENABLED false
  echo "  (Telegram ist aus.)"
fi

# Binance-Zugang (aus GitHub-Secrets)
if [ -n "${BINANCE_KEY:-}" ] && [ -n "${BINANCE_SECRET:-}" ]; then
  set_env FREQTRADE__EXCHANGE__KEY "$BINANCE_KEY"
  set_env FREQTRADE__EXCHANGE__SECRET "$BINANCE_SECRET"
  echo "-> Binance-Zugang eingerichtet"
fi

# Echtgeld nur, wenn LIVE_TRADING=true gesetzt ist UND ein Binance-Key vorhanden ist
MODE="TESTMODUS (kein echtes Geld)"
LIVE_NORM=$(printf "%s" "${LIVE_TRADING:-}" | tr -d "[:space:]" | tr "[:upper:]" "[:lower:]")
if [ "$LIVE_NORM" = "true" ] && grep -q '^FREQTRADE__EXCHANGE__KEY=.' .env; then
  set_env FREQTRADE__DRY_RUN false
  MODE="ECHTGELD"
else
  set_env FREQTRADE__DRY_RUN true
fi

# 4. Starten
echo "-> Starte Bot im Modus: $MODE ..."
docker compose pull
docker compose up -d --force-recreate

echo
echo "Fertig. Der Bot läuft im Modus: $MODE"
echo "Logs ansehen:   cd $DIR && docker compose logs -f"
echo "Telegram:       schreib deinem Bot /status"
