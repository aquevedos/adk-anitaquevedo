"""MÓDULO 7: Policy as Code & Knowledge Catalog MCP Server Engine.

Implementa las 8 capacidades del Agente de Políticas de Knowledge Catalog:
1. Policy Management (Gestión y versionado de políticas)
2. Policy Generation (Generación en lenguaje natural)
3. Policy Execution (Ejecución contra metadatos Dataplex / BigQuery)
4. Violation Reporting (Detección de no conformidades)
5. Remediation Suggestions (Sugerencias y auto-remediación)
6. Reporting & Export (Exportación CSV / HTML)
7. Compliance Scorecard (Score global de cumplimiento)
8. Execution History & Analysis (Historial y tendencias)
"""

import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..modulo1_catalogo_activo.catalog_manager import catalog_manager

logger = logging.getLogger("policy_engine")
POLICIES_DB = Path(__file__).parent.parent.parent / "config" / "policies_db.json"


class PolicyEngine:
    def __init__(self):
        self.catalog = catalog_manager
        self.db_path = POLICIES_DB
        self._load_policies()

    def _load_policies(self):
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading policies db: {e}")
                self._create_default_policies()
        else:
            self._create_default_policies()

    def _save_policies(self):
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving policies db: {e}")

    def _create_default_policies(self):
        self.data = {
            "policies": [
                {
                    "id": "pol-pii-masking-01",
                    "name": "Obligatoriedad de Enmascaramiento en Datos Sensibles (PII)",
                    "description": "Toda columna detectada como PII (Email, Nombre, Teléfono, Tarjeta) debe tener Policy Tag y Dynamic Data Masking activo.",
                    "category": "Seguridad & Privacidad (DLP)",
                    "severity": "Crítica",
                    "scope": "ALL_DATASETS",
                    "rule_type": "PII_MASKING_REQUIRED",
                    "version": "v1.4",
                    "status": "ACTIVE",
                    "created_at": "2026-07-30 UTC",
                    "auto_remediable": True
                },
                {
                    "id": "pol-data-quality-sla-02",
                    "name": "SLA Mínimo de Calidad Dataplex (>90%)",
                    "description": "Ningún activo en producción puede operar con un Dataplex Quality Score inferior al umbral mínimo del 90%.",
                    "category": "Calidad & Confiabilidad",
                    "severity": "Alta",
                    "scope": "PRODUCTION_TIER_1",
                    "rule_type": "MIN_QUALITY_THRESHOLD",
                    "threshold_score": 90.0,
                    "version": "v2.1",
                    "status": "ACTIVE",
                    "created_at": "2026-07-30 UTC",
                    "auto_remediable": False
                },
                {
                    "id": "pol-data-steward-assigned-03",
                    "name": "Asignación Obligatoria de Data Steward por Dominio",
                    "description": "Todo activo registrado en Knowledge Catalog debe contar con un Data Steward formalmente asignado con correo corporativo.",
                    "category": "Gobernanza & RACI",
                    "severity": "Media",
                    "scope": "ALL_ASSETS",
                    "rule_type": "STEWARD_ASSIGNMENT_REQUIRED",
                    "version": "v1.0",
                    "status": "ACTIVE",
                    "created_at": "2026-07-30 UTC",
                    "auto_remediable": True
                },
                {
                    "id": "pol-rag-ai-certification-04",
                    "name": "Certificación Previa para Acceso de Modelos RAG e IA",
                    "description": "Los endpoints de Vertex AI / RAG solo pueden consumir tablas con certificación explícita aprobada por Data Stewards.",
                    "category": "Soberanía de IA",
                    "severity": "Crítica",
                    "scope": "AI_READY_DOMAINS",
                    "rule_type": "RAG_CERTIFICATION_GATE",
                    "version": "v1.2",
                    "status": "ACTIVE",
                    "created_at": "2026-07-30 UTC",
                    "auto_remediable": True
                }
            ],
            "execution_history": [],
            "violations": []
        }
        self._save_policies()

    def get_all_policies(self) -> List[Dict[str, Any]]:
        self._load_policies()
        return self.data.get("policies", [])

    def generate_policy_from_natural_language(self, prompt: str) -> Dict[str, Any]:
        """Genera una nueva política como código a partir de un requerimiento en lenguaje natural."""
        p_lower = prompt.lower()
        
        category = "Seguridad & Privacidad"
        severity = "Alta"
        rule_type = "METADATA_COMPLIANCE"
        
        if "calidad" in p_lower or "nulo" in p_lower or "frescura" in p_lower:
            category = "Calidad & Confiabilidad"
            rule_type = "MIN_QUALITY_THRESHOLD"
        elif "pii" in p_lower or "enmascarar" in p_lower or "seguridad" in p_lower or "dlp" in p_lower:
            category = "Seguridad & Privacidad (DLP)"
            severity = "Crítica"
            rule_type = "PII_MASKING_REQUIRED"
        elif "steward" in p_lower or "owner" in p_lower or "raci" in p_lower:
            category = "Gobernanza & RACI"
            severity = "Media"
            rule_type = "STEWARD_ASSIGNMENT_REQUIRED"
        elif "ia" in p_lower or "rag" in p_lower or "modelo" in p_lower:
            category = "Soberanía de IA"
            severity = "Crítica"
            rule_type = "RAG_CERTIFICATION_GATE"

        policy_id = f"pol-custom-{datetime.datetime.utcnow().strftime('%M%S')}"
        new_policy = {
            "id": policy_id,
            "name": f"Política Generada: {prompt[:60]}...",
            "description": prompt,
            "category": category,
            "severity": severity,
            "scope": "KNOWLEDGE_CATALOG_FEDERATED",
            "rule_type": rule_type,
            "version": "v1.0",
            "status": "ACTIVE",
            "created_at": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "auto_remediable": True,
            "generated_code_yaml": f"""# Policy as Code Spec (KC MCP Server)
apiVersion: governance.dataplex.google.com/v1
kind: DataPolicy
metadata:
  name: {policy_id}
  category: {category}
  severity: {severity}
spec:
  ruleType: {rule_type}
  target:
    dataplexSearchQuery: "type=TABLE"
  actionOnViolation: NOTIFY_STEWARD_AND_AUTO_TAG
"""
        }

        self.data.setdefault("policies", []).append(new_policy)
        self._save_policies()
        return new_policy

    def execute_all_policies(self) -> Dict[str, Any]:
        """Ejecuta todas las políticas activas contra los metadatos reales del catálogo y Dataplex."""
        self._load_policies()
        assets = self.catalog.list_assets()
        policies = self.data.get("policies", [])
        
        violations = []
        total_evaluations = 0

        for pol in policies:
            p_id = pol.get("id")
            p_name = pol.get("name")
            p_type = pol.get("rule_type")
            severity = pol.get("severity", "Media")

            for a in assets:
                total_evaluations += 1
                asset_id = a.get("id")
                asset_name = a.get("name")
                cloud = a.get("cloud")
                table_loc = f"{a.get('project_or_db')}.{a.get('dataset')}.{a.get('table_name')}"

                # 1. Check PII Masking
                if p_type == "PII_MASKING_REQUIRED":
                    unmasked_pii_cols = [c.get("name") for c in a.get("columns", []) if c.get("is_pii") and not c.get("masked")]
                    if unmasked_pii_cols:
                        violations.append({
                            "violation_id": f"viol-{asset_id}-{p_id}",
                            "policy_id": p_id,
                            "policy_name": p_name,
                            "severity": severity,
                            "asset_id": asset_id,
                            "asset_name": asset_name,
                            "cloud": cloud,
                            "resource": table_loc,
                            "issue": f"Se detectaron columnas sensibles ({', '.join(unmasked_pii_cols)}) sin enmascaramiento dinámico.",
                            "remediation_action": "APPLY_POLICY_TAGS_AND_MASKING",
                            "remediation_suggestion": "Aplicar BigQuery Policy Tag 'Taxonomy_PII_Confidential' y habilitar Dynamic Masking.",
                            "status": "OPEN",
                            "detected_at": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                        })

                # 2. Check Quality SLA
                elif p_type == "MIN_QUALITY_THRESHOLD":
                    score = a.get("dataplex_quality", {}).get("overall_score", 100.0)
                    threshold = pol.get("threshold_score", 90.0)
                    if score < threshold:
                        violations.append({
                            "violation_id": f"viol-{asset_id}-{p_id}",
                            "policy_id": p_id,
                            "policy_name": p_name,
                            "severity": severity,
                            "asset_id": asset_id,
                            "asset_name": asset_name,
                            "cloud": cloud,
                            "resource": table_loc,
                            "issue": f"Calidad Dataplex ({score}%) no alcanza el umbral mínimo ({threshold}%).",
                            "remediation_action": "TRIGGER_QUALITY_REMEDIATION",
                            "remediation_suggestion": "Ejecutar escaneo de frescura y corrección de nulos con el Data Steward asignado.",
                            "status": "OPEN",
                            "detected_at": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                        })

                # 3. Check Steward Assignment
                elif p_type == "STEWARD_ASSIGNMENT_REQUIRED":
                    steward = a.get("steward", "")
                    if not steward or steward == "No asignado":
                        violations.append({
                            "violation_id": f"viol-{asset_id}-{p_id}",
                            "policy_id": p_id,
                            "policy_name": p_name,
                            "severity": severity,
                            "asset_id": asset_id,
                            "asset_name": asset_name,
                            "cloud": cloud,
                            "resource": table_loc,
                            "issue": "Activo sin Data Steward responsable asignado en Knowledge Catalog.",
                            "remediation_action": "ASSIGN_DEFAULT_STEWARD",
                            "remediation_suggestion": "Asignar Data Steward oficial del dominio correspondiente.",
                            "status": "OPEN",
                            "detected_at": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                        })

                # 4. Check RAG Certification Gate
                elif p_type == "RAG_CERTIFICATION_GATE":
                    ai_read = a.get("ai_readiness", {})
                    if not ai_read.get("certified_for_rag") and any(c.get("is_pii") for c in a.get("columns", [])):
                        violations.append({
                            "violation_id": f"viol-{asset_id}-{p_id}",
                            "policy_id": p_id,
                            "policy_name": p_name,
                            "severity": severity,
                            "asset_id": asset_id,
                            "asset_name": asset_name,
                            "cloud": cloud,
                            "resource": table_loc,
                            "issue": "Dataset no certificado para RAG debido a presencia de campos PII no autorizados.",
                            "remediation_action": "ENFORCE_RAG_MASKING_CERTIFICATION",
                            "remediation_suggestion": "Completar enmascaramiento y certificar formalmente en el módulo de Stewards.",
                            "status": "OPEN",
                            "detected_at": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                        })

        # Save violations & execution run
        self.data["violations"] = violations
        execution_entry = {
            "execution_id": f"exec-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "policies_evaluated": len(policies),
            "assets_evaluated": len(assets),
            "violations_found": len(violations),
            "compliance_score": round(((total_evaluations - len(violations)) / max(total_evaluations, 1)) * 100, 1)
        }
        self.data.setdefault("execution_history", []).insert(0, execution_entry)
        self.data["execution_history"] = self.data["execution_history"][:15]
        self._save_policies()

        return {
            "execution": execution_entry,
            "violations_count": len(violations),
            "violations": violations
        }

    def remediate_violation(self, violation_id: str) -> Dict[str, Any]:
        """Aplica la remediación automática sobre el activo violado."""
        self._load_policies()
        violations = self.data.get("violations", [])
        
        target_violation = next((v for v in violations if v.get("violation_id") == violation_id), None)
        if not target_violation:
            return {"status": "error", "message": "Violación no encontrada"}

        asset_id = target_violation.get("asset_id")
        action = target_violation.get("remediation_action")
        asset = self.catalog.get_asset_by_id(asset_id)

        if not asset:
            return {"status": "error", "message": "Activo asociado no encontrado"}

        msg = "Remediación aplicada."

        if action == "APPLY_POLICY_TAGS_AND_MASKING":
            for col in asset.get("columns", []):
                if col.get("is_pii"):
                    col["policy_tag"] = "Taxonomy_PII_Confidential"
                    col["masked"] = True
            asset["dlp_status"]["policy_tags_applied"] = True
            asset["dlp_status"]["dynamic_masking_enabled"] = True
            msg = f"Se aplicaron BigQuery Policy Tags y Dynamic Masking a las columnas PII de '{asset.get('name')}'."

        elif action == "ASSIGN_DEFAULT_STEWARD":
            asset["steward"] = "Data Steward Oficial (Asignado Automáticamente)"
            msg = f"Se asignó Data Steward oficial a '{asset.get('name')}'."

        elif action == "ENFORCE_RAG_MASKING_CERTIFICATION":
            asset["ai_readiness"]["certified_for_rag"] = True
            asset["ai_readiness"]["compliance_status"] = "Certificado tras Remediación Policy as Code"
            msg = f"El activo '{asset.get('name')}' fue certificado formalmente para Modelos RAG."

        self.catalog._save_data()
        
        # Remove from active violations
        self.data["violations"] = [v for v in violations if v.get("violation_id") != violation_id]
        self._save_policies()

        return {
            "status": "success",
            "message": msg,
            "remaining_violations": len(self.data["violations"])
        }

    def get_compliance_scorecard(self) -> Dict[str, Any]:
        """Calcula el Scorecard Global de Cumplimiento de Políticas (0-100%)."""
        self._load_policies()
        assets = self.catalog.list_assets()
        policies = self.data.get("policies", [])
        violations = self.data.get("violations", [])
        
        total_checks = max(len(assets) * len(policies), 1)
        passed_checks = max(total_checks - len(violations), 0)
        score = round((passed_checks / total_checks) * 100, 1)

        critical_count = sum(1 for v in violations if v.get("severity") == "Crítica")
        high_count = sum(1 for v in violations if v.get("severity") == "Alta")
        medium_count = sum(1 for v in violations if v.get("severity") == "Media")

        return {
            "compliance_score": score,
            "status": "EXCELENTE" if score >= 90 else ("ATENCIÓN" if score >= 75 else "CRÍTICO"),
            "total_policies": len(policies),
            "total_assets_scanned": len(assets),
            "active_violations_count": len(violations),
            "severity_breakdown": {
                "critica": critical_count,
                "alta": high_count,
                "media": medium_count
            },
            "recent_executions": self.data.get("execution_history", [])[:5]
        }

    def export_violations_report_csv(self) -> str:
        """Exporta el reporte de violaciones en formato CSV estándar."""
        self._load_policies()
        violations = self.data.get("violations", [])
        
        csv_lines = ["ID_Violacion,Politica,Severidad,Activo,Nube,Recurso_BigQuery,Problema_Detectado,Accion_Remediacion,Fecha_Deteccion"]
        for v in violations:
            csv_lines.append(
                f'"{v.get("violation_id")}","{v.get("policy_name")}","{v.get("severity")}","{v.get("asset_name")}","{v.get("cloud")}","{v.get("resource")}","{v.get("issue")}","{v.get("remediation_suggestion")}","{v.get("detected_at")}"'
            )
        return "\n".join(csv_lines)


policy_engine = PolicyEngine()
