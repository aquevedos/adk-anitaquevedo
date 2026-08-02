import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import csv
import pandas as pd
from datetime import datetime
from math import ceil
from google.cloud import bigquery
from google.adk.tools import ToolContext
from google.genai import types

# Cargar configuraciones básicas
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "agentspace-demos-466121")
DATASET_ID = os.getenv("DATASET_ID", "price_shoes_test")

def _get_bq_client():
    return bigquery.Client(project=PROJECT_ID)

def _ensure_arima_model(client):
    model_id = f"{PROJECT_ID}.{DATASET_ID}.arima_model"
    try:
        client.get_model(model_id)
    except Exception:
        print("El modelo ARIMA_PLUS no existe. Entrenándolo ahora...")
        train_query = f"""
        CREATE OR REPLACE MODEL `{model_id}`
        OPTIONS(
          model_type='ARIMA_PLUS',
          time_series_timestamp_col='date_ts',
          time_series_data_col='sales',
          time_series_id_col='product_id',
          data_frequency='DAILY',
          holiday_region='MX'
        ) AS
        SELECT
          TIMESTAMP(date) as date_ts,
          product_id,
          sales
        FROM
          `{PROJECT_ID}.{DATASET_ID}.sales_history`
        """
        client.query(train_query).result()
        print("Entrenamiento del modelo completado exitosamente.")

async def obtener_catalogo_productos() -> list:
    """
    Obtiene el catálogo completo de productos de Price Shoes con sus existencias actuales,
    precio y lead time (días de entrega del proveedor).
    
    Returns:
        list: Lista de diccionarios con la información de los productos.
    """
    client = _get_bq_client()
    query = f"SELECT id, name, category, price, lead_time_days, current_stock FROM `{PROJECT_ID}.{DATASET_ID}.products` ORDER BY category, id"
    query_job = client.query(query)
    results = query_job.result()
    
    catalog = []
    for r in results:
        catalog.append({
            "id": r.id,
            "name": r.name,
            "category": r.category,
            "price": r.price,
            "lead_time_days": r.lead_time_days,
            "current_stock": r.current_stock
        })
    return catalog

async def ejecutar_pronostico(product_id: str, dias_horizonte: int = 30) -> dict:
    """
    Calcula las ventas proyectadas para un producto específico en los próximos dias_horizonte (por defecto 30).
    Realiza una predicción en BigQuery ML usando el modelo ARIMA_PLUS y devuelve el historial reciente junto al pronóstico.
    
    Args:
        product_id: ID del producto (ej: 'SAN-001', 'BOO-001').
        dias_horizonte: Horizonte de pronóstico en días (1 a 90).
    """
    client = _get_bq_client()
    _ensure_arima_model(client)
    
    # 1. Obtener Historial de Ventas Recientes (últimos 60 días)
    history_query = f"""
    SELECT date, sales, stock_level, lost_sales
    FROM `{PROJECT_ID}.{DATASET_ID}.sales_history`
    WHERE product_id = '{product_id}'
    ORDER BY date DESC
    LIMIT 60
    """
    history_df = client.query(history_query).to_dataframe()
    history_df['date'] = history_df['date'].astype(str)
    history_data = history_df.iloc[::-1].to_dict(orient='records') # Invertir para orden cronológico
    
    # 2. Obtener Pronóstico de BigQuery ML
    forecast_query = f"""
    SELECT 
      CAST(forecast_timestamp AS DATE) as date,
      ROUND(forecast_value, 2) as forecast,
      ROUND(confidence_interval_lower_bound, 2) as lower_bound,
      ROUND(confidence_interval_upper_bound, 2) as upper_bound
    FROM 
      ML.FORECAST(MODEL `{PROJECT_ID}.{DATASET_ID}.arima_model`, STRUCT({dias_horizonte} AS horizon, 0.90 AS confidence_level))
    WHERE 
      product_id = '{product_id}'
    ORDER BY 
      date ASC
    """
    forecast_df = client.query(forecast_query).to_dataframe()
    forecast_df['date'] = forecast_df['date'].astype(str)
    forecast_data = forecast_df.to_dict(orient='records')
    
    # 3. Datos del producto
    product_query = f"SELECT name, category, current_stock, lead_time_days FROM `{PROJECT_ID}.{DATASET_ID}.products` WHERE id = '{product_id}'"
    prod_info = list(client.query(product_query).result())
    product_name = prod_info[0].name if prod_info else "Producto Desconocido"
    
    return {
        "status": "success",
        "product_id": product_id,
        "product_name": product_name,
        "historial": history_data,
        "pronostico": forecast_data
    }

async def obtener_analisis_inventario() -> dict:
    """
    Realiza un análisis integral del estado de inventario actual, calcula el Stock de Seguridad óptimo
    y propone la cantidad sugerida de compra para todos los productos de Price Shoes.
    
    Formula:
        Safety Stock = Sum(Confidence Interval Upper Bound - Forecast Value) sobre el Lead Time.
        Suggested Order = (Lead Time Demand + Safety Stock) - Current Stock.
    """
    client = _get_bq_client()
    _ensure_arima_model(client)
    
    query = f"""
    WITH forecast_raw AS (
      SELECT
        product_id,
        CAST(forecast_timestamp AS DATE) AS date,
        forecast_value,
        confidence_interval_upper_bound
      FROM
        ML.FORECAST(MODEL `{PROJECT_ID}.{DATASET_ID}.arima_model`, STRUCT(30 AS horizon, 0.90 AS confidence_level))
    ),
    forecast_with_rn AS (
      SELECT
        f.*,
        p.name AS product_name,
        p.category,
        p.current_stock,
        p.lead_time_days,
        ROW_NUMBER() OVER(PARTITION BY f.product_id ORDER BY f.date ASC) as day_num
      FROM
        forecast_raw f
      JOIN
        `{PROJECT_ID}.{DATASET_ID}.products` p ON f.product_id = p.id
    ),
    lead_time_forecast AS (
      SELECT
        product_id,
        product_name,
        category,
        current_stock,
        lead_time_days,
        SUM(CASE WHEN day_num <= lead_time_days THEN forecast_value ELSE 0 END) as forecasted_demand_lead_time,
        SUM(CASE WHEN day_num <= lead_time_days THEN (confidence_interval_upper_bound - forecast_value) ELSE 0 END) as raw_safety_stock
      FROM
        forecast_with_rn
      GROUP BY
        product_id, product_name, category, current_stock, lead_time_days
    )
    SELECT
      product_id,
      product_name,
      category,
      current_stock,
      lead_time_days,
      ROUND(forecasted_demand_lead_time, 1) as demand_lead_time,
      CAST(CEIL(raw_safety_stock) AS INT64) as safety_stock,
      CAST(GREATEST(0, CEIL(forecasted_demand_lead_time + raw_safety_stock - current_stock)) AS INT64) as suggested_order_qty,
      CASE 
        WHEN current_stock <= (forecasted_demand_lead_time * 0.3) THEN 'CRITICAL'
        WHEN current_stock <= forecasted_demand_lead_time THEN 'HIGH'
        WHEN current_stock <= (forecasted_demand_lead_time + raw_safety_stock) THEN 'MEDIUM'
        ELSE 'LOW'
      END as priority
    FROM
      lead_time_forecast
    ORDER BY
      suggested_order_qty DESC
    """
    query_job = client.query(query)
    results = query_job.result()
    
    analysis = []
    for r in results:
        analysis.append({
            "product_id": r.product_id,
            "product_name": r.product_name,
            "category": r.category,
            "current_stock": r.current_stock,
            "lead_time_days": r.lead_time_days,
            "demand_lead_time": r.demand_lead_time,
            "safety_stock": r.safety_stock,
            "suggested_order_qty": r.suggested_order_qty,
            "priority": r.priority
        })
        
    return {
        "status": "success",
        "analisis": analysis
    }

async def obtener_optimizacion_precios() -> list:
    """
    Analiza la rotación de inventario actual contra la demanda esperada de los productos y
    recomienda ajustes dinámicos de precios (descuentos para liquidar exceso de stock o 
    incrementos marginales para maximizar ganancias en productos de alta demanda y bajo stock).
    
    Returns:
        list: Lista de diccionarios con recomendaciones de precios.
    """
    client = _get_bq_client()
    query = f"""
    WITH sales_30d AS (
      SELECT 
        product_id,
        AVG(sales) as avg_daily_sales
      FROM `{PROJECT_ID}.{DATASET_ID}.sales_history`
      WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
      GROUP BY product_id
    )
    SELECT 
      p.id,
      p.name,
      p.category,
      p.price as current_price,
      p.current_stock,
      COALESCE(ROUND(s.avg_daily_sales, 2), 0.0) as avg_daily_sales,
      CASE 
        WHEN COALESCE(s.avg_daily_sales, 0.0) = 0 THEN 999.0
        ELSE ROUND(p.current_stock / s.avg_daily_sales, 1)
      END as days_of_coverage
    FROM `{PROJECT_ID}.{DATASET_ID}.products` p
    LEFT JOIN sales_30d s ON p.id = s.product_id
    """
    results = client.query(query).result()
    
    recommendations = []
    for r in results:
        days = r.days_of_coverage
        price = r.current_price
        
        if days > 90:
            action = "DESCUENTO / LIQUIDACIÓN"
            pct = 20 if days < 150 else 30
            new_price = round(price * (1 - pct/100), 2)
            reason = f"Exceso de inventario ({days} días de cobertura). Se sugiere descuento de {pct}% para liberar capital y espacio en bodega."
        elif days < 15 and r.current_stock > 0:
            action = "INCREMENTO PREVENTIVO"
            pct = 5 if r.category != "Sneakers" else 8
            new_price = round(price * (1 + pct/100), 2)
            reason = f"Baja cobertura ({days} días). Se sugiere incremento de precio del {pct}% para regular la velocidad de venta y capturar mayor margen."
        else:
            action = "MANTENER PRECIO"
            pct = 0
            new_price = price
            reason = f"Nivel de inventario saludable ({days} días de cobertura)."
            
        recommendations.append({
            "id": r.id,
            "name": r.name,
            "category": r.category,
            "current_price": price,
            "new_price": new_price,
            "action": action,
            "reason": reason
        })
        
    return recommendations

async def simular_impacto_promocion(category: str, sales_lift_pct: float) -> dict:
    """
    Simula el impacto de una campaña promocional (ej. Hot Sale, Buen Fin) para una categoría
    específica de calzado, incrementando el pronóstico de demanda y calculando el stock extra necesario.
    
    Args:
        category: Categoría de calzado ('Sandals', 'Boots', 'Sneakers', 'Dress Shoes').
        sales_lift_pct: Porcentaje estimado de incremento en ventas (ej: 30 para +30% de ventas).
    """
    client = _get_bq_client()
    _ensure_arima_model(client)
    
    query = f"""
    WITH forecast_raw AS (
      SELECT 
        product_id,
        CAST(forecast_timestamp AS DATE) as date,
        forecast_value
      FROM 
        ML.FORECAST(MODEL `{PROJECT_ID}.{DATASET_ID}.arima_model`, STRUCT(30 AS horizon, 0.90 AS confidence_level))
    ),
    forecast_filtered AS (
      SELECT 
        f.*,
        p.name,
        p.category,
        p.current_stock,
        p.price
      FROM forecast_raw f
      JOIN `{PROJECT_ID}.{DATASET_ID}.products` p ON f.product_id = p.id
      WHERE p.category = '{category}'
    )
    SELECT 
      product_id,
      name,
      current_stock,
      price,
      ROUND(SUM(forecast_value), 1) as normal_forecast_30d
    FROM forecast_filtered
    GROUP BY product_id, name, current_stock, price
    """
    results = client.query(query).result()
    
    simulations = []
    total_extra_stock = 0
    total_extra_cost = 0
    
    for r in results:
        normal_f = r.normal_forecast_30d
        promo_f = round(normal_f * (1 + sales_lift_pct/100), 1)
        extra_needed = max(0, ceil(promo_f - r.current_stock))
        cost = round(extra_needed * r.price * 0.6, 2)
        
        total_extra_stock += extra_needed
        total_extra_cost += cost
        
        simulations.append({
            "product_id": r.product_id,
            "product_name": r.name,
            "current_stock": r.current_stock,
            "normal_forecast_30d": normal_f,
            "promotional_forecast_30d": promo_f,
            "extra_stock_required": extra_needed,
            "acquisition_cost_mxn": cost
        })
        
    return {
        "status": "success",
        "category": category,
        "sales_lift_pct": sales_lift_pct,
        "resumen": {
            "total_unidades_adicionales": total_extra_stock,
            "costo_adquisicion_estimado_mxn": total_extra_cost
        },
        "detalles": simulations
    }

async def crear_orden_compra(productos_pedidos: str, tool_context: ToolContext) -> dict:
    """
    Crea una Orden de Compra oficial consolidada basada en una lista de productos y cantidades.
    Genera y guarda un archivo CSV descargable en el contexto de la sesión.
    
    Args:
        productos_pedidos: String de IDs de productos y cantidades en formato 'ID:CANTIDAD' separados por comas.
                         Ejemplo: "SAN-001:120, BOO-002:80"
    """
    client = _get_bq_client()
    
    items = {}
    for part in productos_pedidos.split(","):
        part = part.strip()
        if not part: continue
        try:
            pid, qty = part.split(":")
            items[pid.strip()] = int(qty.strip())
        except ValueError:
            return {"status": "error", "message": f"Formato incorrecto en '{part}'. Debe ser 'PRODUCT_ID:CANTIDAD'"}
            
    if not items:
        return {"status": "error", "message": "No se especificaron productos u órdenes válidas."}
        
    placeholders = ", ".join([f"'{k}'" for k in items.keys()])
    query = f"SELECT id, name, category, price FROM `{PROJECT_ID}.{DATASET_ID}.products` WHERE id IN ({placeholders})"
    results = client.query(query).result()
    
    po_lines = []
    grand_total = 0
    
    for r in results:
        qty = items[r.id]
        unit_cost = round(r.price * 0.6, 2)
        subtotal = round(qty * unit_cost, 2)
        grand_total += subtotal
        
        po_lines.append({
            "id": r.id,
            "name": r.name,
            "category": r.category,
            "qty": qty,
            "unit_cost": unit_cost,
            "subtotal": subtotal
        })
        
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Orden de Compra Price Shoes S.A."])
    writer.writerow(["Fecha de Emision", datetime.now().strftime('%Y-%m-%d %H:%M')])
    writer.writerow([])
    writer.writerow(["ID Producto", "Nombre", "Categoria", "Cantidad Ordenada", "Costo Unitario (MXN)", "Subtotal (MXN)"])
    for line in po_lines:
        writer.writerow([
            line["id"],
            line["name"],
            line["category"],
            line["qty"],
            line["unit_cost"],
            line["subtotal"]
        ])
    writer.writerow([])
    writer.writerow(["", "", "", "", "TOTAL GENERAL:", grand_total])
    
    csv_data = output.getvalue().encode("utf-8")
    filename = f"orden_compra_PriceShoes.csv"
    
    await tool_context.save_artifact(
        filename=filename,
        artifact=types.Part(inline_data=types.Blob(mime_type="text/csv", data=csv_data))
    )
    
    return {
        "status": "success",
        "archivo_generado": filename,
        "total_articulos": sum(items.values()),
        "costo_total_mxn": grand_total,
        "detalles": po_lines,
        "mensaje": f"Se ha generado exitosamente el archivo de orden de compra '{filename}' y guardado como artefacto."
    }
