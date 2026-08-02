#!/usr/bin/env bash
# Script para iniciar la Plataforma e Interfaz Gráfica del Agente de Gobierno de Datos Híbrido y Multi-Cloud

PORT=${PORT:-8085}
HOST=${HOST:-0.0.0.0}

echo "================================================================="
echo "🛡️  Iniciando Agente Inteligente de Gobierno de Datos Multi-Cloud"
echo "🌐  Servidor: http://${HOST}:${PORT}"
echo "📚  Motores: Knowledge Catalog • Dataplex • Cloud DLP (SDP)"
echo "================================================================="

cd "$(dirname "$0")"
uv run uvicorn backend.app:app --host "$HOST" --port "$PORT" --reload
