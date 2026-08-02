# CMI Data Governance Specialist Agent & Control Center

Agente especialista en **Gobierno de Datos, Calidad, Linaje y Cumplimiento de Políticas** para **Corporación Multi Inversiones (CMI)**.

El agente utiliza **Google Cloud Dataplex Knowledge Catalog** como su motor universal de contexto, orquesta consultas estructuradas en **BigQuery Conversational Analytics**, valida políticas no estructuradas en **Cloud Storage (GCS)** vía **MCP Toolbox**, y aplica las reglas de gobernanza, calidad (SLA) y glosarios oficiales de las unidades de negocio de CMI (*CMI Alimentos*, *CMI Capital*, *Servicios Compartidos*).

Cuenta con una **Capa de Administración 100% Configurable** y una **Interfaz Web Moderna (Dashboard + Chat Interactivo + Panel Admin)**.

---

## Inicio Rápido

### 1. Iniciar la Plataforma y Capa de Administración CMI

```bash
# Iniciar la interfaz web de gobierno y administración en http://localhost:8080
make ui
```

Abre tu navegador en **http://localhost:8080** para acceder al Centro de Control de Gobierno de Datos CMI.

### 2. Iniciar el Playground de Desarrollo (ADK)

```bash
make playground
```
Abre en **http://localhost:8501** seleccionando la carpeta `app`.

---

## Estructura del Proyecto

Ruta                                                           | Qué hace
-------------------------------------------------------------- | ------------
[`app/cmi_governance_config.yaml`](app/cmi_governance_config.yaml) | **Archivo central de configuración**: Reglas de calidad CMI, unidades de negocio, glosarios y conexiones GCP.
[`app/cmi_governance_config.py`](app/cmi_governance_config.py)   | Manejador en Python con recarga en caliente de las políticas de gobierno.
[`app/cmi_admin_api.py`](app/cmi_admin_api.py)                 | Backend FastAPI con endpoints REST para el chat, administración y estado de gobierno.
[`app/web/`](app/web/)                                         | **Interfaz de Usuario Web**: Dashboard de salud, chat interactivo, editor de configuración y explorador de catálogo.
[`app/ca_toolbox_kc_wrapper.py`](app/ca_toolbox_kc_wrapper.py) | Agente especialista en gobierno de datos y enrutador de Dataplex Knowledge Catalog.
[`app/ca_toolbox_agent.py`](app/ca_toolbox_agent.py)           | Manejador de BigQuery Conversational Analytics.
[`app/dataplex_utils.py`](app/dataplex_utils.py)               | Búsqueda semántica en Dataplex Catalog e inspección de aspectos.
[`app/mcp_toolbox/`](app/mcp_toolbox/)                         | Configuración de MCP Toolbox para lectura de políticas en Cloud Storage.
[`Makefile`](Makefile)                                         | Comandos de ejecución (`make ui`, `make playground`, `make deploy-all`).

## Comandos Make

| Comando                  | Descripción                                                                 |
| ------------------------ | --------------------------------------------------------------------------- |
| `make ui`                | **Inicia la Plataforma Web de Gobierno y Administración CMI (Puerto 8080)** |
| `make playground`        | Inicia el Agent Playground de ADK en el puerto 8501                        |
| `make deploy-all`        | Despliega el agente en Vertex AI Agent Engine y MCP Toolbox en Cloud Run    |
| `make install`           | Instala dependencias del proyecto con `uv`                                  |
| `make playground`        | Iniciar entorno de desarrollo local             |
| `make lint`              | Ejecutar verificaciones de calidad de código    |
| `make test`              | Ejecutar pruebas unitarias y de integración     |
| `make deploy`            | Desplegar el agente en Agent Engine             |
| `make deploy-mcp`        | Desplegar MCP Toolbox en Cloud Run (capa de acceso a datos para el agente) |
| `make deploy-all`        | Configuración inicial: `deploy-mcp` y luego `deploy` en un solo paso |
| `make compose-mcp-local` | Componer `tools.yaml` desde el manifiesto hacia `/tmp/tools.yaml` (sin llamadas a GCP) |
| `make local-mcp`         | Ejecutar MCP Toolbox localmente en Docker (en primer plano, `http://localhost:5001`) |

## Evaluación

### Evaluación Local (Procesamiento por Lotes)

Para evaluar el agente localmente con un conjunto de preguntas de prueba, utiliza el script `batch_process.py`. Este script ejecuta el agente localmente, simulando la autenticación de Gemini Enterprise mediante tus credenciales predeterminadas de la aplicación (Application Default Credentials, ADC) locales.

1.  Ejecuta el script:
```bash
uv run python -m app.app_utils.batch_process
```

El script creará un directorio `app/app_utils/eval_logs/` y almacenará un archivo de registro para cada pregunta (por ejemplo, `question_1.log`), que contendrá los eventos sin procesar y la respuesta final.

## Despliegue

Para desplegar el agente en Vertex AI Agent Engine:

```bash
gcloud config set project "$GOOGLE_CLOUD_PROJECT"
make deploy
```

Por defecto, esto se despliega con el nombre para mostrar (display name) `data-agent-kc` en el proyecto activo de gcloud.

**Opciones avanzadas de despliegue:**
- `VARIANT`: Desplegar una versión con nombre coexistente del agente — consulta [Múltiples variantes de despliegue](#multiples-variantes-de-despliegue).
- `DISPLAY_NAME`: Sobrescritura explícita del display name para Vertex AI Agent Engine. Tiene prioridad sobre el nombre derivado de `VARIANT`. (por ejemplo, `make deploy DISPLAY_NAME="Mi Agente Personalizado"`).
- `DATAPLEX_ENABLED`: Alternar los pasos de búsqueda/verificación de Knowledge Catalog. Por defecto `true`. Establécelo en `false` para deshabilitarlo (por ejemplo, `make deploy DATAPLEX_ENABLED=false`) — consulta [Lógica de enrutamiento del agente](#logica-de-enrutamiento-del-agente) para conocer los cambios.

### Múltiples variantes de despliegue

Para desplegar múltiples versiones coexistentes del agente (por ejemplo, una con Dataplex activado, una con Dataplex desactivado, una con una toolbox MCP habilitada para Spanner), utiliza la variable de Makefile `VARIANT`:

```bash
# Predeterminado — comportamiento sin cambios
make deploy-all
# → Display name en Agent Engine: data-agent-kc
#   Servicio Cloud Run de MCP:    data-agent-mcp-toolbox
#   Secreto de MCP:               toolbox-tools-config
#   Archivo de metadatos:         deployment_metadata.json

# Variante: no-dataplex
# (DATAPLEX_ENABLED=false también selecciona automáticamente manifest-no-dataplex.yaml
#  en el lado de MCP, agregando herramientas de introspección de BQ para descubrimiento de tablas.)
make deploy-all VARIANT=no-dataplex DATAPLEX_ENABLED=false
# → Display name en Agent Engine: data-agent-kc-no-dataplex
#   Servicio Cloud Run de MCP:    data-agent-mcp-toolbox-no-dataplex
#   Secreto de MCP:               toolbox-tools-config-no-dataplex
#   Archivo de metadatos:         deployment_metadata.no-dataplex.json

# Variante: with-spanner — utiliza un manifiesto diferente
make deploy-all VARIANT=with-spanner \
    MANIFEST=app/mcp_toolbox/manifest-with-spanner.yaml \
    EXTRA_ENV="SPANNER_INSTANCE=foo,SPANNER_DATABASE=bar"
```

**Lo que controla `VARIANT`** (cada valor derivado se puede sobrescribir mediante la variable explícita de Makefile indicada a su lado):

| Recurso                                 | Valor derivado de la variante        | Sobrescritura explícita               |
| --------------------------------------- | ------------------------------------ | ------------------------------------- |
| Nombre para mostrar en Agent Engine     | `data-agent-kc-<variant>`            | `DISPLAY_NAME=...`                    |
| Servicio Cloud Run de MCP               | `data-agent-mcp-toolbox-<variant>`   | `SERVICE_NAME=...`                    |
| Secreto en Secret Manager de MCP        | `toolbox-tools-config-<variant>`     | (`--secret-name` en deploy.py)        |
| Archivo de metadatos de despliegue      | `deployment_metadata.<variant>.json` | (`--metadata-file` en deploy.py)      |

**Compartido entre variantes** (intencionalmente, sin proliferación innecesaria):
- La cuenta de servicio (service account) de la toolbox (`toolbox-identity@<project>`) — múltiples servicios Cloud Run pueden vincular la misma SA.
- La SA en tiempo de ejecución de Vertex AI Agent Engine (predeterminada, gestionada por Google).

**Importante**: pasa la MISMA `VARIANT` tanto a `deploy` como a `deploy-mcp` (o utiliza `deploy-all`) para que el agente tome la URL de MCP de su variante del archivo de metadatos correcto. Mezclar variantes entre el par hace que el agente no cargue herramientas MCP de forma silenciosa (el archivo de metadatos que lee el agente no tendrá un `mcp_toolbox_url` para esa variante).

**Manifiestos por variante**: coloca archivos de manifiesto alternativos junto a `app/mcp_toolbox/manifest.yaml` y selecciónalos con `MANIFEST=`:

```
app/mcp_toolbox/
├── manifest.yaml                  # por defecto — gcs (+ bigquery y spanner deshabilitados)
├── manifest-no-dataplex.yaml      # gcs + introspección de bigquery (usar con DATAPLEX_ENABLED=false)
├── manifest-with-spanner.yaml     # spanner habilitado
└── manifest-extras.yaml           # agrega AlloyDB, Postgres, etc.
```

Cada variante se despliega de forma independiente: `make deploy-mcp VARIANT=foo MANIFEST=...` realiza la composición a partir de ese manifiesto en un secreto con el nombre de la variante + servicio Cloud Run. Actualizar una variante no afecta a las demás.

**Inspeccionar variantes desplegadas**: `ls deployment_metadata*.json` muestra qué variantes se han desplegado desde este repositorio. `cat deployment_metadata.<variant>.json` muestra sus URLs y Cuentas de Servicio (SAs).

## Modo local

Puedes ejecutar todo el stack (el playground del agente + MCP Toolbox) en tu equipo local, sin necesidad de desplegar en Cloud Run. Es útil para iterar sobre el manifiesto, el prompt de orquestación o nuevos fragmentos de origen MCP antes de realizar un despliegue real.

**Requisitos previos**: Docker (para el contenedor de la toolbox) y `gcloud auth application-default login` (la toolbox reutiliza tus ADC para invocar BigQuery / Dataplex / GCS con tus permisos).

**Flujo de trabajo con dos terminales:**

```bash
# Terminal 1 — iniciar MCP Toolbox localmente
make local-mcp
# (compone /tmp/tools.yaml a partir de manifest.yaml, luego ejecuta el contenedor de toolbox
#  en http://localhost:5001 con tus ADC montadas. Ctrl+C para detener.
#  El puerto 5001 es el predeterminado porque el 5000 está reservado por el Receptor AirPlay de macOS.)

# Terminal 2 — iniciar el playground del agente apuntando a él
MCP_TOOLBOX_URL=http://localhost:5001 make playground
```

El agente detecta automáticamente URLs de localhost y omite el token de ID de Cloud Run (que de todos modos fallaría contra una audiencia que no sea de Google); consulta `is_local_mcp_url` en [`app/auth_utils.py`](app/auth_utils.py). Toda la demás autenticación (tus ADC para BQ CA + Dataplex, y las ADC de la toolbox para sus propias llamadas de datos) funciona igual que en producción.

**Variantes:**

-   **Solo componer y ejecutar la toolbox manualmente** (omitir Docker, usar `go run` desde el directorio de [`mcp-toolbox`](../mcp-toolbox/)):
    ```bash
    make compose-mcp-local # escribe /tmp/tools.yaml
    cd ../mcp-toolbox && go run . --config=/tmp/tools.yaml --port=5001
    ```

-   **Puerto diferente**: `make local-mcp PORT=8081` y luego `MCP_TOOLBOX_URL=http://localhost:8081 make playground`.

-   **Habilitar Spanner localmente**: edita [`app/mcp_toolbox/manifest.yaml`](app/mcp_toolbox/manifest.yaml) para cambiar `spanner.enabled: true`, y luego ejecuta `make local-mcp EXTRA_ENV="SPANNER_INSTANCE=foo,SPANNER_DATABASE=bar"`.

-   **Omitir MCP por completo** (solo agente + CA + Dataplex vía SDK directo): `make playground` sin establecer `MCP_TOOLBOX_URL`. El agente registrará una advertencia y se ejecutará solo con herramientas stub y de SDK directo.

**Diferencias de comportamiento frente al modo desplegado:**

-   La toolbox local usa **tus ADC de usuario** de extremo a extremo (las llamadas a BQ CA, Dataplex y GCS se ejecutan como tu usuario). En modo desplegado, BQ CA + Dataplex se ejecutan como la SA de Agent Engine y GCS a través de MCP se ejecuta como `toolbox-identity`. Por lo tanto, el modo local está más cerca de ser "delegado por el usuario" que el modo desplegado actual, un efecto secundario útil para probar suposiciones de gobernanza.
-   Sin barrera de IAM de Cloud Run localmente. La toolbox acepta con gusto cualquier emisor de peticiones en localhost.
-   Sin participación de Secret Manager. El archivo compuesto `tools.yaml` reside en `/tmp/tools.yaml` en tu disco.

## Arquitectura de acceso a datos

El agente se comunica con tres sistemas de datos a través de tres rutas diferentes, cada una seleccionada por motivos de gobernanza:

Sistema                                                         | Ruta                                                                     | Archivo
-------------------------------------------------------------- | ------------------------------------------------------------------------ | ----
BigQuery (ejecución de SQL)                                    | **BigQuery CA** (Conversational Analytics — NL→SQL→ejecutar→insights)    | [`app/ca_toolbox_agent.py`](app/ca_toolbox_agent.py)
BigQuery (descubrimiento de tablas, solo cuando `DATAPLEX_ENABLED=false`) | **MCP Toolbox** — `bigquery_list_*` / `bigquery_get_table_info`          | [`app/mcp_toolbox/sources/bigquery.yaml`](app/mcp_toolbox/sources/bigquery.yaml)
Dataplex                                                       | **SDK directo `dataplex_v1`** con `tool_context.auth` → credencial de usuario o ADC | [`app/dataplex_utils.py`](app/dataplex_utils.py)
GCS (y futuras fuentes)                                        | Sidecar **MCP Toolbox** (Cloud Run, `toolbox-core`)                      | [`app/mcp_toolbox/`](app/mcp_toolbox/)

Las rutas directas conservan un hook limpio de delegación (`get_user_credentials(tool_context)`) de modo que la ejecución vinculada al usuario final se active automáticamente cuando ADK complete `ToolContext.auth` con la identidad del usuario que llama. La ruta de MCP está reservada para fuentes donde el acceso exclusivo por cuenta de servicio (SA) es aceptable y donde la extensibilidad basada en manifiestos de MCP (añadir un YAML y redesplegar) aporta más valor que la brecha de delegación actual. La *introspección* de BigQuery (sin ejecución) también se ofrece a través de MCP, pero únicamente cuando el agente se despliega con `DATAPLEX_ENABLED=false` — consulta [`app/mcp_toolbox/README.md`](app/mcp_toolbox/README.md#why-this-projects-mcp-is-scoped-this-way) para ver el razonamiento arquitectónico.

### Lógica de enrutamiento del agente

El agente de orquestación (definido en [`app/ca_toolbox_kc_wrapper.py`](app/ca_toolbox_kc_wrapper.py)) es un único `LlmAgent` que sigue un **flujo de trabajo de 3 pasos** guiado por Knowledge Catalog — el catálogo mismo le indica al agente qué herramientas invocar, en lugar de que el agente asuma que todo es una pregunta de BigQuery.

```
Pregunta del usuario
    │
    ▼
[1] dataplex_search ─────► devuelve entradas etiquetadas con `Category: BIGQUERY|DATAPLEX|KNOWLEDGE`
    │                       (3 búsquedas filtradas por sistema internamente, desduplicadas)
    ▼
[2] verify_entries_for_question ─► Verificación de Gemini: "¿pueden estas entradas responder a esta pregunta?"
    │   (iterar 1↔2 hasta que pase la verificación)
    ▼
[3] enrutar por `Category:` y ejecutar ─► distribuir por sistema, combinar resultados
```

#### Paso 3 — reglas de enrutamiento

El prompt de orquestación instruye al LLM a **agrupar las entradas verificadas por su campo `Category:` y enrutar cada grupo al manejador adecuado**:

`Category:` en la entrada                                                     | Manejador que llama el agente                                                                                                                                                                                                   | Por qué
----------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---
`BIGQUERY`                                                                    | `call_bigquery_ca` ([`ca_toolbox_agent.py`](app/ca_toolbox_agent.py)) — invoca la [API de Conversational Analytics](https://docs.cloud.google.com/gemini/data-agents/conversational-analytics-api/overview) (NL→SQL→ejecutar→insights) | CA realiza orquestación analítica de extremo a extremo; la primitiva adecuada para preguntas analíticas sobre tablas de BQ.
`CLOUD_STORAGE` (o nombres de entrada con formato de GCS)                    | MCP `gcs_list_buckets` / `gcs_list_objects` / `gcs_read_object` directamente                                                                                                                                                   | Las herramientas de MCP son lo suficientemente simples para el despacho directo del LLM.
`SPANNER` (solo cuando esté habilitado en el manifiesto de MCP)               | MCP `spanner_execute_sql` / `spanner_list_tables` directamente                                                                                                                                                                   | Igual — despacho directo desde el prompt.
`KNOWLEDGE` / `DATAPLEX` (términos de negocio, glosarios, relaciones semánticas) | **Sin llamada a herramienta.** Incorporar descripciones en la respuesta final como contexto de fundamentación (grounding).                                                                                                      | Son entradas únicamente de metadatos — no hay nada que ejecutar.
Cualquier otra cosa                                                           | Usar cualquier descripción de herramienta que encaje, o informar "no hay herramienta de ejecución configurada para esta fuente"                                                                                                  | Mecanismo de reserva elegante a medida que se agregan nuevas fuentes de MCP.

Una sola pregunta puede producir una **combinación** (por ejemplo, una tabla de BigQuery + un término de negocio + un archivo de GCS). El agente invoca cada manejador relevante en paralelo (aproximadamente) y combina los resultados en la respuesta final.

#### Por qué enrutamiento basado en catálogo

El catálogo ya sabe a qué *sistema* pertenece cada entrada. Exponer esto como `Category:` en la salida de búsqueda y permitir que el LLM despache según ello le brinda al agente tres propiedades:

-   **Extensible**: las nuevas fuentes de MCP se vuelven enrutables con solo mencionarlas en la tabla de enrutamiento del prompt (o al ser detectables por el LLM a través de las descripciones de las herramientas).
-   **Consciente de fuentes mixtas**: una sola pregunta que abarque tanto una tabla de BigQuery como un archivo de GCS (y un término de negocio para fundamentación) obtiene una sola respuesta que invoca a cada manejador relevante y concatena la salida.
-   **Patrón de manejador por sistema para orquestaciones no triviales**: consulta el docstring de `call_bigquery_ca` en [`app/ca_toolbox_agent.py`](app/ca_toolbox_agent.py) para ver la convención (`call_<system>_*`). Los sistemas cuyas herramientas MCP existentes sean suficientes omiten el wrapper por completo y se invocan directamente desde el prompt de orquestación.

#### Deshabilitar Dataplex

Establece la variable de entorno `DATAPLEX_ENABLED=false` para omitir por completo los pasos del catálogo. Resulta útil cuando el proyecto no tiene un Knowledge Catalog poblado, o cuando deseas probar el agente contra datos sin procesar sin la intermediación del catálogo.

Sin Dataplex, el LLM necesita otra forma de encontrar tablas de BigQuery antes de entregarlas a Conversational Analytics (CA requiere referencias explícitas a tablas). `DATAPLEX_ENABLED=false` también selecciona automáticamente [`manifest-no-dataplex.yaml`](app/mcp_toolbox/manifest-no-dataplex.yaml) en el lado de MCP, de modo que un solo comando configure ambas partes:

```bash
make deploy-all VARIANT=no-kc DATAPLEX_ENABLED=false
```

Con Dataplex deshabilitado:

-   **Herramientas registradas en el agente**: únicamente `call_bigquery_ca` (se omiten la búsqueda y la verificación). Las herramientas MCP se cargan como de costumbre, incluyendo ahora `bigquery_list_datasets` / `bigquery_list_tables` / `bigquery_get_table_info` para descubrimiento (sin `bigquery_execute_sql` — CA sigue encargándose de la ejecución).
-   **El prompt de orquestación** cambia a un despacho de dos pasos: el LLM utiliza las herramientas de introspección de BQ para encontrar tablas candidatas y luego pasa sus rutas completas a `call_bigquery_ca`. Para sistemas que no sean BQ (GCS, Spanner), despacha directamente a la herramienta MCP correspondiente.
-   **`call_bigquery_ca` rechaza `entry_names` vacíos** con un mensaje de orientación que redirige al LLM hacia la ruta de descubrimiento, evitando que entre en bucle con el error `REFERENCES_NOT_SET` de CA.

Compromisos (trade-offs): más rápido y simple (sin ciclos de búsqueda/verificación, sin dependencia de IAM de Dataplex), pero el LLM pierde el enrutamiento multisistema guiado por catálogo: las entradas que no sean de BQ no se pueden descubrir mediante búsqueda, sino únicamente a través de la redacción de la pregunta del usuario que coincida con la descripción de una herramienta.

#### De dónde proviene `Category:`

`dataplex_search` ([`app/dataplex_utils.py`](app/dataplex_utils.py)) ejecuta **tres búsquedas** internamente y combina/desduplica los resultados:

Búsqueda               | Forma de la consulta                                                            | Ámbito de proyecto | Por qué
---------------------- | ------------------------------------------------------------------------------- | ------------------ | ---
BigQuery               | `{q} system=BIGQUERY type=(TABLE\|VIEW) projectid:(<DATAPLEX_CATALOG_PROJECT>)` | delimitado         | Muestra tablas/vistas consultables de BQ en el proyecto del equipo
Dataplex               | `{q} system=DATAPLEX projectid:(<DATAPLEX_CATALOG_PROJECT>)`                    | delimitado         | Zonas / recursos de Dataplex en el proyecto del equipo
Conocimiento comodín   | `{q}` (sin filtro de sistema ni de proyecto)                                    | **no delimitado**  | Captura glosarios, términos de negocio, documentación personalizada — que a menudo residen en un proyecto separado a nivel de organización o de documentación. Las entradas ya etiquetadas se desduplican; el comodín solo añade entradas que las búsquedas específicas no encontraron.

Los resultados se combinan mediante desduplicación en la que **la primera fuente prevalece**, de modo que una entrada que coincida tanto con la búsqueda de BQ como con el comodín conserva su etiqueta de sistema `BIGQUERY`. El comodín simplemente amplía el alcance al contexto entre proyectos.

#### Configuración del proyecto de catálogo

Las búsquedas delimitadas utilizan `PROJECT_NAME` para `projectid:(...)`, resuelto como:

1.  Variable de entorno `DATAPLEX_CATALOG_PROJECT`, si está establecida — utilízala cuando el agente se ejecute en un proyecto diferente al que aloja el catálogo.
2.  De lo contrario, `GOOGLE_CLOUD_PROJECT` (el proyecto activo del agente).

```bash
# El agente se ejecuta en project-A, pero los recursos de BQ/Dataplex están catalogados en project-B
make deploy DATAPLEX_CATALOG_PROJECT=project-B
# (pásalo mediante --set-env-vars o amplía el Makefile para reenviar la variable)
```

La búsqueda comodín de CONOCIMIENTO no tiene ningún filtro de proyecto, por lo que los glosarios que residan en `project-C` (un proyecto central de documentación, por ejemplo) seguirán apareciendo.

### MCP Toolbox

**Configuración inicial**: `make deploy-all` (ejecuta `deploy-mcp` y luego `deploy` en orden).

Bajo el capó:
1. `make deploy-mcp` — se despliega la toolbox. La SA de ejecución del agente se predice a partir del número de proyecto (el patrón estándar de Google `service-{N}@gcp-sa-aiplatform-re.iam.gserviceaccount.com`), por lo que la concesión de permisos de invocador se realiza aquí. Escribe la URL de la toolbox en `deployment_metadata.json`.
2. `make deploy` — se despliega el agente, toma `MCP_TOOLBOX_URL` del archivo de metadatos y carga las herramientas de la toolbox al inicio.

**Estado estable**: un solo comando para el componente que haya cambiado. `make deploy-mcp` para un cambio en tools.yaml/manifest; `make deploy` para un cambio en el agente. Caso especial con SA personalizada: si despliegas el agente con `--agent-identity` o `--service-account`, vuelve a ejecutar `make deploy-mcp` una vez después de `make deploy` para que pueda otorgar el permiso de invocador a la SA real desde los metadatos.

Consulta [`app/mcp_toolbox/README.md`](app/mcp_toolbox/README.md) para la guía completa del operador: adición de fuentes, gobernanza de acceso, solución de problemas y reactivación de Spanner.

## Observabilidad

Telemetría integrada exporta a Cloud Trace, BigQuery y Cloud Logging.
