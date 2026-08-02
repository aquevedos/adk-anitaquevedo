# Configuración de la Demostración — Knowledge Catalog

Guía oficial para ejecutar la demo:
- [`demo-narrative.md`](demo-narrative.md) — Guión narrativo completo de 6 minutos para el presentador.
- [`demo-prompts.md`](demo-prompts.md) — Teleprompter con los prompts exactos para copiar y pegar durante la demo.

## Resumen de Recursos Configurados

- Un dataset de BigQuery (`retail_demo`) con tablas de comercio electrónico (`orders`, `order_items`, `products`, `users`, `inventory_items`, `distribution_centers`).
- Un bucket de Cloud Storage (`retail-policies-<PROJECT>`) con políticas y contratos en formato markdown.
- Entradas en Dataplex Knowledge Catalog para descubrimiento y enrutamiento inteligente.
- Dos variantes del agente:
  - `baseline` — Sin Knowledge Catalog (`DATAPLEX_ENABLED=false`).
  - `enriched` — Con Knowledge Catalog (`DATAPLEX_ENABLED=true`) y MCP Toolbox.

## Requisitos previos

- **Google Cloud SDK** (`gcloud`, `bq`, `gsutil`).
- **`jq`** — [Guía de instalación de jq](setup/install-jq.md).
- **Autenticación activa**: `gcloud auth login` y `gcloud auth application-default login`.

## Inicio Rápido (4 Pasos de Preparación)

```bash
# 0. Configurar las variables de entorno
export GOOGLE_CLOUD_PROJECT="agentspace-demos-466121"
export DEMO_DATASET="retail_demo"
export DEMO_BUCKET="retail-policies-${GOOGLE_CLOUD_PROJECT}"
export GCS_LOCATION="us-central1"

# 1. Verificar requisitos previos y habilitar APIs
./setup/00-prereqs.sh

# 2. Copiar tablas de BigQuery al dataset de la demo
./setup/10-copy-bq-tables.sh

# 3. Crear el bucket de Cloud Storage y subir las políticas
./setup/20-create-gcs-bucket.sh

# 4. Crear las entradas de catálogo en Dataplex para las políticas (OBLIGATORIO)
./setup/35-create-catalog-entries.sh
```

## Probar y Desplegar el Agente

### Opción A: Probar Localmente (Recomendado para pruebas rápidas)
```bash
cd ..
make playground
```
Abre tu navegador en `http://localhost:8501`, selecciona la carpeta `app` y comienza a interactuar.

### Opción B: Desplegar en Google Cloud (Vertex AI Agent Engine)
```bash
cd ..
make deploy-all VARIANT=enriched DATAPLEX_ENABLED=true
make deploy-all VARIANT=baseline  DATAPLEX_ENABLED=false
```

---

## Limpieza al finalizar la demostración

```bash
./teardown.sh
```
Elimina el dataset de BigQuery, el bucket de Cloud Storage, los despliegues de Agent Engine y los servicios Cloud Run de MCP.

## Qué se crea

Recurso              | Nombre                                                                                           | Propósito
-------------------- | ------------------------------------------------------------------------------------------------ | -------
Dataset de BQ        | `${GOOGLE_CLOUD_PROJECT}.retail_demo`                                                            | Tablas de demostración copiadas de `bigquery-public-data.thelook_ecommerce`
Tablas de BQ         | 6 tablas (ver [setup/10-copy-bq-tables.sh](setup/10-copy-bq-tables.sh))                          | Orders / order_items / products / users / inventory_items / distribution_centers
Bucket de GCS        | `retail-policies-${GOOGLE_CLOUD_PROJECT}`                                                        | Markdown de políticas / contratos
Tipo de entrada Dataplex | `policy-document` (personalizado, en tu proyecto)                                            | Define la estructura de las entradas de documentos de política
Grupo de entradas Dataplex | `retail-policies`                                                                              | Contiene una entrada de catálogo por archivo markdown de política
Entradas de Dataplex | Una por archivo en `sample-docs/`, con un aspecto de resumen y `entry_source.resource` = `gs://...` | Lo que devuelve `dataplex_search` cuando el agente consulta sobre políticas
Despliegue de agente | `data-agent-kc-baseline` (Vertex AI Agent Engine)                                                | Variante de referencia (básica)
Despliegue de agente | `data-agent-kc-enriched` (Vertex AI Agent Engine)                                                | Variante completa
Servicio Cloud Run   | `data-agent-mcp-toolbox-baseline`, `data-agent-mcp-toolbox-enriched`                             | MCP toolbox para cada variante
Secret Manager       | `toolbox-tools-config-baseline`, `toolbox-tools-config-enriched`                                 | Archivo compuesto tools.yaml
Archivos de metadatos| `deployment_metadata.baseline.json`, `deployment_metadata.enriched.json`                         | Transferencia de configuración entre variantes

## Costo estimado

-   BigQuery: copia pequeña por única vez (~$0.05 almacenamiento / mes para ~5 GB de datos de prueba).
-   Cloud Storage: <$0.01 / mes para ~50 KB de archivos markdown.
-   Vertex AI Agent Engine: el nivel gratuito cubre con facilidad la ejecución de una demo de 6 minutos.
-   Cloud Run (MCP toolbox): escala a cero; las invocaciones de la demo cuestan <$0.01.

Ejecuta `teardown.sh` después de la demo para evitar cargos recurrentes de almacenamiento.

## Prompts de la demostración

[`demo-prompts.md`](demo-prompts.md) contiene los prompts exactos para utilizar durante la demo, la variante a la que apuntar con cada uno y el comportamiento esperado. Utilízalo como un teleprompter.

## Solución de problemas

### `409: A Cloud Storage bucket named '...' already exists`

Los nombres de bucket de GCS son globalmente únicos. Si eliminaste el bucket recientemente e intentas recrearlo de inmediato, el nombre puede permanecer en reserva de eliminación suave (soft-delete) durante ~7 días. O bien, otra persona puede ser dueña de ese nombre globalmente. En cualquier caso, la solución es elegir un nombre diferente y volver a ejecutar **los tres** scripts de configuración que usan el bucket para que apunten al nuevo nombre:

```bash
export DEMO_BUCKET="retail-policies-${GOOGLE_CLOUD_PROJECT}-v2"
./setup/20-create-gcs-bucket.sh
./setup/30-dataplex-discovery.sh
./setup/35-create-catalog-entries.sh
```

El script de creación de bucket también intentará restaurar automáticamente el bucket si tu versión de gcloud es lo suficientemente nueva como para incluir `gcloud storage buckets restore` — pero el plan de respaldo con el nombre v2 siempre funciona.

### `Cloud Storage bucket location US is invalid, allowed regions are {US_CENTRAL1}`

Tu bucket se creó en la multirregión `US`, pero las zonas de Dataplex no lo admiten. El valor predeterminado de `GCS_LOCATION` es ahora `us-central1`. Si previamente lo configuraste en `US`, recrea el bucket:

```bash
gsutil -m rm -r "gs://${DEMO_BUCKET}"
gcloud dataplex assets delete policies-bucket --zone=policies-zone --lake=retail-lake \
  --location=us-central1 --project="$GOOGLE_CLOUD_PROJECT" --quiet 2>/dev/null || true
gcloud dataplex zones delete policies-zone --lake=retail-lake \
  --location=us-central1 --project="$GOOGLE_CLOUD_PROJECT" --quiet
gcloud dataplex lakes delete retail-lake \
  --location=us-central1 --project="$GOOGLE_CLOUD_PROJECT" --quiet
export GCS_LOCATION=us-central1
./setup/20-create-gcs-bucket.sh
./setup/30-dataplex-discovery.sh
./setup/35-create-catalog-entries.sh
```

`setup/30-dataplex-discovery.sh` incluye una verificación previa que detecta esta incompatibilidad antes de intentar crear el asset de Dataplex.

### `404: The destination bucket does not exist` inmediatamente después de crearlo

Es una condición de carrera de consistencia en `gsutil`. El script ahora espera 8 segundos tras crear un nuevo bucket y reintenta la subida hasta 3 veces; si sigues experimentando este problema, simplemente vuelve a ejecutar el paso de subida de forma manual:

```bash
gsutil -m cp ./setup/sample-docs/*.md "gs://${DEMO_BUCKET}/"
```

### `gcloud.storage.buckets: Invalid choice: 'restore'`

Tu versión de gcloud es anterior a la que incluye `gcloud storage buckets restore`. Ejecuta `gcloud components update` para actualizar, o simplemente omite la restauración y utiliza la alternativa del nombre v2 explicada arriba.

### El agente no encuentra los documentos de políticas en el Acto III / Acto IV

Verifica que existan las entradas del catálogo:

```bash
gcloud dataplex entries list --entry-group=retail-policies --location=global \
  --project="$GOOGLE_CLOUD_PROJECT"
```

Si la lista está vacía, `setup/35-create-catalog-entries.sh` no se ejecutó correctamente; vuelve a ejecutarlo. Si tuvo éxito pero el agente aún no puede encontrarlas, comprueba que el despliegue enriquecido (`enriched`) tenga configurado `MCP_TOOLBOX_URL` (el agente usa `gcs_read_object` de MCP para leer el cuerpo del archivo después de que el catálogo le proporciona el URI).
