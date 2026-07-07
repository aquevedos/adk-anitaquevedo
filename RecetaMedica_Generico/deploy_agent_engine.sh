#!/usr/bin/env bash
# Copyright 2026 Google LLC
# Script de construcción y despliegue para Google Cloud Agent Engine (Gemini Enterprise)

set -e

PROJECT_ID="agentspace-demos-466121"
REGION="us-central1"
SERVICE_NAME="agent-engine-arrocha"

echo "=== Iniciando Despliegue en Google Cloud Agent Engine ==="
echo "Proyecto: $PROJECT_ID"
echo "Región: $REGION"
echo "Servicio: $SERVICE_NAME"

# 1. Desplegar contenedor en Cloud Run habilitado para invocación desde Agent Engine
gcloud run deploy "$SERVICE_NAME" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --source=agent_engine_app/ \
    --memory=1024Mi \
    --cpu=1 \
    --allow-unauthenticated \
    --set-env-vars GOOGLE_CLOUD_PROJECT="$PROJECT_ID",GOOGLE_CLOUD_LOCATION="$REGION",GEMINI_MODEL="gemini-2.5-pro"

echo "\n✅ ¡Despliegue exitoso! Tu agente ha sido desplegado en Agent Engine y está listo para integrarse con Gemini Enterprise."
