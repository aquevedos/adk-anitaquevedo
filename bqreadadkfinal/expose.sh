#buscar que el agent AI Platform Reasoning Engine Service Agent  , 
#@gcp-sa-aiplatform-re.iam.gserviceaccount.com
  #debera tener storage admin, bigquery admin,  vertex ai user, bigquery metadata viewer
  #https://cloud.google.com/generative-ai-app-builder/docs/locations?hl=es-419

export PROJECT_ID="agentspace-demos-466121" # String 
export PROJECT_NUMBER="697254066228" # String 

export REASONING_ENGINE_ID="5479178702510096384" # String - Normally a 18-digit number
export REASONING_ENGINE_LOCATION="us-central1" # String - e.g. us-central1
export REASONING_ENGINE="projects/${PROJECT_ID}/locations/${REASONING_ENGINE_LOCATION}/reasoningEngines/${REASONING_ENGINE_ID}"


export AS_APP="agentspace-demos_1755096718053" # String - Find it in Google Cloud AI Applications
export AS_LOCATION="global" # String - e.g. global, eu, us

export AGENT_DISPLAY_NAME="demo-final-bq con memory" # String - this will appear as the name of the agent into your AgentSpace
AGENT_DESCRIPTION=$(cat <<EOF
Un agente que traduce preguntas en lenguaje natural a consultas SQL.
Entiende la consulta del usuario, genera el SQL apropiado,
lo revisa y lo reescribe para garantizar su precisión,
lo ejecuta e incluso puede generar gráficos a partir de los resultados.
EOF
)
export AGENT_DESCRIPTION

DISCOVERY_ENGINE_PROD_API_ENDPOINT="https://discoveryengine.googleapis.com"

deploy_agent_to_agentspace () {
  curl -X POST \
        -H "Authorization: Bearer $(gcloud auth print-access-token)" \
        -H "Content-Type: application/json" \
        -H "x-goog-user-project: ${PROJECT_ID}" \
        ${DISCOVERY_ENGINE_PROD_API_ENDPOINT}/v1alpha/projects/${PROJECT_NUMBER}/locations/${AS_LOCATION}/collections/default_collection/engines/${AS_APP}/assistants/default_assistant/agents \
        -d '{
      "displayName": "'"${AGENT_DISPLAY_NAME}"'",
      "description": "'"${AGENT_DESCRIPTION}"'",
      "icon": {
        "uri": "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/corporate_fare/default/24px.svg"
      },
      "adk_agent_definition": {
        "tool_settings": {
          "toolDescription": "'"${AGENT_DESCRIPTION}"'",
        },
        "provisioned_reasoning_engine": {
          "reasoningEngine": "'"${REASONING_ENGINE}"'"
        },
      }
    }'
}




list_agents_in_agentspace() {
    echo "Listing agents in AgentSpace..."
    curl -X GET \
        -H "Authorization: Bearer $(gcloud auth print-access-token)" \
        -H "Content-Type: application/json" \
        -H "x-goog-user-project: ${PROJECT_ID}" \
        "${DISCOVERY_ENGINE_PROD_API_ENDPOINT}/v1alpha/projects/${PROJECT_NUMBER}/locations/${AS_LOCATION}/collections/default_collection/engines/${AS_APP}/assistants/default_assistant/agents"
}


# Para usar las funciones, descomenta la que necesites:
# Una vez que tengas el nombre del recurso del agente que quieres borrar (del comando anterior),
# descomenta y edita la siguiente línea con el nombre correcto:


delete_agent_from_agentspace() {
    #if [ -z "$1" ]; then
    #    echo "Error: Debes proporcionar el nombre completo del recurso del agente a eliminar."
    #    echo "Ejemplo: projects/${PROJECT_NUMBER}/locations/${AS_LOCATION}/collections/default_collection/engines/${AS_APP}/assistants/default_assistant/agents/${REASONING_ENGINE_ID}"
    #    return 1
    #fi

    AGENT_RESOURCE_NAME=projects/${PROJECT_NUMBER}/locations/${AS_LOCATION}/collections/default_collection/engines/${AS_APP}/assistants/default_assistant/agents/8942238862502305948
    #echo "Deleting agent: ${AGENT_RESOURCE_NAME}"



    curl -X DELETE \
        -H "Authorization: Bearer $(gcloud auth print-access-token)" \
        -H "Content-Type: application/json" \
        -H "x-goog-user-project: ${PROJECT_ID}" \
        "${DISCOVERY_ENGINE_PROD_API_ENDPOINT}/v1alpha/${AGENT_RESOURCE_NAME}"
}
#
#deploy_agent_to_agentspace
#list_agents_in_agentspace
delete_agent_from_agentspace 

#"projects/288743223172/locations/global/collections/default_collection/engines/agentspace-analysis_1743518693470/assistants/default_assistant/agents/13950714762542804936"

