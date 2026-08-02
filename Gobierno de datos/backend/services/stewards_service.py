"""Data Stewards and AI/RAG Dataset Readiness Service."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from .knowledge_catalog_service import catalog_service

logger = logging.getLogger("stewards_service")
CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "governance_config.yaml"


class DataStewardsService:
    def __init__(self):
        self.catalog = catalog_service
        self.config_path = CONFIG_PATH
        self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Error loading config yaml: {e}")
                self.config = {}
        else:
            self.config = {}
        return self.config

    def get_domains_and_stewards(self) -> List[Dict[str, Any]]:
        self._load_config()
        domains = self.config.get("dominios_negocio", [])
        assets = self.catalog.list_assets()

        for d in domains:
            d_id = d.get("id")
            domain_assets = [a for a in assets if a.get("domain") == d_id]
            d["active_assets_count"] = len(domain_assets)
            d["avg_quality_score"] = (
                round(sum(a.get("dataplex_quality", {}).get("overall_score", 0) for a in domain_assets) / len(domain_assets), 1)
                if domain_assets else 100.0
            )
            d["ai_certified_assets"] = sum(1 for a in domain_assets if a.get("ai_readiness", {}).get("certified_for_rag"))
        return domains

    def get_ai_readiness_catalog(self) -> List[Dict[str, Any]]:
        """Returns assets specifically evaluated for AI and RAG readiness."""
        assets = self.catalog.list_assets()
        ai_list = []
        for a in assets:
            ai_list.append({
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
        return ai_list

    def certify_dataset_for_ai(self, asset_id: str, certified: bool, notes: str) -> Dict[str, Any]:
        """Allows Data Stewards to approve or reject a dataset for AI / RAG pipeline ingestion."""
        asset = self.catalog.get_asset(asset_id)
        if not asset:
            return {"status": "error", "message": "Asset not found"}

        asset.setdefault("ai_readiness", {})
        asset["ai_readiness"]["certified_for_rag"] = certified
        asset["ai_readiness"]["compliance_status"] = "Certified by Steward" if certified else "Revoked by Steward"
        asset["ai_readiness"]["notes"] = notes
        self.catalog._save_data()

        return {
            "status": "success",
            "asset_id": asset_id,
            "certified_for_rag": certified,
            "message": f"Estado de certificación IA actualizado para '{asset.get('name')}'"
        }


stewards_service = DataStewardsService()
