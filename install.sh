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
mkdir -p user_data/logs

# 3. .env anlegen (nur beim ersten Mal)
if [ ! -f .env ]; then
  cp .env.example .env
  echo
  echo "Telegram einrichten (Enter drücken zum Überspringen):"
  read -r -p "  Telegram-Bot-Token von @BotFather: " TG_TOKEN < /dev/tty || true
  read -r -p "  Deine Chat-ID von @userinfobot:    " TG_CHAT < /dev/tty || true
  sed -i "s|^FREQTRADE__TELEGRAM__TOKEN=.*|FREQTRADE__TELEGRAM__TOKEN=${TG_TOKEN:-}|" .env
  sed -i "s|^FREQTRADE__TELEGRAM__CHAT_ID=.*|FREQTRADE__TELEGRAM__CHAT_ID=${TG_CHAT:-}|" .env
  if [ -z "${TG_TOKEN:-}" ]; then
    sed -i 's/"enabled": true/"enabled": false/' user_data/config.json
    echo "  (Telegram ist aus. Später in .env eintragen und in user_data/config.json enabled auf true setzen.)"
  fi
  chmod 600 .env
fi

# 4. Starten (Testmodus, kein echtes Geld)
echo "-> Starte Bot im Testmodus ..."
docker compose pull
docker compose up -d

echo
echo "Fertig. Der Bot läuft im TESTMODUS (kein echtes Geld)."
echo "Logs ansehen:   cd $DIR && docker compose logs -f"
echo "Telegram:       schreib deinem Bot /status"
