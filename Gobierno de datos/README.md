# 🛡️ Plataforma Modular del Agente Inteligente de Gobierno de Datos Multi-Cloud

Arquitectura desacoplada y modular diseñada para **demostración y despliegue empresarial ante clientes**, permitiendo conectar fácilmente sus propias fuentes de datos (**GCP, AWS, Azure, On-Premises y SaaS**) y operar de forma autónoma con **Knowledge Catalog**, **Cloud DLP (Sensitive Data Protection)** y **Dataplex Data Quality**.

---

## 📁 Estructura Modular y Separación por Carpetas

Cada módulo de gobierno y conector está encapsulado en su propia carpeta independiente con su documentación `README.md`:

```
Gobierno de datos/
├── agente_gobierno_datos.md          # 📜 Definición formal y System Prompt del Agente
├── README.md                         # 📘 Guía general de la plataforma
├── run.sh                            # 🚀 Script de ejecución local (puerto 8085)
├── requirements.txt                  # 📦 Dependencias Python
│
├── config/                           # ⚙️ Configuración del Cliente
│   ├── governance_config.yaml        # Dominios de negocio, SLAs y umbrales de calidad
│   ├── connectors_config.yaml        # Credenciales, proyectos y endpoints de fuentes
│   └── mock_catalog_db.json         # Base unificada de metadatos multi-cloud
│
├── modulos/                          # 🧩 CARPETAS MODULARES DE GOBIERNO
│   ├── modulo1_catalogo_activo/      # 🔍 MÓDULO 1: Descubrimiento, Context Graph y Golden Queries
│   │   ├── catalog_manager.py        # Búsqueda semántica y actualización activa de metadatos
│   │   ├── golden_queries.py         # Catálogo de consultas SQL pre-aprobadas y auditadas
│   │   └── README.md                 # Guía explicativa para el cliente
│   │
│   ├── modulo2_dlp_seguridad_pii/    # 🛡️ MÓDULO 2: Suite Integral de Sensitive Data Protection (Cloud DLP / SDP)
│   │   ├── sdp_manager.py            # Dashboard Ejecutivo Looker Studio, Discovery, Inspection, Risk & Policies
│   │   ├── dlp_scanner.py            # Detección de InfoTypes (Nombres, emails, tarjetas, IBAN)
│   │   ├── policy_tagger.py          # Conversión a BigQuery Policy Tags y taxonomías
│   │   └── README.md                 # Guía explicativa para el cliente
│   │
│   ├── modulo3_calidad_dataplex/     # 🩺 MÓDULO 3: Dataplex Data Quality y Profiling
│   │   ├── quality_engine.py         # Evaluación de SLAs de frescura, completitud y unicidad
│   │   └── README.md                 # Guía explicativa para el cliente
│   │
│   ├── modulo4_linaje_trazabilidad/  # 🔗 MÓDULO 4: Linaje End-to-End y Análisis de Impacto
│   │   ├── lineage_graph.py          # Constructor de grafos de trazabilidad SVG
│   │   └── README.md                 # Guía explicativa para el cliente
│   │
│   ├── modulo5_seguridad_cumplimiento/ # 🔒 MÓDULO 5: Privacidad y Regla de Oro
│   │   ├── privacy_guard.py          # Filtro que garantiza operación exclusiva sobre metadatos
│   │   └── README.md                 # Guía explicativa para el cliente
│   │
│   ├── modulo6_data_stewards_ia/     # 👤 MÓDULO 6: Data Stewards y Preparación para IA / RAG
│   │   ├── stewards_manager.py       # Asignación de Data Owners y certificación para RAG
│   │   └── README.md                 # Guía explicativa para el cliente
│   │
│   └── conectores_multicloud/        # 🔌 CONECTORES DE FUENTES DE DATOS DEL CLIENTE
│       ├── connector_factory.py      # Gestor unificado de conectores
│       ├── gcp_connector.py          # Conector GCP BigQuery, Dataplex, DLP y GCS
│       ├── other_connectors.py       # Conectores AWS (Redshift/Glue), Azure (Synapse) y On-Prem (Postgres)
│       └── README.md                 # Guía de conexión para el cliente
│
├── core_agent/                       # 🤖 Cerebro del Agente y Orquestador
│   ├── agent_brain.py                # Razonador agéntico con respuesta obligatoria en 6 pasos
│   └── __init__.py
│
├── backend/                          # 🌐 Servidor y API REST
│   └── app.py                        # FastAPI endpoints consumiendo los módulos
│
└── frontend/                         # 🖥️ Interfaz Gráfica SPA (Vanilla JS + Dark Glassmorphism)
    ├── index.html                    # Dashboard interactivo con 7 pestañas
    ├── css/style.css                 # Diseño moderno con tema oscuro
    └── js/                           # Controladores JavaScript por módulo
        ├── app.js, chat.js, catalog.js, dlp.js, quality.js, lineage.js, stewards.js, connectors.js
```

---

## 🎯 Cómo Explicar esta Solución a un Cliente

1. **Desacoplamiento Total:** Cada módulo de gobierno funciona de forma independiente. Si el cliente solo quiere empezar con *Dataplex Quality* o *Cloud DLP*, se puede habilitar ese módulo específico sin afectar el resto.
2. **Conexión de Fuentes sin Egress:** El módulo `conectores_multicloud/` opera mediante el principio de **cero transferencia de datos reales** (*Metadata Only*), garantizando cumplimiento normativo y evitando costos de salida de red.
3. **Interfaz en Lenguaje Natural con 6 Pasos:** El cliente no necesita ser experto en consolas de nube; puede consultar en lenguaje natural y obtener una respuesta estructurada con resumen, ubicación, clasificación DLP, calidad Dataplex, linaje y Golden Query pre-aprobada.
4. **Preparación para IA Empresarial:** El Módulo 6 permite al Data Steward certificar si un dataset está listo para alimentar modelos RAG y asistentes de IA con datos enmascarados y de alta calidad.

---

## ▶️ Ejecución

```bash

cd /usr/local/google/home/anitaquevedo/antigravity/adk-anitaquevedo/Gobierno de datos
cd "Gobierno de datos"
uv run uvicorn backend.app:app --host 0.0.0.0 --port 8085 --reload
```

Acceso al Dashboard:
👉 **`http://localhost:8085`**
