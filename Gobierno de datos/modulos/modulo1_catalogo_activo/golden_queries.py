"""Gestor de Golden Queries pre-aprobadas y auditadas."""

from typing import Any, Dict, List, Optional
from .catalog_manager import catalog_manager


class GoldenQueryManager:
    def __init__(self):
        self.catalog = catalog_manager

    def get_golden_query(self, asset_id: str) -> Optional[str]:
        asset = self.catalog.get_asset_by_id(asset_id)
        if asset:
            return asset.get("golden_query")
        return None

    def set_golden_query(self, asset_id: str, query: str) -> bool:
        res = self.catalog.update_metadata(asset_id, golden_query=query)
        return res is not None


golden_query_manager = GoldenQueryManager()
