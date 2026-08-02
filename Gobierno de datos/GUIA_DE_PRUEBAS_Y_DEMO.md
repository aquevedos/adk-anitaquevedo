# 📘 Guía Oficial de Pruebas y Demostración para Clientes
## Agentic Data Governance Hub (Multi-Cloud, Conexión MySQL, Calidad de Negocio & Looker)

Esta guía explica paso a paso cómo responder a las necesidades exactas que busca tu cliente:
1. **Conexión real/simulada con bases de datos externas (MySQL Online como FreeMySQLDatabase, Azure SQL, PostgreSQL)**.
2. **Descubrimiento y catálogo automatizado (Discovery, Linaje, Data Profiling e indexación en Knowledge Catalog)**.
3. **Selección específica de tablas a gobernar (Filtro por lista o carga de archivo CSV)**.
4. **Evaluación de reglas y umbrales de calidad de negocio (Drill-Down & Detección de variaciones anormales en volumen de ventas)**.
5. **Gobernanza Semántica de Looker & Catálogo de Métricas de Negocio**.

---

## 🌐 1. Acceso a la Plataforma

* **URL Local:** [`http://localhost:8086`](http://localhost:8086) (o [`http://localhost:8085`](http://localhost:8085))
* **Estilo Visual:** Colores pasteles suaves, interfaz relajante para la vista, limpia y modular por rol.

---

## 👥 2. Los 4 Roles y sus Credenciales

| Avatar & Rol | Usuario | Correo Demo | Contraseña | Vistas Exclusivas |
| :--- | :--- | :--- | :--- | :--- |
| 👔 **El Estratega Ejecutivo** | Elena Rostova | `cdo@empresa.com` | `123` | • Asistente Estratégico (CDO)<br/>• Tablero de Valor & ROI<br/>• Looker & Capa Semántica<br/>• Compliance Scorecard |
| 📋 **El Gestor del Programa** | Mateo Valdivia | `governance@empresa.com` | `123` | • Asistente de Gobernanza Ágil<br/>• Diagnóstico de Madurez (DMM)<br/>• Matriz RACI & Comités<br/>• Policy as Code (KC MCP) |
| 🛡️ **El Guardián del Dato** | Lucía Morales | `steward@empresa.com` | `123` | • Asistente de Calidad & DLP<br/>• Calidad Dataplex & Reglas de Negocio (Drill-Down)<br/>• Cloud DLP & Policy Tags<br/>• Glosario & RAG |
| ⚙️ **El Arquitecto e Ingeniero** | Javier Mendoza | `architect@empresa.com` | `123` | • Asistente Técnico & SQL<br/>• Conectores & Discovery Externo (MySQL/Azure/CSV)<br/>• Linaje End-to-End & Impacto<br/>• Esquemas Técnicos & Queries |

---

## 🧪 3. Demostración de las 5 Necesidades Clave del Cliente

---

### 🔌 1. Conexión a MySQL Online (FreeMySQLDatabase) & Selección Específica por Lista o CSV
> **Dónde probar:** Inicia sesión con **`⚙️ El Arquitecto`** (`architect@empresa.com` / `123`) y ve a la pestaña **`🔌 Conectores & Discovery Externo`**.

1. **Cargar Preset de Conexión:**
   * Haz clic en el botón **`⚡ Cargar Preset FreeMySQL`** (o escribe tus credenciales de `https://www.freesqldatabase.com/freemysqldatabase/` o Azure SQL).
2. **Probar Conexión en Vivo:**
   * Haz clic en **`🔌 Probar Conexión en Vivo`**. El conector ejecutará una conexión TCP real y extraerá la versión del motor.
3. **Selección Específica de Tablas a Gobernar (Filtro por Lista o CSV):**
   * En el campo *Lista de Tablas*, escribe únicamente las tablas que deseas procesar (ejemplo: `clientes_online, pedidos_ecommerce`) o sube un archivo `.csv`.
4. **Ejecutar Descubrimiento Automatizado:**
   * Haz clic en **`🚀 Ejecutar Descubrimiento Automatizado, Linaje & Profiling`**.
   * **Qué observar:** El agente inspecciona los esquemas, calcula filas y nulos, enmascara PII automáticamente y las indexa en Google Cloud Knowledge Catalog.

---

### 📊 2. Reglas de Calidad de Negocio Avanzadas, Variaciones Anormales en Ventas & Drill-Down
> **Dónde probar:** Inicia sesión con **`🛡️ El Guardián`** (`steward@empresa.com` / `123`) y ve a la pestaña **`🩺 Calidad Dataplex & Reglas de Negocio`**.

1. **Ajuste de Umbrales Dinámicos:**
   * En la tabla de *Reglas de Calidad de Negocio Avanzadas*, ajusta el umbral dinámico de la regla **`Detección de Variación Anormal en Volumen de Ventas`** (ej. `15%`) y haz clic en **Guardar**.
2. **Ejecutar Evaluación de Reglas de Negocio:**
   * Haz clic en el botón **`🚀 Evaluar Reglas de Negocio`**.
3. **Inspección Drill-Down (Causa Raíz):**
   * Verás la alerta de caída del **-27% en ventas** respecto al baseline histórico.
   * Revisa la tabla de **Drill-Down** que muestra las transacciones individuales afectadas (por ejemplo, transacciones en México y Colombia) y la **Causa Raíz** identificada por el agente (*Timeout en webhook de pasarela de pago*).

---

### 📈 3. Gobernanza Semántica de Looker & Catálogo de Métricas de Negocio
> **Dónde probar:** Inicia sesión con **`👔 El Estratega`** (`cdo@empresa.com` / `123`) o **`⚙️ El Arquitecto`** y ve a la pestaña **`📊 Looker & Capa Semántica`**.

1. **Inspección de Métricas Oficiales:**
   * Revisa métricas como **`Ingresos Brutos (Gross Revenue)`**, **`Margen de Ganancia Neta (%)`** y **`Tasa de Abandono (Churn Rate)`**.
2. **Mapeo Semántico LookML & Privacidad:**
   * Cada tarjeta muestra la fórmula SQL de LookML (`sql: SUM(${TABLE}.sale_price)`), la tabla origen en BigQuery (`ecommerce.events`), el Data Steward responsable y el tag de protección PII.

---

### 📜 4. Knowledge Catalog MCP Server & Policy as Code
> **Dónde probar:** En la pestaña **`📜 Policy as Code (KC MCP)`**.

1. **Compliance Scorecard:** Indicador en tiempo real del % de cumplimiento general (0-100%).
2. **Generador con IA:** Escribe una política en lenguaje natural y genera su código YAML automáticamente.
3. **Auto-Remediación 1-Clic (`⚡ Auto-Remediar`):** Corrige violaciones de PII y calidad con un solo clic.

---

### ☁️ 5. Infraestructura Real de Google Cloud en `agentspace-demos-466121`
* **Dataplex DataScans:** Estado `Succeeded` en GCP Console (`dq-ecommerce-products-scan`).
* **BigQuery Tables:** Tablas reales sincronizadas (`ecommerce.events` con 2.4M filas, `fabril.Gastos_master`, `governed_data_sdp_scan.customer`).
