"""MÓDULO 1: Descubrimiento, Catálogo Activo y Gestión de Metadatos / Tagging (Knowledge Catalog & Context Graph)."""

import datetime
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("modulo1_catalogo_activo")
DB_PATH = Path(__file__).parent.parent.parent / "config" / "mock_catalog_db.json"

# Definición oficial de Tag Templates de Google Cloud Knowledge Catalog
KNOWLEDGE_CATALOG_TAG_TEMPLATES = [
    {
        "template_id": "data_governance_core",
        "display_name": "Plantilla de Gobernanza de Datos (Core)",
        "dataplex_resource": "projects/corp-analytics-prod/locations/us-central1/tagTemplates/data_governance_core",
        "description": "Metadatos obligatorios de propiedad, dominio, clasificación y retención para activos corporativos.",
        "fields": [
            {"field_id": "data_steward", "display_name": "Data Steward Responsable", "type": "STRING", "required": True},
            {"field_id": "data_domain", "display_name": "Dominio de Negocio", "type": "ENUM", "options": ["clientes", "ventas", "finanzas", "operaciones"], "required": True},
            {"field_id": "confidentiality_level", "display_name": "Nivel de Confidencialidad", "type": "ENUM", "options": ["Pública", "Uso Interno", "Confidencial PII", "Altamente Restringida"], "required": True},
            {"field_id": "retention_policy_months", "display_name": "Retención (Meses)", "type": "INTEGER", "required": False},
            {"field_id": "golden_source", "display_name": "Fuente Dorada / Origen Primario", "type": "STRING", "required": False},
            {"field_id": "ai_certified", "display_name": "Aprobado para IA / RAG", "type": "BOOLEAN", "required": True}
        ]
    },
    {
        "template_id": "sdp_security_classification",
        "display_name": "Plantilla de Seguridad & SDP (Sensitive Data Protection)",
        "dataplex_resource": "projects/corp-analytics-prod/locations/us-central1/tagTemplates/sdp_security_classification",
        "description": "Etiquetas de seguridad derivadas de Cloud DLP, taxonomías y Dynamic Data Masking.",
        "fields": [
            {"field_id": "infotypes_detected", "display_name": "InfoTypes Detectados", "type": "STRING", "required": True},
            {"field_id": "dlp_risk_level", "display_name": "Nivel de Riesgo DLP", "type": "ENUM", "options": ["Bajo / Sin PII", "Medio", "Alto", "Crítico"], "required": True},
            {"field_id": "dynamic_masking_enabled", "display_name": "Dynamic Data Masking Activo", "type": "BOOLEAN", "required": True},
            {"field_id": "policy_tag_taxonomy", "display_name": "Taxonomía de Policy Tag", "type": "STRING", "required": False},
            {"field_id": "last_scan_date", "display_name": "Fecha Último Escaneo DLP", "type": "TIMESTAMP", "required": False}
        ]
    },
    {
        "template_id": "dataplex_quality_slas",
        "display_name": "Plantilla de Calidad Dataplex & SLAs",
        "dataplex_resource": "projects/corp-analytics-prod/locations/us-central1/tagTemplates/dataplex_quality_slas",
        "description": "Métricas operacionales de calidad, frescura y estado de cumplimiento de reglas de negocio.",
        "fields": [
            {"field_id": "quality_score", "display_name": "Dataplex Quality Score (%)", "type": "DOUBLE", "required": True},
            {"field_id": "freshness_hours", "display_name": "SLA de Frescura (Horas)", "type": "DOUBLE", "required": True},
            {"field_id": "rules_status", "display_name": "Cumplimiento de Reglas", "type": "STRING", "required": True}
        ]
    }
]


class CatalogManager:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading catalog database: {e}")
                self.data = {"assets": [], "glossary": []}
        else:
            self.data = {"assets": [], "glossary": []}
        return self.data

    def _save_data(self) -> bool:
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving catalog database: {e}")
            return False

    def list_assets(self, cloud: Optional[str] = None, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        self._load_data()
        assets = self.data.get("assets", [])
        if cloud and cloud.lower() != "all":
            assets = [a for a in assets if a.get("cloud", "").lower() == cloud.lower()]
        if domain and domain.lower() != "all":
            assets = [a for a in assets if a.get("domain", "").lower() == domain.lower()]
        return assets

    def get_asset_by_id(self, asset_id: str) -> Optional[Dict[str, Any]]:
        self._load_data()
        for asset in self.data.get("assets", []):
            if asset.get("id") == asset_id:
                return asset
        return None

    def search_semantic(self, query: str, cloud: Optional[str] = None) -> List[Dict[str, Any]]:
        self._load_data()
        query_lower = query.lower().strip()
        tokens = [w for w in re.split(r'[\s,._\-:;]+', query_lower) if len(w) > 2 and w not in ["analiza", "tabla", "dataset", "muestra", "ver", "consulta", "dame", "sobre", "con", "las", "los", "del", "para", "informacion", "información"]]
        
        results = []
        for asset in self.data.get("assets", []):
            if cloud and cloud.lower() != "all" and asset.get("cloud", "").lower() != cloud.lower():
                continue

            score = 0
            t_name = asset.get("table_name", "").lower()
            a_name = asset.get("name", "").lower()
            d_name = asset.get("dataset", "").lower()
            c_name = asset.get("cloud", "").lower()
            s_name = asset.get("service", "").lower()
            p_name = asset.get("project_or_db", "").lower()
            a_id = asset.get("id", "").lower()

            # Exact full phrase match
            if query_lower in t_name or (len(query_lower) > 3 and t_name in query_lower): score += 60
            if query_lower in a_name or (len(query_lower) > 3 and a_name in query_lower): score += 50
            if d_name in query_lower: score += 35
            if c_name in query_lower: score += 40

            # Special keyword priorities
            if "mysql" in query_lower and ("mysql" in c_name or "mysql" in a_id or "mysql" in a_name):
                score += 55
            if "aiven" in query_lower and ("aiven" in c_name or "aiven" in p_name or "aiven" in s_name):
                score += 55
            if "bdcomercial" in query_lower and ("bdcomercial" in d_name or "bdcomercial" in a_id):
                score += 55

            # Token level matching
            for tok in tokens:
                if tok == t_name: score += 50
                elif tok in t_name: score += 25
                if tok == d_name: score += 30
                elif tok in d_name: score += 15
                if tok == a_name: score += 25
                if tok in c_name: score += 25
                if tok in s_name: score += 20
                if tok in p_name: score += 20
                if tok in a_id: score += 20
                if tok in asset.get("description", "").lower(): score += 10
                for col in asset.get("columns", []):
                    col_name = col.get("name", "").lower()
                    if tok == col_name: score += 20
                    elif tok in col_name: score += 8

            if score > 0 or not tokens:
                c = dict(asset)
                c["relevance_score"] = score
                results.append(c)

        results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return results

    def update_metadata(
        self,
        asset_id: str,
        description: Optional[str] = None,
        steward: Optional[str] = None,
        golden_query: Optional[str] = None,
        column_updates: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Dict[str, Any]]:
        self._load_data()
        for asset in self.data.get("assets", []):
            if asset.get("id") == asset_id:
                if description is not None: asset["description"] = description
                if steward is not None: asset["steward"] = steward
                if golden_query is not None: asset["golden_query"] = golden_query
                if column_updates:
                    for cu in column_updates:
                        for col in asset.get("columns", []):
                            if col.get("name") == cu.get("name"):
                                if "description" in cu: col["description"] = cu["description"]
                                if "is_pii" in cu: col["is_pii"] = cu["is_pii"]
                                if "policy_tag" in cu: col["policy_tag"] = cu["policy_tag"]
                                if "masked" in cu: col["masked"] = cu["masked"]
                self._save_data()
                return asset
        return None

    def get_glossary(self) -> List[Dict[str, Any]]:
        self._load_data()
        return self.data.get("glossary", [])

    def add_glossary_term(self, term: str, definition: str, domain: str, approved_by: str) -> Dict[str, Any]:
        self._load_data()
        entry = {"term": term, "definition": definition, "domain": domain, "approved_by": approved_by}
        self.data.setdefault("glossary", []).append(entry)
        self._save_data()
        return entry

    # =========================================================================
    # GOBERNANZA & GESTIÓN DE METADATOS (TAG TEMPLATES & TAGGING)
    # =========================================================================
    def get_tag_templates(self) -> List[Dict[str, Any]]:
        """Retorna las plantillas oficiales de etiquetas de Knowledge Catalog."""
        return KNOWLEDGE_CATALOG_TAG_TEMPLATES

    def get_asset_tags(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Retorna los metadatos y etiquetas aplicadas a un activo (tabla y columnas)."""
        asset = self.get_asset_by_id(asset_id)
        if not asset:
            return None

        # Si el activo no tiene tag_templates inicializados, construirlos dinámicamente
        tags = asset.get("tag_templates")
        if not tags:
            tags = self._generate_default_tags_for_asset(asset)
            asset["tag_templates"] = tags
            self._save_data()

        return {
            "asset_id": asset.get("id"),
            "asset_name": asset.get("name"),
            "cloud": asset.get("cloud"),
            "service": asset.get("service"),
            "location": f"{asset.get('project_or_db')}.{asset.get('dataset')}.{asset.get('table_name')}",
            "domain": asset.get("domain"),
            "steward": asset.get("steward"),
            "available_templates": KNOWLEDGE_CATALOG_TAG_TEMPLATES,
            "applied_tags": tags,
            "columns": asset.get("columns", [])
        }

    def _generate_default_tags_for_asset(self, asset: Dict[str, Any]) -> Dict[str, Any]:
        """Genera valores predeterminados para las 3 plantillas de Knowledge Catalog."""
        domain = asset.get("domain", "ventas")
        steward = asset.get("steward", "Lucía Morales (Data Steward)")
        is_pii = any(c.get("is_pii") for c in asset.get("columns", []))
        infotypes = [c.get("dlp_info_type") for c in asset.get("columns", []) if c.get("dlp_info_type")]
        infotypes_str = ", ".join(list(set(infotypes))) if infotypes else "Ninguno detectado"
        quality_score = asset.get("dataplex_quality", {}).get("overall_score", 98.8)

        is_mysql = "MYSQL" in asset.get("cloud", "").upper() or "AIVEN" in asset.get("service", "").upper()
        golden_src = f"MySQL Aiven Cloud ({asset.get('project_or_db')})" if is_mysql else f"BigQuery ({asset.get('project_or_db')})"

        return {
            "data_governance_core": {
                "template_id": "data_governance_core",
                "template_name": "Plantilla de Gobernanza de Datos (Core)",
                "fields": {
                    "data_steward": steward,
                    "data_domain": domain,
                    "confidentiality_level": "Confidencial PII" if is_pii else "Uso Interno",
                    "retention_policy_months": 24,
                    "golden_source": golden_src,
                    "ai_certified": asset.get("ai_readiness", {}).get("certified_for_rag", True)
                },
                "last_updated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            },
            "sdp_security_classification": {
                "template_id": "sdp_security_classification",
                "template_name": "Plantilla de Seguridad & SDP (Sensitive Data Protection)",
                "fields": {
                    "infotypes_detected": infotypes_str,
                    "dlp_risk_level": asset.get("dlp_status", {}).get("risk_level", "Medio" if is_pii else "Bajo / Sin PII"),
                    "dynamic_masking_enabled": asset.get("dlp_status", {}).get("dynamic_masking_enabled", True),
                    "policy_tag_taxonomy": "Taxonomy_PII_Confidential" if is_pii else "Taxonomy_General_Internal",
                    "last_scan_date": asset.get("dlp_status", {}).get("last_scan_date", datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
                },
                "last_updated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            },
            "dataplex_quality_slas": {
                "template_id": "dataplex_quality_slas",
                "template_name": "Plantilla de Calidad Dataplex & SLAs",
                "fields": {
                    "quality_score": quality_score,
                    "freshness_hours": asset.get("dataplex_quality", {}).get("freshness_hours", 1.0),
                    "rules_status": f"{asset.get('dataplex_quality', {}).get('passed_rules', 5)} de {asset.get('dataplex_quality', {}).get('passed_rules', 5)} reglas aprobadas (100%)"
                },
                "last_updated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            }
        }

    def update_asset_tags(
        self,
        asset_id: str,
        template_id: str,
        fields: Dict[str, Any],
        column_tags: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Dict[str, Any]]:
        """Actualiza las etiquetas de una plantilla en Knowledge Catalog y las columnas asociadas."""
        self._load_data()
        for asset in self.data.get("assets", []):
            if asset.get("id") == asset_id:
                if "tag_templates" not in asset:
                    asset["tag_templates"] = self._generate_default_tags_for_asset(asset)

                if template_id in asset["tag_templates"]:
                    asset["tag_templates"][template_id]["fields"].update(fields)
                    asset["tag_templates"][template_id]["last_updated"] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                else:
                    asset["tag_templates"][template_id] = {
                        "template_id": template_id,
                        "template_name": next((t["display_name"] for t in KNOWLEDGE_CATALOG_TAG_TEMPLATES if t["template_id"] == template_id), template_id),
                        "fields": fields,
                        "last_updated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                    }

                # Sincronizar campos clave al activo
                if "data_steward" in fields:
                    asset["steward"] = fields["data_steward"]
                if "data_domain" in fields:
                    asset["domain"] = fields["data_domain"]
                if "ai_certified" in fields:
                    asset.setdefault("ai_readiness", {})["certified_for_rag"] = bool(fields["ai_certified"])

                # Actualizar tags a nivel de columna
                if column_tags:
                    for ct in column_tags:
                        c_name = ct.get("name")
                        for col in asset.get("columns", []):
                            if col.get("name") == c_name:
                                if "is_pii" in ct: col["is_pii"] = bool(ct["is_pii"])
                                if "dlp_info_type" in ct: col["dlp_info_type"] = ct["dlp_info_type"]
                                if "policy_tag" in ct: col["policy_tag"] = ct["policy_tag"]
                                if "masked" in ct: col["masked"] = bool(ct["masked"])
                                if "business_tag" in ct: col["business_tag"] = ct["business_tag"]

                self._save_data()
                return self.get_asset_tags(asset_id)
        return None

    def auto_tag_with_sdp(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Ejecuta el pipeline de Auto-Tagging automatizado con Sensitive Data Protection (SDP)."""
        asset = self.get_asset_by_id(asset_id)
        if not asset:
            return None

        # 1. Analizar columnas e inferir InfoTypes
        detected_infotypes = []
        for col in asset.get("columns", []):
            c_name = col.get("name", "").lower()
            if any(k in c_name for k in ["nombre", "name", "cliente", "vendedor"]):
                col["is_pii"] = True
                col["dlp_info_type"] = "PERSON_NAME"
                col["policy_tag"] = "Taxonomy_PII_Confidential"
                col["masked"] = True
                col["business_tag"] = "PII: Identidad Personal"
                detected_infotypes.append("PERSON_NAME")
            elif any(k in c_name for k in ["email", "correo"]):
                col["is_pii"] = True
                col["dlp_info_type"] = "EMAIL_ADDRESS"
                col["policy_tag"] = "Taxonomy_PII_HighRestricted"
                col["masked"] = True
                col["business_tag"] = "PII: Contacto Directo"
                detected_infotypes.append("EMAIL_ADDRESS")
            elif any(k in c_name for k in ["ciudad", "region", "direccion", "pais"]):
                col["is_pii"] = True
                col["dlp_info_type"] = "LOCATION_GEO"
                col["policy_tag"] = "Taxonomy_Location_Restricted"
                col["masked"] = True
                col["business_tag"] = "Ubicación Geográfica"
                detected_infotypes.append("LOCATION_GEO")
            elif any(k in c_name for k in ["total", "monto", "precio", "subtotal", "comision"]):
                col["business_tag"] = "Métrica Financiera"
            elif col.get("is_primary_key"):
                col["business_tag"] = "Clave Primaria / Identificador"

        # 2. Re-generar tags oficiales
        tags = self._generate_default_tags_for_asset(asset)
        asset["tag_templates"] = tags
        asset["dlp_status"]["policy_tags_applied"] = True
        asset["dlp_status"]["dynamic_masking_enabled"] = True
        asset["dlp_status"]["risk_level"] = "Protegido (Policy Tags Activas)"
        asset["dlp_status"]["last_scan_date"] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        self._save_data()
        return self.get_asset_tags(asset_id)


catalog_manager = CatalogManager()
