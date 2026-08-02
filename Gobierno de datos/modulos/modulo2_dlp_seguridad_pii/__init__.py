"""Módulo 2: Clasificación y Etiquetado de PII (Cloud DLP / SDP)."""

from .dlp_scanner import dlp_scanner, DLPScanner
from .policy_tagger import policy_tagger, PolicyTagger, INFOTYPE_MAPPINGS
from .sdp_manager import sdp_manager, SDPManager
