# 🔌 Conectores Multi-Cloud e Híbridos (Guía para el Cliente)

Este módulo gestiona la conectividad segura con las plataformas de datos empresariales del cliente sin transferir datos reales (operando exclusivamente sobre metadatos).

---

## ☁️ Fuentes Soportadas

1. **Google Cloud Platform (GCP):**
   - **Servicios:** BigQuery, Dataplex Knowledge Catalog, Cloud DLP (SDP), Cloud Storage.
   - **Autenticación:** Application Default Credentials (ADC) o Service Account con roles `roles/datacatalog.viewer`, `roles/bigquery.metadataViewer`, `roles/dlp.inspectJobUser`.

2. **Amazon Web Services (AWS):**
   - **Servicios:** Amazon Redshift, AWS Glue Data Catalog, Amazon S3.
   - **Autenticación:** IAM Role / AWS Access Key con políticas de lectura de catálogos Glue.

3. **Microsoft Azure:**
   - **Servicios:** Azure Synapse Analytics, Azure Data Lake Storage Gen2, Microsoft Purview.
   - **Autenticación:** Service Principal con rol *Reader* y acceso a APIs de Purview.

4. **On-Premises / Datacenter:**
   - **Servicios:** PostgreSQL, Oracle Enterprise, Microsoft SQL Server.
   - **Conectividad:** Vía Cloud VPN / Cloud Interconnect o Tunnel SSH seguro.

5. **SaaS Enterprise:**
   - **Servicios:** Salesforce Data Cloud, SAP S/4HANA (vía RFC o OData).

---

## ⚙️ Cómo Conectar una Nueva Fuente del Cliente

1. Abre el archivo de configuración `config/connectors_config.yaml`.
2. Actualiza los IDs de proyecto, regiones o cadenas de conexión de tu infraestructura.
3. El agente detectará automáticamente los catálogos y registrará los esquemas en Knowledge Catalog.
