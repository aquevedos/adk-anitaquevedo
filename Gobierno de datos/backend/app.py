"""FastAPI Backend and Web Server for Agentic Data Governance Platform."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# Importaciones directas desde la estructura modular
from modulos.modulo1_catalogo_activo import catalog_manager
from modulos.modulo2_dlp_seguridad_pii import dlp_scanner, policy_tagger, sdp_manager
from modulos.modulo3_calidad_dataplex import quality_engine
from modulos.modulo4_linaje_trazabilidad import lineage_graph_builder
from modulos.modulo5_seguridad_cumplimiento import privacy_guard
from modulos.modulo6_data_stewards_ia import stewards_manager
from modulos.modulo7_policy_as_code_mcp import policy_engine
from modulos.modulo8_looker_semantic_governance import looker_governance_manager
from modulos.modulo3_calidad_dataplex.business_quality_rules import business_quality_engine
from modulos.conectores_multicloud import connector_factory, gcp_connector
from modulos.conectores_multicloud.external_db_connector import external_db_connector
from modulos.perfiles_gobierno import firestore_profile_service
from core_agent import agent_brain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("governance_api")

app = FastAPI(
    title="Agentic Data Governance Hub API",
    description="Backend Modular para el Agente Inteligente de Gobierno de Datos Multi-Cloud con 4 Perfiles",
    version="3.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


# --- Modelos de Petición ---
class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[Dict[str, str]]] = None
    profile_id: Optional[str] = None


class ProfileSwitchRequest(BaseModel):
    profile_id: str


class MaturityDiagnosisRequest(BaseModel):
    answers: Optional[Dict[str, int]] = None


class MetadataUpdateRequest(BaseModel):
    description: Optional[str] = None
    steward: Optional[str] = None
    golden_query: Optional[str] = None
    column_updates: Optional[List[Dict[str, Any]]] = None


class PolicyTagRequest(BaseModel):
    auto_mask: Optional[bool] = True


class GlossaryTermRequest(BaseModel):
    term: str
    definition: str
    domain: str
    approved_by: str


class TagUpdateRequest(BaseModel):
    template_id: str
    fields: Dict[str, Any]
    column_tags: Optional[List[Dict[str, Any]]] = None


class AICertificationRequest(BaseModel):
    certified: bool
    notes: Optional[str] = "Certificado por Data Steward"


class LoginRequest(BaseModel):
    email: str
    password: str


class PolicyGenerateRequest(BaseModel):
    prompt: str


class ExternalDBTestRequest(BaseModel):
    engine: str = "mysql"
    host: str
    port: int = 10283
    database: str
    user: str
    password: str
    ssl_enabled: bool = False


class ExternalDBDiscoverRequest(BaseModel):
    engine: str = "mysql"
    host: str
    port: int = 10283
    database: str
    user: str
    password: str
    selected_tables: Optional[List[str]] = None
    csv_content: Optional[str] = None


class ThresholdUpdateRequest(BaseModel):
    rule_id: str
    new_threshold: float


class ImpactAnalysisRequest(BaseModel):
    modified_columns: List[str]


# --- Modelos de Petición para Sensitive Data Protection (SDP) ---
class DiscoveryScanRequest(BaseModel):
    asset_id: Optional[str] = None
    source_type: Optional[str] = None
    cloud: Optional[str] = None


class CustomInfoTypeCreateRequest(BaseModel):
    name: str
    display_name: str
    type: str = "REGEX"
    regex_pattern: Optional[str] = None
    dictionary_words: Optional[List[str]] = None
    likelihood: str = "VERY_LIKELY"
    hotwords: Optional[List[str]] = None
    description: Optional[str] = ""
    created_by: Optional[str] = "Data Steward"


class CustomInfoTypeTestRequest(BaseModel):
    type: str = "REGEX"
    regex_pattern: Optional[str] = None
    dictionary_words: Optional[List[str]] = None
    sample_text: str
    hotwords: Optional[List[str]] = None


class InspectJobCreateRequest(BaseModel):
    name: str
    target_asset_id: str
    infotypes_selected: List[str]
    min_likelihood: str = "LIKELY"
    sampling_pct: int = 100
    auto_apply_tags: bool = True
    created_by: Optional[str] = "Data Steward"


class JobTriggerCreateRequest(BaseModel):
    name: str
    description: str
    schedule: str
    target_asset_id: str
    template_id: str = "tmpl_pii_latam_standard"
    created_by: Optional[str] = "Data Steward"


class RiskAnalysisRequest(BaseModel):
    quasi_identifiers: Optional[List[str]] = None
    sensitive_attributes: Optional[List[str]] = None


class InspectTemplateCreateRequest(BaseModel):
    name: str
    description: str
    infotypes: List[str]
    min_likelihood: str = "LIKELY"
    max_findings: int = 1000
    created_by: Optional[str] = "Data Steward"


class DeidentifyTemplateCreateRequest(BaseModel):
    name: str
    transformation_type: str
    description: str
    parameters: Dict[str, Any]
    sample_input: str
    sample_output: str
    created_by: Optional[str] = "Data Steward"


# --- Autenticación y Login por Rol ---
@app.post("/api/auth/login")
async def login_user(req: LoginRequest):
    user_profile = firestore_profile_service.authenticate_user(req.email, req.password)
    if not user_profile:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas. Verifica tu correo y contraseña.")
    
    return JSONResponse(content={
        "status": "success",
        "message": f"Bienvenido, {user_profile.get('user_name')}",
        "user": user_profile,
        "token": f"token_{user_profile.get('id')}_auth"
    })


@app.get("/api/auth/current_user")
async def get_current_user():
    active = firestore_profile_service.get_active_profile()
    return JSONResponse(content={"status": "success", "user": active})


# --- Endpoints de Chat & Agente ---
@app.post("/api/chat")
async def chat_with_agent(req: ChatRequest):
    try:
        response = await agent_brain.chat(req.message, req.conversation_history, profile_id=req.profile_id)
        return JSONResponse(content={"status": "success", "data": response})
    except Exception as e:
        logger.error(f"Error en chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# --- MÓDULO PERFILES DE GOBIERNO & FIRESTORE ---
@app.get("/api/profiles")
async def list_profiles():
    """Retorna los 4 perfiles de gobierno persistidos en Firestore."""
    profiles = firestore_profile_service.get_all_profiles()
    active_profile = firestore_profile_service.get_active_profile()
    return JSONResponse(content={
        "status": "success",
        "active_profile_id": active_profile.get("id"),
        "total": len(profiles),
        "data": profiles
    })


@app.get("/api/profiles/active")
async def get_active_profile():
    active = firestore_profile_service.get_active_profile()
    return JSONResponse(content={"status": "success", "data": active})


@app.post("/api/profiles/switch")
async def switch_profile(req: ProfileSwitchRequest):
    """Cambia el perfil activo del agente y lo sincroniza con Firestore."""
    res = firestore_profile_service.set_active_profile(req.profile_id)
    if res.get("status") == "error":
        raise HTTPException(status_code=404, detail=res.get("message"))
    return JSONResponse(content={"status": "success", "data": res})


@app.post("/api/profiles/maturity_diagnosis")
async def calculate_maturity(req: MaturityDiagnosisRequest):
    """Calcula el diagnóstico de madurez de gobierno para el Perfil 2."""
    res = firestore_profile_service.calculate_maturity_diagnosis(req.answers or {})
    return JSONResponse(content={"status": "success", "data": res})


# --- MÓDULO 1: Knowledge Catalog & Metadatos ---
@app.get("/api/catalog/assets")
async def list_assets(cloud: Optional[str] = Query(None), domain: Optional[str] = Query(None)):
    assets = catalog_manager.list_assets(cloud=cloud, domain=domain)
    return JSONResponse(content={"status": "success", "total": len(assets), "data": assets})


@app.get("/api/catalog/assets/{asset_id}")
async def get_asset(asset_id: str):
    asset = catalog_manager.get_asset_by_id(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset no encontrado")
    return JSONResponse(content={"status": "success", "data": asset})


@app.get("/api/catalog/search")
async def search_catalog(q: str = Query(..., description="Query de búsqueda"), cloud: Optional[str] = Query(None)):
    results = catalog_manager.search_semantic(query=q, cloud=cloud)
    return JSONResponse(content={"status": "success", "query": q, "total": len(results), "data": results})


@app.post("/api/catalog/assets/{asset_id}/update")
async def update_asset_metadata(asset_id: str, req: MetadataUpdateRequest):
    updated = catalog_manager.update_metadata(
        asset_id=asset_id,
        description=req.description,
        steward=req.steward,
        golden_query=req.golden_query,
        column_updates=req.column_updates
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Error al actualizar metadatos")
    return JSONResponse(content={"status": "success", "message": "Metadatos actualizados", "data": updated})


@app.get("/api/catalog/glossary")
async def get_glossary():
    glossary = catalog_manager.get_glossary()
    return JSONResponse(content={"status": "success", "total": len(glossary), "data": glossary})


@app.post("/api/catalog/glossary")
async def add_glossary_term(req: GlossaryTermRequest):
    new_term = catalog_manager.add_glossary_term(
        term=req.term,
        definition=req.definition,
        domain=req.domain,
        approved_by=req.approved_by
    )
    return JSONResponse(content={"status": "success", "data": new_term})


# --- MÓDULO 1.1: Gobernanza y Gestión de Metadatos (Tagging & Tag Templates) ---
@app.get("/api/tags/templates")
async def get_tag_templates():
    templates = catalog_manager.get_tag_templates()
    return JSONResponse(content={"status": "success", "total": len(templates), "data": templates})


@app.get("/api/tags/asset/{asset_id}")
async def get_asset_tags(asset_id: str):
    tags_info = catalog_manager.get_asset_tags(asset_id)
    if not tags_info:
        raise HTTPException(status_code=404, detail="Asset no encontrado")
    return JSONResponse(content={"status": "success", "data": tags_info})


@app.post("/api/tags/asset/{asset_id}")
async def update_asset_tags(asset_id: str, req: TagUpdateRequest):
    updated = catalog_manager.update_asset_tags(
        asset_id=asset_id,
        template_id=req.template_id,
        fields=req.fields,
        column_tags=req.column_tags
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Error al actualizar etiquetas")
    return JSONResponse(content={"status": "success", "message": "Etiquetas de gobierno actualizadas", "data": updated})


@app.post("/api/tags/auto_tag_sdp/{asset_id}")
async def auto_tag_with_sdp(asset_id: str):
    tagged = catalog_manager.auto_tag_with_sdp(asset_id)
    if not tagged:
        raise HTTPException(status_code=404, detail="Error al ejecutar Auto-Tagging con SDP")
    return JSONResponse(content={"status": "success", "message": "Auto-Tagging ejecutado con éxito", "data": tagged})


# --- MÓDULO 2: SENSITIVE DATA PROTECTION (CLOUD DLP / SDP INTEGRAL) ---

# 2.0 Dashboard Ejecutivo (Looker Studio SDP Template)
@app.get("/api/sdp/dashboard/overview")
async def get_sdp_dashboard_overview(
    project: Optional[str] = Query("-"),
    asset_type: Optional[str] = Query("-"),
    data_risk: Optional[str] = Query("-"),
    encryption: Optional[str] = Query("-"),
    data_asset: Optional[str] = Query("-"),
    infotype: Optional[str] = Query("-"),
    data_sensitivity: Optional[str] = Query("-"),
    is_public: Optional[str] = Query("-"),
    data_location: Optional[str] = Query("-"),
    date_range: Optional[str] = Query("-")
):
    filters = {
        "project": project,
        "asset_type": asset_type,
        "data_risk": data_risk,
        "encryption": encryption,
        "data_asset": data_asset,
        "infotype": infotype,
        "data_sensitivity": data_sensitivity,
        "is_public": is_public,
        "data_location": data_location,
        "date_range": date_range
    }
    data = sdp_manager.get_dashboard_overview(filters=filters)
    return JSONResponse(content=data)


@app.post("/api/sdp/dashboard/remediate/{issue_id}")
async def remediate_sdp_dashboard_issue(issue_id: str):
    res = sdp_manager.remediate_dashboard_issue(issue_id)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return JSONResponse(content=res)


# 2.1 Discovery (Descubrimiento Continuo & Data Profiles)
@app.get("/api/sdp/discovery/profiles")
async def get_sdp_discovery_profiles(cloud: Optional[str] = Query(None), risk_level: Optional[str] = Query(None)):
    profiles = sdp_manager.get_discovery_profiles(cloud=cloud, risk_level=risk_level)
    return JSONResponse(content={"status": "success", "total": len(profiles), "data": profiles})


@app.get("/api/sdp/discovery/summary")
async def get_sdp_discovery_summary():
    summary = sdp_manager.get_discovery_summary()
    return JSONResponse(content={"status": "success", "data": summary})


@app.post("/api/sdp/discovery/scan")
async def run_sdp_discovery_scan(req: Optional[DiscoveryScanRequest] = None):
    asset_id = req.asset_id if req else None
    source_type = req.source_type if req else None
    cloud = req.cloud if req else None
    result = sdp_manager.run_discovery_profile_scan(asset_id=asset_id, source_type=source_type, cloud=cloud)
    return JSONResponse(content=result)


# 2.2 Inspection & InfoTypes (Built-in & Custom InfoTypes)
@app.get("/api/sdp/infotypes/builtin")
async def get_builtin_infotypes(category: Optional[str] = Query(None), q: Optional[str] = Query(None)):
    items = sdp_manager.get_builtin_infotypes(category=category, query=q)
    return JSONResponse(content={"status": "success", "total": len(items), "data": items})


@app.get("/api/sdp/infotypes/custom")
async def get_custom_infotypes():
    custom_list = sdp_manager.get_custom_infotypes()
    return JSONResponse(content={"status": "success", "total": len(custom_list), "data": custom_list})


@app.post("/api/sdp/infotypes/custom/create")
async def create_custom_infotype(req: CustomInfoTypeCreateRequest):
    try:
        created = sdp_manager.create_custom_infotype(
            name=req.name,
            display_name=req.display_name,
            infotype_type=req.type,
            regex_pattern=req.regex_pattern,
            dictionary_words=req.dictionary_words,
            likelihood=req.likelihood,
            hotwords=req.hotwords,
            description=req.description or "",
            created_by=req.created_by or "Data Steward"
        )
        return JSONResponse(content={"status": "success", "message": f"InfoType '{created['name']}' creado exitosamente", "data": created})
    except Exception as e:
        logger.error(f"Error creando custom infotype: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/sdp/infotypes/custom/test")
async def test_custom_infotype(req: CustomInfoTypeTestRequest):
    test_result = sdp_manager.test_custom_infotype(
        infotype_type=req.type,
        regex_pattern=req.regex_pattern,
        dictionary_words=req.dictionary_words,
        sample_text=req.sample_text,
        hotwords=req.hotwords
    )
    return JSONResponse(content=test_result)


@app.delete("/api/sdp/infotypes/custom/{infotype_id}")
async def delete_custom_infotype(infotype_id: str):
    deleted = sdp_manager.delete_custom_infotype(infotype_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="InfoType no encontrado")
    return JSONResponse(content={"status": "success", "message": "InfoType personalizado eliminado correctamente"})


# 2.3 Inspect Jobs (Trabajos de Inspección On-Demand)
@app.get("/api/sdp/inspect/jobs")
async def list_inspect_jobs():
    jobs = sdp_manager.list_inspect_jobs()
    return JSONResponse(content={"status": "success", "total": len(jobs), "data": jobs})


@app.post("/api/sdp/inspect/jobs/create_and_run")
async def create_and_run_inspect_job(req: InspectJobCreateRequest):
    try:
        job = sdp_manager.create_and_run_inspect_job(
            name=req.name,
            target_asset_id=req.target_asset_id,
            infotypes_selected=req.infotypes_selected,
            min_likelihood=req.min_likelihood,
            sampling_pct=req.sampling_pct,
            auto_apply_tags=req.auto_apply_tags,
            created_by=req.created_by or "Data Steward"
        )
        return JSONResponse(content={"status": "success", "message": f"Trabajo de inspección '{job['name']}' completado", "data": job})
    except Exception as e:
        logger.error(f"Error en inspect job: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# 2.4 Job Triggers (Disparadores Programados)
@app.get("/api/sdp/inspect/triggers")
async def list_job_triggers():
    triggers = sdp_manager.list_job_triggers()
    return JSONResponse(content={"status": "success", "total": len(triggers), "data": triggers})


@app.post("/api/sdp/inspect/triggers/create")
async def create_job_trigger(req: JobTriggerCreateRequest):
    try:
        trigger = sdp_manager.create_job_trigger(
            name=req.name,
            description=req.description,
            schedule=req.schedule,
            target_asset_id=req.target_asset_id,
            template_id=req.template_id,
            created_by=req.created_by or "Data Steward"
        )
        return JSONResponse(content={"status": "success", "message": f"Disparador '{trigger['name']}' configurado exitosamente", "data": trigger})
    except Exception as e:
        logger.error(f"Error creando trigger: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/sdp/inspect/triggers/{trigger_id}/toggle")
async def toggle_job_trigger(trigger_id: str):
    try:
        res = sdp_manager.toggle_job_trigger(trigger_id)
        return JSONResponse(content=res)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/sdp/inspect/triggers/{trigger_id}/run_now")
async def run_job_trigger_now(trigger_id: str):
    try:
        res = sdp_manager.run_job_trigger_now(trigger_id)
        return JSONResponse(content=res)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/sdp/inspect/triggers/{trigger_id}")
async def delete_job_trigger(trigger_id: str):
    deleted = sdp_manager.delete_job_trigger(trigger_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Disparador no encontrado")
    return JSONResponse(content={"status": "success", "message": "Disparador de inspección eliminado"})


# 2.5 Risk Analysis (k-anonymity, l-diversity, delta-presence) - EXCLUSIVO PARA BIGQUERY
@app.post("/api/sdp/risk_analysis/evaluate/{asset_id}")
async def evaluate_risk_analysis(asset_id: str, req: Optional[RiskAnalysisRequest] = None):
    try:
        q_ids = req.quasi_identifiers if req else None
        s_attrs = req.sensitive_attributes if req else None
        report = sdp_manager.evaluate_bigquery_risk_analysis(
            asset_id=asset_id,
            quasi_identifiers=q_ids,
            sensitive_attributes=s_attrs
        )
        return JSONResponse(content={"status": "success", "data": report})
    except ValueError as ve:
        # Error específico si el asset no es BigQuery o no existe
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error en Risk Analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sdp/risk_analysis/asset/{asset_id}")
async def get_risk_analysis_for_asset(asset_id: str):
    try:
        report = sdp_manager.evaluate_bigquery_risk_analysis(asset_id=asset_id)
        return JSONResponse(content={"status": "success", "data": report})
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


# 2.6 Plantillas (Templates: Inspect & Deidentify)
@app.get("/api/sdp/templates/inspect")
async def list_inspect_templates():
    templates = sdp_manager.list_inspect_templates()
    return JSONResponse(content={"status": "success", "total": len(templates), "data": templates})


@app.post("/api/sdp/templates/inspect/create")
async def create_inspect_template(req: InspectTemplateCreateRequest):
    new_tmpl = sdp_manager.create_inspect_template(
        name=req.name,
        description=req.description,
        infotypes=req.infotypes,
        min_likelihood=req.min_likelihood,
        max_findings=req.max_findings,
        created_by=req.created_by or "Data Steward"
    )
    return JSONResponse(content={"status": "success", "message": "Plantilla de inspección creada", "data": new_tmpl})


@app.get("/api/sdp/templates/deidentify")
async def list_deidentify_templates():
    templates = sdp_manager.list_deidentify_templates()
    return JSONResponse(content={"status": "success", "total": len(templates), "data": templates})


@app.post("/api/sdp/templates/deidentify/create")
async def create_deidentify_template(req: DeidentifyTemplateCreateRequest):
    new_tmpl = sdp_manager.create_deidentify_template(
        name=req.name,
        transformation_type=req.transformation_type,
        description=req.description,
        parameters=req.parameters,
        sample_input=req.sample_input,
        sample_output=req.sample_output,
        created_by=req.created_by or "Data Steward"
    )
    return JSONResponse(content={"status": "success", "message": "Plantilla de desidentificación creada", "data": new_tmpl})


# 2.7 Content Policies de Gobernanza Continua
@app.get("/api/sdp/policies")
async def list_sdp_content_policies():
    policies = sdp_manager.list_content_policies()
    return JSONResponse(content={"status": "success", "total": len(policies), "data": policies})


@app.post("/api/sdp/policies/{policy_id}/toggle")
async def toggle_sdp_content_policy(policy_id: str):
    try:
        res = sdp_manager.toggle_content_policy(policy_id)
        return JSONResponse(content=res)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/sdp/policies/evaluate")
async def evaluate_sdp_content_policies():
    res = sdp_manager.evaluate_content_policies()
    return JSONResponse(content=res)


# 2.8 Resumen y Acciones por Perfil Responsable
@app.get("/api/sdp/overview/{profile_id}")
async def get_sdp_persona_overview(profile_id: str):
    overview = sdp_manager.get_persona_overview(profile_id)
    return JSONResponse(content={"status": "success", "data": overview})


# Endpoints heredados / retrocompatibles
@app.api_route("/api/dlp/scan/{asset_id}", methods=["GET", "POST"])
async def run_dlp_scan(asset_id: str):
    scan_result = dlp_scanner.inspect_asset(asset_id)
    if not scan_result:
        raise HTTPException(status_code=404, detail="Asset no encontrado")
    return JSONResponse(content={"status": "success", "data": scan_result})


@app.post("/api/dlp/apply_policy_tags/{asset_id}")
async def apply_policy_tags(asset_id: str, req: PolicyTagRequest):
    res = policy_tagger.apply_tags_and_masking(asset_id, auto_mask=req.auto_mask)
    if res.get("status") == "error":
        raise HTTPException(status_code=404, detail=res.get("message"))
    return JSONResponse(content={"status": "success", "data": res})


# --- MÓDULO 3: Dataplex Data Quality ---
@app.api_route("/api/quality/scan/{asset_id}", methods=["GET", "POST"])
async def run_quality_scan(asset_id: str):
    quality_result = quality_engine.evaluate_asset(asset_id)
    if not quality_result:
        raise HTTPException(status_code=404, detail="Asset no encontrado")
    return JSONResponse(content={"status": "success", "data": quality_result})


@app.get("/api/quality/health")
async def get_global_health():
    health = quality_engine.get_global_health()
    return JSONResponse(content={"status": "success", "data": health})


@app.get("/api/quality/real_dataplex_scans")
async def get_real_dataplex_scans():
    scans = quality_engine.fetch_real_dataplex_scans()
    return JSONResponse(content={"status": "success", "total": len(scans), "data": scans})


# --- MÓDULO 4: Linaje de Datos & Impacto ---
@app.get("/api/lineage/{asset_id}")
async def get_lineage_graph(asset_id: str):
    graph = lineage_graph_builder.build_graph(asset_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Asset no encontrado")
    return JSONResponse(content={"status": "success", "data": graph})


@app.post("/api/lineage/impact_analysis/{asset_id}")
async def analyze_impact(asset_id: str, req: ImpactAnalysisRequest):
    impact = lineage_graph_builder.analyze_schema_impact(asset_id, req.modified_columns)
    return JSONResponse(content={"status": "success", "data": impact})


# --- MÓDULO 6: Data Stewards & Certificación IA ---
@app.get("/api/stewards/domains")
async def get_domains():
    domains = stewards_manager.get_domains_summary()
    return JSONResponse(content={"status": "success", "data": domains})


@app.get("/api/stewards/ai_readiness")
async def get_ai_readiness():
    readiness = stewards_manager.get_ai_readiness_list()
    return JSONResponse(content={"status": "success", "data": readiness})


@app.post("/api/stewards/certify_ai/{asset_id}")
async def certify_ai_dataset(asset_id: str, req: AICertificationRequest):
    res = stewards_manager.certify_dataset(asset_id, req.certified, req.notes or "")
    if res.get("status") == "error":
        raise HTTPException(status_code=404, detail=res.get("message"))
    return JSONResponse(content={"status": "success", "data": res})


# --- MÓDULO 7: Policy as Code & Knowledge Catalog MCP Server ---
@app.get("/api/policies")
async def list_policies():
    policies = policy_engine.get_all_policies()
    return JSONResponse(content={"status": "success", "total": len(policies), "data": policies})


@app.post("/api/policies/generate")
async def generate_policy(req: PolicyGenerateRequest):
    new_policy = policy_engine.generate_policy_from_natural_language(req.prompt)
    return JSONResponse(content={"status": "success", "data": new_policy, "message": "Política generada como código exitosamente"})


@app.post("/api/policies/execute")
async def execute_policies():
    exec_result = policy_engine.execute_all_policies()
    return JSONResponse(content={"status": "success", "data": exec_result})


@app.get("/api/policies/violations")
async def get_policy_violations():
    policy_engine._load_policies()
    violations = policy_engine.data.get("violations", [])
    return JSONResponse(content={"status": "success", "total": len(violations), "data": violations})


@app.post("/api/policies/remediate/{violation_id}")
async def remediate_policy_violation(violation_id: str):
    res = policy_engine.remediate_violation(violation_id)
    if res.get("status") == "error":
        raise HTTPException(status_code=404, detail=res.get("message"))
    return JSONResponse(content={"status": "success", "data": res})


@app.get("/api/policies/scorecard")
async def get_compliance_scorecard():
    scorecard = policy_engine.get_compliance_scorecard()
    return JSONResponse(content={"status": "success", "data": scorecard})


@app.get("/api/policies/export_csv")
async def export_violations_csv():
    csv_content = policy_engine.export_violations_report_csv()
    return HTMLResponse(content=csv_content, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=compliance_violations_report.csv"})


# --- CONECTORES MULTI-CLOUD ---
@app.get("/api/connectors/status")
async def get_connectors():
    status = connector_factory.get_all_connectors_status()
    return JSONResponse(content={"status": "success", "data": status})


@app.post("/api/connectors/sync_real_gcp")
async def sync_real_gcp():
    real_tables = gcp_connector.fetch_real_bigquery_tables()
    if real_tables:
        existing_ids = {a["id"] for a in catalog_manager.data.get("assets", [])}
        for rt in real_tables:
            if rt["id"] not in existing_ids:
                catalog_manager.data.setdefault("assets", []).append(rt)
        catalog_manager._save_data()

    return JSONResponse(content={
        "status": "success",
        "synced_tables_count": len(real_tables),
        "message": f"Se sincronizaron {len(real_tables)} tablas reales desde el proyecto GCP '{gcp_connector.project_id}'"
    })


# --- CONECTORES EXTERNOS & DESCUBRIMIENTO AUTOMATIZADO (MySQL, Azure, Postgres) ---
@app.post("/api/connectors/external/test")
async def test_external_db_connection(req: ExternalDBTestRequest):
    res = external_db_connector.test_mysql_connection(
        host=req.host,
        port=req.port,
        database=req.database,
        user=req.user,
        password=req.password,
        ssl_enabled=req.ssl_enabled
    )
    return JSONResponse(content={"status": "success", "data": res})


@app.post("/api/connectors/external/discover")
async def discover_external_db(req: ExternalDBDiscoverRequest):
    res = external_db_connector.discover_and_catalog_database(
        engine_type=req.engine,
        host=req.host,
        port=req.port,
        database=req.database,
        user=req.user,
        password=req.password,
        selected_tables=req.selected_tables,
        csv_tables_content=req.csv_content
    )
    return JSONResponse(content={"status": "success", "data": res})


# --- REGLAS DE CALIDAD DE NEGOCIO AVANZADAS & DRILL-DOWN ---
@app.get("/api/quality/business_rules")
async def list_business_quality_rules():
    rules = business_quality_engine.get_all_rules()
    last_eval = business_quality_engine.data.get("last_evaluation")
    return JSONResponse(content={"status": "success", "total": len(rules), "data": rules, "last_evaluation": last_eval})


@app.post("/api/quality/business_rules/evaluate")
async def evaluate_business_quality_rules():
    evaluation = business_quality_engine.evaluate_business_quality_rules()
    return JSONResponse(content={"status": "success", "data": evaluation})


@app.post("/api/quality/business_rules/update_threshold")
async def update_business_rule_threshold(req: ThresholdUpdateRequest):
    res = business_quality_engine.update_rule_threshold(req.rule_id, req.new_threshold)
    return JSONResponse(content=res)


# --- GOBERNANZA SEMÁNTICA LOOKER & MÉTRICAS DE NEGOCIO ---
@app.get("/api/looker/semantic_metrics")
async def list_looker_semantic_metrics():
    metrics = looker_governance_manager.list_governed_metrics()
    return JSONResponse(content={"status": "success", "total": len(metrics), "data": metrics})


@app.get("/api/config")
async def get_governance_config():
    cfg = stewards_manager.load_config()
    return JSONResponse(content={"status": "success", "data": cfg})


# --- Frontend Estático ---
if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
    app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")

    @app.get("/")
    async def serve_index():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return HTMLResponse("<h1>Frontend cargando...</h1>")


def run():
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8085, reload=True)


if __name__ == "__main__":
    run()
