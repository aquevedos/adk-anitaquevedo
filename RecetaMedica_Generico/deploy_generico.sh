#!/usr/bin/env bash
# Script de despliegue para Google Cloud Run Functions (2nd Gen) - Genérico

set -e

PROJECT_ID="agentspace-demos-466121"
REGION="us-central1"
FUNCTION_NAME="procesar-receta-generico"

echo "=== Iniciando Despliegue en Google Cloud Run Functions (2nd Gen) - Genérico ==="
echo "Proyecto: $PROJECT_ID"
echo "Región: $REGION"
echo "Función: $FUNCTION_NAME"

gcloud functions deploy "$FUNCTION_NAME" \
    --project="$PROJECT_ID" \
    --gen2 \
    --runtime=python311 \
    --region="$REGION" \
    --memory=1024MB \
    --cpu=1 \
    --timeout=300 \
    --source=. \
    --entry-point=procesar_receta_http \
    --trigger-http \
    --allow-unauthenticated \
    --set-build-env-vars GOOGLE_FUNCTION_SOURCE="cloud_function.py" \
    --set-env-vars GOOGLE_CLOUD_PROJECT="$PROJECT_ID",GOOGLE_CLOUD_LOCATION="$REGION",GEMINI_MODEL="gemini-2.5-pro",GOOGLE_FUNCTION_SOURCE="cloud_function.py"

echo "\n✅ ¡Despliegue exitoso! Tu nueva Cloud Run Function genérica está lista para atender peticiones HTTP."
