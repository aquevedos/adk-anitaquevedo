# 🛡️ Módulo 2: Suite Integral de Sensitive Data Protection (Cloud DLP / SDP)

Este módulo implementa todas las capacidades empresariales de **Google Cloud Sensitive Data Protection (SDP / Cloud DLP)** integradas con Knowledge Catalog, BigQuery y conectores multi-cloud:

---

## 🏛️ Arquitectura de los 5 Pilares de SDP

### 0. 📊 Dashboard Ejecutivo (Looker Studio / SDP Discovery Template)
- **Visión Ejecutiva y KPIs Globales:** Visualización integral de más de 7,342 activos perfilados, 15 ubicaciones descubiertas y 1,452 activos altamente sensibles.
- **Filtros Dinámicos Multi-Criterio:** Filtrado simultáneo por *Proyecto*, *Tipo de Activo*, *Riesgo de Datos*, *Encriptación*, *Rango de Fechas*, *Activo*, *infoType*, *Sensibilidad*, *Visibilidad Pública* y *Ubicación*.
- **Desglose de Riesgo y Sensibilidad:** Gráficos de barras comparativos para niveles `RISK_HIGH`, `RISK_LOW`, `RISK_MODERATE` y sensibilidad.
- **Distribución de InfoTypes Detectados:** Gráfico interactivo tipo Donut con los infoTypes predominantes (`EMAIL_ADDRESS`, `CREDIT_CARD_NUMBER`, `PERSON_NAME`, `US_SSN`, `PHONE_NUMBER`, etc.).
- **Vulnerabilidades de Seguridad & Remediación 1-Clic:** Identificación y mitigación directa de tablas sin claves CMEK, activos expuestos públicamente y columnas de BigQuery sin Policy Tags.
- **Evolución Temporal de Descubrimiento:** Serie temporal del volumen de datos clasificados por riesgo a lo largo del tiempo.

### 1. 🌐 Descubrimiento Automatizado (Discovery Profiles & Heatmap)
- **Data Profiles Continuos:** Generación automática de perfiles de riesgo y sensibilidad a nivel de organización, proyecto, dataset y tabla.
- **Métricas de Sensibilidad:** Clasificación en niveles `HIGH`, `MODERATE` y `LOW`, cálculo de riesgo de texto libre y estado de encriptación en reposo (Google-Managed vs. CMEK).
- **Auto-Discovery Multi-Cloud:** Perfilado de BigQuery, Cloud Storage, MySQL y Azure SQL sin transferir datos reales (*Metadata-Only*).

### 2. 🔍 Inspección Completa (Inspection Suite)
- **Catálogo de InfoTypes Built-in:** Más de 18 InfoTypes nativos globales y regionales (`EMAIL_ADDRESS`, `PERSON_NAME`, `PHONE_NUMBER`, `CREDIT_CARD_NUMBER`, `IBAN_BANK_ACCOUNT`, `US_SSN`, `PERU_DNI`, `SPAIN_NIF`, `MEXICO_RFC`, `CHILE_RUT`, `COLOMBIA_NIT`, `AUTH_TOKEN`, `MEDICAL_RECORD_NUMBER`, `CRYPTO_WALLET_ADDRESS`, etc.).
- **Creador de Custom InfoTypes con Regex Live Sandbox:**
  - Definición de patrones con expresiones regulares (`REGEX`) o listas de palabras (`DICTIONARY`).
  - Hotwords de proximidad para elevar la confianza estadística.
  - Sandbox de pruebas en tiempo real para verificar matches antes del despliegue.
- **Inspect Jobs On-Demand:**
  - Ejecución bajo demanda con muestreo configurable (10%, 50%, 100%) y probabilidad mínima.
  - Desglose de hallazgos por columna y registro de auditoría.
- **Job Triggers Programados:**
  - Disparadores con expresiones Cron periódicas (diario, semanal) o dirigidos por eventos (`Pub/Sub` en GCS).
  - Acciones automáticas de persistencia y sincronización de Policy Tags.

### 3. 📊 Análisis Cuantitativo de Riesgo (Risk Analysis - Exclusivo para BigQuery)
> ⚠️ **Regla de Arquitectura:** El cálculo de re-identificación cuantitativa de SDP opera de manera exclusiva sobre fuentes estructuradas de **Google Cloud BigQuery**.
- **Métrica k-anonymity:** Distribución de clases de equivalencia, identificación de registros únicos vulnerables ($k=1, k=2, k<5$) y porcentaje de riesgo.
- **Métrica l-diversity:** Diversidad de atributos sensibles por grupo de quasi-identificadores y detección de clases homogéneas.
- **Delta-presence & Re-identificación:** Estimación del riesgo de re-identificación frente a bases de datos y registros poblacionales externos.
- **Recomendaciones de Anonimización:** Generalización (Bucketization), Dynamic Data Masking (DDM) SHA-256 y Tokenización Criptográfica Determinística con Cloud KMS.

### 4. ⚙️ Configuración & Gobernanza de Seguridad
- **Inspect Templates:** Plantillas preconfiguradas reutilizables para PII regional, PCI-DSS y fuga de credenciales (SecOps).
- **De-identify Templates:** Transformaciones de desidentificación (Enmascaramiento de caracteres `*`, Hash SHA-256 con salt, Tokenización reversible por IAM y Date Shifting).
- **Stored Custom InfoTypes:** Inventario persistente de identificadores corporativos propios.
- **Content Policies:** Reglas de cumplimiento continuo con auto-enmascaramiento, cuarentena de objetos y bloqueo de exportación a Vertex AI / RAG no certificado.

---

## 👤 Adaptación por Perfil de Gobierno

- **Guardián del Dato (Data Steward / DPO):** Control total de InfoTypes personalizados, disparadores, desidentificación y análisis de riesgo.
- **Arquitecto e Ingeniero (Lead Architect / SecOps):** Operación de pipelines de inspección, conectores multi-cloud y control de claves CMEK en Cloud KMS.
- **Gestor del Programa (Governance Lead):** Supervisión de Content Policies, auditorías de cumplimiento y roadmaps de remediación.
- **Estratega Ejecutivo (CDO):** Visión de alto nivel de sensibilidad, mitigación de riesgos regulatorios (GDPR/PCI) y ROI de privacidad.
