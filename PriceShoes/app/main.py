import os
import sys
import json
import io
from fastapi import FastAPI, Request, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from google.genai import types as genai_types
from google.genai import Client
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts.file_artifact_service import FileArtifactService

# Agregar el directorio raíz al path para importar el agente
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_forecast.agent import root_agent
from agent_forecast.tools import (
    obtener_catalogo_productos,
    ejecutar_pronostico,
    obtener_analisis_inventario,
    obtener_optimizacion_precios,
    simular_impacto_promocion
)

# Configurar Variables de Entorno por Defecto
if "GOOGLE_CLOUD_PROJECT" not in os.environ:
    os.environ["GOOGLE_CLOUD_PROJECT"] = "agentspace-demos-466121"
if "DATASET_ID" not in os.environ:
    os.environ["DATASET_ID"] = "price_shoes_test"

# Configurar e Inicializar el Servicio de Artefactos en Disco
artifacts_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app_artifacts"))
os.makedirs(artifacts_dir, exist_ok=True)
artifact_service = FileArtifactService(root_dir=artifacts_dir)

# Inicializar Servicio de Sesión de ADK y Runner con Soporte para Artefactos
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name="calzaintel",
    session_service=session_service,
    artifact_service=artifact_service,
    auto_create_session=True
)

app = FastAPI(title="Price Shoes - Demanda Inteligente")

# Montar archivos estáticos y plantillas
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

class ChatRequest(BaseModel):
    message: str
    session_id: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/catalog")
async def get_catalog():
    try:
        return await obtener_catalogo_productos()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/forecast/{product_id}")
async def get_product_forecast(product_id: str):
    try:
        return await ejecutar_pronostico(product_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/inventory-analysis")
async def get_inventory_analysis():
    try:
        return await obtener_analisis_inventario()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pricing-optimization")
async def get_pricing_optimization():
    try:
        return await obtener_optimizacion_precios()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/simulate-promotion")
async def get_promotion_simulation(category: str, sales_lift_pct: float):
    try:
        return await simular_impacto_promocion(category, sales_lift_pct)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/artifacts/{session_id}/{filename}")
async def download_artifact_endpoint(session_id: str, filename: str):
    try:
        user_id = "default_user"
        part = await artifact_service.load_artifact(
            app_name="calzaintel",
            user_id=user_id,
            filename=filename,
            session_id=session_id
        )
        if not part or not part.inline_data:
            raise HTTPException(status_code=404, detail=f"Artefacto {filename} no encontrado en la sesión {session_id}")
            
        file_bytes = part.inline_data.data
        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type=part.inline_data.mime_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al descargar artefacto: {str(e)}")

@app.post("/api/analyze-image")
async def analyze_image_endpoint(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        
        prompt = """
        Analiza esta imagen de calzado para el catálogo de Price Shoes y devuelve un objeto JSON estructurado con las siguientes propiedades exactas:
        {
          "category": "Sandals" | "Boots" | "Sneakers" | "Dress Shoes",
          "copywriting": "Una descripción de marketing atractiva, elegante y persuasiva en español de moda (aproximadamente de 60 a 80 palabras). Destaca los materiales, la comodidad y el estilo.",
          "tariff_hs_code": "Fracción arancelaria de importación estimada para México (formato de 8 dígitos, ej: 6403.99.99)",
          "tariff_rate": "Porcentaje arancelario aplicable (ej: 15%)",
          "retouch_background_removed": true | false (es true solo si el fondo es blanco puro o transparente sin elementos extra),
          "retouch_lighting_ok": true | false (es true si la iluminación del calzado es clara, uniforme y profesional),
          "retouch_centered": true | false (es true si el calzado está centrado y alineado),
          "image_resolution_score": entero del 1 al 10 (calidad visual y de nitidez),
          "status": "APPROVED" | "REQUIRES_RETOUCH" (APPROVED si background, lighting y centered son true y resolution_score >= 7, de lo contrario REQUIRES_RETOUCH)
        }
        Asegúrate de responder ÚNICAMENTE con el objeto JSON válido. No agregues formatos de markdown ```json ni explicaciones adicionales.
        """
        
        client = Client()
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                genai_types.Part.from_bytes(
                    data=contents,
                    mime_type=file.content_type
                ),
                prompt
            ],
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        result_json = json.loads(response.text)
        
        # Sanitizar nombre del archivo para la ruta de storage
        filename_sanitized = "".join([c if c.isalnum() or c in "._-" else "_" for c in file.filename])
        result_json["cloud_storage_path"] = f"gs://priceshoes-catalog-images/{result_json['category'].lower()}/{filename_sanitized}"
        
        return result_json
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al analizar la imagen: {str(e)}")

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    user_id = "default_user"
    
    async def event_generator():
        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=req.session_id,
                new_message=genai_types.Content(
                    role="user",
                    parts=[genai_types.Part.from_text(text=req.message)]
                ),
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            # Reemplazar SESSION_ID dinámicamente con la sesión del usuario
                            text_replaced = part.text.replace("SESSION_ID", req.session_id)
                            yield text_replaced
        except Exception as e:
            yield f"\n[Error de Agente: {str(e)}]"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
