#!/bin/bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Configuración por defecto del despliegue
FUNCTION_NAME="procesar-receta-quevedo"
PROJECT_ID="agentspace-demos-466121"
REGION="us-central1"
RUNTIME="python311"
ENTRY_POINT="procesar_receta_http"

echo "================================================================="
echo "   Despliegue de Cloud Run Function (2nd Gen) - Portal Médico"
echo "================================================================="
echo "Nombre de Función: $FUNCTION_NAME"
echo "Proyecto GCP:      $PROJECT_ID"
echo "Región:            $REGION"
echo "Entorno de Ejec.:  $RUNTIME"
echo "Entry Point:       $ENTRY_POINT"
echo "================================================================="
echo ""

# Verificar si gcloud está instalado
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI no está instalado en el sistema."
    echo "Por favor instálelo antes de continuar: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Configurar el proyecto de gcloud
echo "⚙️ Configurando el proyecto GCP '$PROJECT_ID' en gcloud..."
gcloud config set project $PROJECT_ID

if [ $? -ne 0 ]; then
    echo "❌ Error al configurar el proyecto en gcloud."
    exit 1
fi

# Confirmar despliegue
read -p "¿Desea continuar con el despliegue? (s/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "🛑 Despliegue cancelado por el usuario."
    exit 0
fi

echo "🚀 Desplegando función en Google Cloud..."
gcloud functions deploy $FUNCTION_NAME \
    --project=$PROJECT_ID \
    --gen2 \
    --runtime=$RUNTIME \
    --region=$REGION \
    --source=. \
    --entry-point=$ENTRY_POINT \
    --trigger-http \
    --allow-unauthenticated \
    --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION,GEMINI_MODEL=gemini-2.5-pro,PORTAL_USERNAME=admin,PORTAL_PASSWORD=admin,PORTAL_SESSION_TOKEN=admin_session_token

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ ¡Despliegue completado con éxito!"
    echo "Busca la URL HTTPS del disparador en el resumen de gcloud superior."
else
    echo ""
    echo "❌ Error durante el despliegue de la función."
    exit 1
fi
