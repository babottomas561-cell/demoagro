#!/bin/bash
# Script para refrescar el cache de APIs externas
# Uso: ./scripts/refresh_cache.sh [fuente]
# Ejemplo: ./scripts/refresh_cache.sh bcra
# Ejemplo: ./scripts/refresh_cache.sh all

BASE_URL="${BACKEND_URL:-http://localhost:8000}"
FUENTE="${1:-all}"

echo ""
echo "══════════════════════════════════════════════"
echo "  AgroControl — Refresh de Cache Externo"
echo "══════════════════════════════════════════════"
echo ""

if [ "$FUENTE" = "all" ]; then
    echo "  Refrescando todas las fuentes..."
    curl -s -X POST "$BASE_URL/api/cache/refresh" | python3 -m json.tool
else
    echo "  Refrescando fuente: $FUENTE"
    curl -s -X POST "$BASE_URL/api/cache/refresh/$FUENTE" | python3 -m json.tool
fi

echo ""
echo "  Estado actual del cache:"
curl -s "$BASE_URL/api/cache/status" | python3 -m json.tool
echo ""
