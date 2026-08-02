"""Configuration manager for CMI Data Governance Platform."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

CONFIG_PATH = Path(__file__).parent / "cmi_governance_config.yaml"

logger = logging.getLogger(__name__)


def load_governance_config() -> Dict[str, Any]:
    """Loads the CMI governance configuration from the YAML file."""
    if not CONFIG_PATH.exists():
        logger.warning(f"Configuration file not found at {CONFIG_PATH}, returning default.")
        return get_default_config()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data or get_default_config()
    except Exception as e:
        logger.error(f"Failed to load governance config from {CONFIG_PATH}: {e}")
        return get_default_config()


def save_governance_config(new_config: Dict[str, Any]) -> bool:
    """Saves updated governance configuration to the YAML file."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(new_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        logger.info(f"Successfully saved updated governance configuration to {CONFIG_PATH}")
        return True
    except Exception as e:
        logger.error(f"Failed to save governance configuration to {CONFIG_PATH}: {e}")
        return False


def get_governance_prompt_context() -> str:
    """Generates the data governance context snippet to inject into the agent prompt."""
    config = load_governance_config()
    client_name = config.get("cliente", "Corporación Multi Inversiones (CMI)")
    bus = config.get("unidades_negocio", [])
    quality_rules = config.get("reglas_calidad", {})
    glossary = config.get("glosario_terminos", [])
    security = config.get("clasificacion_seguridad", {}).get("niveles", [])

    lines = [
        f"### Cliente y Entorno de Gobierno: {client_name}",
        "Eres el **Especialista Sénior en Gobierno de Datos de CMI**. Debes aplicar estrictamente las políticas, términos de negocio y reglas de calidad de datos corporativos.",
        "\n#### 1. Unidades de Negocio y Dominios de CMI:",
    ]
    for b in bus:
        lines.append(f"- **{b.get('nombre')}** ({b.get('id')}): {b.get('descripcion')} (Data Steward: {b.get('data_steward_lider')})")

    lines.append("\n#### 2. Reglas y Umbrales de Calidad de Datos (Data Quality SLA):")
    for k, v in quality_rules.items():
        lines.append(f"- `{k}`: **{v}**")

    lines.append("\n#### 3. Términos Oficiales del Glosario Empresarial CMI:")
    for item in glossary:
        lines.append(f"- **{item.get('termino')}** ({item.get('unidad_negocio')}): {item.get('definicion')} | Fórmula: `{item.get('formula_sql')}` (Steward: {item.get('data_steward')})")

    lines.append("\n#### 4. Niveles de Seguridad y Clasificación:")
    for sec in security:
        lines.append(f"- **{sec.get('codigo')}**: {sec.get('descripcion')} (Enmascaramiento requerido: {sec.get('requiere_enmascaramiento')})")

    lines.append("\n#### 5. Obligación de Auditoría en Cada Respuesta:")
    lines.append("Cada respuesta debe incluir una sección de **Evaluación de Gobierno de Datos CMI** indicando: (1) Nivel de cumplimiento de políticas, (2) Validación de umbrales de calidad/SLA, (3) Documento o entrada del catálogo que lo respalda, y (4) Data Steward a contactar en caso de anomalías.")

    return "\n".join(lines)


def get_default_config() -> Dict[str, Any]:
    """Fallback default configuration."""
    return {
        "version": "2.0",
        "cliente": "Corporación Multi Inversiones (CMI)",
        "agente": {
            "nombre": "Agente Especialista en Gobierno de Datos CMI",
            "version": "2.1.0",
            "modelo": "gemini-3-flash-preview",
            "temperatura": 0.1,
        },
        "unidades_negocio": [
            {
                "id": "cmi_alimentos",
                "nombre": "CMI Alimentos",
                "descripcion": "Molinos Modernos, Negocio B4B, Avícola, Porcícola y Pollo Campero.",
                "data_steward_lider": "steward.alimentos@cmi.com",
            },
            {
                "id": "cmi_capital",
                "nombre": "CMI Capital",
                "descripcion": "Energía Renovable, Desarrollo Inmobiliario y Unidad Financiera.",
                "data_steward_lider": "steward.capital@cmi.com",
            },
        ],
        "reglas_calidad": {
            "tolerancia_nulos_maxima_pct": 5.0,
            "tolerancia_duplicados_maxima_pct": 0.0,
            "umbral_alerta_devoluciones_pct": 8.0,
            "frescura_datos_max_horas": 24,
        },
    }
