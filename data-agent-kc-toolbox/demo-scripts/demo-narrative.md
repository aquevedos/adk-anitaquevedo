# Demo: Desbloqueando la Inteligencia Empresarial con Google Cloud Knowledge Catalog

**Duración total**: ~6 minutos. Diseñado en torno al agente `data-agent-kc` — un agente de ADK que permite a Knowledge Catalog dirigir el enrutamiento de sus herramientas, enviando consultas de BigQuery a Conversational Analytics, documentos de GCS a la MCP Toolbox y combinando ambos para ofrecer respuestas multimodales.

**Escenario**: un comercio minorista mediano que opera en Google Cloud. **Datos de origen**: una copia de `bigquery-public-data.thelook_ecommerce` en el proyecto de demostración (pedidos, productos, usuarios, inventario). **Datos no estructurados**: un bucket pequeño de Cloud Storage con contratos de proveedores, políticas de clientes y una política de segmentación de clientes — publicados tanto en markdown (que el agente lee en tiempo de ejecución) como en PDF (para capturas de pantalla ejecutivas).

**Configuración**: consulta [`README.md`](README.md). Todos los datos de ejemplo son creados por los scripts en [`setup/`](setup/). El agente se despliega dos veces: una variante **Enriquecida** (`enriched`) con Dataplex activado, y una variante de **Referencia** (`baseline`) sin él.

---

## Sección 1 — La Brecha de Contexto Empresarial (0:00 – 1:00)

**Momento "Aha"**: Por qué los catálogos tradicionales dejan a los agentes a ciegas.

**Elemento visual**: Diapositiva que muestra tres iconos de fuentes de datos (BigQuery, Cloud Storage, Knowledge Catalog) alimentando a un único agente. Detrás de ellos, una ilustración genérica del sector minorista.

**Orador**:

> "Toda empresa moderna compite por colocar agentes de IA generativa frente a sus datos — para automatizar la atención al cliente, optimizar las cadenas de suministro o consultar métricas financieras bajo demanda. La realidad es más compleja: existe una **brecha de contexto** que está frenando estos proyectos.
>
> Los LLMs son brillantes, pero operan a ciegas en tu entorno. No saben qué significan tus tablas, qué representan realmente los nombres de tus columnas, ni qué hay enterrado en los PDFs de políticas, wikis y guías de usuario que tus analistas han memorizado con los años. Sin un mapa, tu IA se detiene — o peor aún, fabrica una respuesta con total seguridad.
>
> **Knowledge Catalog** de Google Cloud cierra esa brecha con un **doble superpoder**. Primero, es un motor de contexto universal — agrega automáticamente esquemas técnicos, perfiles operativos y semántica de negocio desde BigQuery, Cloud Storage, Spanner y sistemas asociados en una base única, consistente y segura para descubrimiento y generación aumentada por recuperación (RAG). Segundo —y esta es la parte verdaderamente transformadora— utiliza **Gemini para enriquecer esos datos**, leyendo esquemas, registros de consultas, wikis, PDFs y guías de usuario para capturar el conocimiento tácito que normalmente vive solo en la mente de tus analistas, convirtiéndolo en metadatos estructurados, claros y fáciles de buscar. Tus bases de datos complejas y nombres de columnas crípticos se convierten en contenido que tanto los agentes de IA *como* los analistas humanos pueden finalmente entender.
>
> Hoy veremos cómo una empresa minorista utiliza Knowledge Catalog como ese motor de contexto universal para transformar recursos empresariales sin procesar en una capa de contexto unificada, segura y lista para IA. Comencemos donde suele empezar la fricción: los datos sin procesar."

---

## Acto I — El Agente a Ciegas vs. el Agente Enriquecido (1:00 – 2:00)

**Momento "Aha"**: Observa cómo la IA *adquiere visión*.

**Elemento visual**: Consola de Vertex AI Agent Engine, con dos agentes **desplegados** abiertos lado a lado en sus pestañas de chat:
- **Agente de Referencia (Baseline)** — agente personalizado en Gemini Enterprise, sin acceso a Knowledge Catalog.
- **Agente Enriquecido (Enriched)** — agente personalizado en Gemini Enterprise, con Knowledge Catalog conectado.

Ambos son despliegues reales de Agent Engine que se ejecutan en la nube; estamos interactuando con ellos a través de la consola de Agent Engine (no en un playground local), por lo que la audiencia observa el entorno de ejecución en producción.

**Orador**:

> "Tenemos dos agentes personalizados, ambos construidos sobre **Gemini Enterprise**, ambos apuntando al mismo almacén de datos, con el mismo modelo y en el mismo proyecto. El de la izquierda **no** tiene acceso a Knowledge Catalog. El de la derecha sí lo tiene. Esa es la única diferencia. Vamos a hacerles una pregunta de negocio habitual a ambos:
>
> **'Para nuestro segmento de clientes premium, ¿cuál fue el valor promedio de pedido en el cuarto trimestre de 2025 y qué categoría de producto generó el mayor gasto?'**"

**Elemento visual**: El presentador pega la pregunta en ambos despliegues.

**Baseline (Dataplex desactivado)** — el resultado muestra uno de dos modos de fallo:

> "Con gusto te ayudo. ¿Podrías aclarar qué define a un cliente premium en tus datos? Veo tablas como `orders`, `users` y `events`, pero no estoy seguro de qué señal indica 'premium'."

…o, lo que es más peligroso, una respuesta que suena convincente pero que inventa en silencio su propia definición (por ejemplo, "el 10% superior de usuarios por gasto histórico"). Los mismos datos, pero sin gobernanza — y sin forma de que el lector sepa que el agente inventó el límite del segmento.

**Enriched (Dataplex activado)** — el agente opera visiblemente a través del catálogo y luego responde:

> "Según la Política de Segmentación de Clientes registrada, 'Premium' se define como `users.traffic_source = 'Email'` y `users.age >= 35` con al menos un pedido completado en los últimos 12 meses. Aplicando ese filtro a los pedidos del cuarto trimestre de 2025: valor promedio de pedido de **$58.01** en 305 pedidos. La categoría de producto principal por gasto total fue **Outerwear & Coats** con $3,483, seguida de Jeans con $2,728 y Sweaters con $2,330. SQL generado: …"

**Orador**:

> "Éxito inmediato — y *gobernanza* inmediata. Entre bastidores, el Agente Enriquecido ejecutó una búsqueda en Knowledge Catalog, encontró el **documento de Política de Segmentación de Clientes** que *define* premium, extrajo el filtro SQL de referencia de ese documento, seleccionó las tablas correctas de BigQuery y *luego* invocó la API de Conversational Analytics con ese contexto preciso.
>
> El Agente de Referencia tenía acceso exactamente al mismo almacén, a las mismas tablas y a los mismos datos. Lo que le faltaba era el *mapa* — y observa que produce uno de dos malos resultados: se detiene y pide al usuario que haga el trabajo del equipo de datos, o inventa silenciosamente una definición. Ambos son peores que una respuesta pausada, correcta y auditable.
>
> Y aquí es donde los proyectos de IA se lanzan o se archivan en silencio. En la analítica empresarial real, la diferencia entre un agente con contexto curado y uno sin él suele elevar la precisión de **un 60%–70% (útil en un hackathon, peligroso en producción) a más del 90%**. Ese es el umbral donde el negocio realmente confía en el resultado y el despliegue pasa de ser una demo a respaldar decisiones críticas.
>
> Esta es la diferencia entre una IA que adivina y una IA que sabe."

---

## Acto II — Curaduría Autónoma: El Catálogo se Construye a Sí Mismo (2:00 – 2:50)

**Momento "Aha"**: El enriquecimiento de esquemas no es un proyecto de meses de administración de datos — es un flujo de trabajo autónomo que el agente aprovecha en tiempo de ejecución a través de **cuatro** capas de enriquecimiento.

**Elemento visual**: Cambiar a la interfaz de usuario de Knowledge Catalog, abierta en `retail_demo.order_items`.

**Orador**:

> "¿Cómo aprendió el agente a usar esa política y escribir el SQL correcto? Tradicionalmente, los administradores de datos pasaban meses entrevistando a ingenieros para documentar esquemas, redactar consultas de ejemplo y mapear relaciones entre tablas manualmente. Knowledge Catalog automatiza completamente ese paso en **cuatro frentes**, todos impulsados por Gemini.
>
> El esquema está aquí automáticamente — Dataplex lo sincroniza desde BigQuery en tiempo real. Pero observa las columnas: `sale_price`, `inventory_item_id`, `status`. Sin descripciones en una tabla recién creada. Un humano que lea esto puede intuirlo; un LLM va a alucinar cuando lo intente.
>
> Mira lo que hace Knowledge Catalog cuando hago clic en **Generate Descriptions**."

**Elemento visual**: Hacer clic en **Generate Descriptions**. Breve animación de progreso. Texto legible por humanos completa la columna de descripciones.

**Orador**:

> "**Enriquecimiento nº 1 — descripciones de columnas.** En segundo plano, los modelos integrados de Gemini evaluaron la forma real de los datos, distribuciones de valores, claves foráneas y convenciones de nomenclatura, completando automáticamente la documentación. `sale_price` se convierte en 'Precio final por unidad pagado por el cliente, en USD, después de descuentos'. `inventory_item_id` pasa a ser 'Clave foránea hacia inventory_items.id; identifica la unidad física específica enviada'. Al hacer clic en Guardar, queda confirmado en el esquema empresarial.
>
> Ahora abramos la pestaña **Insights**."

**Elemento visual**: Cambiar a la pestaña **Insights** — una lista de preguntas generadas por IA con sus consultas SQL asociadas.

**Orador**:

> "**Enriquecimiento nº 2 — Insights.** Gemini redacta las preguntas que los analistas suelen formular sobre esta tabla — '¿Cuáles fueron los productos más vendidos en el cuarto trimestre?', '¿Cuántas devoluciones hubo por categoría el mes pasado?' — y escribe el SQL que responde a cada una. Estos se convierten en patrones de consulta prevalidados en los que el agente puede apoyarse en lugar de inventar SQL desde cero, y los analistas los utilizan como plantillas de inicio para su propio trabajo. Ejemplos de consultas gratuitos generados por máquina para cada tabla del almacén.
>
> A continuación, el **Data Profile**."

**Elemento visual**: Cambiar a la pestaña **Data Profile**. Aparecen barras de perfil: distribuciones, tasas de nulos, valores principales por columna, cardinalidad.

**Orador**:

> "**Enriquecimiento nº 3 — Perfiles de Datos (Data Profiles).** Huellas estadísticas en tiempo real sobre cada columna: promedios, porcentajes de nulos, valores más frecuentes, cardinalidad. La calidad de los datos es completamente transparente, lo que evita que el agente consulte datos corruptos — y en tiempo de ejecución el agente los utiliza para validar sus propias acciones. Si está a punto de filtrar por una columna que tiene un 90% de valores nulos, sabe que debe reconsiderarlo.
>
> Por último, ampliemos la vista a la **descripción general del dataset**."

**Elemento visual**: Cambiar a la vista general del dataset / mapa de relaciones que muestra claves foráneas y enlaces semánticos entre `users`, `orders`, `order_items`, `products`, `inventory_items`.

**Orador**:

> "**Enriquecimiento nº 4 — Relaciones a nivel de dataset.** Claves foráneas, uniones (joins) y enlaces semánticos entre todas las tablas del dataset, capturados automáticamente. Eso es lo que permite al agente conectar con seguridad `users` → `orders` → `order_items` → `products` para nuestra pregunta de clientes Premium sin necesidad de explicarle el esquema paso a paso.
>
> Cuatro capas de enriquecimiento — descripciones, insights, perfiles y relaciones a nivel de dataset — y cero horas de administración manual. El paso de verificación de nuestro agente las utiliza todas en tiempo de ejecución: descripciones para confirmar la tabla adecuada, insights como ejemplos de SQL listos para usar, perfiles para evitar columnas corruptas y el mapa de relaciones para planificar sus uniones. El catálogo no es solo documentación: es el *entorno de ejecución* del cual depende el agente."

---

## Acto III — Desbloqueando Datos Ocultos con Inferencia Semántica (2:50 – 3:50)

**Momento "Aha"**: Transformar una carpeta de PDFs en contexto vivo.

**Elemento visual**: Cambiar al bucket de Cloud Storage `retail-policies-<PROJECT>`. Mostrar los archivos (tanto los originales en `.md` como las versiones renderizadas en `.pdf`):

- `customer-segment-policy.pdf` (la definición del segmento citada en el Acto I)
- `return-policy-2024.pdf`
- `supplier-jackets-carhartt-contract.pdf`
- `holiday-pricing-policy-q4.pdf`
- `vendor-sla-template.pdf`

**Orador**:

> "Las tablas estructuradas son solo una fracción del panorama general. Hasta el 80% del conocimiento corporativo reside en **datos oscuros (dark data)** — documentos no estructurados como contratos de proveedores, políticas de clientes y SLAs que se encuentran en este bucket.
>
> Si un cliente le pregunta a nuestro agente de soporte '¿Cuándo puedo obtener un reemplazo para una chaqueta dañada?', la respuesta se encuentra distribuida entre los datos transaccionales de BigQuery *y* el documento de política de devoluciones en este bucket. Sin un catálogo, el agente no sabe que ninguno de los dos existe.
>
> En lugar de construir complejas canalizaciones de procesamiento, apuntamos Knowledge Catalog a este bucket y activamos una funcionalidad clave: **Inferencia Semántica (Semantic Inference)**."

**Elemento visual**: Cambiar a la vista de Insights del catálogo para el bucket. Los documentos aparecen como entradas de catálogo de primer nivel con resúmenes generados por IA, nombres descriptivos y el URI del recurso `gs://...` en cada uno.

**Orador**:

> "Gemini leyó esos documentos directamente a partir del contenido sin procesar, resumió cada uno e infirió relaciones reales del negocio — mapeando categorías de productos con las políticas que las regulan y proveedores con los contratos que los vinculan. La configuración creó previamente estas entradas a través de la API de Dataplex Catalog, pero el mismo resultado puede obtenerse ejecutando el escaneo de Context Discovery de Knowledge Catalog con Semantic Inference habilitado.
>
> Una carpeta de texto antes inexplorable acaba de convertirse en una red viva de información corporativa que un analista —o un agente autónomo— puede recorrer."

**Elemento visual**: De vuelta al agente enriquecido. Preguntar: **'¿Cuál es nuestro plazo de devolución publicado para prendas de abrigo (outerwear)?'**

**El razonamiento del agente muestra**:
- Llama a `dataplex_search` → encuentra `return-policy-2024` etiquetado como `Category: KNOWLEDGE`
- Llama a `verify_entries_for_question` → confirma la relevancia
- Enruta al lector de GCS porque la entrada es un objeto de Cloud Storage
- Devuelve la respuesta citando la cláusula exacta de la política

**Respuesta**:

> "Según `return-policy-2024`, las prendas de abrigo (outerwear) tienen un **plazo de devolución de 45 días** a partir de la fecha de entrega, extendido a **60 días** para compras realizadas entre el 1 de noviembre y el 24 de diciembre (extensión por temporada festiva)."

**Orador**:

> "El agente no tenía una herramienta especial de 'leer política' configurada manualmente. Buscó en el catálogo, el catálogo indicó 'esta es una entrada de Cloud Storage' y el agente despachó a sus herramientas de GCS automáticamente. Si agregas al bucket un nuevo documento que el catálogo descubra, este se convierte en contexto utilizable de inmediato, sin necesidad de redesplegar el agente."

---

## Acto IV — Síntesis Multimodal: La Auditoría Trimestral de Proveedores (3:50 – 5:00)

**Momento "Aha"**: Una sola pregunta, dos sistemas, múltiples documentos, una respuesta sintetizada y lista para auditoría.

**Elemento visual**: De vuelta a la pestaña de chat del despliegue enriquecido.

**Orador**:

> "Hasta ahora hemos visto datos estructurados y no estructurados por separado. La verdadera inteligencia empresarial requiere combinar ambos. Este es el tipo de pregunta que formula un responsable de Compras — y que resulta sumamente compleja de responder sin un agente como este:
>
> **'Realiza una evaluación trimestral de salud del proveedor para las prendas de abrigo de Carhartt. Incluye el margen obtenido frente a nuestro objetivo contractual y la tasa de devoluciones de clientes frente al umbral publicado en nuestra política. Señala cualquier aspecto que esté fuera de la política.'**"

**Elemento visual**: La cadena de razonamiento del agente se transmite (a nivel general):

```
1. dataplex_search("Carhartt outerwear margin return rate quarterly")
   → 5 entradas:
       Category: BIGQUERY  -> retail_demo.order_items
       Category: BIGQUERY  -> retail_demo.products
       Category: BIGQUERY  -> retail_demo.orders
       Category: KNOWLEDGE -> supplier-jackets-carhartt-contract
       Category: KNOWLEDGE -> return-policy-2024

2. verify_entries_for_question(...) -> SÍ; instrucción: "Calcular el margen obtenido
   para Outerwear & Coats de Carhartt; calcular la tasa de devoluciones; contrastar cada
   métrica con el umbral de su documento regulador."

3. Enrutar por Category:
   - Entradas BIGQUERY  -> call_bigquery_ca(question, entry_names)
   - Entradas KNOWLEDGE -> gcs_read_object en cada una

4. Combinar resultados en la respuesta final.
```

**Elemento visual**: La respuesta final del agente (con formato claro):

> **Salud del programa Carhartt Outerwear — 1T 2026**
>
> | Métrica | Obtenido (1T 2026) | Objetivo de política/contrato | Estado |
> |---|---|---|---|
> | Margen comercial (`sale_price / cost`) | **2.24×** | 1.85× – 1.95× (Sección 2, contrato Carhartt) | ✅ Saludable — por encima del rango objetivo |
> | Tasa de devoluciones de clientes (desde 2025) | **9.5%** | Umbral de alerta 8% (Sección 4, return-policy-2024) | ⚠️ Por encima del umbral |
> | Volumen (artículos, 1T 2026) | 65 | Compromiso de 1,500 / año (Sección 1, contrato) | En ritmo (~260 anualizados × factor estacional) |
>
> **Margen**: el 2.24× obtenido se sitúa holgadamente por encima del rango objetivo de 1.85×–1.95× especificado en la Sección 2 del acuerdo de proveedor de Carhartt. Se aprecia una ligera compresión interanual (2.35× en 2024 → 2.24× en 2026 — una variación de aprox. 5%), pero el rango se sigue cumpliendo. No se requiere escalamiento por margen.
>
> **Tasa de devoluciones**: el 9.5% de Carhartt se sitúa **por encima** del umbral de alerta del 8% definido en la Sección 4 de la política de devoluciones. Según la Sección 3.2 del contrato de Carhartt, "las marcas que se sitúen de forma consistente por encima de este umbral durante dos meses consecutivos activan una revisión comercial conjunta con el proveedor enfocada en calidad de producto, precisión de tallas y exactitud en las descripciones del catálogo".
>
> **Recomendación**: programar la revisión comercial conjunta con el gerente de cuenta de Carhartt (jorge.menendez@carhartt.example, según el encabezado del contrato). La misma alerta se activa para la categoría Outerwear & Coats en general (tasa de devoluciones del 10.3%), por lo que la conversación probablemente deba abarcar más marcas además de Carhartt.

**Orador**:

> "Observen lo que acaba de suceder. El agente ejecutó una búsqueda en Knowledge Catalog, obtuvo entradas que abarcan dos sistemas completamente diferentes —BigQuery para datos transaccionales y Cloud Storage para la política y el contrato— y enrutó cada una a la herramienta correspondiente. Conversational Analytics calculó el margen y la tasa de devoluciones a partir de millones de filas. El lector de Cloud Storage extrajo las cláusulas exactas que definen qué significa 'saludable'.
>
> Noten tres aspectos fundamentales. Primero, el agente no se limitó a decir 'las devoluciones son del 9.5%' — indicó *9.5% **frente al umbral del 8% definido en la Sección 4 del documento de política correspondiente***. Los números sin contexto son ruido; los números acompañados de su documento regulador constituyen una auditoría. Segundo, el agente identificó tanto la acción *como* la persona de contacto adecuada, ambos extraídos de los documentos. Tercero, cuando uno de esos documentos cambie el próximo trimestre, el agente utilizará automáticamente el nuevo umbral — sin redespliegues ni solicitudes de desarrollo.
>
> Ningún humano programó una herramienta para 'verificar Carhartt contra contrato'. Ningún ingeniero codificó qué documentos consultar. El catálogo describió lo que existe y el agente hizo el resto. Esto es síntesis multimodal — solo posible porque Knowledge Catalog proporciona una fuente única y unificada de contexto de verdad tanto para filas estructuradas como para texto no estructurado."

---

## Conclusión — El Motor de Contexto Universal Siempre Activo (5:00 – 5:30)

**Elemento visual**: Panel general que muestra el entorno de ejecución del agente, Knowledge Catalog y las fuentes de BQ + GCS conectadas.

**Orador**:

> "Tres pilares hicieron esto posible:
>
> 1. **Agregación** — Knowledge Catalog recopiló esquemas estructurados de BigQuery, escaneó documentos no estructurados en Cloud Storage y unificó definiciones de negocio en un solo índice consultable.
> 2. **Enriquecimiento** — Gemini generó automáticamente cuatro capas de contexto sobre datos estructurados —descripciones de columnas, insights con SQL preelaborado, perfiles de datos y relaciones a nivel de dataset— e inferencia semántica sobre documentos no estructurados, todo sin administración manual.
> 3. **Búsqueda** — Un único agente utilizó ese índice en tiempo de ejecución para encontrar lo relevante, decidir qué herramienta invocar para cada resultado y combinar respuestas entre múltiples sistemas.
>
> Deja de permitir que tu IA adivine el significado de tus datos. Construye una base de contexto confiable e inteligente con Google Cloud Knowledge Catalog.
>
> Muchas gracias."

---

## Apéndice — Lo que la demo demuestra sobre el agente

Para la audiencia técnica: el comportamiento anterior está construido sobre estas capacidades (todas en [`app/`](../app/)):

| Capacidad | Código |
|---|---|
| Enrutamiento de herramientas guiado por catálogo según el sistema de la entrada | [`app/ca_toolbox_kc_wrapper.py`](../app/ca_toolbox_kc_wrapper.py) (prompt de orquestación) |
| Búsqueda en Dataplex particionada por sistema con comodín global para glosarios entre proyectos | [`app/dataplex_utils.py:dataplex_search`](../app/dataplex_utils.py) |
| Despliegues de dos variantes (`baseline` vs `enriched`) coexistiendo en un mismo proyecto | `VARIANT=baseline DATAPLEX_ENABLED=false` vs `VARIANT=enriched DATAPLEX_ENABLED=true` vía [`Makefile`](../Makefile) |
| Manejador de BigQuery → Conversational Analytics | [`app/ca_toolbox_agent.py:call_bigquery_ca`](../app/ca_toolbox_agent.py) |
| Herramientas de GCS → MCP Toolbox | [`app/mcp_toolbox/sources/gcs.yaml`](../app/mcp_toolbox/sources/gcs.yaml) |
| Generación de Markdown → PDF para el bucket | [`demo-scripts/setup/40-create-pdfs.sh`](setup/40-create-pdfs.sh) |
| Hooks de delegación de usuario final (preparados para cuando ADK exponga la identidad del usuario) | [`app/auth_utils.py`](../app/auth_utils.py) |
