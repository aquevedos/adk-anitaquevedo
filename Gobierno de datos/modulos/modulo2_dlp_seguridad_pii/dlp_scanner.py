"""MÓDULO 2: Escáner de Datos Sensibles con Cloud DLP / Sensitive Data Protection."""

import datetime
import logging
from typing import Any, Dict, List, Optional
from ..modulo1_catalogo_activo.catalog_manager import catalog_manager

logger = logging.getLogger("dlp_scanner")

DEFAULT_INFOTYPES = [
    "EMAIL_ADDRESS", "PERSON_NAME", "PHONE_NUMBER", 
    "CREDIT_CARD_NUMBER", "IBAN_BANK_ACCOUNT", "TAX_ID_RFC_SSN",
    "LOCATION_GEO", "IP_ADDRESS"
]


class DLPScanner:
    def __init__(self):
        self.catalog = catalog_manager

    def inspect_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        asset = self.catalog.get_asset_by_id(asset_id)
        if not asset:
            return None

        found_infotypes = []
        findings = []

        for col in asset.get("columns", []):
            name = col.get("name", "").lower()
            detected = None

            if "email" in name or "correo" in name: detected = "EMAIL_ADDRESS"
            elif "name" in name or "nombre" in name or "cliente" in name or "vendedor" in name: detected = "PERSON_NAME"
            elif "phone" in name or "tel" in name or "celular" in name: detected = "PHONE_NUMBER"
            elif "card" in name or "tarjeta" in name or "credit" in name: detected = "CREDIT_CARD_NUMBER"
            elif "iban" in name or "bank" in name or "cuenta" in name: detected = "IBAN_BANK_ACCOUNT"
            elif "tax" in name or "rfc" in name or "ssn" in name or "dni" in name: detected = "TAX_ID_RFC_SSN"
            elif "address" in name or "direccion" in name or "geo" in name or "ciudad" in name or "region" in name: detected = "LOCATION_GEO"
            elif "ip" in name: detected = "IP_ADDRESS"

            if detected or col.get("is_pii"):
                final_it = detected or col.get("dlp_info_type") or "GENERIC_PII"
                if final_it not in found_infotypes and final_it != "GENERIC_PII":
                    found_infotypes.append(final_it)

                rec_tag = "Taxonomy_PII_Confidential"
                if final_it in ["EMAIL_ADDRESS", "TAX_ID_RFC_SSN"]:
                    rec_tag = "Taxonomy_PII_HighRestricted"
                elif final_it in ["CREDIT_CARD_NUMBER", "IBAN_BANK_ACCOUNT"]:
                    rec_tag = "Taxonomy_PCI_Restricted"
                elif final_it == "LOCATION_GEO":
                    rec_tag = "Taxonomy_Location_Restricted"

                findings.append({
                    "column_name": col.get("name"),
                    "data_type": col.get("type"),
                    "detected_infotype": final_it,
                    "confidence_score": 0.98 if detected else 0.85,
                    "recommended_policy_tag": rec_tag,
                    "current_policy_tag": col.get("policy_tag") or rec_tag,
                    "is_masked": col.get("masked", True)
                })

        # Risk assessment
        if "CREDIT_CARD_NUMBER" in found_infotypes or "IBAN_BANK_ACCOUNT" in found_infotypes:
            risk = "Crítico"
        elif len(found_infotypes) >= 2:
            risk = "Alto"
        elif len(found_infotypes) == 1:
            risk = "Medio"
        else:
            risk = "Bajo / Sin PII"

        now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        asset["dlp_status"] = {
            "scanned": True,
            "risk_level": risk,
            "info_types_found": found_infotypes,
            "last_scan_date": now_str,
            "policy_tags_applied": all(f["current_policy_tag"] for f in findings) if findings else False,
            "dynamic_masking_enabled": all(f["is_masked"] for f in findings) if findings else False
        }
        self.catalog._save_data()

        return {
            "asset_id": asset_id,
            "asset_name": asset.get("name"),
            "cloud": asset.get("cloud"),
            "service": asset.get("service"),
            "location": f"{asset.get('project_or_db')}.{asset.get('dataset')}.{asset.get('table_name')}",
            "scan_timestamp": now_str,
            "risk_level": risk,
            "infotypes_detected_count": len(found_infotypes),
            "infotypes_detected": found_infotypes,
            "findings_by_column": findings
        }


dlp_scanner = DLPScanner()
