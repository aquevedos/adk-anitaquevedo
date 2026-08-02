"""MÓDULO 4: Linaje de Datos y Trazabilidad End-to-End."""

import logging
from typing import Any, Dict, List, Optional
from ..modulo1_catalogo_activo.catalog_manager import catalog_manager

logger = logging.getLogger("lineage_graph")


class LineageGraphBuilder:
    def __init__(self):
        self.catalog = catalog_manager

    def build_graph(self, asset_id: str) -> Optional[Dict[str, Any]]:
        asset = self.catalog.get_asset_by_id(asset_id)
        if not asset:
            return None

        nodes = []
        edges = []

        central_id = f"node_{asset['id']}"
        nodes.append({
            "id": central_id,
            "label": asset.get("name"),
            "subtext": f"[{asset.get('cloud')} / {asset.get('service')}] {asset.get('table_name')}",
            "type": "central",
            "cloud": asset.get("cloud"),
            "quality_score": asset.get("dataplex_quality", {}).get("overall_score", 100),
            "risk_level": asset.get("dlp_status", {}).get("risk_level", "Bajo")
        })

        # Upstreams
        for i, up in enumerate(asset.get("lineage", {}).get("upstream", [])):
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
                "to": central_id,
                "label": up.get("transformation", "ETL Pipeline"),
                "style": "solid"
            })

        # Downstreams
        for i, down in enumerate(asset.get("lineage", {}).get("downstream", [])):
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
                "from": central_id,
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
            "upstream_count": len(asset.get("lineage", {}).get("upstream", [])),
            "downstream_count": len(asset.get("lineage", {}).get("downstream", []))
        }

    def analyze_schema_impact(self, asset_id: str, modified_columns: List[str]) -> Dict[str, Any]:
        asset = self.catalog.get_asset_by_id(asset_id)
        if not asset:
            return {"status": "error", "message": "Asset no encontrado"}

        downstreams = asset.get("lineage", {}).get("downstream", [])
        impacted = []

        for d in downstreams:
            level = "Crítico" if "AI" in d.get("type", "") or "Dashboard" in d.get("type", "") else "Alto"
            impacted.append({
                "target": d.get("target"),
                "type": d.get("type"),
                "purpose": d.get("purpose"),
                "impact_level": level,
                "recommended_action": f"Revisar transformaciones en '{d.get('target')}' para las columnas modificadas {modified_columns}."
            })

        return {
            "asset_id": asset_id,
            "asset_name": asset.get("name"),
            "modified_columns": modified_columns,
            "total_downstream_impacted": len(impacted),
            "impact_summary": f"Un cambio en {modified_columns} impacta {len(impacted)} artefactos downstream.",
            "impacted_consumers": impacted
        }


lineage_graph_builder = LineageGraphBuilder()
