# Price Shoes - Demand Planning & CalzaIntel AI Agent 📊👟

Este repositorio contiene una solución integral de simulación, predicción y planificación de abastecimiento inteligente para **Price Shoes**. Combina simulación de datos de retail en BigQuery, entrenamiento de modelos analíticos de series de tiempo **ARIMA_PLUS** y un Dashboard interactivo premium con el **Agente CalzaIntel** (habilitado con ADK y Gemini).

---

## 🚀 Arquitectura del Sistema

```
  ┌────────────────────────┐      ┌─────────────────────────┐
  │ Generador de Datos     │      │   Entorno de BigQuery   │
  │ (generate_to_bigquery) │ ───> │ - Tabla: products       │
  └────────────────────────┘      │ - Tabla: sales_history  │
                                  └────────────┬────────────┘
                                               │
                                               ▼
  ┌────────────────────────┐      ┌─────────────────────────┐
  │   Dashboard Web App    │ <─── │   CalzaIntel AI Agent   │
  │  (FastAPI + Chart.js)  │ ───> │  (ADK + Gemini 2.5)     │
  └────────────────────────┘      └─────────────────────────┘
```

---

## 🛠️ Requisitos Previos

Asegúrate de contar con lo siguiente:
1. Tener instalado [Python 3.9+](https://www.python.org/downloads/).
2. Tener instalado y configurado el [Google Cloud CLI (gcloud)](https://cloud.google.com/sdk/gcloud).

---

## 🚀 Guía de Inicio Rápido

Sigue estos pasos para levantar el sistema completo localmente.

### Paso 1: Autenticación en Google Cloud

Configura tus credenciales predeterminadas de aplicación (ADC) para permitir la conexión segura del script y del agente con BigQuery:

```bash
gcloud auth application-default login
```
*Sigue las instrucciones en pantalla en tu navegador para autorizar el acceso.*

### Paso 2: Crear el Entorno Virtual e Instalar Dependencias

Crea un entorno de Python aislado e instala todas las dependencias requeridas (BigQuery, ADK, FastAPI, Uvicorn, etc.):

```bash
# 1. Crear el entorno virtual
python3 -m venv .venv

# 2. Activar el entorno virtual
# En Linux/macOS:
source .venv/bin/activate
# En Windows:
# .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt
```

### Paso 3: Generar y Cargar Datos en BigQuery

Ejecuta el script simulador para crear el dataset, las tablas (`products` y `sales_history`) e insertar los datos sintéticos de retail:

```bash
python3 generate_to_bigquery.py --project "agentspace-demos-466121" --dataset "price_shoes_test"
```

### Paso 4: Lanzar la Aplicación Dashboard Web

Levanta el servidor web FastAPI localmente:

```bash
python3 app/main.py
```
Abre tu navegador en la dirección: **[http://127.0.0.1:8080](http://127.0.0.1:8080)**

---

## ✨ Características Premium (Efecto WOW)

* **Storytelling Interactivo**: Un carrusel narrativo en el encabezado desglosa los patrones estacionales del catálogo (Sandalias en verano, Botas en invierno, etc.) y explica el origen de las pérdidas por agotados (stock-outs).
* **Gráficos Dinámicos de Demanda**: Gráfico interactivo con Chart.js que muestra de forma animada el historial de ventas del producto seleccionado y su pronóstico a 30 días con sombreado del intervalo de confianza.
* **Agente CalzaIntel Conversacional**: Chatbot flotante que permite interactuar con el agente en tiempo real y que cuenta con **renderizado en streaming (palabra por palabra)**. El agente puede analizar inventarios, proponer cantidades de reabastecimiento usando la fórmula estándar de la industria y explicar la lógica del negocio.
