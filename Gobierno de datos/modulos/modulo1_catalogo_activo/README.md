# 🔍 Módulo 1: Descubrimiento y Catálogo Activo (Knowledge Catalog)

## 📌 Propósito y Capacidades
Este módulo permite descubrir, catalogar y gobernar activamente activos de datos en múltiples plataformas en la nube y on-premises.

### Funcionalidades Clave:
1. **Búsqueda Semántica Multi-Cloud:** Indexa tablas, columnas, dominios y etiquetas a través del Context Graph de Knowledge Catalog.
2. **Actualización Activa de Metadatos:** Permite a usuarios de negocio y Data Stewards actualizar descripciones técnicas y funcionales mediante lenguaje natural o interfaz gráfica.
3. **Golden Queries Pre-Aprobadas:** Asocia consultas SQL optimizadas y seguras a cada tabla para garantizar que los analistas y modelos de IA utilicen los datasets correctamente.
4. **Glosario de Términos de Negocio:** Centraliza definiciones semánticas oficiales aprobadas por el Comité de Gobierno.

---

## 🛠️ Integración con Sistemas del Cliente
- **GCP:** Se sincroniza directamente con Dataplex Knowledge Catalog (`google-cloud-datacatalog`).
- **AWS:** Lee metadatos desde AWS Glue Data Catalog.
- **Azure:** Consulta esquemas de Azure Synapse y Purview.
- **On-Premise:** Extrae catálogos mediante vistas `information_schema`.
