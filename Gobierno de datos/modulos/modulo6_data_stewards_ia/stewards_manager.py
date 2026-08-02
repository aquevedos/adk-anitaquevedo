"""MÓDULO 6: Asistencia a Data Stewards y Certificación para IA / RAG."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from ..modulo1_catalogo_activo.catalog_manager import catalog_manager

logger = logging.getLogger("stewards_manager")
CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "governance_config.yaml"


class StewardsManager:
    def __init__(self):
        self.catalog = catalog_manager
        self.config_path = CONFIG_PATH

    def load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Error loading governance config: {e}")
        return {}

    def get_domains_summary(self) -> List[Dict[str, Any]]:
        cfg = self.load_config()
        domains = cfg.get("dominios_negocio", [])
        assets = self.catalog.list_assets()

        for d in domains:
            d_id = d.get("id")
            d_assets = [a for a in assets if a.get("domain") == d_id]
            d["active_assets_count"] = len(d_assets)
            d["avg_quality_score"] = (
                round(sum(a.get("dataplex_quality", {}).get("overall_score", 0) for a in d_assets) / len(d_assets), 1)
                if d_assets else 100.0
            )
            d["ai_certified_assets"] = sum(1 for a in d_assets if a.get("ai_readiness", {}).get("certified_for_rag"))
        return domains

    def get_ai_readiness_list(self) -> List[Dict[str, Any]]:
        assets = self.catalog.list_assets()
        res = []
        for a in assets:
            res.append({
                "asset_id": a.get("id"),
                "name": a.get("name"),
                "cloud": a.get("cloud"),
                "domain": a.get("domain"),
                "quality_score": a.get("dataplex_quality", {}).get("overall_score"),
                "dlp_risk": a.get("dlp_status", {}).get("risk_level"),
                "policy_tags_active": a.get("dlp_status", {}).get("policy_tags_applied"),
                "dynamic_masking": a.get("dlp_status", {}).get("dynamic_masking_enabled"),
                "certified_for_rag": a.get("ai_readiness", {}).get("certified_for_rag", False),
                "compliance_status": a.get("ai_readiness", {}).get("compliance_status", "Pending"),
                "notes": a.get("ai_readiness", {}).get("notes", "")
            })
        return res

    def certify_dataset(self, asset_id: str, certified: bool, notes: str) -> Dict[str, Any]:
        asset = self.catalog.get_asset_by_id(asset_id)
        if not asset:
            return {"status": "error", "message": "Asset no encontrado"}

        asset.setdefault("ai_readiness", {})
        asset["ai_readiness"]["certified_for_rag"] = certified
        asset["ai_readiness"]["compliance_status"] = "Certificado por Data Steward" if certified else "Revocado por Data Steward"
        asset["ai_readiness"]["notes"] = notes
        self.catalog._save_data()

        return {
            "status": "success",
            "asset_id": asset_id,
            "certified_for_rag": certified,
            "message": f"Estado de certificación para IA actualizado para '{asset.get('name')}'"
        }


stewards_manager = StewardsManager()
