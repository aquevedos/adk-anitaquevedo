# Prompts de la demostración — Teleprompter

Utiliza esto como pantalla secundaria durante la demostración. Cada fila indica a qué variante de agente apuntar, el prompt exacto para pegar y qué señalar en la respuesta.

## Acto I — Baseline vs Enriched (un prompt, dos agentes desplegados)

Ambos agentes están desplegados en **Vertex AI Agent Engine**. Abre cada uno en la pestaña de chat de la consola de Agent Engine (no en una sesión de desarrollo local). Pega el prompt en AMBOS, primero en la variante baseline.

> **Prompt**:
> *"For our premium customer segment, what was the average order value in Q4 2024, and which product category drove the largest share of spend?"*
> *(En español: "Para nuestro segmento de clientes premium, ¿cuál fue el valor promedio de pedido en el cuarto trimestre de 2024 y qué categoría de producto concentró la mayor parte del gasto?")*

**Qué señalar**:

- La variante **Baseline** probablemente falle (sin catálogo → BQ CA recibe una pregunta imprecisa sin contexto de esquema) o devuelva una respuesta confusa/excesivamente genérica ("Necesitaría saber qué tabla consultar…").
- La variante **Enriched** ejecuta la secuencia `dataplex_search` → `verify_entries_for_question` → `call_bigquery_ca`. La cadena de razonamiento muestra que seleccionó tablas específicas (`orders`, `order_items`, `users`, `products`). La respuesta cita el SQL y un valor monetario concreto.

Si el baseline responde coherentemente de todos modos (CA a veces logra autodescubrimiento), realiza una pregunta de seguimiento más acotada para forzar el límite:

> *"Now break that down by the specific customer cohort defined as 'premium' in our user-segmentation business glossary, not your own interpretation."*
> *(En español: "Ahora desglosa eso por la cohorte específica de clientes definida como 'premium' en nuestro glosario de términos de negocio de segmentación de usuarios, no según tu propia interpretación.")*

El baseline no tiene acceso a la entrada del glosario de términos. El enriquecido sí lo tiene (a través del catch-all `KNOWLEDGE` en `dataplex_search`).

---

## Acto II — Recorrido por la interfaz de usuario del Catálogo (sin prompt; mostrar la interfaz)

Cambia a la **interfaz de Knowledge Catalog** en Cloud Console. Navega a tu proyecto de demostración → `retail_demo.order_items`.

**Haz clic en estos elementos en secuencia**:

1. **Pestaña Schema** — destaca que `sale_price`, `inventory_item_id`, `status` no tienen descripciones.
2. Haz clic en **Generate Descriptions** → espera a que termine → despliega para mostrar el texto autogenerado.
3. Haz clic en **Run Data Profile** → muestra distribuciones de valores, nulos y valores principales por columna.
4. (Opcional) Navega a **Aspects** → muestra cómo aspectos personalizados (como un aspecto `customer_segment` del glosario de negocio en la tabla `users`) se incorporan al contexto del agente.

Este acto es una demostración de la interfaz de usuario, no un prompt del agente — pero enfatiza: **todo lo que escribe Generate Descriptions se convierte en contexto que el agente utiliza en el Acto IV.**

---

## Acto III — GCS como contexto descubrible por el catálogo

**Objetivo**: el despliegue **Enriched** en la consola de Agent Engine.

> **Prompt**:
> *"What's our published return window for outerwear, including any holiday extension?"*
> *(En español: "¿Cuál es nuestro plazo de devolución publicado para prendas de abrigo, incluida cualquier extensión por temporada festiva?")*

**Qué señalar**:

- La cadena de razonamiento muestra que `dataplex_search` devuelve `return-policy-2024.md` etiquetado como `Category: KNOWLEDGE`.
- La verificación confirma que es el documento adecuado.
- El agente enruta a `gcs_read_object` de MCP (ya que la entrada está en Cloud Storage) — destaca: *no se configuró ninguna herramienta especial de "lectura de políticas"; es catálogo → enrutamiento → MCP.*
- La respuesta final cita **45 días** estándar y **60 días** para compras realizadas entre el 1 de noviembre y el 24 de diciembre.

Pregunta de seguimiento opcional para mostrar cómo escala a otros documentos:

> *"Do we have a Q4 cap on outerwear discounting? Quote the exact rule."*
> *(En español: "¿Tenemos un tope de descuento en el cuarto trimestre para prendas de abrigo? Cita la regla exacta.")*

Debe devolver el **tope del 25% para Black Friday** de `holiday-pricing-policy-q4.md`, nuevamente enrutado vía MCP.

---

## Acto IV — Multimodal: la evaluación de salud trimestral del proveedor (el acto principal)

**Objetivo**: el despliegue **Enriched** en la consola de Agent Engine.

> **Prompt**:
> *"Run a quarterly vendor health check on Carhartt outerwear. I want realized margin against our contract target, and customer return rate against our published policy threshold. Flag anything outside policy and recommend who to involve."*
> *(En español: "Ejecuta una evaluación trimestral de salud del proveedor para las prendas de abrigo de Carhartt. Quiero el margen obtenido frente a nuestro objetivo de contrato y la tasa de devoluciones de clientes frente al umbral publicado en nuestra política. Señala cualquier aspecto fuera de política y recomienda a quién involucrar.")*

**Qué señalar mientras se ejecuta la cadena de razonamiento**:

1. `dataplex_search` devuelve un conjunto mixto de entradas — señala la columna `Category:` mostrando tanto `BIGQUERY` (`order_items`, `products`, `orders`) como `KNOWLEDGE` (el markdown del contrato de proveedor de Carhartt y el markdown de la política de devoluciones).
2. `verify_entries_for_question` confirma con una instrucción que menciona explícitamente ambas métricas + sus documentos que definen los umbrales.
3. El agente **agrupa por System y enruta**:
   - Entradas BIGQUERY → `call_bigquery_ca` para calcular el margen y la tasa de devoluciones a partir de datos reales.
   - Entradas KNOWLEDGE → `gcs_read_object` en cada URI de markdown para extraer las cláusulas exactas de umbrales.
4. La respuesta final es una tabla de evaluación con una estructura de columnas Realized / Target / Status, citando tanto los datos de origen como la sección del documento que define cada objetivo. La fila de la tasa de devoluciones muestra ⚠️ por encima del umbral; la recomendación incluye el correo de contacto del encabezado del contrato.

**Los números esperados** (datos reales — verifica con anticipación con las consultas en la sección de preparación, o confía en la lectura de BQ por el agente):

- Margen comercial obtenido, Carhartt Outerwear & Coats, 1T 2026: **2.24×** (por encima de la banda objetivo de 1.85×–1.95× en la Sección 2 del contrato de Carhartt → ✅)
- Tasa de devoluciones, Carhartt Outerwear & Coats, desde 2025-01: **9.5%** (por encima de la alerta del 8% en la Sección 4 de `return-policy-2024.md` → ⚠️)
- Recomendación: programar la revisión comercial conjunta con el proveedor según la Sección 3.2 del contrato; la misma alerta se activa para la categoría en general (10.3%), por lo que la conversación probablemente deba abarcar más marcas.

**La frase a destacar**: *"Observa que el agente no se limitó a darte un número — te dio un número comparado contra el umbral del documento específico que lo define. Esa es la diferencia entre un analista y una calculadora. Y cuando ese documento de política se actualice el próximo trimestre, el agente adoptará el nuevo umbral automáticamente — sin necesidad de redespliegue."*

---

## Prompts de respaldo (en caso de fallos en vivo)

| Si esto falla | Prueba esto en su lugar |
|---|---|
| BQ CA da una respuesta imprecisa en el Acto I | Pregunta: *"Which `traffic_source` value in our `users` table represents our premium customer segment per the business glossary?"* — más acotado y claramente dependiente del catálogo |
| El agente no encuentra la política en GCS en el Acto III | Verifica que la MCP toolbox del despliegue enriquecido esté activa — el escaneo de descubrimiento del catálogo debe haber finalizado para el bucket y el servicio Cloud Run de la toolbox debe estar saludable |
| El razonamiento del Acto IV está incompleto | Divídelo en dos partes: *"What's the realized markup on Carhartt outerwear since the start of 2025, by quarter? Compare to any contractual target we have on file."* y luego continúa con *"And separately, what's the customer return rate for Carhartt outerwear, and is it within our published policy threshold?"* |
| Inestabilidad de red o de CA | Ten a mano una grabación de pantalla de respaldo del Acto IV ejecutándose limpiamente. El objetivo de la demo es mostrar la *capacidad*, no la conexión en vivo. |

---

## Limpieza al finalizar

```bash
cd demo-scripts && ./teardown.sh
```

Elimina el dataset de BQ, el bucket de GCS, el Lake de Dataplex (si ejecutaste el paso 30) y ambos despliegues del agente + el servicio Cloud Run de la MCP toolbox enriquecida.
