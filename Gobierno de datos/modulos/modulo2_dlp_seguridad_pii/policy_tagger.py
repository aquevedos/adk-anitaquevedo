"""Conversor de hallazgos DLP en BigQuery Policy Tags y Dynamic Data Masking."""

import logging
from typing import Any, Dict, List, Optional
from ..modulo1_catalogo_activo.catalog_manager import catalog_manager

logger = logging.getLogger("policy_tagger")

INFOTYPE_MAPPINGS = {
    "EMAIL_ADDRESS": "Taxonomy_PII_HighRestricted",
    "PERSON_NAME": "Taxonomy_PII_Confidential",
    "PHONE_NUMBER": "Taxonomy_PII_Confidential",
    "CREDIT_CARD_NUMBER": "Taxonomy_PCI_Restricted",
    "IBAN_BANK_ACCOUNT": "Taxonomy_Financial_HighConfidential",
    "TAX_ID_RFC_SSN": "Taxonomy_PII_HighRestricted",
    "LOCATION_GEO": "Taxonomy_PII_Confidential",
    "IP_ADDRESS": "Taxonomy_Security_InternalOnly"
}


class PolicyTagger:
    def __init__(self):
        self.catalog = catalog_manager

    def apply_tags_and_masking(self, asset_id: str, auto_mask: bool = True) -> Dict[str, Any]:
        asset = self.catalog.get_asset_by_id(asset_id)
        if not asset:
            return {"status": "error", "message": f"Asset {asset_id} no encontrado"}

        applied = []
        for col in asset.get("columns", []):
            name = col.get("name", "").lower()
            for it, tag in INFOTYPE_MAPPINGS.items():
                if it == col.get("dlp_info_type") or it.lower() in name:
                    col["is_pii"] = True
                    col["dlp_info_type"] = it
                    col["policy_tag"] = tag
                    if auto_mask:
                        col["masked"] = True
                    applied.append({"column": col.get("name"), "tag": tag, "masked": col["masked"]})
                    break

        asset["dlp_status"]["policy_tags_applied"] = True
        asset["dlp_status"]["dynamic_masking_enabled"] = auto_mask
        asset["dlp_status"]["risk_level"] = "Protegido (Policy Tags Activas)"

        # Update AI Readiness
        if asset.get("dataplex_quality", {}).get("overall_score", 0) >= 90:
            asset["ai_readiness"]["certified_for_rag"] = True
            asset["ai_readiness"]["compliance_status"] = "Compliant (Masked & Governed)"
            asset["ai_readiness"]["notes"] = "Dataset protegido con Policy Tags de BigQuery y Dynamic Masking. Apto para IA."

        self.catalog._save_data()

        return {
            "status": "success",
            "asset_id": asset_id,
            "asset_name": asset.get("name"),
            "applied_tags": applied,
            "message": f"Se aplicaron {len(applied)} Policy Tags y reglas de Dynamic Data Masking con éxito."
        }


policy_tagger = PolicyTagger()
