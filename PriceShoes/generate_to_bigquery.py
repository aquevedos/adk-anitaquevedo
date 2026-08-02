import os
import argparse
import random
import math
from datetime import datetime, timedelta
from google.cloud import bigquery

def parse_arguments():
    parser = argparse.ArgumentParser(description="Genera datos sintéticos de retail y los almacena en Google Cloud BigQuery.")
    
    parser.add_argument(
        "--project",
        type=str,
        default=os.getenv("GOOGLE_CLOUD_PROJECT", "agentspace-demos-466121"),
        help="ID del Proyecto de Google Cloud"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        help="Nombre del Dataset de BigQuery destino"
    )
    parser.add_argument(
        "--sales-table",
        type=str,
        default="sales_history",
        help="Nombre de la Tabla destino para el historial de ventas"
    )
    parser.add_argument(
        "--products-table",
        type=str,
        default="products",
        help="Nombre de la Tabla destino para el catálogo de productos"
    )
    parser.add_argument(
        "--location",
        type=str,
        default="US",
        help="Ubicación geográfica del dataset"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=730,
        help="Número de días de historial de ventas a generar"
    )
    
    return parser.parse_args()

def init_bigquery_destination(project_id, dataset_id, sales_table_name, products_table_name, location):
    client = bigquery.Client(project=project_id)
    
    # 1. Crear el dataset si no existe
    dataset_ref = bigquery.DatasetReference(project_id, dataset_id)
    try:
        client.get_dataset(dataset_ref)
        print(f"El dataset '{dataset_id}' ya existe.")
    except Exception:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = location
        dataset = client.create_dataset(dataset, timeout=30)
        print(f"Se creó exitosamente el dataset '{project_id}.{dataset_id}' en ubicación '{location}'")
        
    # 2. Configurar la tabla de productos
    products_table_id = f"{project_id}.{dataset_id}.{products_table_name}"
    client.delete_table(products_table_id, not_found_ok=True)
    products_schema = [
        bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("category", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("price", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("lead_time_days", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("current_stock", "INTEGER", mode="REQUIRED"),
    ]
    products_table = bigquery.Table(products_table_id, schema=products_schema)
    client.create_table(products_table)
    print(f"Se creó exitosamente la tabla: '{products_table_id}'")
    
    # 3. Configurar la tabla de historial de ventas
    sales_table_id = f"{project_id}.{dataset_id}.{sales_table_name}"
    client.delete_table(sales_table_id, not_found_ok=True)
    sales_schema = [
        bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("product_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("sales", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("stock_level", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("lost_sales", "INTEGER", mode="REQUIRED"),
    ]
    sales_table = bigquery.Table(sales_table_id, schema=sales_schema)
    sales_table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="date"
    )
    client.create_table(sales_table)
    print(f"Se creó exitosamente la tabla particionada: '{sales_table_id}'")
    
    return client, products_table_id, sales_table_id

def generate_synthetic_data(products, days_count):
    print(f"Generando {days_count} días de historial de ventas para el catálogo...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_count)
    
    sales_rows = []
    random.seed(42) # Semilla fija para reproducibilidad
    
    for p in products:
        prod_id = p["id"]
        category = p["category"]
        
        # Parámetros base de demanda promedio por categoría
        base_demand = {
            "Sandals": 12,
            "Boots": 10,
            "Sneakers": 20,
            "Dress Shoes": 8
        }[category]
        
        # Nivel inicial de stock
        simulated_stock = 150
        
        for d in range(days_count):
            dt = start_date + timedelta(days=d)
            day_of_week = dt.weekday()
            month = dt.month
            
            # 1. Factor de Estacionalidad
            if category == "Sandals":
                seasonality = 1.8 if month in [4, 5, 6, 7, 8] else 0.3
            elif category == "Boots":
                seasonality = 2.0 if month in [10, 11, 12, 1, 2] else 0.2
            elif category == "Sneakers":
                seasonality = 1.5 if month in [8, 12] else 1.0
            elif category == "Dress Shoes":
                seasonality = 2.2 if month == 12 else 0.8
            else:
                seasonality = 1.0
                
            # 2. Factor Fin de Semana
            dow_factor = 1.8 if day_of_week in [4, 5, 6] else 0.8
            
            # 3. Factor de Crecimiento Anual
            year_factor = 1.0 if dt.year < 2025 else 1.15
            
            # 4. Ruido
            u1, u2 = random.random(), random.random()
            noise = math.sqrt(-2.0 * math.log(max(1e-9, u1))) * math.cos(2.0 * math.pi * u2) * 2.0
            
            # 5. Demanda Real
            demand = int(max(0, (base_demand * seasonality * dow_factor * year_factor) + noise))
            
            # 6. Simulación de stock-outs
            is_stockout_period = False
            if category == "Boots" and month == 12 and dt.day in range(15, 25):
                is_stockout_period = True
            if category == "Sandals" and month == 7 and dt.day in range(1, 10):
                is_stockout_period = True
                
            if is_stockout_period:
                simulated_stock = 0
                
            if simulated_stock >= demand:
                sales = demand
                simulated_stock -= sales
                lost_sales = 0
            else:
                sales = simulated_stock
                lost_sales = demand - sales
                simulated_stock = 0
                
            stock_level = simulated_stock
            
            # Simulación de resurtido
            if stock_level < 20 and not is_stockout_period:
                if random.random() < 0.2:
                    simulated_stock += random.randint(80, 150)
            
            sales_rows.append({
                "date": dt.strftime('%Y-%m-%d'),
                "product_id": prod_id,
                "sales": sales,
                "stock_level": stock_level,
                "lost_sales": lost_sales
            })
            
    return sales_rows

def upload_data_to_bigquery(client, table_id, data_rows):
    total_rows = len(data_rows)
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    job = client.load_table_from_json(data_rows, table_id, job_config=job_config)
    job.result()
    print(f"¡Carga exitosa! Se guardaron {total_rows} filas en la tabla '{table_id}'.")

def main():
    args = parse_arguments()
    
    products = [
        {"id": "SAN-001", "name": "Sandalia Playera Confort", "category": "Sandals", "price": 350.0, "lead_time_days": 7, "current_stock": 45},
        {"id": "SAN-002", "name": "Plataforma Corcho Chic", "category": "Sandals", "price": 599.0, "lead_time_days": 10, "current_stock": 20},
        {"id": "BOO-001", "name": "Bota Alta Piel Negra", "category": "Boots", "price": 1299.0, "lead_time_days": 15, "current_stock": 10},
        {"id": "BOO-002", "name": "Botín Gamuza Café", "category": "Boots", "price": 1299.0, "lead_time_days": 12, "current_stock": 5},
        {"id": "SNE-001", "name": "Tenis Urban Blanco", "category": "Sneakers", "price": 799.0, "lead_time_days": 5, "current_stock": 80},
        {"id": "SNE-002", "name": "Tenis Deportivo Run", "category": "Sneakers", "price": 950.0, "lead_time_days": 7, "current_stock": 60},
        {"id": "DRE-001", "name": "Zapatilla Tacón Aguja", "category": "Dress Shoes", "price": 699.0, "lead_time_days": 14, "current_stock": 25},
        {"id": "DRE-002", "name": "Mocasín Formal Piel", "category": "Dress Shoes", "price": 850.0, "lead_time_days": 10, "current_stock": 30}
    ]
    
    # 1. Preparar las tablas y el dataset en BigQuery
    client, products_table_id, sales_table_id = init_bigquery_destination(
        project_id=args.project,
        dataset_id=args.dataset,
        sales_table_name=args.sales_table,
        products_table_name=args.products_table,
        location=args.location
    )
    
    # 2. Subir Catálogo de Productos
    print("Subiendo catálogo de productos...")
    upload_data_to_bigquery(client, products_table_id, products)
    
    # 3. Generar datos sintéticos
    sales_rows = generate_synthetic_data(products, days_count=args.days)
    
    # 4. Subir datos de ventas generados
    print("Subiendo historial de ventas...")
    upload_data_to_bigquery(client, sales_table_id, sales_rows)
    
    print("\nProceso finalizado exitosamente. Tus datos de simulación ya están en BigQuery.")

if __name__ == '__main__':
    main()
