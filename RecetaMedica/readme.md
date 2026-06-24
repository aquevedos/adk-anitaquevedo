crea un agente en la carpeta 2026/RecetaMedica , hecho con ADK para que pueda extraer los campos que estan siguiendo las buenas practicas de ADK, la data que extraigas del los pdf tienenes que guardarlo en Bigquery en una tabla con un dataset que diga recetamedicas en el proyecto, 	agentspace-demos-466121

cd /Users/anitaquevedo/2026/RecetaMedica
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt


python main.py
kill -9 $(lsof -ti:8000)


gcloud auth login
gcloud config set project agentspace-demos-466121
gcloud auth application-default login
gcloud auth application-default set-quota-project agentspace-demos-466121
gcloud config set billing/quota_project agentspace-demos-466121

pip install --upgrade google-genai
pip install --upgrade google-cloud-aiplatform grpcio google-auth



Se refactorizó /api/procesar_lote en 
web_app.py
 utilizando el módulo asyncio.
Se sustituyó el flujo secuencial por procesamiento concurrente mediante asyncio.gather y client.aio.models.generate_content.

chmod +x deploy_cloud_run_function.sh
bash deploy_cloud_run_function.sh



gcloud functions deploy procesar-receta-arrocha \
    --project=agentspace-demos-466121 \
    --gen2 \
    --runtime=python311 \
    --region=us-central1 \
    --source=. \
    --entry-point=procesar_receta_http \
    --trigger-http \
    --allow-unauthenticated \
    --set-env-vars GOOGLE_CLOUD_PROJECT=agentspace-demos-466121,GOOGLE_CLOUD_LOCATION=us-central1,GEMINI_MODEL=gemini-2.5-pro



bash deploy_agent_engine.sh
