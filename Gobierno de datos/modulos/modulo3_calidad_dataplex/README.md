# 🩺 Módulo 3: Calidad y Profiling Agéntico (Dataplex Data Quality)

## 📌 Propósito y Capacidades
Este módulo evalúa en tiempo real y bajo demanda la salud de las tablas y pipelines de datos en GCP, AWS, Azure y On-Premises.

### Dimensiones de Calidad Evaluadas:
- **Completitud:** Detección y umbrales de nulidad en claves primarias y campos obligatorios.
- **Frescura (SLAs):** Monitoreo de desfase temporal de actualización de datos.
- **Unicidad:** Validación de duplicidad en identificadores.
- **Conformidad:** Validación de formato (regex para emails, teléfonos, códigos postales).
- **Consistencia y Outliers:** Detección de anomalías estadísticas mediante perfiles continuos.

### Regla Proactiva:
Si un activo presenta un score **< 90%**, el agente emitirá una advertencia proactiva y restringirá su certificación para ingesta en modelos de IA generativa (RAG).
