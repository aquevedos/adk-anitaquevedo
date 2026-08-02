"""Servicio de Gestión de Perfiles de Gobierno y Persistencia en Firestore / Local."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import google.auth
import google.auth.transport.requests
import requests

logger = logging.getLogger("firestore_profile_service")
DB_FILE = Path(__file__).parent.parent.parent / "config" / "firestore_profiles_db.json"


class FirestoreProfileService:
    def __init__(self, project_id: str = "agentspace-demos-466121", collection_name: str = "governance_profiles"):
        self.project_id = project_id
        self.collection_name = collection_name
        self.db_file = DB_FILE
        self._load_local_data()

    def _load_local_data(self) -> Dict[str, Any]:
        if self.db_file.exists():
            try:
                with open(self.db_file, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading local profiles db: {e}")
                self.data = {"profiles": [], "active_profile_id": "guardian_dato"}
        else:
            self.data = {"profiles": [], "active_profile_id": "guardian_dato"}
        return self.data

    def _save_local_data(self) -> bool:
        try:
            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving local profiles db: {e}")
            return False

    def get_all_profiles(self) -> List[Dict[str, Any]]:
        self._load_local_data()
        return self.data.get("profiles", [])

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        self._load_local_data()
        email_clean = email.strip().lower()
        pass_clean = password.strip()

        for p in self.data.get("profiles", []):
            if p.get("email", "").lower() == email_clean and p.get("password") == pass_clean:
                self.set_active_profile(p.get("id"))
                return p
        return None

    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        self._load_local_data()
        for p in self.data.get("profiles", []):
            if p.get("id") == profile_id:
                return p
        return None

    def get_active_profile(self) -> Dict[str, Any]:
        self._load_local_data()
        active_id = self.data.get("active_profile_id", "guardian_dato")
        p = self.get_profile(active_id)
        if p:
            return p
        profiles = self.get_all_profiles()
        return profiles[0] if profiles else {}

    def set_active_profile(self, profile_id: str) -> Dict[str, Any]:
        self._load_local_data()
        p = self.get_profile(profile_id)
        if not p:
            return {"status": "error", "message": f"Perfil '{profile_id}' no encontrado"}

        self.data["active_profile_id"] = profile_id
        self._save_local_data()
        
        # Also attempt async sync to Firestore in GCP
        self._sync_to_gcp_firestore(profile_id, p)

        return {
            "status": "success",
            "active_profile": p,
            "message": f"Perfil activo cambiado a: {p.get('name')} ({p.get('role')})"
        }

    def _sync_to_gcp_firestore(self, doc_id: str, payload: Dict[str, Any]):
        """Intenta sincronizar el perfil con Cloud Firestore vía REST si está habilitado."""
        try:
            creds, _ = google.auth.default()
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            token = creds.token

            url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/{self.collection_name}/{doc_id}"
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            
            # Firestore document representation
            fields = {
                "id": {"stringValue": str(payload.get("id", ""))},
                "name": {"stringValue": str(payload.get("name", ""))},
                "role": {"stringValue": str(payload.get("role", ""))},
                "mission": {"stringValue": str(payload.get("mission", ""))}
            }
            requests.patch(url, headers=headers, json={"fields": fields}, timeout=2)
        except Exception as e:
            logger.debug(f"Firestore cloud sync skipped/fallback used: {e}")

    def calculate_maturity_diagnosis(self, answers: Dict[str, int]) -> Dict[str, Any]:
        """Calcula el diagnóstico de madurez de gobierno para el Perfil 2 (Gestor del Programa)."""
        scores = list(answers.values()) if answers else [3, 3, 2, 3, 2]
        avg = round(sum(scores) / max(len(scores), 1), 1)

        if avg >= 4.0:
            level_name = "Nivel 4-5: Optimizado & Cuantitativamente Gestionado"
            recommendation = "Enfocarse en automatización de linaje con IA, Dynamic Data Masking generalizado y Data Products monetizables."
        elif avg >= 2.5:
            level_name = "Nivel 2-3: Definido y Estandarizado"
            recommendation = "Formalizar comités de dominio, matrices RACI y desplegar Dataplex Data Quality con alertas automáticas."
        else:
            level_name = "Nivel 1: Inicial / Ad-Hoc"
            recommendation = "Iniciar con inventario de activos en Knowledge Catalog, nombrar Data Stewards principales y proteger PII con Cloud DLP."

        return {
            "score": avg,
            "max_score": 5.0,
            "maturity_level": level_name,
            "recommendation": recommendation,
            "roadmap_sprints": [
                {"sprint": "Sprint 1", "foco": "Descubrimiento y Glosario Inicial con Knowledge Catalog"},
                {"sprint": "Sprint 2", "foco": "Escaneo de PII y Reglas de Calidad Dataplex"},
                {"sprint": "Sprint 3", "foco": "Matriz RACI y Certificación de Datasets para IA / RAG"}
            ]
        }


firestore_profile_service = FirestoreProfileService()
