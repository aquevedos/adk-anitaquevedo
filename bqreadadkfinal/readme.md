Explicacion: 
Al conectarse a BQ hay dos formas: 
https://cloud.google.com/blog/products/ai-machine-learning/bigquery-meets-google-adk-and-mcp

    A. https://google.github.io/adk-docs/tools/built-in-tools/#bigquery
    B. MCP https://googleapis.github.io/genai-toolbox/resources/tools/bigquery/




pasos a realizar:
gcloud config set project 	agentspace-demos-466121
sudo add-apt-repository universe
sudo apt update
sudo apt install python3.12-venv
python3.12 -m venv .venv
source .venv/bin/activate


pip install -r requirements.txt

gcloud auth application-default login
adk web


adk deploy agent_engine data_agent \
--project=agentspace-demos-466121 \
--region=us-central1 \
--staging_bucket=gs://adk-anitaquevedo-2 \
--display_name "agent bigquery final" 



gcloud beta run services add-iam-policy-binding --region=us-central1 --member=allUsers --role=roles/run.invoker mi-agente-adk


adk deploy cloud_run \
    --project=agentspace-demos-466121 \
    --region=us-central1 \
--service_name=data_agent \
--app_name=agent_bigquery \
--with_ui data_agent