"""MÓDULO 2 AVANZADO: Motor Integral de Sensitive Data Protection (Cloud DLP / SDP).

Incluye:
1. Discovery (Descubrimiento Continuo & Data Profiles).
2. Inspection Suite:
   - InfoTypes Built-in globales y regionales.
   - Creación y prueba interactiva de Custom InfoTypes (Regex, Diccionario, Surrogate).
   - Inspect Jobs On-Demand con escaneo multi-fuente.
   - Job Triggers programados periódicos y por eventos.
3. Risk Analysis (Análisis Cuantitativo k-anonymity, l-diversity, delta-presence) EXCLUSIVO para BigQuery.
4. Configuración & Gobernanza:
   - Inspect Templates & De-identify Templates (Masking, Hash, Tokenización, Date Shifting).
   - Stored Custom InfoTypes.
   - Content Policies de seguridad continua.
5. Vistas y métricas personalizadas según el Perfil Responsable.
"""

import datetime
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from ..modulo1_catalogo_activo.catalog_manager import catalog_manager

logger = logging.getLogger("sdp_manager")
DB_PATH = Path(__file__).parent.parent.parent / "config" / "sdp_governance_db.json"


class SDPManager:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.catalog = catalog_manager
        self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading SDP database: {e}")
                self.data = {}
        else:
            self.data = {}
        return self.data

    def _save_data(self) -> bool:
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving SDP database: {e}")
            return False

    # =========================================================================
    # 1. DISCOVERY (Descubrimiento Automatizado & Data Profiles)
    # =========================================================================
    def get_discovery_profiles(
        self,
        cloud: Optional[str] = None,
        risk_level: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        self._load_data()
        profiles = self.data.get("discovery", {}).get("profiles", [])
        
        # Ensure all catalog assets are profiled
        assets = self.catalog.list_assets()
        existing_ids = {p.get("asset_id") for p in profiles}
        if any(a["id"] not in existing_ids for a in assets):
            self.run_discovery_profile_scan()
            profiles = self.data.get("discovery", {}).get("profiles", [])

        filtered = []
        for p in profiles:
            if cloud and cloud.lower() not in p.get("cloud", "").lower():
                continue
            if risk_level and risk_level.upper() != p.get("data_risk_level", "").upper():
                continue
            filtered.append(p)
        return filtered

    def get_discovery_summary(self) -> Dict[str, Any]:
        if not self.data:
            self._load_data()
        profiles = self.data.get("discovery", {}).get("profiles", [])
        
        total = len(profiles)
        high_sens = sum(1 for p in profiles if p.get("sensitivity_level") == "HIGH")
        mod_sens = sum(1 for p in profiles if p.get("sensitivity_level") == "MODERATE")
        low_sens = sum(1 for p in profiles if p.get("sensitivity_level") == "LOW")

        high_risk = sum(1 for p in profiles if p.get("data_risk_level") == "HIGH")
        mod_risk = sum(1 for p in profiles if p.get("data_risk_level") == "MODERATE")
        low_risk = sum(1 for p in profiles if p.get("data_risk_level") == "LOW")

        all_infotypes = set()
        for p in profiles:
            for it in p.get("predicted_infotypes", []):
                all_infotypes.add(it)

        now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        summary = {
            "total_tables_profiled": total,
            "high_sensitivity_count": high_sens,
            "moderate_sensitivity_count": mod_sens,
            "low_sensitivity_count": low_sens,
            "high_risk_count": high_risk,
            "moderate_risk_count": mod_risk,
            "low_risk_count": low_risk,
            "total_infotypes_detected": len(all_infotypes),
            "unique_infotypes_list": sorted(list(all_infotypes)),
            "last_global_scan": now_str
        }

        self.data.setdefault("discovery", {})["summary"] = summary
        self._save_data()
        return summary

    def run_discovery_profile_scan(
        self,
        asset_id: Optional[str] = None,
        source_type: Optional[str] = None,
        cloud: Optional[str] = None
    ) -> Dict[str, Any]:
        """Genera o re-evalúa perfiles de descubrimiento continuos para uno, un tipo de fuente o todos los activos."""
        self._load_data()
        assets = self.catalog.list_assets()
        
        if asset_id:
            target_assets = [a for a in assets if a["id"] == asset_id]
        elif source_type and source_type.upper() != "ALL":
            st = source_type.lower().strip()
            target_assets = []
            for a in assets:
                c = (a.get("cloud") or "").lower()
                s = (a.get("service") or "").lower()
                loc = (a.get("table_name") or a.get("project_or_db") or "").lower()
                if st == "bigquery" and "bigquery" in s:
                    target_assets.append(a)
                elif st == "mysql" and ("mysql" in c or "mysql" in s or "mysql" in a.get("id", "")):
                    target_assets.append(a)
                elif st in ("gcs", "storage") and ("storage" in s or "gcs" in s or a.get("id", "").startswith("gcp_gcs")):
                    target_assets.append(a)
                elif st in ("azure", "synapse") and ("azure" in c or "synapse" in s):
                    target_assets.append(a)
                elif st in ("aws", "redshift") and ("aws" in c or "redshift" in s):
                    target_assets.append(a)
                elif st in ("postgres", "postgresql") and ("postgres" in s or "postgres" in c):
                    target_assets.append(a)
                elif cloud and cloud.lower() in c:
                    target_assets.append(a)
        else:
            target_assets = assets
        
        now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        updated_profiles = []

        existing_profiles = {p["asset_id"]: p for p in self.data.get("discovery", {}).get("profiles", [])}

        for a in target_assets:
            col_list = a.get("columns", [])
            detected_it = []
            for c in col_list:
                name = c.get("name", "").lower()
                if "email" in name or "correo" in name: detected_it.append("EMAIL_ADDRESS")
                elif "name" in name or "nombre" in name: detected_it.append("PERSON_NAME")
                elif "phone" in name or "tel" in name: detected_it.append("PHONE_NUMBER")
                elif "card" in name or "tarjeta" in name: detected_it.append("CREDIT_CARD_NUMBER")
                elif "iban" in name or "bank" in name or "cuenta" in name: detected_it.append("IBAN_BANK_ACCOUNT")
                elif "tax" in name or "rfc" in name or "ssn" in name or "dni" in name: detected_it.append("TAX_ID_RFC_SSN")
                elif "ip" in name: detected_it.append("IP_ADDRESS")
                elif c.get("is_pii") and c.get("dlp_info_type"):
                    detected_it.append(c.get("dlp_info_type"))

            unique_it = sorted(list(set(detected_it)))
            
            # Compute Sensitivity & Risk
            if "CREDIT_CARD_NUMBER" in unique_it or "IBAN_BANK_ACCOUNT" in unique_it or len(unique_it) >= 3:
                sens = "HIGH"
                risk = "HIGH"
                rec = "Aplicar Dynamic Data Masking obligatorio y monitoreo con Job Triggers."
            elif len(unique_it) >= 1:
                sens = "MODERATE"
                risk = "MODERATE"
                rec = "Clasificar con Tag Template de Gobernanza y verificar encriptación."
            else:
                sens = "LOW"
                risk = "LOW"
                rec = "Activo verificado sin PII detectable. Certificado para consumo general."

            profile_entry = {
                "id": f"prof_{a['id']}",
                "asset_id": a["id"],
                "name": a.get("name", a.get("table_name")),
                "cloud": a.get("cloud", "GCP"),
                "service": a.get("service", "BigQuery"),
                "resource_location": f"{a.get('project_or_db')}.{a.get('dataset')}.{a.get('table_name')}",
                "sensitivity_level": sens,
                "data_risk_level": risk,
                "predicted_infotypes": unique_it,
                "columns_total": len(col_list),
                "sensitive_columns_count": len(unique_it),
                "free_text_risk": "HIGH" if "GCS" in a.get("service", "") or "Storage" in a.get("service", "") else "LOW",
                "encryption_type": "Customer-Managed Key (CMEK)" if a.get("cloud") == "GCP" and sens == "HIGH" else "Google-Managed Key",
                "status": "GENERATED",
                "last_profile_date": now_str,
                "recommendation": rec
            }

            existing_profiles[a["id"]] = profile_entry
            updated_profiles.append(profile_entry)

        self.data.setdefault("discovery", {})["profiles"] = list(existing_profiles.values())
        self._save_data()
        self.get_discovery_summary()

        return {
            "status": "success",
            "message": f"Se generaron/actualizaron {len(updated_profiles)} perfiles de descubrimiento SDP",
            "scanned_at": now_str,
            "profiles_updated": updated_profiles
        }

    # =========================================================================
    # 2. INFOTYPES (Built-in & Custom InfoTypes Creator)
    # =========================================================================
    def get_builtin_infotypes(self, category: Optional[str] = None, query: Optional[str] = None) -> List[Dict[str, Any]]:
        self._load_data()
        items = self.data.get("infotypes", {}).get("builtin", [])
        res = []
        for it in items:
            if category and category.lower() != it.get("category", "").lower():
                continue
            if query:
                q = query.lower()
                if q not in it.get("name", "").lower() and q not in it.get("display_name", "").lower() and q not in it.get("description", "").lower():
                    continue
            res.append(it)
        return res

    def get_custom_infotypes(self) -> List[Dict[str, Any]]:
        self._load_data()
        return self.data.get("infotypes", {}).get("custom", [])

    def create_custom_infotype(
        self,
        name: str,
        display_name: str,
        infotype_type: str = "REGEX",
        regex_pattern: Optional[str] = None,
        dictionary_words: Optional[List[str]] = None,
        likelihood: str = "VERY_LIKELY",
        hotwords: Optional[List[str]] = None,
        description: str = "",
        created_by: str = "Data Steward"
    ) -> Dict[str, Any]:
        self._load_data()
        
        # Clean clean name
        clean_name = re.sub(r"[^A-Z0-9_]", "", name.upper().strip())
        if not clean_name.startswith("CUSTOM_"):
            clean_name = f"CUSTOM_{clean_name}"

        # Validate regex if type is REGEX
        if infotype_type.upper() == "REGEX":
            if not regex_pattern:
                raise ValueError("Se requiere una expresión regular válida para tipo REGEX.")
            try:
                re.compile(regex_pattern)
            except re.error as e:
                raise ValueError(f"Expresión regular inválida: {e}")

        # Check uniqueness
        existing = [c for c in self.data.get("infotypes", {}).get("custom", []) if c["name"] == clean_name]
        if existing:
            raise ValueError(f"El InfoType personalizado con nombre '{clean_name}' ya existe.")

        now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        new_entry = {
            "id": f"custom_{clean_name.lower()}_{uuid.uuid4().hex[:6]}",
            "name": clean_name,
            "display_name": display_name.strip() or clean_name,
            "type": infotype_type.upper(),
            "description": description.strip() or f"InfoType personalizado {display_name}",
            "regex_pattern": regex_pattern.strip() if regex_pattern else "",
            "dictionary_words": dictionary_words or [],
            "likelihood": likelihood.upper(),
            "hotwords": hotwords or [],
            "created_by": created_by,
            "created_at": now_str,
            "status": "ACTIVE",
            "inspect_count": 0
        }

        self.data.setdefault("infotypes", {}).setdefault("custom", []).append(new_entry)
        self._save_data()
        return new_entry

    def test_custom_infotype(
        self,
        infotype_type: str = "REGEX",
        regex_pattern: Optional[str] = None,
        dictionary_words: Optional[List[str]] = None,
        sample_text: str = "",
        hotwords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Prueba un InfoType personalizado contra una muestra de texto en tiempo real."""
        if not sample_text:
            return {"status": "success", "matches_found": 0, "matches": []}

        matches = []
        if infotype_type.upper() == "REGEX" and regex_pattern:
            try:
                pattern = re.compile(regex_pattern)
                for m in pattern.finditer(sample_text):
                    matches.append({
                        "value": m.group(0),
                        "start": m.start(),
                        "end": m.end(),
                        "context": sample_text[max(0, m.start() - 20):min(len(sample_text), m.end() + 20)]
                    })
            except re.error as e:
                return {"status": "error", "message": f"Error en expresión regular: {e}", "matches": []}

        elif infotype_type.upper() == "DICTIONARY" and dictionary_words:
            for word in dictionary_words:
                w_clean = word.strip()
                if not w_clean: continue
                idx = 0
                while True:
                    found = sample_text.lower().find(w_clean.lower(), idx)
                    if found == -1: break
                    end = found + len(w_clean)
                    matches.append({
                        "value": sample_text[found:end],
                        "start": found,
                        "end": end,
                        "context": sample_text[max(0, found - 20):min(len(sample_text), end + 20)]
                    })
                    idx = end

        # Proximity hotwords score boost
        has_hotword = False
        if hotwords:
            sample_lower = sample_text.lower()
            for hw in hotwords:
                if hw.lower() in sample_lower:
                    has_hotword = True
                    break

        return {
            "status": "success",
            "matches_found": len(matches),
            "hotword_proximity_boost": has_hotword,
            "estimated_likelihood": "VERY_LIKELY" if (matches and has_hotword) else ("LIKELY" if matches else "UNLIKELY"),
            "matches": matches
        }

    def delete_custom_infotype(self, infotype_id: str) -> bool:
        self._load_data()
        custom_list = self.data.get("infotypes", {}).get("custom", [])
        new_list = [c for c in custom_list if c["id"] != infotype_id and c["name"] != infotype_id]
        if len(new_list) == len(custom_list):
            return False
        self.data.setdefault("infotypes", {})["custom"] = new_list
        self._save_data()
        return True

    # =========================================================================
    # 3. INSPECT JOBS (Trabajos de Inspección On-Demand)
    # =========================================================================
    def list_inspect_jobs(self) -> List[Dict[str, Any]]:
        self._load_data()
        return self.data.get("inspect_jobs", [])

    def create_and_run_inspect_job(
        self,
        name: str,
        target_asset_id: str,
        infotypes_selected: List[str],
        min_likelihood: str = "LIKELY",
        sampling_pct: int = 100,
        auto_apply_tags: bool = True,
        created_by: str = "Data Steward"
    ) -> Dict[str, Any]:
        self._load_data()
        asset = self.catalog.get_asset_by_id(target_asset_id)
        if not asset:
            raise ValueError(f"Asset con ID '{target_asset_id}' no encontrado.")

        # Dynamic real row count based on catalog asset
        findings_breakdown = []
        columns = asset.get("columns", [])
        total_findings = 0
        actual_total_rows = int(asset.get("row_count") or 50)
        rows_scanned = max(1, int(actual_total_rows * (sampling_pct / 100)))

        # Check which columns match selected infotypes
        for col in columns:
            col_name = col.get("name", "").lower()
            detected_it = None

            if ("email" in col_name or "correo" in col_name) and "EMAIL_ADDRESS" in infotypes_selected:
                detected_it = "EMAIL_ADDRESS"
            elif ("name" in col_name or "nombre" in col_name) and "PERSON_NAME" in infotypes_selected:
                detected_it = "PERSON_NAME"
            elif ("phone" in col_name or "tel" in col_name) and "PHONE_NUMBER" in infotypes_selected:
                detected_it = "PHONE_NUMBER"
            elif ("card" in col_name or "tarjeta" in col_name) and "CREDIT_CARD_NUMBER" in infotypes_selected:
                detected_it = "CREDIT_CARD_NUMBER"
            elif ("iban" in col_name or "bank" in col_name or "cuenta" in col_name) and "IBAN_BANK_ACCOUNT" in infotypes_selected:
                detected_it = "IBAN_BANK_ACCOUNT"
            elif ("tax" in col_name or "rfc" in col_name or "ssn" in col_name or "dni" in col_name) and any(x in infotypes_selected for x in ["TAX_ID_RFC_SSN", "US_SSN", "PERU_DNI", "MEXICO_RFC"]):
                detected_it = "TAX_ID_RFC_SSN"
            elif "id" in col_name and "CUSTOM_EMPLOYEE_ID" in infotypes_selected:
                detected_it = "CUSTOM_EMPLOYEE_ID"
            elif col.get("is_pii") and col.get("dlp_info_type") in infotypes_selected:
                detected_it = col.get("dlp_info_type")

            if detected_it:
                count_simulated = rows_scanned
                findings_breakdown.append({
                    "column": col.get("name"),
                    "infotype": detected_it,
                    "count": count_simulated,
                    "likelihood": min_likelihood
                })
                total_findings += 1

        now = datetime.datetime.utcnow()
        now_str = now.strftime("%Y-%m-%d %H:%M UTC")
        completed_str = (now + datetime.timedelta(seconds=45)).strftime("%Y-%m-%d %H:%M UTC")

        actions = ["Resultado persistido en tabla de auditoría Cloud DLP"]
        if auto_apply_tags:
            actions.append("Policy Tags y taxonomías de BigQuery sincronizadas automáticamente")

        new_job = {
            "job_id": f"job_insp_{now.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:4]}",
            "name": name.strip() or f"Inspección {asset.get('name')}",
            "target_asset_id": target_asset_id,
            "target_name": f"{asset.get('name')} ({asset.get('service')})",
            "target_type": asset.get("service", "BigQuery"),
            "target_location": f"{asset.get('project_or_db')}.{asset.get('dataset')}.{asset.get('table_name')}",
            "infotypes_selected": infotypes_selected,
            "min_likelihood": min_likelihood,
            "sampling_pct": sampling_pct,
            "status": "COMPLETED",
            "rows_scanned": rows_scanned,
            "findings_count": total_findings,
            "findings_breakdown": findings_breakdown,
            "actions_executed": actions,
            "created_at": now_str,
            "completed_at": completed_str,
            "duration_seconds": 45,
            "created_by": created_by
        }

        self.data.setdefault("inspect_jobs", []).insert(0, new_job)
        
        # Sincronizar estado en catálogo
        if total_findings > 0:
            asset.setdefault("dlp_status", {})["scanned"] = True
            asset["dlp_status"]["risk_level"] = "Crítico" if any(f["infotype"] in ["CREDIT_CARD_NUMBER", "IBAN_BANK_ACCOUNT"] for f in findings_breakdown) else "Alto"
            asset["dlp_status"]["info_types_found"] = [f["infotype"] for f in findings_breakdown]
            asset["dlp_status"]["last_scan_date"] = now_str
            self.catalog._save_data()

        self._save_data()
        return new_job

    # =========================================================================
    # 4. JOB TRIGGERS (Disparadores Programados)
    # =========================================================================
    def list_job_triggers(self) -> List[Dict[str, Any]]:
        self._load_data()
        return self.data.get("job_triggers", [])

    def create_job_trigger(
        self,
        name: str,
        description: str,
        schedule: str,
        target_asset_id: str,
        template_id: str = "tmpl_pii_latam_standard",
        created_by: str = "Data Steward"
    ) -> Dict[str, Any]:
        self._load_data()
        asset = self.catalog.get_asset_by_id(target_asset_id)
        if not asset:
            raise ValueError(f"Asset con ID '{target_asset_id}' no encontrado.")

        now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        
        new_trigger = {
            "trigger_id": f"trig_{uuid.uuid4().hex[:8]}",
            "name": name.strip(),
            "description": description.strip(),
            "schedule": schedule,
            "cron_expression": "0 2 * * *" if "diario" in schedule.lower() or "24" in schedule else "0 4 * * 0",
            "target_asset_id": target_asset_id,
            "target_name": asset.get("name", target_asset_id),
            "template_id": template_id,
            "status": "ACTIVE",
            "last_run": "Pendiente de primer disparo",
            "next_run": "Próxima ejecución según cronograma",
            "execution_count": 0,
            "created_by": created_by
        }

        self.data.setdefault("job_triggers", []).append(new_trigger)
        self._save_data()
        return new_trigger

    def toggle_job_trigger(self, trigger_id: str) -> Dict[str, Any]:
        self._load_data()
        triggers = self.data.get("job_triggers", [])
        for t in triggers:
            if t["trigger_id"] == trigger_id:
                t["status"] = "PAUSED" if t["status"] == "ACTIVE" else "ACTIVE"
                self._save_data()
                return {"status": "success", "trigger_id": trigger_id, "new_status": t["status"]}
        raise ValueError(f"Trigger con ID '{trigger_id}' no encontrado.")

    def run_job_trigger_now(self, trigger_id: str) -> Dict[str, Any]:
        self._load_data()
        triggers = self.data.get("job_triggers", [])
        for t in triggers:
            if t["trigger_id"] == trigger_id:
                now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                t["last_run"] = now_str
                t["execution_count"] = t.get("execution_count", 0) + 1
                
                # Run underlying inspect job
                tmpl_id = t.get("template_id", "tmpl_pii_latam_standard")
                templates = {tm["template_id"]: tm for tm in self.data.get("templates", {}).get("inspect_templates", [])}
                tmpl = templates.get(tmpl_id, {})
                selected_it = tmpl.get("infotypes", ["EMAIL_ADDRESS", "PERSON_NAME", "PHONE_NUMBER"])

                job = self.create_and_run_inspect_job(
                    name=f"Ejecución disparada: {t.get('name')}",
                    target_asset_id=t.get("target_asset_id"),
                    infotypes_selected=selected_it,
                    min_likelihood=tmpl.get("min_likelihood", "LIKELY"),
                    sampling_pct=100,
                    auto_apply_tags=True,
                    created_by=f"Trigger Automático ({t.get('trigger_id')})"
                )

                self._save_data()
                return {
                    "status": "success",
                    "message": f"Trigger '{t.get('name')}' ejecutado exitosamente.",
                    "job_generated": job
                }
        raise ValueError(f"Trigger con ID '{trigger_id}' no encontrado.")

    def delete_job_trigger(self, trigger_id: str) -> bool:
        self._load_data()
        triggers = self.data.get("job_triggers", [])
        new_list = [t for t in triggers if t["trigger_id"] != trigger_id]
        if len(new_list) == len(triggers):
            return False
        self.data["job_triggers"] = new_list
        self._save_data()
        return True

    # =========================================================================
    # 5. RISK ANALYSIS (Análisis Cuantitativo k-anonymity, l-diversity, delta-presence)
    #    CRÍTICO: EXCLUSIVO PARA BIGQUERY
    # =========================================================================
    def evaluate_bigquery_risk_analysis(
        self,
        asset_id: str,
        quasi_identifiers: Optional[List[str]] = None,
        sensitive_attributes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Calcula métricas de re-identificación k-anonymity y l-diversity.
        
        REGLA DE ARQUITECTURA: Esta funcionalidad es EXCLUSIVA para BigQuery.
        Si se intenta sobre otra fuente (GCS, MySQL, Azure), se rechaza con error explícito.
        """
        asset = self.catalog.get_asset_by_id(asset_id)
        if not asset:
            raise ValueError(f"Asset con ID '{asset_id}' no encontrado.")

        # Validación estricta de BigQuery
        service = (asset.get("service") or "").upper()
        cloud = (asset.get("cloud") or "").upper()
        
        is_bigquery = "BIGQUERY" in service or ("GCP" in cloud and "BIGQUERY" in asset.get("storage_format", "").upper())
        if not is_bigquery:
            raise ValueError(
                f"El servicio '{asset.get('service')}' ({asset.get('cloud')}) no soporta Risk Analysis de SDP. "
                "El análisis cuantitativo de re-identificación (k-anonymity, l-diversity, delta-presence) está disponible "
                "únicamente para conjuntos de datos estructurados de Google Cloud BigQuery."
            )

        self._load_data()
        existing_evals = self.data.get("risk_analysis", {}).get("evaluations", {})
        
        # If already computed and custom inputs not provided, return cached
        if asset_id in existing_evals and not quasi_identifiers and not sensitive_attributes:
            return existing_evals[asset_id]

        # Determine Quasi-Identifiers and Sensitive Attributes
        cols = asset.get("columns", [])
        available_col_names = [c.get("name") for c in cols]
        
        q_ids = quasi_identifiers or [c.get("name") for c in cols if c.get("is_pii") or "name" in c.get("name") or "phone" in c.get("name") or "segment" in c.get("name")]
        s_attrs = sensitive_attributes or [c.get("name") for c in cols if "card" in c.get("name") or "spend" in c.get("name") or "monto" in c.get("name") or "salary" in c.get("name")]

        if not q_ids:
            q_ids = available_col_names[:2] if len(available_col_names) >= 2 else available_col_names
        if not s_attrs:
            s_attrs = [available_col_names[-1]] if available_col_names else ["generic_sensitive_col"]

        now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        # Simulate statistical calculations
        total_rows = 154200 if "cliente" in asset.get("name", "").lower() else 2890000
        has_full_name = any("name" in q.lower() or "nombre" in q.lower() for q in q_ids)

        if has_full_name:
            min_k = 1
            vulnerable_k1 = int(total_rows * 0.0025)
            vulnerable_k5 = int(total_rows * 0.0095)
            reid_prob = 14.8
            risk_gauge = "MODERADO"
            gauge_color = "#f59e0b"
            k_status = "REQUIRES_GENERALIZATION"
        else:
            min_k = 4
            vulnerable_k1 = 0
            vulnerable_k5 = int(total_rows * 0.0002)
            reid_prob = 1.8
            risk_gauge = "BAJO"
            gauge_color = "#10b981"
            k_status = "WELL_PROTECTED"

        eval_report = {
            "asset_id": asset_id,
            "table_name": asset.get("table_name"),
            "dataset": asset.get("dataset"),
            "project": asset.get("project_or_db"),
            "total_records": total_rows,
            "evaluated_at": now_str,
            "quasi_identifiers": q_ids,
            "sensitive_attributes": s_attrs,
            "k_anonymity": {
                "min_k_value": min_k,
                "vulnerable_records_k1": vulnerable_k1,
                "vulnerable_percentage_k1": round((vulnerable_k1 / total_rows) * 100, 2),
                "records_k_less_than_5": vulnerable_k5,
                "vulnerable_percentage_k5": round((vulnerable_k5 / total_rows) * 100, 2),
                "status": k_status,
                "equivalence_classes_count": int(total_rows / max(min_k * 3, 1)),
                "distribution": [
                    {"k_range": "k = 1 (Identificable Directo)", "count": vulnerable_k1, "pct": round((vulnerable_k1 / total_rows) * 100, 2), "risk": "Alto"},
                    {"k_range": "k = 2 - 4 (Riesgo Significativo)", "count": max(0, vulnerable_k5 - vulnerable_k1), "pct": round(((vulnerable_k5 - vulnerable_k1) / total_rows) * 100, 2), "risk": "Medio"},
                    {"k_range": "k = 5 - 19 (Moderadamente Anónimo)", "count": int(total_rows * 0.12), "pct": 12.0, "risk": "Bajo"},
                    {"k_range": "k >= 20 (Altamente Protegido)", "count": total_rows - vulnerable_k5 - int(total_rows * 0.12), "pct": round(100 - (vulnerable_k5 / total_rows * 100) - 12.0, 2), "risk": "Mínimo"}
                ]
            },
            "l_diversity": {
                "min_l_value": 1 if min_k == 1 else 3,
                "sensitive_column": s_attrs[0] if s_attrs else "N/A",
                "distinct_values_avg": 4.8 if min_k == 1 else 14.5,
                "status": "MODERATE_DIVERSITY" if min_k == 1 else "HIGH_DIVERSITY",
                "risk_insight": "Se recomienda agrupar quasi-identificadores para garantizar diversidad de valores sensibles >= 3."
            },
            "delta_presence": {
                "reidentification_probability_pct": reid_prob,
                "risk_gauge": risk_gauge,
                "color": gauge_color,
                "benchmark_population": "Población de referencia en BigQuery Analytics Data Warehouse"
            },
            "anonymization_recommendations": [
                {
                    "technique": "Generalización de Rangos (Bucketization)",
                    "target_column": ", ".join(q_ids),
                    "action": "Agrupar columnas continuas o de texto en rangos para elevar el k-anonymity mínimo a k >= 5.",
                    "impact_on_utility": "Bajo (Conserva valor analítico para modelos ML)"
                },
                {
                    "technique": "Dynamic Data Masking (DDM)",
                    "target_column": ", ".join(s_attrs),
                    "action": "Vincular BigQuery Policy Tag con Enmascaramiento SHA-256 o Redacción Parcial.",
                    "impact_on_utility": "Nulo para usuarios sin permisos de lectura en claro"
                },
                {
                    "technique": "Tokenización Criptográfica Determinística",
                    "target_column": "customer_id / identificador_primario",
                    "action": "Reemplazar el ID con token reversible con clave Cloud KMS para preservar joins analíticos.",
                    "impact_on_utility": "Mantiene 100% de integridad referencial"
                }
            ]
        }

        self.data.setdefault("risk_analysis", {}).setdefault("evaluations", {})[asset_id] = eval_report
        self._save_data()
        return eval_report

    # =========================================================================
    # 6. CONFIGURACIÓN & PLANTILLAS (Templates & Content Policies)
    # =========================================================================
    def list_inspect_templates(self) -> List[Dict[str, Any]]:
        self._load_data()
        return self.data.get("templates", {}).get("inspect_templates", [])

    def create_inspect_template(
        self,
        name: str,
        description: str,
        infotypes: List[str],
        min_likelihood: str = "LIKELY",
        max_findings: int = 1000,
        created_by: str = "Data Steward"
    ) -> Dict[str, Any]:
        self._load_data()
        tmpl_id = f"tmpl_{uuid.uuid4().hex[:8]}"
        now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        new_tmpl = {
            "template_id": tmpl_id,
            "name": name.strip(),
            "description": description.strip(),
            "infotypes": infotypes,
            "min_likelihood": min_likelihood,
            "max_findings_per_item": max_findings,
            "created_by": created_by,
            "created_at": now_str,
            "active_usage_count": 0
        }

        self.data.setdefault("templates", {}).setdefault("inspect_templates", []).append(new_tmpl)
        self._save_data()
        return new_tmpl

    def list_deidentify_templates(self) -> List[Dict[str, Any]]:
        self._load_data()
        return self.data.get("templates", {}).get("deidentify_templates", [])

    def create_deidentify_template(
        self,
        name: str,
        transformation_type: str,
        description: str,
        parameters: Dict[str, Any],
        sample_input: str,
        sample_output: str,
        created_by: str = "Data Steward"
    ) -> Dict[str, Any]:
        self._load_data()
        tmpl_id = f"deid_{uuid.uuid4().hex[:8]}"

        new_tmpl = {
            "template_id": tmpl_id,
            "name": name.strip(),
            "transformation_type": transformation_type,
            "description": description.strip(),
            "parameters": parameters,
            "sample_input": sample_input,
            "sample_output": sample_output,
            "created_by": created_by
        }

        self.data.setdefault("templates", {}).setdefault("deidentify_templates", []).append(new_tmpl)
        self._save_data()
        return new_tmpl

    def list_content_policies(self) -> List[Dict[str, Any]]:
        self._load_data()
        return self.data.get("content_policies", [])

    def toggle_content_policy(self, policy_id: str) -> Dict[str, Any]:
        self._load_data()
        policies = self.data.get("content_policies", [])
        for pol in policies:
            if pol["policy_id"] == policy_id:
                pol["status"] = "DISABLED" if pol["status"] == "ENABLED" else "ENABLED"
                self._save_data()
                return {"status": "success", "policy_id": policy_id, "new_status": pol["status"]}
        raise ValueError(f"Content Policy '{policy_id}' no encontrada.")

    def evaluate_content_policies(self) -> Dict[str, Any]:
        self._load_data()
        policies = self.data.get("content_policies", [])
        now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        for pol in policies:
            if pol["status"] == "ENABLED":
                pol["last_enforced"] = now_str
                pol["enforced_count"] = pol.get("enforced_count", 0) + 1

        self._save_data()
        return {
            "status": "success",
            "message": f"Se evaluaron {len(policies)} políticas de contenido de Sensitive Data Protection",
            "evaluated_at": now_str,
            "policies": policies
        }

    # =========================================================================
    # 7. PERFIL RESPONSABLE (Role Tailored Overview & KPIs)
    # =========================================================================
    def get_persona_overview(self, profile_id: str) -> Dict[str, Any]:
        """Genera métricas, accesos y resúmenes adaptados al perfil responsable activo."""
        summary = self.get_discovery_summary()
        jobs = self.list_inspect_jobs()
        triggers = self.list_job_triggers()
        custom_it = self.get_custom_infotypes()
        policies = self.list_content_policies()

        if profile_id == "guardian_dato":
            return {
                "profile_id": "guardian_dato",
                "role_title": "Senior Data Steward & DPO (Guardián del Dato)",
                "mission": "Control total del ciclo de vida de PII, plantillas, desidentificación y análisis de riesgo.",
                "permissions": {
                    "can_create_infotypes": True,
                    "can_run_inspect_jobs": True,
                    "can_manage_triggers": True,
                    "can_run_risk_analysis": True,
                    "can_manage_templates": True,
                    "can_manage_policies": True
                },
                "key_kpis": [
                    {"label": "Tablas con PII Alta", "value": summary["high_sensitivity_count"], "color": "#e11d48"},
                    {"label": "InfoTypes Custom Creados", "value": len(custom_it), "color": "#10b981"},
                    {"label": "Triggers SDP Activos", "value": sum(1 for t in triggers if t["status"] == "ACTIVE"), "color": "#3b82f6"},
                    {"label": "Políticas en Cumplimiento", "value": f"{sum(1 for p in policies if p['status'] == 'ENABLED')}/{len(policies)}", "color": "#8b5cf6"}
                ],
                "recommended_actions": [
                    "Crear un nuevo Custom InfoType para códigos confidenciales de clientes",
                    "Ejecutar Risk Analysis en dim_clientes_360 para validar k-anonymity",
                    "Configurar Trigger de inspección periódica en tablas transaccionales"
                ]
            }
        elif profile_id == "arquitecto_ingeniero":
            return {
                "profile_id": "arquitecto_ingeniero",
                "role_title": "Lead Data Architect & SecOps (El Arquitecto)",
                "mission": "Operación de pipelines de inspección, conectores multi-cloud y encriptación CMEK/KMS.",
                "permissions": {
                    "can_create_infotypes": True,
                    "can_run_inspect_jobs": True,
                    "can_manage_triggers": True,
                    "can_run_risk_analysis": True,
                    "can_manage_templates": False,
                    "can_manage_policies": True
                },
                "key_kpis": [
                    {"label": "Jobs de Inspección Totales", "value": len(jobs), "color": "#0ea5e9"},
                    {"label": "Triggers Programados", "value": len(triggers), "color": "#3b82f6"},
                    {"label": "Activos BigQuery Analizados", "value": len(self.data.get("risk_analysis", {}).get("evaluations", {})), "color": "#10b981"},
                    {"label": "Protección CMEK Activa", "value": "100%", "color": "#059669"}
                ],
                "recommended_actions": [
                    "Automatizar Job Trigger nocturno en tablas de ventas BigQuery",
                    "Verificar políticas de salida en conexiones federadas MySQL/Azure",
                    "Monitorear latencia y muestreo en Inspect Jobs de gran volumen"
                ]
            }
        elif profile_id == "gestor_programa":
            return {
                "profile_id": "gestor_programa",
                "role_title": "Governance Manager & Agile Lead (El Gestor)",
                "mission": "Supervisión del cumplimiento de Content Policies, auditorías y priorización de remediación.",
                "permissions": {
                    "can_create_infotypes": False,
                    "can_run_inspect_jobs": True,
                    "can_manage_triggers": False,
                    "can_run_risk_analysis": True,
                    "can_manage_templates": False,
                    "can_manage_policies": True
                },
                "key_kpis": [
                    {"label": "Cumplimiento de Políticas", "value": "99.2%", "color": "#10b981"},
                    {"label": "Activos en Riesgo Alto", "value": summary["high_risk_count"], "color": "#e11d48"},
                    {"label": "Cobertura de Discovery", "value": f"{summary['total_tables_profiled']} Tablas", "color": "#3b82f6"},
                    {"label": "Sprints de Remediación", "value": "Fase 2 / 3", "color": "#ec4899"}
                ],
                "recommended_actions": [
                    "Revisar el Scorecard de Content Policies para el comité de gobierno",
                    "Asignar tareas de desidentificación al Data Steward responsable",
                    "Alinear SLAs de remediación PII con las métricas de madurez DMM"
                ]
            }
        else: # estratega_ejecutivo
            return {
                "profile_id": "estratega_ejecutivo",
                "role_title": "Chief Data Officer / C-Level (El Estratega)",
                "mission": "Visión macro de riesgo regulatorio, mitigación de multas GDPR/PCI y ROI de la privacidad.",
                "permissions": {
                    "can_create_infotypes": False,
                    "can_run_inspect_jobs": False,
                    "can_manage_triggers": False,
                    "can_run_risk_analysis": True,
                    "can_manage_templates": False,
                    "can_manage_policies": False
                },
                "key_kpis": [
                    {"label": "Índice Global de Privacidad", "value": "96.4 / 100", "color": "#8b5cf6"},
                    {"label": "Ahorro Estimado Riesgo Multas", "value": "$2.4M USD", "color": "#10b981"},
                    {"label": "Activos Críticos Protegidos", "value": f"{summary['total_tables_profiled'] - summary['high_risk_count']}/{summary['total_tables_profiled']}", "color": "#3b82f6"},
                    {"label": "Madurez SDP", "value": "Nivel 4 (Optimizado)", "color": "#5b21b6"}
                ],
                "recommended_actions": [
                    "Presentar resumen de mitigación de riesgo PII ante el Directorio",
                    "Aprobar presupuesto para tokenización reversible en nuevos Data Products",
                    "Autorizar expansión de políticas de descubrimiento hacia nubes satélite"
                ]
            }

    # =========================================================================
    # 8. DASHBOARD EJECUTIVO SENSITIVE DATA PROTECTION (LOOKER STUDIO TEMPLATE)
    # =========================================================================
    def get_dashboard_overview(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Retorna las métricas y series temporales para el Dashboard de Sensitive Data Protection (Summary Overview)."""
        filters = filters or {}
        project = filters.get("project", "-")
        asset_type = filters.get("asset_type", "-")
        data_risk = filters.get("data_risk", "-")
        encryption = filters.get("encryption", "-")
        data_asset = filters.get("data_asset", "-")
        infotype = filters.get("infotype", "-")
        data_sensitivity = filters.get("data_sensitivity", "-")
        is_public = filters.get("is_public", "-")
        data_location = filters.get("data_location", "-")
        date_range = filters.get("date_range", "-")

        # Base default figures (matching the GCP SDP Discovery Template)
        base_total = 7342
        base_locations = 15
        base_high_sensitive = 1452

        base_risk_high = 1452
        base_risk_low = 5780
        base_risk_moderate = 110

        base_sens_high = 1452
        base_sens_low = 5780
        base_sens_moderate = 110

        base_issue_cmek = 957
        base_issue_public = 1
        base_issue_policy_tags = 2402

        # Multiplier according to project / filter selection to simulate real dynamic lookups
        mult = 1.0
        if project and project != "-":
            if "prod" in project: mult = 0.65
            elif "marketing" in project: mult = 0.20
            elif "fintech" in project: mult = 0.10
            else: mult = 0.05
        
        if asset_type and asset_type != "-":
            if "BigQuery" in asset_type: mult *= 0.70
            elif "Storage" in asset_type or "GCS" in asset_type: mult *= 0.20
            elif "MySQL" in asset_type: mult *= 0.06
            else: mult *= 0.04

        if data_risk and data_risk != "-":
            if data_risk == "RISK_HIGH":
                base_risk_low = 0
                base_risk_moderate = 0
                base_total = int(base_risk_high * mult)
            elif data_risk == "RISK_LOW":
                base_risk_high = 0
                base_risk_moderate = 0
                base_high_sensitive = 0
                base_total = int(base_risk_low * mult)
            elif data_risk == "RISK_MODERATE":
                base_risk_high = 0
                base_risk_low = 0
                base_high_sensitive = 0
                base_total = int(base_risk_moderate * mult)

        if data_sensitivity and data_sensitivity != "-":
            if data_sensitivity == "SENSITIVITY_HIGH":
                base_sens_low = 0
                base_sens_moderate = 0
            elif data_sensitivity == "SENSITIVITY_LOW":
                base_sens_high = 0
                base_sens_moderate = 0
            elif data_sensitivity == "SENSITIVITY_MODERATE":
                base_sens_high = 0
                base_sens_low = 0

        total_profiled = max(1, int(base_total * mult))
        locations_discovered = max(1, int(base_locations if mult > 0.5 else base_locations * mult + 1))
        highly_sensitive = int(base_high_sensitive * mult) if data_risk != "RISK_LOW" else 0

        risk_high = int(base_risk_high * mult)
        risk_low = int(base_risk_low * mult)
        risk_moderate = int(base_risk_moderate * mult)

        sens_high = int(base_sens_high * mult)
        sens_low = int(base_sens_low * mult)
        sens_moderate = int(base_sens_moderate * mult)

        issue_cmek = int(base_issue_cmek * mult)
        issue_public = 1 if mult > 0.3 and is_public in ("-", "True", "Public") else 0
        issue_policy_tags = int(base_issue_policy_tags * mult)

        # InfoType distribution
        infotype_distribution = [
            {"name": "none", "label": "none (Sin PII)", "pct": 48.5, "count": int(total_profiled * 0.485), "color": "#0084ff"},
            {"name": "EMAIL_ADDRESS", "label": "EMAIL_ADDRESS", "pct": 12.3, "count": int(total_profiled * 0.123), "color": "#ec4899"},
            {"name": "CREDIT_CARD_NUMBER", "label": "CREDIT_CARD_NUMBER", "pct": 11.2, "count": int(total_profiled * 0.112), "color": "#f97316"},
            {"name": "PERSON_NAME", "label": "PERSON_NAME", "pct": 10.9, "count": int(total_profiled * 0.109), "color": "#06b6d4"},
            {"name": "US_SOCIAL_SECURITY_NUMBER", "label": "US_SOCIAL_SECURITY_N...", "pct": 4.2, "count": int(total_profiled * 0.042), "color": "#8b5cf6"},
            {"name": "PHONE_NUMBER", "label": "PHONE_NUMBER", "pct": 3.8, "count": int(total_profiled * 0.038), "color": "#6366f1"},
            {"name": "VEHICLE_IDENTIFICATION_NUMBER", "label": "VEHICLE_IDENTIFICATIO...", "pct": 3.1, "count": int(total_profiled * 0.031), "color": "#64748b"},
            {"name": "GENDER", "label": "GENDER", "pct": 2.5, "count": int(total_profiled * 0.025), "color": "#78716c"},
            {"name": "DATE_OF_BIRTH", "label": "DATE_OF_BIRTH", "pct": 2.0, "count": int(total_profiled * 0.020), "color": "#10b981"},
            {"name": "others", "label": "others", "pct": 1.5, "count": int(total_profiled * 0.015), "color": "#ef4444"}
        ]

        # Time series points (Sep 2023 to Mar 2024)
        time_series = [
            {"date": "Sep 25, 2023", "low": 480, "high": 45, "moderate": 5},
            {"date": "Oct 1, 2023", "low": 490, "high": 40, "moderate": 4},
            {"date": "Oct 7, 2023", "low": 500, "high": 75, "moderate": 3},
            {"date": "Oct 13, 2023", "low": 495, "high": 12, "moderate": 1},
            {"date": "Oct 19, 2023", "low": 490, "high": 10, "moderate": 1},
            {"date": "Oct 25, 2023", "low": 492, "high": 10, "moderate": 1},
            {"date": "Oct 31, 2023", "low": 485, "high": 9, "moderate": 1},
            {"date": "Nov 6, 2023", "low": 10, "high": 9, "moderate": 1},
            {"date": "Nov 12, 2023", "low": 110, "high": 9, "moderate": 1},
            {"date": "Nov 18, 2023", "low": 100, "high": 8, "moderate": 1},
            {"date": "Nov 24, 2023", "low": 120, "high": 8, "moderate": 1},
            {"date": "Nov 30, 2023", "low": 100, "high": 7, "moderate": 1},
            {"date": "Dec 6, 2023", "low": 98, "high": 8, "moderate": 1},
            {"date": "Dec 12, 2023", "low": 100, "high": 3, "moderate": 1},
            {"date": "Dec 18, 2023", "low": 102, "high": 12, "moderate": 1},
            {"date": "Dec 24, 2023", "low": 75, "high": 8, "moderate": 1},
            {"date": "Dec 30, 2023", "low": 78, "high": 9, "moderate": 1},
            {"date": "Jan 5, 2024", "low": 80, "high": 10, "moderate": 1},
            {"date": "Jan 11, 2024", "low": 82, "high": 9, "moderate": 1},
            {"date": "Jan 17, 2024", "low": 80, "high": 10, "moderate": 1},
            {"date": "Jan 23, 2024", "low": 79, "high": 8, "moderate": 1},
            {"date": "Jan 29, 2024", "low": 81, "high": 15, "moderate": 1},
            {"date": "Feb 4, 2024", "low": 80, "high": 9, "moderate": 1},
            {"date": "Feb 10, 2024", "low": 82, "high": 11, "moderate": 1},
            {"date": "Feb 16, 2024", "low": 80, "high": 18, "moderate": 1},
            {"date": "Feb 22, 2024", "low": 81, "high": 8, "moderate": 1},
            {"date": "Feb 28, 2024", "low": 115, "high": 10, "moderate": 1},
            {"date": "Mar 5, 2024", "low": 12, "high": 9, "moderate": 1},
            {"date": "Mar 11, 2024", "low": 15, "high": 12, "moderate": 1}
        ]

        return {
            "status": "success",
            "metadata": {
                "title": "Sensitive Data Protection Dashboard",
                "subtitle": "Summary Overview",
                "engine": "Google Cloud Sensitive Data Protection (Discovery & Cloud DLP API)",
                "generated_at": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                "applied_filters": {
                    "project": project,
                    "asset_type": asset_type,
                    "data_risk": data_risk,
                    "encryption": encryption,
                    "date_range": date_range,
                    "data_asset": data_asset,
                    "infotype": infotype,
                    "data_sensitivity": data_sensitivity,
                    "is_public": is_public,
                    "data_location": data_location
                }
            },
            "kpis": {
                "data_assets_profiled": total_profiled,
                "data_locations_discovered": locations_discovered,
                "highly_sensitive_assets": highly_sensitive
            },
            "data_risk": {
                "RISK_HIGH": risk_high,
                "RISK_LOW": risk_low,
                "RISK_MODERATE": risk_moderate
            },
            "data_sensitivity": {
                "SENSITIVITY_HIGH": sens_high,
                "SENSITIVITY_LOW": sens_low,
                "SENSITIVITY_MODERATE": sens_moderate
            },
            "infotypes_distribution": infotype_distribution,
            "security_issues": [
                {
                    "id": "issue_cmek",
                    "title": "Highly sensitive data assets without customer-managed encryption keys",
                    "count": issue_cmek,
                    "severity": "WARNING",
                    "action_label": "Aplicar CMEK / Cloud KMS",
                    "status": "REQUIRES_KEY_ROTATION"
                },
                {
                    "id": "issue_public_asset",
                    "title": "Sensitive data assets shared publicly",
                    "count": issue_public,
                    "severity": "CRITICAL",
                    "action_label": "Aislar y Restringir IAM",
                    "status": "OPEN_ALERT" if issue_public > 0 else "RESOLVED"
                },
                {
                    "id": "issue_column_policy",
                    "title": "Highly sensitive BigQuery columns without a column-level policy",
                    "count": issue_policy_tags,
                    "severity": "HIGH",
                    "action_label": "Auto-Tagging & Policy Tags BQ",
                    "status": "UNPROTECTED_PII"
                }
            ],
            "time_series": time_series,
            "filter_options": {
                "projects": ["-", "corp-analytics-prod", "sales-crm-eu", "fintech-core-latam", "marketing-dw", "retail-ecommerce-prod"],
                "asset_types": ["-", "BigQuery Table", "Cloud Storage (GCS)", "Cloud SQL (MySQL)", "Azure Synapse Table", "AWS Redshift Table"],
                "data_risks": ["-", "RISK_HIGH", "RISK_LOW", "RISK_MODERATE"],
                "encryptions": ["-", "Customer-Managed Key (CMEK)", "Google-Managed Key", "Cloud KMS HSM"],
                "data_assets": ["-", "dim_clientes_360", "fact_ventas_pos", "ecommerce_payments_raw", "credit_risk_scoring", "medical_records_anon", "pos_card_swipes"],
                "infotypes": ["-", "EMAIL_ADDRESS", "CREDIT_CARD_NUMBER", "PERSON_NAME", "US_SOCIAL_SECURITY_NUMBER", "PHONE_NUMBER", "VEHICLE_IDENTIFICATION_NUMBER", "GENDER", "DATE_OF_BIRTH", "IBAN_BANK_ACCOUNT", "TAX_ID_RFC_SSN"],
                "data_sensitivities": ["-", "SENSITIVITY_HIGH", "SENSITIVITY_LOW", "SENSITIVITY_MODERATE"],
                "is_public_options": ["-", "False", "True"],
                "data_locations": ["-", "us-central1 (Iowa)", "us-east1 (S. Carolina)", "europe-west1 (Belgium)", "southamerica-east1 (São Paulo)", "global"],
                "date_ranges": ["-", "Sep 25, 2023 - Mar 11, 2024", "Últimos 30 días", "Últimos 90 días", "Año 2024", "Histórico Completo"]
            }
        }

    def remediate_dashboard_issue(self, issue_id: str) -> Dict[str, Any]:
        """Aplica una remediación directa a los problemas de seguridad detectados en el Dashboard."""
        self._load_data()
        now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        if issue_id == "issue_cmek":
            # Encrypt sensitive tables with CMEK
            profiles = self.data.get("discovery", {}).get("profiles", [])
            updated = 0
            for p in profiles:
                if p.get("sensitivity_level") == "HIGH":
                    p["encryption_type"] = "Customer-Managed Key (CMEK) via Cloud KMS"
                    updated += 1
            self._save_data()
            return {
                "status": "success",
                "issue_id": issue_id,
                "message": f"Se aplicó encriptación con Customer-Managed Encryption Key (CMEK) a {updated} activos sensibles.",
                "remediated_at": now_str
            }
        elif issue_id == "issue_public_asset":
            return {
                "status": "success",
                "issue_id": issue_id,
                "message": "Se revocaron los permisos públicos ('allUsers') en el bucket GCS. Acceso restringido a identidades autenticadas de gobierno.",
                "remediated_at": now_str
            }
        elif issue_id == "issue_column_policy":
            # Auto-tag all high PII columns with Policy Tags
            profiles = self.data.get("discovery", {}).get("profiles", [])
            for p in profiles:
                if p.get("sensitivity_level") == "HIGH":
                    self.catalog.auto_tag_with_sdp(p["asset_id"])
            return {
                "status": "success",
                "issue_id": issue_id,
                "message": "Se aplicaron BigQuery Column-Level Policy Tags y Dynamic Data Masking a todas las columnas de alta sensibilidad.",
                "remediated_at": now_str
            }
        return {"status": "error", "message": f"Tipo de problema desconocido: {issue_id}"}


sdp_manager = SDPManager()

