"""Agentic Reasoning Engine for Hybrid & Multi-Cloud Data Governance."""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from .services.knowledge_catalog_service import catalog_service
from .services.dlp_service import dlp_service
from .services.dataplex_quality_service import dataplex_service
from .services.lineage_service import lineage_service
from .services.stewards_service import stewards_service

logger = logging.getLogger("agent_engine")

SYSTEM_PROMPT = """Eres un Agente Inteligente de Gobierno de Datos ("Agentic Data Governance"), diseñado para actuar como un participante activo y autónomo en la gestión, mejora y protección de los activos de datos de la empresa. Operas a través de una infraestructura híbrida y multi-cloud (GCP, AWS, Azure, On-Premise y SaaS) utilizando Knowledge Catalog, Dataplex y Cloud DLP (Sensitive Data Protection) como tus motores principales.

Tu propósito es trascender los catálogos de datos pasivos: ejecutas tareas operativas, actualizas metadatos automáticamente, verificas calidad en tiempo real y garantizas la seguridad sin requerir que los usuarios naveguen manualmente por consolas complejas.

REGLAS DE ORO:
1. Operación Exclusiva en Metadatos: NUNCA muestres datos reales sensibles en tus respuestas. Muestra únicamente metadatos, niveles de sensibilidad DLP y estado de enmascaramiento.
2. Claridad sobre la Ubicación: Especifica siempre el origen físico de la fuente (Ej. [GCP / BigQuery], [AWS / Redshift], [On-Prem / PostgreSQL]).
3. Proactividad y Advertencias: Si detectas tablas con calidad deficiente (<90%), datos PII sin enmascarar o esquemas desactualizados, notifícalo proactivamente.
4. Respuestas Estructuradas: Formatea tus respuestas siguiendo la estructura obligatoria de 6 pasos:
   1. 📌 Resumen Ejecutivo / Acción Realizada
   2. 📍 Ubicación y Origen
   3. 🔒 Clasificación y Sensibilidad (DLP)
   4. 🩺 Salud y Calidad del Dato
   5. 🔗 Linaje Rápido
   6. 💡 Siguiente Paso / Ejemplo SQL (Golden Query)
"""


class DataGovernanceAgent:
    def __init__(self):
        self.catalog = catalog_service
        self.dlp = dlp_service
        self.quality = dataplex_service
        self.lineage = lineage_service
        self.stewards = stewards_service

    async def chat(self, user_message: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Processes the user prompt, determines intent, executes backend actions, and builds the 6-step response."""
        msg = user_message.lower().strip()
        
        # Check if user asks for greeting or general intro
        if any(w in msg for w in ["hola", "buenos días", "buenas tardes", "buenas noches", "quién eres", "inicio", "help", "ayuda", "empezar"]):
            return {
                "message": self._generate_welcome_response(),
                "action_type": "welcome",
                "suggested_actions": [
                    "Analizar la tabla dim_clientes_360 en BigQuery",
                    "Escanear PII con Cloud DLP en prospectos de Azure",
                    "Verificar calidad con Dataplex en Redshift",
                    "Consultar linaje de tbl_inventario_bodegas",
                    "Actualizar descripción de un dataset"
                ]
            }

        # Check for update metadata intent
        if ("actualiza" in msg or "cambia" in msg or "modifica" in msg) and ("descripción" in msg or "descripcion" in msg or "steward" in msg or "metadato" in msg):
            return self._handle_update_metadata_intent(user_message)

        # Check for DLP scanning intent
        if "dlp" in msg or "pii" in msg or "enmascarar" in msg or "sensible" in msg or "policy tag" in msg:
            return self._handle_dlp_intent(user_message)

        # Check for Quality scan intent
        if "calidad" in msg or "dataplex" in msg or "freshness" in msg or "frescura" in msg or "nulos" in msg or "duplicados" in msg:
            return self._handle_quality_intent(user_message)

        # Check for Lineage intent
        if "linaje" in msg or "lineage" in msg or "trazabilidad" in msg or "origen" in msg or "impacto" in msg:
            return self._handle_lineage_intent(user_message)

        # Check for Steward or AI certification intent
        if "steward" in msg or "owner" in msg or "rag" in msg or "ia" in msg or "certific" in msg:
            return self._handle_steward_intent(user_message)

        # Default: Semantic search and asset intelligence
        return self._handle_search_and_explain_intent(user_message)

    def _generate_welcome_response(self) -> str:
        return (
            "¡Hola! Soy el **Agente Inteligente de Gobierno de Datos Híbrido y Multi-Cloud** (*Agentic Data Governance*).\n\n"
            "Estoy aquí para ayudarte a gobernar, clasificar, evaluar y proteger activamente tus activos de datos distribuidos en **GCP, AWS, Azure, On-Premises y SaaS** utilizando los motores de **Knowledge Catalog**, **Dataplex** y **Cloud DLP (Sensitive Data Protection)**.\n\n"
            "### ¿Qué puedo hacer por ti?\n"
            "- 🔍 **Búsqueda activa y metadatos:** Consultar esquemas, catálogos multi-cloud y actualizar descripciones en lenguaje natural.\n"
            "- 🔒 **Clasificación y DLP:** Descubrir PII/PHI y aplicar *Policy Tags* con *Dynamic Data Masking* automático.\n"
            "- 🩺 **Calidad con Dataplex:** Evaluar completitud, frescura, duplicados y reglas de negocio.\n"
            "- 🔗 **Linaje y Trazabilidad:** Mapear el flujo end-to-end de datos y analizar el impacto de cambios de esquema.\n"
            "- 🤖 **Certificación para IA / RAG:** Validar y certificar datasets gobernados para ingesta en modelos de IA.\n\n"
            "*¿Qué tabla, dominio o análisis de gobierno te gustaría iniciar hoy?*"
        )

    def _find_best_matching_asset(self, query: str) -> Optional[Dict[str, Any]]:
        results = self.catalog.search_catalog(query)
        if results:
            return results[0]
        # Return first default if none matched
        assets = self.catalog.list_assets()
        return assets[0] if assets else None

    def _format_six_step_response(
        self,
        resumen: str,
        asset: Dict[str, Any],
        custom_dlp: Optional[str] = None,
        custom_quality: Optional[str] = None,
        custom_lineage: Optional[str] = None,
        custom_next_step: Optional[str] = None
    ) -> str:
        # Step 2: Location
        location = f"[{asset.get('cloud')} / {asset.get('service')}] `{asset.get('project_or_db')}.{asset.get('dataset')}.{asset.get('table_name')}`"
        
        # Step 3: DLP
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

        # Step 4: Quality
        q_stat = asset.get("dataplex_quality", {})
        if custom_quality:
            quality_info = custom_quality
        else:
            score = q_stat.get("overall_score", 95.0)
            score_emoji = "🟢" if score >= 90 else ("🟡" if score >= 80 else "🔴")
            quality_info = (
                f"- **Dataplex Quality Score:** {score_emoji} **{score}%** ({q_stat.get('status', 'PASSED')})\n"
                f"- **Frescura:** Actualizado hace ~{q_stat.get('freshness_hours', 2)} horas\n"
                f"- **Completitud y Duplicados:** Nulos {q_stat.get('null_rate_pct', 0)}% | Duplicados {q_stat.get('duplicate_rate_pct', 0)}% | Anomalías: {q_stat.get('anomaly_count', 0)}"
            )

        # Step 5: Lineage
        lin_data = asset.get("lineage", {})
        if custom_lineage:
            lineage_info = custom_lineage
        else:
            up_sources = ", ".join([u.get("source", "") for u in lin_data.get("upstream", [])]) or "Origen raíz"
            down_targets = ", ".join([d.get("target", "") for d in lin_data.get("downstream", [])]) or "Sin consumidores directos"
            lineage_info = (
                f"- **Orígenes Upstream:** {up_sources}\n"
                f"- **Destinos Downstream:** {down_targets}"
            )

        # Step 6: Next Step / Golden Query
        if custom_next_step:
            next_step_info = custom_next_step
        else:
            golden_sql = asset.get("golden_query", f"SELECT * FROM `{asset.get('table_name')}` LIMIT 10;")
            next_step_info = (
                f"```sql\n-- Golden Query Pre-Aprobada (Campos PII Enmascarados)\n{golden_sql}\n```\n"
                f"👤 **Data Steward Responsable:** {asset.get('steward')}"
            )

        return (
            f"### 1. 📌 Resumen Ejecutivo / Acción Realizada\n{resumen}\n\n"
            f"### 2. 📍 Ubicación y Origen\n{location}\n\n"
            f"### 3. 🔒 Clasificación y Sensibilidad (DLP)\n{dlp_info}\n\n"
            f"### 4. 🩺 Salud y Calidad del Dato\n{quality_info}\n\n"
            f"### 5. 🔗 Linaje Rápido\n{lineage_info}\n\n"
            f"### 6. 💡 Siguiente Paso / Ejemplo SQL\n{next_step_info}"
        )

    def _handle_search_and_explain_intent(self, user_message: str) -> Dict[str, Any]:
        asset = self._find_best_matching_asset(user_message)
        if not asset:
            return {
                "message": "No se encontraron activos coincidentes en el catálogo multi-cloud.",
                "action_type": "not_found"
            }

        resumen = (
            f"Se consultó y analizó con éxito el activo **{asset.get('name')}** a través del Context Graph de Knowledge Catalog. "
            f"La tabla contiene {len(asset.get('columns', []))} columnas registradas en el dominio `{asset.get('domain')}`."
        )

        response_text = self._format_six_step_response(resumen, asset)
        return {
            "message": response_text,
            "action_type": "catalog_query",
            "asset_id": asset.get("id"),
            "asset_data": asset
        }

    def _handle_dlp_intent(self, user_message: str) -> Dict[str, Any]:
        asset = self._find_best_matching_asset(user_message)
        if not asset:
            asset = self.catalog.list_assets()[0]

        # Trigger DLP scan or policy tags
        scan_res = self.dlp.scan_asset_for_pii(asset["id"])
        
        # If user asked to apply or mask
        if "aplica" in user_message.lower() or "enmascara" in user_message.lower() or "protege" in user_message.lower():
            apply_res = self.dlp.apply_policy_tags_and_masking(asset["id"], auto_mask=True)
            resumen = (
                f"🛡️ **Etiquetado de Seguridad Ejecutado:** Se completó el escaneo de Cloud DLP y se aplicaron automáticamente "
                f"**Policy Tags de BigQuery** con reglas de **Dynamic Data Masking** en {len(apply_res['applied_tags'])} columnas sensibles."
            )
        else:
            resumen = (
                f"🔍 **Inspección Cloud DLP Completada:** Se detectaron {scan_res.get('infotypes_detected_count')} tipos de datos sensibles "
                f"(PII) con nivel de riesgo `{scan_res.get('risk_level')}`. El catálogo recomienda aplicar Policy Tags."
            )

        # Refresh asset data
        asset = self.catalog.get_asset(asset["id"])
        response_text = self._format_six_step_response(resumen, asset)

        return {
            "message": response_text,
            "action_type": "dlp_inspection",
            "asset_id": asset.get("id"),
            "scan_data": scan_res
        }

    def _handle_quality_intent(self, user_message: str) -> Dict[str, Any]:
        asset = self._find_best_matching_asset(user_message)
        if not asset:
            asset = self.catalog.list_assets()[0]

        q_res = self.quality.run_quality_scan(asset["id"])
        q_data = q_res["quality"]

        score = q_data["overall_score"]
        if score >= 90:
            resumen = f"✅ **Escaneo de Calidad Dataplex Superado:** La tabla obtuvo un score del **{score}%**, cumpliendo con los SLAs de frescura, completitud y unicidad."
        else:
            resumen = f"⚠️ **Advertencia de Calidad Dataplex (<90%):** La tabla obtuvo un score de **{score}%** debido a tasas de nulidad ({q_data['null_rate_pct']}%) o anomalías estadísticas. Se requiere intervención del Data Steward."

        asset = self.catalog.get_asset(asset["id"])
        response_text = self._format_six_step_response(resumen, asset)

        return {
            "message": response_text,
            "action_type": "quality_scan",
            "asset_id": asset.get("id"),
            "quality_data": q_data
        }

    def _handle_lineage_intent(self, user_message: str) -> Dict[str, Any]:
        asset = self._find_best_matching_asset(user_message)
        if not asset:
            asset = self.catalog.list_assets()[0]

        lin_graph = self.lineage.get_asset_lineage_graph(asset["id"])
        resumen = (
            f"🔗 **Trazabilidad de Linaje Generada:** Se reconstruyó el grafo end-to-end conectando {lin_graph['upstream_count']} "
            f"fuentes upstream y {lin_graph['downstream_count']} consumidores downstream (incluyendo tableros Looker y pipelines de IA)."
        )

        response_text = self._format_six_step_response(resumen, asset)
        return {
            "message": response_text,
            "action_type": "lineage_graph",
            "asset_id": asset.get("id"),
            "lineage_data": lin_graph
        }

    def _handle_update_metadata_intent(self, user_message: str) -> Dict[str, Any]:
        asset = self._find_best_matching_asset(user_message)
        if not asset:
            asset = self.catalog.list_assets()[0]

        # Extract new description if present
        new_desc = None
        match = re.search(r'(?:descripción|descripcion)\s*(?:a|como|:)\s*["\']?([^"\']+)["\']?', user_message, re.IGNORECASE)
        if match:
            new_desc = match.group(1).strip()
        else:
            new_desc = f"{asset.get('description')} (Actualizada por Data Steward vía Agente de Gobierno)."

        self.catalog.update_asset_metadata(asset["id"], description=new_desc)
        asset = self.catalog.get_asset(asset["id"])

        resumen = f"📝 **Metadatos Actualizados con Éxito:** Se actualizó la descripción técnica en Knowledge Catalog para `{asset.get('table_name')}`."
        response_text = self._format_six_step_response(resumen, asset)

        return {
            "message": response_text,
            "action_type": "metadata_updated",
            "asset_id": asset.get("id"),
            "asset_data": asset
        }

    def _handle_steward_intent(self, user_message: str) -> Dict[str, Any]:
        asset = self._find_best_matching_asset(user_message)
        if not asset:
            asset = self.catalog.list_assets()[0]

        ai_read = asset.get("ai_readiness", {})
        status_rag = "✅ Aprobado para RAG" if ai_read.get("certified_for_rag") else "⚠️ No Certificado para RAG"
        
        resumen = (
            f"👤 **Gestión de Data Stewardship y Gobierno para IA:**\n"
            f"- **Data Steward:** `{asset.get('steward')}`\n"
            f"- **Dominio:** `{asset.get('domain')}`\n"
            f"- **Certificación RAG/IA:** {status_rag} ({ai_read.get('compliance_status')})\n"
            f"- **Detalle:** {ai_read.get('notes')}"
        )

        response_text = self._format_six_step_response(resumen, asset)
        return {
            "message": response_text,
            "action_type": "steward_info",
            "asset_id": asset.get("id"),
            "asset_data": asset
        }


governance_agent = DataGovernanceAgent()
