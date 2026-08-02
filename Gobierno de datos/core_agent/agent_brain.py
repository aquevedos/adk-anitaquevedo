"""Cerebro y Motor de Razonamiento del Agente con Soporte de 4 Perfiles de Gobierno."""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from modulos.modulo1_catalogo_activo import catalog_manager
from modulos.modulo2_dlp_seguridad_pii import dlp_scanner, policy_tagger, sdp_manager
from modulos.modulo3_calidad_dataplex import quality_engine
from modulos.modulo4_linaje_trazabilidad import lineage_graph_builder
from modulos.modulo5_seguridad_cumplimiento import privacy_guard
from modulos.modulo6_data_stewards_ia import stewards_manager
from modulos.modulo7_policy_as_code_mcp import policy_engine
from modulos.conectores_multicloud import connector_factory
from modulos.perfiles_gobierno import firestore_profile_service

logger = logging.getLogger("agent_brain")


class DataGovernanceAgentBrain:
    def __init__(self):
        self.catalog = catalog_manager
        self.dlp = dlp_scanner
        self.sdp = sdp_manager
        self.tagger = policy_tagger
        self.quality = quality_engine
        self.lineage = lineage_graph_builder
        self.privacy = privacy_guard
        self.stewards = stewards_manager
        self.connectors = connector_factory
        self.profiles = firestore_profile_service
        self.policies = policy_engine

    async def chat(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        profile_id: Optional[str] = None
    ) -> Dict[str, Any]:
        msg = user_message.lower().strip()
        
        # Get active profile
        if profile_id:
            profile = self.profiles.get_profile(profile_id) or self.profiles.get_active_profile()
        else:
            profile = self.profiles.get_active_profile()

        # Welcome or greeting
        if any(w in msg for w in ["hola", "buenos días", "buenas tardes", "quién eres", "inicio", "help", "ayuda"]):
            return {
                "message": self._generate_welcome_for_profile(profile),
                "action_type": "welcome",
                "active_profile": profile,
                "suggested_actions": profile.get("quick_prompts", [])
            }

        # Actualizar metadatos
        if ("actualiza" in msg or "cambia" in msg or "modifica" in msg) and ("descripción" in msg or "descripcion" in msg or "steward" in msg or "metadato" in msg):
            return self._handle_update_metadata(user_message, profile)

        # Sensitive Data Protection (SDP), Risk Analysis, InfoTypes, Triggers, Discovery
        if any(w in msg for w in ["sdp", "dlp", "pii", "enmascarar", "sensible", "policy tag", "risk analysis", "k-anonymity", "l-diversity", "infotype", "trigger", "discovery", "desidentificacion"]):
            return self._handle_dlp_action(user_message, profile)

        # Calidad Dataplex
        if "calidad" in msg or "dataplex" in msg or "freshness" in msg or "frescura" in msg or "nulos" in msg or "duplicados" in msg:
            return self._handle_quality_action(user_message, profile)

        # Linaje
        if "linaje" in msg or "lineage" in msg or "trazabilidad" in msg or "origen" in msg or "impacto" in msg:
            return self._handle_lineage_action(user_message, profile)

        # Policy as Code / Knowledge Catalog MCP
        if any(w in msg for w in ["política", "politica", "policy", "scorecard", "violacion", "violación", "cumplimiento", "remediar"]):
            return self._handle_policy_action(user_message, profile)

        # Búsqueda y análisis general
        return self._handle_search_and_explain(user_message, profile)

    def _generate_welcome_for_profile(self, profile: Dict[str, Any]) -> str:
        avatar = profile.get("avatar", "🛡️")
        name = profile.get("name", "Agente de Gobierno")
        role = profile.get("role", "Especialista")
        mission = profile.get("mission", "Gobernar datos.")

        return (
            f"¡Hola! Soy **{avatar} {name}** (*{role}*).\n\n"
            f"🎯 **Mi Misión:** {mission}\n\n"
            f"### Habilidades Clave en mi Rol:\n" +
            "\n".join([f"- {s}" for s in profile.get("skills", [])]) +
            f"\n\n*¿Qué iniciativa, activo de datos o decisión estratégica abordaremos hoy?*"
        )

    def _find_best_asset(self, query: str) -> Optional[Dict[str, Any]]:
        res = self.catalog.search_semantic(query)
        if res: return res[0]
        # Check if query suggests MySQL
        q_lower = query.lower()
        assets = self.catalog.list_assets()
        if any(k in q_lower for k in ["mysql", "aiven", "externa", "external", "10283", "defaultdb"]):
            for a in assets:
                if "mysql" in a.get("cloud", "").lower() or "mysql" in a.get("id", "").lower():
                    return a
        return assets[0] if assets else None

    def _format_six_steps(self, resumen: str, asset: Dict[str, Any], profile: Dict[str, Any], custom_dlp: Optional[str] = None) -> str:
        service_name = asset.get('service') or ('Aiven MySQL Engine' if 'MYSQL' in asset.get('cloud', '').upper() else 'BigQuery Knowledge Catalog')
        location = f"[{asset.get('cloud')} | {service_name}] `{asset.get('project_or_db')}.{asset.get('dataset')}.{asset.get('table_name')}`"
        
        # DLP
        dlp_stat = asset.get("dlp_status", {})
        if custom_dlp:
            dlp_info = custom_dlp
        else:
            infotypes = ", ".join(dlp_stat.get("info_types_found", [])) or "Ninguno detectado"
            tags_active = "✅ Aplicadas (Dynamic Masking Activo)" if dlp_stat.get("policy_tags_applied") else "⚠️ Pendiente de aplicar"
            dlp_info = (
                f"- **Nivel de Riesgo:** `{dlp_stat.get('risk_level', 'Bajo')}`\n"
                f"- **InfoTypes Detectados:** {infotypes}\n"
                f"- **Policy Tags / Enmascaramiento:** {tags_active}"
            )

        # Quality
        q_stat = asset.get("dataplex_quality", {})
        score = q_stat.get("overall_score", 95.0)
        score_emoji = "🟢" if score >= 90 else "🟡"
        quality_info = (
            f"- **Dataplex Quality Score:** {score_emoji} **{score}%** ({q_stat.get('status', 'PASSED')})\n"
            f"- **Frescura:** Actualizado hace ~{q_stat.get('freshness_hours', 1)} horas\n"
            f"- **Completitud y Duplicados:** Nulos {q_stat.get('null_rate_pct', 0)}% | Duplicados {q_stat.get('duplicate_rate_pct', 0)}% | Anomalías: {q_stat.get('anomaly_count', 0)}"
        )

        # Lineage
        lin_data = asset.get("lineage", {})
        up_sources = ", ".join([u.get("source", "") for u in lin_data.get("upstream", [])]) or "Origen raíz (Cluster BD)"
        down_targets = ", ".join([d.get("target", "") for d in lin_data.get("downstream", [])]) or "Consumo analítico federado"
        lineage_info = f"- **Orígenes Upstream:** {up_sources}\n- **Destinos Downstream:** {down_targets}"

        # Golden Query / Next Step tailored by persona
        p_id = profile.get("id", "guardian_dato")
        golden_sql = asset.get("golden_query", f"SELECT * FROM `{asset.get('table_name')}` LIMIT 10;")
        is_mysql = "MYSQL" in asset.get("cloud", "").upper() or "mysql" in asset.get("id", "").lower()

        if p_id == "estratega_ejecutivo":
            next_step = (
                f"💼 **Perspectiva de Negocio & ROI:** Este activo es clave para el dominio `{asset.get('domain')}`. "
                f"Mantener la calidad en **{score}%** reduce costos de retrabajo y garantiza decisiones de alta confiabilidad.\n\n"
                f"```sql\n-- Golden Query Auditada para Reportes Financieros\n{golden_sql}\n```\n"
                f"👤 **Data Steward Responsable:** {asset.get('steward')}"
            )
        elif p_id == "gestor_programa":
            next_step = (
                f"📋 **Gobierno y Matriz RACI:** El rol de **Accountable** está asignado al Owner de `{asset.get('domain')}` y el **Responsible** a `{asset.get('steward')}`.\n\n"
                f"```sql\n-- Consulta Pre-Aprobada según Políticas de Dominio\n{golden_sql}\n```"
            )
        elif p_id == "arquitecto_ingeniero":
            if is_mysql:
                next_step = (
                    f"⚙️ **Arquitectura Técnica & Conectividad Multi-Cloud:**\n"
                    f"- **Motor y Almacenamiento:** `{asset.get('storage_format', 'MySQL 8.0 InnoDB')}` en `{asset.get('project_or_db')}`.\n"
                    f"- **Protocolo:** TLS/SSL encriptado vía puerto `10283` con Dataplex Discovery Agent.\n"
                    f"- **Seguridad & Enmascaramiento:** Reglas de Dynamic Data Masking en columnas PII (`nombre_completo`, `email`).\n"
                    f"- **Federación:** Replicación hacia Google Cloud BigQuery (`corp-analytics-prod.raw_zone`) y exposición en Vertex AI para RAG.\n\n"
                    f"```sql\n-- Golden Query Auditada para MySQL / Replicación BigQuery\n{golden_sql}\n```\n"
                    f"🔗 **Pipeline Recomendado:** Sincronización continua vía Dataplex Ingestion / Cloud Data Fusion."
                )
            else:
                next_step = (
                    f"⚙️ **Arquitectura Técnica:** Tabla almacenada en `{asset.get('storage_format', 'BigQuery Columnar')}` con particionamiento y reglas de seguridad aplicadas a nivel de columna.\n\n"
                    f"```sql\n-- Query Optimizada con Escaneo Reducido de Bytes\n{golden_sql}\n```\n"
                    f"🔗 **Pipeline Recomendado:** Sincronización continua vía Dataplex / BigQuery Data Transfer."
                )
        else: # guardian_dato
            next_step = (
                f"```sql\n-- Golden Query Pre-Aprobada (Campos PII Enmascarados)\n{golden_sql}\n```\n"
                f"👤 **Data Steward Responsable:** {asset.get('steward')}"
            )

        return (
            f"### 1. 📌 Resumen Ejecutivo / Acción Realizada\n{resumen}\n\n"
            f"### 2. 📍 Ubicación y Origen\n{location}\n\n"
            f"### 3. 🔒 Clasificación y Sensibilidad (DLP)\n{dlp_info}\n\n"
            f"### 4. 🩺 Salud y Calidad del Dato\n{quality_info}\n\n"
            f"### 5. 🔗 Linaje Rápido\n{lineage_info}\n\n"
            f"### 6. 💡 Siguiente Paso / Perspectiva ({profile.get('name')})\n{next_step}"
        )

    def _handle_search_and_explain(self, query: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        asset = self._find_best_asset(query)
        if not asset:
            return {"message": "No se encontraron activos coincidentes en el catálogo.", "action_type": "not_found"}

        resumen = (
            f"[{profile.get('avatar')} {profile.get('name')}]: Se analizó el activo **{asset.get('name')}** "
            f"a través del Context Graph de Knowledge Catalog en el dominio `{asset.get('domain')}` con {len(asset.get('columns', []))} columnas registradas."
        )
        return {
            "message": self._format_six_steps(resumen, asset, profile),
            "action_type": "catalog_query",
            "asset_id": asset.get("id"),
            "asset_data": asset,
            "active_profile": profile
        }

    def _handle_dlp_action(self, query: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        q_lower = query.lower()
        asset = self._find_best_asset(query) or self.catalog.list_assets()[0]
        
        # 1. Caso: Risk Analysis Cuantitativo (k-anonymity, l-diversity, delta-presence)
        if any(w in q_lower for w in ["risk analysis", "k-anonymity", "l-diversity", "re-identificacion", "reidentificacion", "re-identificación"]):
            is_bq = "BIGQUERY" in (asset.get("service") or "").upper() or ("GCP" in (asset.get("cloud") or "").upper() and "BIGQUERY" in asset.get("storage_format", "").upper())
            if not is_bq:
                resumen = (
                    f"[{profile.get('avatar')} {profile.get('name')}]: ⚠️ **Restricción de Arquitectura SDP:** "
                    f"El **Análisis Cuantitativo de Riesgo** (*k-anonymity*, *l-diversity*, *delta-presence*) de Sensitive Data Protection "
                    f"está diseñado y disponible **exclusivamente para Google Cloud BigQuery**. La tabla actual `{asset.get('name')}` es de tipo `{asset.get('cloud')} ({asset.get('service')})`. "
                    f"Para ejecutar Risk Analysis, selecciona un dataset estructurado en BigQuery como `dim_clientes_360` o `fact_ventas_pos`."
                )
                return {
                    "message": self._format_six_steps(resumen, asset, profile),
                    "action_type": "sdp_risk_analysis_notice",
                    "asset_id": asset.get("id"),
                    "active_profile": profile
                }
            else:
                try:
                    risk_rep = self.sdp.evaluate_bigquery_risk_analysis(asset["id"])
                    k_stat = risk_rep.get("k_anonymity", {})
                    l_stat = risk_rep.get("l_diversity", {})
                    dp_stat = risk_rep.get("delta_presence", {})
                    
                    custom_dlp_info = (
                        f"📊 **Métricas de Risk Analysis (Sensitive Data Protection en BigQuery):**\n"
                        f"- **k-anonymity Mínimo:** `k = {k_stat.get('min_k_value')}` (Registros únicos vulnerables k=1: **{k_stat.get('vulnerable_records_k1')}** - {k_stat.get('vulnerable_percentage_k1')}%)\n"
                        f"- **l-diversity Mínimo:** `l = {l_stat.get('min_l_value')}` (Columna sensible: `{l_stat.get('sensitive_column')}`, diversidad promedio: {l_stat.get('distinct_values_avg')})\n"
                        f"- **Delta-presence / Re-identificación:** {dp_stat.get('risk_gauge')} (**{dp_stat.get('reidentification_probability_pct')}%**)\n"
                        f"- **Recomendación:** {risk_rep.get('anonymization_recommendations', [{}])[0].get('action', 'Aplicar Dynamic Data Masking')}"
                    )
                    resumen = f"[{profile.get('avatar')} {profile.get('name')}]: 📊 **Risk Analysis Cuantitativo BigQuery Completado:** Nivel de re-identificación `{dp_stat.get('risk_gauge')}` ({dp_stat.get('reidentification_probability_pct')}%) con `k-anonymity min = {k_stat.get('min_k_value')}`."
                    return {
                        "message": self._format_six_steps(resumen, asset, profile, custom_dlp=custom_dlp_info),
                        "action_type": "sdp_risk_analysis",
                        "asset_id": asset.get("id"),
                        "risk_report": risk_rep,
                        "active_profile": profile
                    }
                except Exception as e:
                    logger.error(f"Error evaluating risk analysis in brain: {e}")

        # 2. Caso: Custom InfoTypes o Job Triggers
        if "infotype" in q_lower or "custom" in q_lower or "trigger" in q_lower or "disparador" in q_lower:
            custom_list = self.sdp.get_custom_infotypes()
            triggers_list = self.sdp.list_job_triggers()
            c_names = ", ".join([c['name'] for c in custom_list]) or "Ninguno registrado"
            t_names = ", ".join([t['name'] for t in triggers_list]) or "Ninguno configurado"
            
            resumen = (
                f"[{profile.get('avatar')} {profile.get('name')}]: ⚙️ **Configuración SDP:**\n"
                f"- **Custom InfoTypes Disponibles:** `{c_names}`\n"
                f"- **Disparadores Programados (Job Triggers):** `{t_names}`\n"
                f"- Puedes crear nuevos Custom InfoTypes con Regex o Diccionarios y programar escaneos automáticos desde la pestaña de SDP."
            )
            return {
                "message": self._format_six_steps(resumen, asset, profile),
                "action_type": "sdp_config_info",
                "asset_id": asset.get("id"),
                "active_profile": profile
            }

        # 3. Caso: Escaneo e Inspección estándar o aplicación de Policy Tags
        scan_res = self.dlp.inspect_asset(asset["id"])
        if "aplica" in query.lower() or "enmascara" in query.lower() or "protege" in query.lower():
            apply_res = self.tagger.apply_tags_and_masking(asset["id"], auto_mask=True)
            resumen = f"[{profile.get('avatar')} {profile.get('name')}]: 🛡️ **Protección Ejecutada:** Se escanearon datos sensibles con Cloud DLP y se aplicaron **BigQuery Policy Tags** con **Dynamic Data Masking** en {len(apply_res['applied_tags'])} columnas."
        else:
            resumen = f"[{profile.get('avatar')} {profile.get('name')}]: 🔍 **Inspección Cloud DLP / SDP:** Se detectaron {scan_res.get('infotypes_detected_count')} tipos de datos sensibles (PII) con nivel de riesgo `{scan_res.get('risk_level')}`."

        asset = self.catalog.get_asset_by_id(asset["id"])
        return {
            "message": self._format_six_steps(resumen, asset, profile),
            "action_type": "dlp_inspection",
            "asset_id": asset.get("id"),
            "scan_data": scan_res,
            "active_profile": profile
        }

    def _handle_quality_action(self, query: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        asset = self._find_best_asset(query) or self.catalog.list_assets()[0]
        q_res = self.quality.evaluate_asset(asset["id"])
        score = q_res["quality"]["overall_score"]
        
        if score >= 90:
            resumen = f"[{profile.get('avatar')} {profile.get('name')}]: ✅ **Calidad Dataplex Aprobada:** La tabla obtuvo **{score}%**, cumpliendo con los SLAs corporativos."
        else:
            resumen = f"[{profile.get('avatar')} {profile.get('name')}]: ⚠️ **Alerta de Calidad Dataplex (<90%):** La tabla obtuvo **{score}%**. Se requiere atención del Data Steward."

        asset = self.catalog.get_asset_by_id(asset["id"])
        return {
            "message": self._format_six_steps(resumen, asset, profile),
            "action_type": "quality_scan",
            "asset_id": asset.get("id"),
            "quality_data": q_res["quality"],
            "active_profile": profile
        }

    def _handle_lineage_action(self, query: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        asset = self._find_best_asset(query) or self.catalog.list_assets()[0]
        lin = self.lineage.build_graph(asset["id"])
        resumen = f"[{profile.get('avatar')} {profile.get('name')}]: 🔗 **Trazabilidad Reconstruida:** Grafo end-to-end con {lin['upstream_count']} fuentes upstream y {lin['downstream_count']} consumidores downstream."
        return {
            "message": self._format_six_steps(resumen, asset, profile),
            "action_type": "lineage_graph",
            "asset_id": asset.get("id"),
            "lineage_data": lin,
            "active_profile": profile
        }

    def _handle_update_metadata(self, query: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        asset = self._find_best_asset(query) or self.catalog.list_assets()[0]
        match = re.search(r'(?:descripción|descripcion)\s*(?:a|como|:)\s*["\']?([^"\']+)["\']?', query, re.IGNORECASE)
        new_desc = match.group(1).strip() if match else f"{asset.get('description')} (Actualizada por {profile.get('name')})."
        
        self.catalog.update_metadata(asset["id"], description=new_desc)
        asset = self.catalog.get_asset_by_id(asset["id"])
        resumen = f"[{profile.get('avatar')} {profile.get('name')}]: 📝 **Metadatos Actualizados:** Se actualizó la descripción técnica en Knowledge Catalog para `{asset.get('table_name')}`."
        return {
            "message": self._format_six_steps(resumen, asset, profile),
            "action_type": "metadata_updated",
            "asset_id": asset.get("id"),
            "asset_data": asset,
            "active_profile": profile
        }

    def _handle_steward_action(self, query: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        asset = self._find_best_asset(query) or self.catalog.list_assets()[0]
        ai_read = asset.get("ai_readiness", {})
        status_rag = "✅ Aprobado para RAG" if ai_read.get("certified_for_rag") else "⚠️ No Certificado para RAG"
        resumen = (
            f"[{profile.get('avatar')} {profile.get('name')}]: 👤 **Gobierno de Datos & Preparación IA:**\n"
            f"- **Data Steward:** `{asset.get('steward')}`\n"
            f"- **Certificación RAG:** {status_rag} ({ai_read.get('compliance_status')})\n"
            f"- **Detalle:** {ai_read.get('notes')}"
        )
        return {
            "message": self._format_six_steps(resumen, asset, profile),
            "action_type": "steward_info",
            "asset_id": asset.get("id"),
            "asset_data": asset,
            "active_profile": profile
        }


agent_brain = DataGovernanceAgentBrain()
