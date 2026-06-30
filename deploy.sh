#!/usr/bin/env bash
#
# Script de deploy del bot de Cuentitas en la VPS.
# Trae los últimos cambios de git, reconstruye la imagen y levanta los contenedores.
#
# Requiere que OpenWA ya esté corriendo (crea la red externa "openwa-network").
# El bot le pega a la API de Cuentitas por internet (CUENTITAS_API_URL), no por
# la red Docker: los dos stacks son independientes.
#
# Uso:
#   ./deploy.sh   -> git pull + build + up
#
set -euo pipefail

# Pararse siempre en la carpeta del script, sin importar desde dónde se ejecute.
cd "$(dirname "$0")"

echo "==> 1/3  Trayendo los últimos cambios de git..."
git pull --ff-only

if [ ! -f .env ]; then
  echo ""
  echo "ERROR: falta el archivo .env."
  echo "Copiá la plantilla y completá los valores antes de deployar:"
  echo "    cp .env.example .env && nano .env"
  echo "Clave: BOT_API_KEY (igual que la de Cuentitas), LLM_API_KEY (OpenRouter),"
  echo "CUENTITAS_API_URL y, para WhatsApp, OPENWA_* + WEBHOOK_SECRET."
  exit 1
fi

echo "==> 2/3  Construyendo y levantando contenedores..."
docker compose up -d --build

echo "==> 2.5  Limpiando imágenes viejas..."
docker image prune -f >/dev/null 2>&1 || true

echo "==> 3/3  Estado de los contenedores:"
docker compose ps

echo ""
echo "Listo. El bot quedó corriendo y escuchando el webhook de OpenWA."
