"""MÓDULO 8: Gobernanza Semántica de Looker & Catálogo de Métricas de Negocio.

Permite gobernar las métricas y modelos semánticos oficiales utilizados en Looker:
- Métricas aprobadas por comités (MRR, Margen Bruto, Churn, CAC, LTV).
- Mapeo hacia vistas LookML y tablas físicas en BigQuery / MySQL.
- Certificación y linaje hacia tableros ejecutivos.
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("looker_governance")


class LookerGovernanceManager:
    def __init__(self):
        self.metrics = [
            {
                "id": "metric-mysql-total-ventas",
                "name": "Ventas Totales Consolidadas (MySQL Aiven)",
                "domain": "Ventas & Operaciones",
                "definition": "Monto total acumulado de ventas comerciales registradas en el clúster MySQL (Aiven Cloud).",
                "lookml_model": "comercial_mysql_model",
                "lookml_view": "resumen_comercial_consolidado",
                "lookml_sql": "SUM(${TABLE}.total_venta)",
                "source_table": "mysql-1c645071-google-beed.j.aivencloud.com:10283.bdcomercial.resumen_comercial_consolidado",
                "owner_steward": "Lucía Morales (Data Steward MySQL)",
                "governance_status": "CERTIFICADA_OFICIAL",
                "last_updated": "2026-07-31 UTC",
                "pii_classification": "No PII (Métrica Agregada / Enmascaramiento en Nombres)",
                "dashboard_consumers": ["Tablero de Ventas Ejecutivas (Looker Studio)", "Agente RAG Comercial (Vertex AI)"]
            },
            {
                "id": "metric-mysql-comisiones-vendedores",
                "name": "Comisiones Pagadas a Vendedores (MySQL)",
                "domain": "Finanzas & Ventas",
                "definition": "Suma de comisiones devengadas por la fuerza de ventas registrada en MySQL.",
                "lookml_model": "comercial_mysql_model",
                "lookml_view": "resumen_comercial_consolidado",
                "lookml_sql": "SUM(${TABLE}.comision_vendedor)",
                "source_table": "mysql-1c645071-google-beed.j.aivencloud.com:10283.bdcomercial.resumen_comercial_consolidado",
                "owner_steward": "Mateo Valdivia (Agile Lead)",
                "governance_status": "CERTIFICADA_OFICIAL",
                "last_updated": "2026-07-31 UTC",
                "pii_classification": "Enmascarado con Dynamic Masking",
                "dashboard_consumers": ["Control de Comisiones (Looker)", "Auditoría Financiera"]
            },
            {
                "id": "metric-mysql-clientes-registrados",
                "name": "Clientes Únicos Registrados (MySQL)",
                "domain": "Clientes & Fidelización",
                "definition": "Conteo de clientes activos registrados en la base de datos MySQL bdcomercial.",
                "lookml_model": "comercial_mysql_model",
                "lookml_view": "clientes",
                "lookml_sql": "COUNT(DISTINCT ${TABLE}.cliente_id)",
                "source_table": "mysql-1c645071-google-beed.j.aivencloud.com:10283.bdcomercial.clientes",
                "owner_steward": "Lucía Morales (Data Steward)",
                "governance_status": "CERTIFICADA_OFICIAL",
                "last_updated": "2026-07-31 UTC",
                "pii_classification": "Protegido con Cloud DLP Policy Tags",
                "dashboard_consumers": ["Dashboard de Clientes 360", "Vertex AI Assistant"]
            }
        ]

    def list_governed_metrics(self) -> List[Dict[str, Any]]:
        return self.metrics

    def get_metric_by_id(self, metric_id: str) -> Optional[Dict[str, Any]]:
        return next((m for m in self.metrics if m.get("id") == metric_id), None)


looker_governance_manager = LookerGovernanceManager()
