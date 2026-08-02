# MCP Toolbox

Guía del operador para el sidecar de MCP Toolbox que gestiona el acceso auxiliar a datos para `data-agent-kc`.

## Qué es esto

Un servicio independiente de Cloud Run que ejecuta la imagen oficial de [MCP Toolbox](https://googleapis.github.io/genai-toolbox/). El agente (desplegado en Vertex AI Agent Engine) lo invoca a través de HTTPS para **acceso a GCS y futuras fuentes** que no cuenten con una ruta dedicada. **La ejecución de SQL para BigQuery se mantiene en la ruta directa de CA**: MCP únicamente proporciona *introspección* de BigQuery (listar datasets/tablas, obtener esquemas) y solo cuando el agente se despliega con `DATAPLEX_ENABLED=false`. **Dataplex nunca pasa a través de MCP**. Consulta [Por qué el MCP de este proyecto está delimitado de esta manera](#por-que-el-mcp-de-este-proyecto-esta-delimitado-de-esta-manera) a continuación.

La autenticación utiliza dos cabeceras; la segunda está reservada para futura delegación de usuario final:

```
                Authorization: Bearer <Google ID token de la SA del agente>   ← Barrera IAM de Cloud Run
                X-Goog-User-Authorization: Bearer <token del usuario final>   ← Reservado (ver gobernanza)

Usuario Final ──► Agente (Vertex AI Agent Engine) ──► MCP Toolbox (Cloud Run) ──► GCS / Spanner / ...
```

La configuración de la toolbox (`tools.yaml`) se compone en el momento del despliegue a partir de fragmentos YAML por fuente en [`sources/`](sources/), guiada por [`manifest.yaml`](manifest.yaml). El YAML compuesto reside en Secret Manager (`toolbox-tools-config`) y se monta dentro del contenedor en `/app/tools.yaml`.

## Por qué el MCP de este proyecto está delimitado de esta manera

El agente interactúa con tres sistemas de datos principales y la ruta de acceso adecuada para cada uno es diferente:

Sistema                                          | Ruta utilizada                                                 | Por qué
----------------------------------------------- | -------------------------------------------------------------- | ---
BigQuery (ejecución de SQL)                        | **BigQuery CA** (`call_bigquery_ca` → API geminidataanalytics) | CA es una capa analítica que realiza NL→SQL→ejecutar→insights en una sola llamada. `bigquery-execute-sql` de MCP reemplazaría el valor añadido de CA con una primitiva de nivel inferior. CA también acepta el token OAuth del usuario en la cabecera `Authorization`, brindándonos una ruta limpia de delegación una vez que ADK exponga la identidad del usuario.
BigQuery (descubrimiento, solo cuando Dataplex está desactivado) | **MCP `bigquery_list_*` / `bigquery_get_table_info`**          | Cuando `DATAPLEX_ENABLED=false`, el agente pierde `dataplex_search` como ruta de descubrimiento. El LLM todavía necesita encontrar tablas antes de entregarlas a CA (que requiere referencias explícitas a tablas). Las herramientas de introspección cubren exactamente esa brecha. La ejecución se mantiene en la ruta de CA; consulta [`sources/bigquery.yaml`](sources/bigquery.yaml) para saber por qué `bigquery-execute-sql` se excluye deliberadamente.
Dataplex                                        | **SDK directo `dataplex_v1`** (`dataplex_utils.py`)             | Mantiene el patrón `tool_context.auth` → credenciales de usuario o ADC. Cuando ADK completa `ToolContext.auth` con la identidad del usuario final, cada llamada a Dataplex se ejecuta automáticamente como el usuario. La fuente Dataplex de MCP no soporta `useClientOAuth` en upstream actualmente, por lo que enrutar a través de MCP *impediría* activamente la delegación por usuario.
GCS / futuras fuentes (Spanner, etc.)            | **Esta MCP Toolbox**                                           | Sin ruta directa dedicada. La extensibilidad guiada por manifiestos (añadir un YAML y redesplegar) es exactamente lo que se busca para incorporar nuevas capacidades auxiliares. Hoy en día funcionan exclusivamente con cuenta de servicio (SA) en la capa de datos, lo cual es aceptable para escenarios de exploración/lectura.

Cuando el proyecto MCP upstream añada `useClientOAuth` a más fuentes, o cuando los servidores MCP alojados de Google (por ejemplo, [Dataplex Remote MCP](https://docs.cloud.google.com/dataplex/docs/use-remote-mcp)) alcancen disponibilidad general (GA) y cubran nuestras necesidades, esta división se podrá revisar.

## Fuentes iniciales (Day-1)

Fuente     | Herramientas                                                                                                        | Variables de entorno requeridas                      | Permisos IAM otorgados a la SA de la toolbox
---------- | ------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- | -------------------------
`gcs`      | `gcs_list_buckets`, `gcs_list_objects`, `gcs_read_object`                                                           | `PROJECT_ID` (automático)                            | `storage.objectViewer`
`bigquery` | `bigquery_list_datasets`, `bigquery_list_tables`, `bigquery_get_table_info` (solo introspección, sin ejecución SQL) | `PROJECT_ID` (automático)                            | `bigquery.metadataViewer`
`spanner`  | *se entrega deshabilitado* — consulta [Reactivar Spanner](#reactivar-spanner)                                       | `PROJECT_ID`, `SPANNER_INSTANCE`, `SPANNER_DATABASE` | `spanner.databaseUser`, `spanner.viewer`

La cuenta de servicio de la toolbox siempre recibe `roles/secretmanager.secretAccessor` para el secreto de configuración.

### Selección de manifiesto

Se incluyen dos manifiestos y el correcto se **selecciona automáticamente a partir de `DATAPLEX_ENABLED`**; normalmente no es necesario pasar `MANIFEST=` manualmente.

El agente se despliega con…          | Manifiesto seleccionado automáticamente                  | Qué habilita
------------------------------------ | -------------------------------------------------------- | ---------------
`DATAPLEX_ENABLED=true` (por defecto)| [`manifest.yaml`](manifest.yaml)                         | Solo GCS: `dataplex_search` gestiona el descubrimiento de tablas, por lo que la fuente de introspección de BigQuery se entrega deshabilitada.
`DATAPLEX_ENABLED=false`             | [`manifest-no-dataplex.yaml`](manifest-no-dataplex.yaml) | GCS + introspección de BigQuery: el LLM usa `bigquery_list_*` / `bigquery_get_table_info` para encontrar tablas antes de entregarlas a `call_bigquery_ca`.

```bash
# Predeterminado (Dataplex activado):
make deploy-all

# Variante sin Dataplex — una sola bandera cambia ambos lados:
make deploy-all VARIANT=no-kc DATAPLEX_ENABLED=false
```

Pasa un `MANIFEST=ruta/a/personalizado.yaml` explícito solo cuando requieras una combinación no predeterminada (por ejemplo, sin Dataplex Y con Spanner habilitado). El parámetro explícito `MANIFEST=` tiene prioridad sobre la selección automática.

## Despliegue

Requisitos previos: `gcloud auth application-default login` y `gcloud auth login`.

**Configuración inicial** (un solo comando):

```bash
make deploy-all   # = make deploy-mcp + make deploy
```

Esto funciona porque `deploy-mcp` puede ejecutarse antes de que exista ningún agente: predice la SA de ejecución del agente a partir del número de proyecto (el patrón estándar de Google `service-{N}@gcp-sa-aiplatform-re.iam.gserviceaccount.com`) y le otorga permisos de invocador.

**Cambios posteriores**: un comando para la parte que haya cambiado.

```bash
make deploy-mcp   # tools.yaml o manifiesto modificado
make deploy       # código del agente modificado (selecciona automáticamente MCP_TOOLBOX_URL de los metadatos)
```

Lo que crea o actualiza `make deploy-mcp`:
1. APIs habilitadas: `run`, `secretmanager`, `iam`, más las APIs por fuente (`storage` hoy; `spanner` si está habilitado).
2. Cuenta de servicio `toolbox-identity@<project>.iam.gserviceaccount.com` con los roles IAM de `manifest.yaml`.
3. Secreto en Secret Manager `toolbox-tools-config` con una nueva versión que contiene el `tools.yaml` compuesto.
4. Servicio Cloud Run `data-agent-mcp-toolbox` (privado, solo con token de ID) ejecutando la imagen oficial de toolbox.
5. Permiso `roles/run.invoker` otorgado a la SA del agente (predicho en la primera ejecución; leído de `deployment_metadata.json` en ejecuciones posteriores).
6. `deployment_metadata.json` actualizado con `mcp_toolbox_url` y `mcp_toolbox_service_account`.

**Caso especial con SA personalizada**: si despliegas el agente con `--agent-identity` o `--service-account=<email>`, la SA predeterminada calculada no coincidirá. Vuelve a ejecutar `make deploy-mcp` una vez después de `make deploy`; en ese momento `deployment_metadata.json` tendrá la SA real y el permiso de invocador se transferirá a ella.

Verificar:

```bash
gcloud run services describe data-agent-mcp-toolbox --region us-central1 --format='value(status.url)'
URL=$(gcloud run services describe data-agent-mcp-toolbox --region us-central1 --format='value(status.url)')
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" "$URL/api/toolset"
```

El último comando debe devolver una lista JSON con las herramientas cargadas (3 herramientas de GCS, más si Spanner u otras fuentes están habilitadas).

### Limpieza única si actualizas desde un despliegue anterior

El script de despliegue añade permisos IAM de manera aditiva; nunca elimina vinculaciones obsoletas. Si tu SA `toolbox-identity` todavía conserva roles de un despliegue anterior que incluía ejecución en BigQuery (`roles/bigquery.user`) o Dataplex (`roles/dataplex.catalogViewer`), revócalos manualmente:

```bash
PROJECT=$(gcloud config get-value project)
SA="toolbox-identity@${PROJECT}.iam.gserviceaccount.com"
for role in roles/bigquery.user roles/dataplex.catalogViewer; do
  gcloud projects remove-iam-policy-binding "$PROJECT" \
    --member="serviceAccount:$SA" --role="$role" --quiet || true
done
```

(Nota: `roles/bigquery.metadataViewer` es necesario cuando la fuente `bigquery` está habilitada; no lo elimines si estás usando `manifest-no-dataplex.yaml`.)

Auditar después:

```bash
gcloud projects get-iam-policy "$PROJECT" --flatten=bindings --filter="bindings.members:toolbox-identity*"
```

Debe mostrar `roles/secretmanager.secretAccessor` + `roles/storage.objectViewer` (y `roles/bigquery.metadataViewer` si se usa el manifiesto sin dataplex, más los roles de Spanner si están habilitados).

## Añadir una nueva fuente

Tres pasos, sin modificaciones en Python. Ejemplo práctico: AlloyDB Postgres con autenticación IAM.

### Paso 1 — crear un fragmento de fuente

Crea [`sources/alloydb.yaml`](sources/) con la fuente MCP + herramientas + toolset:

```yaml
kind: source
name: alloydb-source
type: alloydb-postgres
project: ${PROJECT_ID}
cluster: ${ALLOYDB_CLUSTER}
instance: ${ALLOYDB_INSTANCE}
database: ${ALLOYDB_DATABASE}
user: ""  # vacío = autenticación IAM a través de la SA de la toolbox
---
kind: tool
name: alloydb_execute_sql
type: alloydb-postgres-execute-sql
source: alloydb-source
description: Execute SQL against the AlloyDB database.
---
kind: toolset
name: alloydb
tools:
  - alloydb_execute_sql
```

### Paso 2 — añadir una entrada en el manifiesto

Agrega al final de [`manifest.yaml`](manifest.yaml):

```yaml
  alloydb:
    enabled: true
    file: sources/alloydb.yaml
    iam_roles:
      - roles/alloydb.client
      - roles/serviceusage.serviceUsageConsumer
    required_env: [PROJECT_ID, ALLOYDB_CLUSTER, ALLOYDB_INSTANCE, ALLOYDB_DATABASE]
    apis: [alloydb.googleapis.com]
    description: AlloyDB Postgres access (IAM-authenticated)
```

### Paso 3 — desplegar

```bash
make deploy-mcp EXTRA_ENV="ALLOYDB_CLUSTER=my-cluster,ALLOYDB_INSTANCE=my-inst,ALLOYDB_DATABASE=my-db"
```

El script detecta el nuevo fragmento del manifiesto automáticamente: otorga los nuevos roles IAM a `toolbox-identity`, incluye el fragmento en el archivo compuesto `tools.yaml`, genera una nueva versión del secreto y redespliega. El agente cargará las nuevas herramientas en su próximo despliegue o reinicio.

**Nota de gobernanza**: la mayoría de las fuentes de MCP son **exclusivas de cuenta de servicio (SA)** hoy (`useClientOAuth` está implementado en upstream únicamente en la fuente de BigQuery). Si el cumplimiento de IAM por usuario final es un requisito para la nueva fuente, evalúalo cuidadosamente: consulta [Gobernanza de acceso](#gobernanza-de-acceso) a continuación.

## Referencia del esquema del manifiesto

Todos los campos excepto `enabled` y `file` son opcionales.

Campo               | Tipo      | Valor por defecto | Propósito
------------------- | --------- | ----------------- | -------
`enabled`           | bool      | requerido         | Cuando es `false`, la fuente se excluye de `tools.yaml`, no se otorga IAM y no se valida el entorno.
`file`              | str       | requerido         | Ruta (relativa a `manifest.yaml`) al fragmento YAML por fuente.
`iam_roles`         | list[str] | `[]`              | Roles GCP a nivel de proyecto otorgados a `toolbox-identity` cuando esta fuente está habilitada.
`required_env`      | list[str] | `[]`              | Variables de entorno requeridas en Cloud Run. El despliegue falla de inmediato con un mensaje claro si faltan. `PROJECT_ID` se establece automáticamente del proyecto de despliegue.
`required_secrets`  | list[str] | `[]`              | Variables de entorno obtenidas de Secret Manager. Formato: `"PG_PASSWORD=pg-pwd-secret:latest"`. Mapeado a `gcloud --set-secrets`.
`apis`              | list[str] | `[]`              | APIs de GCP a habilitar para esta fuente.
`network.connector` | str       | `null`            | Conector VPC para fuentes con IP privada.
`network.egress`    | str       | `null`            | `all-traffic` o `private-ranges-only`.
`client_auth_mode`  | str       | `service_account` | Uno de `service_account`, `end_user`, `hybrid`. Consulta [Gobernanza de acceso](#gobernanza-de-acceso).
`description`       | str       | `""`              | Nota descriptiva.

## Reactivar Spanner

La fuente de Spanner se incluye preconfigurada pero deshabilitada (no hay una instancia activa en este proyecto actualmente). Para habilitarla:

1.  Edita [`manifest.yaml`](manifest.yaml): cambia `spanner.enabled: false` → `true`.
2.  Despliega suministrando la instancia/base de datos mediante variables de entorno:

```bash
make deploy-mcp EXTRA_ENV="SPANNER_INSTANCE=tu-inst,SPANNER_DATABASE=tu-db"
```

El script otorgará automáticamente `roles/spanner.databaseUser` y `roles/spanner.viewer` a la SA de la toolbox e incluirá la fuente Spanner en el YAML compuesto. El agente incorporará `spanner_execute_sql` y `spanner_list_tables` en el siguiente despliegue.

**Nota**: al igual que GCS, Spanner a través de MCP funciona exclusivamente con cuenta de servicio (SA) actualmente — la fuente MCP de Spanner aún no implementa `useClientOAuth`. Si se requiere control de IAM por usuario en Spanner, considera el acceso directo por SDK (similar a la ruta de Dataplex) hasta que upstream incorpore soporte para delegación.

## Gobernanza de acceso

### Realidad actual

El proyecto upstream de MCP Toolbox soporta la cabecera de delegación de usuario final (`useClientOAuth: "X-Goog-User-Authorization"`) **únicamente en la fuente de BigQuery** hoy. GCS, Spanner, Dataplex y todas las demás fuentes son exclusivas de cuenta de servicio (SA): siempre usan las credenciales de la SA de la toolbox independientemente de lo que se configure en `client_auth_mode` en el manifiesto.

El MCP de este proyecto no utiliza actualmente ninguna fuente que soporte delegación, por lo que la cabecera `X-Goog-User-Authorization` se reenvía pero no se procesa en ninguna parte. La infraestructura de la cabecera se mantiene porque:
1. No tiene costo alguno.
2. En el momento en que MCP upstream añada `useClientOAuth` a GCS/Spanner/etc., cambiar `client_auth_mode: end_user` en el manifiesto activará la delegación por fuente sin requerir código adicional.

### Dos modos de autenticación (cuando useClientOAuth esté soportado por la fuente)

Cuando incorpores una fuente que soporte `useClientOAuth`:

-   **`service_account`** (por defecto): la fuente utiliza las credenciales GCP de la SA de la toolbox. Los registros de auditoría del sistema de datos muestran `toolbox-identity@...` como principal.
-   **`end_user`**: la toolbox reenvía el token OAuth del usuario final (vía `X-Goog-User-Authorization`) a la fuente, que lo utiliza en lugar de las credenciales de la SA. Los registros de auditoría del sistema de datos reflejan al usuario real.

### Hipotético: cambiar una fuente al modo `end_user`

(No aplica actualmente: ninguna de nuestras fuentes activas upstream lo soporta todavía. Se documenta aquí como referencia futura).

Para una fuente hipotética de BigQuery añadida al manifiesto:

1.  En `manifest.yaml`:
```diff
 bigquery:
   enabled: true
   file: sources/bigquery.yaml
+  client_auth_mode: end_user
```
2.  En `sources/bigquery.yaml`:
```diff
 kind: source
 name: bigquery-source
 type: bigquery
 project: ${PROJECT_ID}
-useClientOAuth: false
+useClientOAuth: "X-Goog-User-Authorization"
 ---
 kind: tool
 name: bq_execute_sql
 type: bigquery-execute-sql
 source: bigquery-source
+authRequired: [google-auth]
```

Redespliega con `make deploy-mcp`. El script de despliegue detecta que al menos una fuente tiene `client_auth_mode != service_account` y antepone automáticamente la configuración de authService de Google desde [`auth/google.yaml`](auth/google.yaml) al archivo compuesto `tools.yaml`.

### Requisitos de alcance (scopes) OAuth

Cuando una fuente está en modo `end_user`, el token OAuth del usuario final debe contar con el alcance adecuado. La interfaz del agente (Gemini Enterprise) debe solicitar estos alcances al iniciar sesión.

| Fuente                                        | Alcance (scope) OAuth requerido                        |
| --------------------------------------------- | ------------------------------------------------------ |
| BigQuery (hipotético, soportado en upstream)  | `https://www.googleapis.com/auth/bigquery`             |
| GCS (lectura) — si upstream añade soporte     | `https://www.googleapis.com/auth/devstorage.read_only` |
| Spanner — si upstream añade soporte           | `https://www.googleapis.com/auth/spanner.data`         |

### Estado de la integración (leer antes de activar `end_user`)

El agente llama a la toolbox hoy y reenvía un token de ID de Google (cabecera `Authorization`): el modo `service_account` funciona de extremo a extremo. La cabecera `X-Goog-User-Authorization` está conectada mediante un invocable en [`app/ca_toolbox_engine_app.py`](../ca_toolbox_engine_app.py) que delega en [`app/auth_utils.py:get_end_user_token()`](../auth_utils.py), el cual devuelve `None` hoy porque el `ToolContext` de ADK no expone la identidad del usuario final (limitación del framework, no del código).

Cuando ADK / Vertex AI Agent Engine incorpore una forma de leer el token OAuth del emisor en el momento de llamar a la herramienta, bastará con actualizar `get_end_user_token()` — ese cambio de una sola línea activará el modo `end_user` para cada fuente que *también* soporte `useClientOAuth` en upstream.

**Hasta entonces**: `client_auth_mode: end_user` está completamente configurado pero permanece inactivo por partida doble: (1) el hook devuelve None, por lo que no se reenvía ningún token de usuario, y (2) ninguna fuente actual procesa la cabecera aunque se enviara. Mantén `service_account` para uso en producción.

### Verificación del hook de forma aislada

Para comprobar que los cambios de tu manifiesto funcionen antes de que las piezas de upstream estén disponibles, establece un token de usuario simulado en el agente (y añade una fuente de BQ hipotética para confirmar que llega la cabecera):

```bash
make deploy AGENT_IDENTITY=true   # añadir: --set-env-vars _FAKE_USER_TOKEN_FOR_TESTING=test123
```

Luego observa los registros de la toolbox (`gcloud run services logs read data-agent-mcp-toolbox`) — las peticiones entrantes deben incluir `X-Goog-User-Authorization: Bearer test123`. (El hecho de que la fuente HAGA algo con él depende del soporte de `useClientOAuth` en upstream).

### Limitaciones

-   **La mayoría de las fuentes son exclusivas de cuenta de servicio (SA) en upstream hoy**. Solo BigQuery tiene implementado `useClientOAuth` en MCP Toolbox; GCS, Spanner, Dataplex y otras siempre usan la SA de la toolbox.
-   **Fuentes con autenticación por contraseña** (Cloud SQL con contraseña, Mongo con contraseña, etc.) no pueden realizar delegación por usuario: la credencial es un único secreto compartido. Mantén `client_auth_mode: service_account` en estas fuentes.
-   **Usuarios entre organizaciones**: la delegación de usuario final solo funciona para usuarios en la misma organización de Google Cloud propietaria de los recursos de datos.

### Dónde reside realmente la gobernanza en este proyecto

Para los sistemas de datos en los que *sí* tenemos requisitos de gobernanza (ejecución de SQL en BigQuery y Dataplex), la gobernanza se gestiona mediante las **rutas directas** (`ca_toolbox_agent.py` y `dataplex_utils.py`), no MCP. Esas rutas leen `tool_context.auth` a través de `auth_utils.get_user_credentials()` — usando ADC por defecto hoy, pero preparadas para usar las credenciales del usuario final en cuanto ADK complete ese campo.

Las herramientas de introspección de BigQuery que *sí* exponemos mediante MCP (en la variante sin dataplex) heredan la autenticación exclusiva por SA de la toolbox hoy. Upstream MCP soporta `useClientOAuth` en la fuente de BigQuery, por lo que activar `client_auth_mode: end_user` en `manifest-no-dataplex.yaml` habilitará la delegación para esas llamadas de introspección en el momento en que `get_end_user_token()` devuelva un token real. Consulta el [README.md](../../README.md) en la raíz del proyecto para ver la visión general de la arquitectura.

## Operaciones

Tareas comunes del operador:

**Obtener la URL del servicio**
```bash
gcloud run services describe data-agent-mcp-toolbox --region us-central1 --format='value(status.url)'
```

**Ver registros de la toolbox**
```bash
gcloud run services logs read data-agent-mcp-toolbox --region us-central1
```

**Actualizar la configuración (editar el YAML de una fuente o el manifiesto)**
```bash
make deploy-mcp
```
Esto crea una nueva versión en Secret Manager y una nueva revisión en Cloud Run.

**Auditar IAM en la SA de la toolbox**
```bash
gcloud projects get-iam-policy <PROJECT> --flatten=bindings --filter="bindings.members:toolbox-identity*"
```

**Forzar un redespliegue limpio**
```bash
gcloud run services delete data-agent-mcp-toolbox --region us-central1
make deploy-mcp
```

**Hacer una prueba rápida (smoke-test) de una herramienta desde tu equipo**
```bash
URL=$(gcloud run services describe data-agent-mcp-toolbox --region us-central1 --format='value(status.url)')
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" "$URL/api/toolset"
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
     -H "Content-Type: application/json" \
     -d '{}' \
     "$URL/api/tool/gcs_list_buckets/invoke"
```

## Solución de problemas

Síntoma                                                                         | Diagnóstico
------------------------------------------------------------------------------- | ---------
`PERMISSION_DENIED` desde GCS                                                    | La SA de la toolbox no tiene `roles/storage.objectViewer`. Revisa `gcloud projects get-iam-policy`.
El agente recibe `403` al invocar la toolbox                                    | La SA del agente no tiene `roles/run.invoker` en el servicio de la toolbox. Suele deberse a que `make deploy-mcp` se ejecutó antes de conocer la SA del agente. Solución: vuelve a ejecutar `make deploy-mcp` después de `make deploy` para otorgar el permiso a la SA real de `deployment_metadata.json`.
Script de despliegue: `Secret not found`                                        | Primer despliegue en un nuevo proyecto; vuelve a ejecutar `make deploy-mcp` (el secreto se crea en la primera ejecución, pero una condición de carrera con la habilitación de APIs puede fallar).
`unknown source kind: X` en los registros de Cloud Run                          | La imagen de MCP es más antigua que el tipo de fuente. Actualiza `--image` a una etiqueta más reciente.
`Missing required env vars: SPANNER_INSTANCE, ...`                              | No se pasaron las `required_env` de una fuente. Añádelas mediante `make deploy-mcp EXTRA_ENV="SPANNER_INSTANCE=foo,..."`.
`Source fragment not found: sources/X.yaml`                                     | El manifiesto hace referencia a un archivo inexistente. Coloca el fragmento en `sources/` o elimina la entrada del manifiesto.
Revisión de Cloud Run atascada en `not ready`                                   | `gcloud run services logs read data-agent-mcp-toolbox --region us-central1` — suele ser un error de sintaxis YAML o una referencia de variable de entorno no válida.
El agente no carga herramientas (solo stubs)                                    | Comprueba que `MCP_TOOLBOX_URL` esté configurado en Agent Engine (revisa el registro de despliegue; debe imprimir `Found MCP Toolbox URL: ...`). Si no, `deployment_metadata.json` carece de `mcp_toolbox_url`; vuelve a ejecutar `make deploy-mcp`.
La SA de la toolbox aún conserva roles de BQ / Dataplex tras actualizar de un despliegue anterior | Consulta la sección [Limpieza única si actualizas desde un despliegue anterior](#limpieza-unica-si-actualizas-desde-un-despliegue-anterior).

## Análisis en profundidad de la arquitectura

```
make deploy-mcp
   │
   ├─► cargar manifest.yaml
   ├─► validar fuentes habilitadas (env, existencia de fragmentos, modo)
   ├─► componer tools.yaml (concatenar fragmentos + auth/google.yaml si hay algún end_user)
   ├─► habilitar APIs (gcloud services enable)
   ├─► crear u obtener SA toolbox-identity (gcloud iam service-accounts)
   ├─► otorgar IAM a nivel de proyecto (resourcemanager_v3 - idempotente por rol+miembro)
   ├─► crear/actualizar secreto en Secret Manager (gcloud secrets create/versions add)
   ├─► desplegar servicio Cloud Run (gcloud run deploy)
   ├─► otorgar roles/run.invoker a la SA del agente (gcloud run services add-iam-policy-binding)
   └─► fusionar mcp_toolbox_url en deployment_metadata.json
```

Por qué esta estructura:

-   **Imagen preconstruida** (`us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:latest`): no hay Dockerfile que mantener; la imagen upstream sigue las nuevas fuentes automáticamente.
-   **Fragmentos por fuente**: prioridad en la extensibilidad. Añadir una fuente implica modificar dos archivos (fragmento + entrada en manifiesto), cero código en Python.
-   **`gcloud` mediante subproceso** para Cloud Run / Secret Manager / IAM de proyecto: coincide de forma idéntica con la documentación de MCP toolbox, sin nuevas dependencias de Python. (El despliegue de Agent Engine en [app/app_utils/deploy.py](../app_utils/deploy.py) continúa utilizando el SDK de vertexai debido a la complejidad de `AgentEngineConfig`; Cloud Run no lo requiere).
-   **`deployment_metadata.json` como punto de transferencia**: desacoplamiento entre despliegues del agente y de la toolbox. Cualquiera puede reejecutarse de forma independiente.
-   **MCP está intencionalmente acotado**: GCS (siempre) + introspección de BigQuery (únicamente cuando Dataplex está deshabilitado). Consulta [Por qué el MCP de este proyecto está delimitado de esta manera](#por-que-el-mcp-de-este-proyecto-esta-delimitado-de-esta-manera).

## Trabajo futuro

Brechas conocidas pospuestas deliberadamente:

-   **Soporte upstream de MCP `useClientOAuth` en GCS / Spanner / Dataplex**: abrir una incidencia en https://github.com/googleapis/genai-toolbox/ solicitándolo. Una vez fusionado, nuestras fuentes podrán pasar a modo `end_user` sin cambios en el código.
-   **Población de `get_end_user_token()`**: depende de que ADK / Agent Engine exponga el token OAuth del usuario final en `ToolContext`. El hook ya está ubicado en [`../auth_utils.py`](../auth_utils.py); cuando se implemente en upstream, será un cambio de una sola función.
-   **Revisar [Dataplex Remote MCP](https://docs.cloud.google.com/dataplex/docs/use-remote-mcp)** de Google cuando alcance GA: cuenta con delegación nativa de OAuth e IAM y podría reemplazar la ruta directa del SDK `dataplex_v1` por completo.
-   **Credenciales basadas en archivos** (certificados TLS como archivos montados para mTLS de Neo4j, etc.): añadir un campo `required_files:` al esquema del manifiesto cuando se requiera por primera vez.
-   **Manifiestos por entorno** (dev / staging / prod): actualmente un solo manifiesto, desplegado sobre el proyecto activo de gcloud.

