"""Data Lineage and End-to-End Traceability Service."""

import logging
from typing import Any, Dict, List, Optional
from .knowledge_catalog_service import catalog_service

logger = logging.getLogger("lineage_service")


class DataLineageService:
    def __init__(self):
        self.catalog = catalog_service

    def get_asset_lineage_graph(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Generates a node-edge graph suitable for rich visual rendering and impact tracing."""
        asset = self.catalog.get_asset(asset_id)
        if not asset:
            return None

        nodes = []
        edges = []

        # Central Node
        central_node_id = f"node_{asset['id']}"
        nodes.append({
            "id": central_node_id,
            "label": asset.get("name"),
            "subtext": f"[{asset.get('cloud')} / {asset.get('service')}] {asset.get('table_name')}",
            "type": "central",
            "cloud": asset.get("cloud"),
            "quality_score": asset.get("dataplex_quality", {}).get("overall_score", 100),
            "risk_level": asset.get("dlp_status", {}).get("risk_level", "Bajo")
        })

        # Upstream Nodes
        upstream_list = asset.get("lineage", {}).get("upstream", [])
        for i, up in enumerate(upstream_list):
            up_id = f"up_{i}_{asset['id']}"
            nodes.append({
                "id": up_id,
                "label": up.get("source"),
                "subtext": up.get("type"),
                "type": "upstream",
                "cloud": up.get("source").split("/")[0].replace("[", "").strip() if "/" in up.get("source") else "External",
                "transformation": up.get("transformation", "Direct Sync")
            })
            edges.append({
                "from": up_id,
                "to": central_node_id,
                "label": up.get("transformation", "ETL Pipeline"),
                "style": "solid"
            })

        # Downstream Nodes
        downstream_list = asset.get("lineage", {}).get("downstream", [])
        for i, down in enumerate(downstream_list):
            down_id = f"down_{i}_{asset['id']}"
            nodes.append({
                "id": down_id,
                "label": down.get("target"),
                "subtext": down.get("purpose"),
                "type": "downstream",
                "cloud": down.get("target").split("/")[0].replace("[", "").strip() if "/" in down.get("target") else "Consumer",
                "target_type": down.get("type", "Consumer")
            })
            edges.append({
                "from": central_node_id,
                "to": down_id,
                "label": down.get("purpose", "Consumo"),
                "style": "dashed"
            })

        return {
            "asset_id": asset_id,
            "asset_name": asset.get("name"),
            "cloud": asset.get("cloud"),
            "nodes": nodes,
            "edges": edges,
            "upstream_count": len(upstream_list),
            "downstream_count": len(downstream_list)
        }

    def analyze_schema_change_impact(self, asset_id: str, modified_columns: List[str]) -> Dict[str, Any]:
        """Calculates downstream systems, reports, and AI models impacted by a column/schema modification."""
        asset = self.catalog.get_asset(asset_id)
        if not asset:
            return {"status": "error", "message": "Asset not found"}

        downstreams = asset.get("lineage", {}).get("downstream", [])
        impacted_items = []

        for down in downstreams:
            impact_level = "Crítico" if "AI" in down.get("type", "") or "Dashboard" in down.get("type", "") else "Alto"
            impacted_items.append({
                "target": down.get("target"),
                "type": down.get("type"),
                "purpose": down.get("purpose"),
                "impact_level": impact_level,
                "recommended_action": f"Revisar dependencias de esquema en '{down.get('target')}' para las columnas {modified_columns}."
            })

        return {
            "asset_id": asset_id,
            "asset_name": asset.get("name"),
            "modified_columns": modified_columns,
            "total_downstream_impacted": len(impacted_items),
            "impact_summary": f"Un cambio en las columnas {modified_columns} afectará a {len(impacted_items)} artefactos downstream (BI, Datamarts y Modelos de IA).",
            "impacted_consumers": impacted_items
        }


lineage_service = DataLineageService()
