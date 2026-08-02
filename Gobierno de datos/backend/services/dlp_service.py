"""Cloud DLP (Sensitive Data Protection) Service for automated PII discovery & policy tagging."""

import datetime
import logging
from typing import Any, Dict, List, Optional
from .knowledge_catalog_service import catalog_service

logger = logging.getLogger("dlp_service")

# InfoType mapping to default Policy Tags
INFOTYPE_TO_POLICY_TAG = {
    "EMAIL_ADDRESS": "Taxonomy_PII_HighRestricted",
    "PERSON_NAME": "Taxonomy_PII_Confidential",
    "PHONE_NUMBER": "Taxonomy_PII_Confidential",
    "CREDIT_CARD_NUMBER": "Taxonomy_PCI_Restricted",
    "IBAN_BANK_ACCOUNT": "Taxonomy_Financial_HighConfidential",
    "TAX_ID_RFC_SSN": "Taxonomy_PII_HighRestricted",
    "LOCATION_GEO": "Taxonomy_PII_Confidential",
    "IP_ADDRESS": "Taxonomy_Security_InternalOnly"
}


class CloudDLPService:
    def __init__(self):
        self.catalog = catalog_service

    def scan_asset_for_pii(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Simulates a Cloud DLP inspection job on the specified asset schema & sampling."""
        asset = self.catalog.get_asset(asset_id)
        if not asset:
            return None

        found_infotypes = []
        findings_by_column = []

        for col in asset.get("columns", []):
            col_name = col.get("name", "").lower()
            detected_type = None

            if "email" in col_name or "correo" in col_name:
                detected_type = "EMAIL_ADDRESS"
            elif "name" in col_name or "nombre" in col_name:
                detected_type = "PERSON_NAME"
            elif "phone" in col_name or "tel" in col_name or "celular" in col_name:
                detected_type = "PHONE_NUMBER"
            elif "card" in col_name or "tarjeta" in col_name or "credit" in col_name:
                detected_type = "CREDIT_CARD_NUMBER"
            elif "iban" in col_name or "bank" in col_name or "cuenta" in col_name or "clabe" in col_name:
                detected_type = "IBAN_BANK_ACCOUNT"
            elif "tax" in col_name or "rfc" in col_name or "ssn" in col_name or "dni" in col_name or "rut" in col_name:
                detected_type = "TAX_ID_RFC_SSN"
            elif "address" in col_name or "direccion" in col_name or "geo" in col_name or "calle" in col_name:
                detected_type = "LOCATION_GEO"
            elif "ip" in col_name:
                detected_type = "IP_ADDRESS"

            if detected_type or col.get("is_pii"):
                final_type = detected_type or col.get("dlp_info_type") or "GENERIC_PII"
                if final_type not in found_infotypes and final_type != "GENERIC_PII":
                    found_infotypes.append(final_type)
                
                findings_by_column.append({
                    "column_name": col.get("name"),
                    "data_type": col.get("type"),
                    "detected_infotype": final_type,
                    "recommended_policy_tag": INFOTYPE_TO_POLICY_TAG.get(final_type, "Taxonomy_PII_Confidential"),
                    "current_policy_tag": col.get("policy_tag"),
                    "is_masked": col.get("masked", False),
                    "confidence_score": 0.98 if detected_type else 0.85
                })

        # Calculate risk level
        if "CREDIT_CARD_NUMBER" in found_infotypes or "IBAN_BANK_ACCOUNT" in found_infotypes:
            risk_level = "Crítico"
        elif len(found_infotypes) >= 2:
            risk_level = "Alto"
        elif len(found_infotypes) == 1:
            risk_level = "Medio"
        else:
            risk_level = "Bajo / Sin PII"

        now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        # Update the asset's DLP status in catalog
        asset["dlp_status"] = {
            "scanned": True,
            "risk_level": risk_level,
            "info_types_found": found_infotypes,
            "last_scan_date": now_str,
            "policy_tags_applied": all(f["current_policy_tag"] for f in findings_by_column) if findings_by_column else False,
            "dynamic_masking_enabled": all(f["is_masked"] for f in findings_by_column) if findings_by_column else False
        }
        self.catalog._save_data()

        return {
            "asset_id": asset_id,
            "asset_name": asset.get("name"),
            "cloud": asset.get("cloud"),
            "service": asset.get("service"),
            "location": f"{asset.get('project_or_db')}.{asset.get('dataset')}.{asset.get('table_name')}",
            "scan_timestamp": now_str,
            "risk_level": risk_level,
            "infotypes_detected_count": len(found_infotypes),
            "infotypes_detected": found_infotypes,
            "findings_by_column": findings_by_column
        }

    def apply_policy_tags_and_masking(self, asset_id: str, auto_mask: bool = True) -> Dict[str, Any]:
        """Converts DLP inspection findings into active Policy Tags and Dynamic Data Masking rules."""
        asset = self.catalog.get_asset(asset_id)
        if not asset:
            return {"status": "error", "message": f"Asset '{asset_id}' not found"}

        updated_columns = []
        applied_tags = []

        for col in asset.get("columns", []):
            col_name = col.get("name", "").lower()
            # If PII is found
            for it, tag in INFOTYPE_TO_POLICY_TAG.items():
                if it == col.get("dlp_info_type") or it.lower() in col_name:
                    col["is_pii"] = True
                    col["dlp_info_type"] = it
                    col["policy_tag"] = tag
                    if auto_mask:
                        col["masked"] = True
                    applied_tags.append({"column": col.get("name"), "tag": tag, "masked": col["masked"]})
                    break
            updated_columns.append(col)

        asset["columns"] = updated_columns
        asset["dlp_status"]["policy_tags_applied"] = True
        asset["dlp_status"]["dynamic_masking_enabled"] = auto_mask
        asset["dlp_status"]["risk_level"] = "Protegido (Policy Tags Activas)"
        
        # Also update AI readiness
        if asset.get("dataplex_quality", {}).get("overall_score", 0) >= 90:
            asset["ai_readiness"]["certified_for_rag"] = True
            asset["ai_readiness"]["compliance_status"] = "Compliant (Masked & Governed)"
            asset["ai_readiness"]["notes"] = "Dataset protegido con Policy Tags de BigQuery y enmascaramiento dinámico. Listo para consumo por agentes IA."

        self.catalog._save_data()

        return {
            "status": "success",
            "asset_id": asset_id,
            "asset_name": asset.get("name"),
            "applied_tags": applied_tags,
            "message": f"Se aplicaron {len(applied_tags)} Policy Tags y reglas de Dynamic Data Masking con éxito."
        }


dlp_service = CloudDLPService()
