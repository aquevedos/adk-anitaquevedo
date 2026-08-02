"""Knowledge Catalog and Context Graph Service for Multi-Cloud Metadata Management."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("knowledge_catalog_service")
DB_PATH = Path(__file__).parent.parent.parent / "config" / "mock_catalog_db.json"


class KnowledgeCatalogService:
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

    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        self._load_data()
        for asset in self.data.get("assets", []):
            if asset.get("id") == asset_id:
                return asset
        return None

    def search_catalog(self, query: str, cloud: Optional[str] = None) -> List[Dict[str, Any]]:
        self._load_data()
        query_lower = query.lower().strip()
        results = []
        for asset in self.data.get("assets", []):
            if cloud and cloud.lower() != "all" and asset.get("cloud", "").lower() != cloud.lower():
                continue
            
            # Match against table_name, name, description, columns, domain, tags
            match_score = 0
            if query_lower in asset.get("name", "").lower():
                match_score += 10
            if query_lower in asset.get("table_name", "").lower():
                match_score += 10
            if query_lower in asset.get("description", "").lower():
                match_score += 5
            if query_lower in asset.get("dataset", "").lower():
                match_score += 4
            if query_lower in asset.get("domain", "").lower():
                match_score += 3
            if query_lower in asset.get("service", "").lower() or query_lower in asset.get("cloud", "").lower():
                match_score += 2

            for col in asset.get("columns", []):
                if query_lower in col.get("name", "").lower() or query_lower in col.get("description", "").lower():
                    match_score += 3

            if match_score > 0 or not query_lower:
                asset_copy = dict(asset)
                asset_copy["relevance_score"] = match_score
                results.append(asset_copy)

        results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return results

    def update_asset_metadata(
        self,
        asset_id: str,
        description: Optional[str] = None,
        steward: Optional[str] = None,
        column_updates: Optional[List[Dict[str, Any]]] = None,
        golden_query: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        self._load_data()
        for asset in self.data.get("assets", []):
            if asset.get("id") == asset_id:
                if description is not None:
                    asset["description"] = description
                if steward is not None:
                    asset["steward"] = steward
                if golden_query is not None:
                    asset["golden_query"] = golden_query
                if column_updates:
                    for col_update in column_updates:
                        c_name = col_update.get("name")
                        for col in asset.get("columns", []):
                            if col.get("name") == c_name:
                                if "description" in col_update:
                                    col["description"] = col_update["description"]
                                if "is_pii" in col_update:
                                    col["is_pii"] = col_update["is_pii"]
                                if "policy_tag" in col_update:
                                    col["policy_tag"] = col_update["policy_tag"]
                                if "masked" in col_update:
                                    col["masked"] = col_update["masked"]
                self._save_data()
                return asset
        return None

    def get_glossary(self) -> List[Dict[str, Any]]:
        self._load_data()
        return self.data.get("glossary", [])

    def add_glossary_term(self, term: str, definition: str, domain: str, approved_by: str) -> Dict[str, Any]:
        self._load_data()
        new_entry = {
            "term": term,
            "definition": definition,
            "domain": domain,
            "approved_by": approved_by
        }
        self.data.setdefault("glossary", []).append(new_entry)
        self._save_data()
        return new_entry


catalog_service = KnowledgeCatalogService()
