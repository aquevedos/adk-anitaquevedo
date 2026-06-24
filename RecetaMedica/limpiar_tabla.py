# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import logging
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def limpiar_tabla_prescripciones(interactivo=True):
    """
    Script de utilidad para vaciar (truncar) la tabla de prescripciones médicas en BigQuery
    antes de realizar nuevas rondas de pruebas. Incluye confirmación de seguridad obligatoria.
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    dataset_id = "recetamedicas"
    table_id = "prescripciones"
    full_table_id = f"{project_id}.{dataset_id}.{table_id}"

    print("\n" + "="*55)
    print(" ⚠️  ADVERTENCIA DE SEGURIDAD (Data Loss Prevention) ⚠️")
    print("="*55)
    print(f"Estás a punto de eliminar TODOS los registros existentes en la tabla de BigQuery:")
    print(f"👉 {full_table_id}")
    print("Esta acción vaciará completamente los datos para iniciar pruebas desde cero.\n")
    
    if interactivo:
        try:
            confirmacion = input("¿Estás absolutamente seguro de limpiar la tabla? Escribe 'SI' (en mayúsculas) para confirmar: ").strip()
        except KeyboardInterrupt:
            print("\nOperación cancelada por el usuario.")
            sys.exit(0)
        
        if confirmacion != "SI":
            print("\nOperación de limpieza abortada exitosamente. Tu tabla y datos permanecen intactos.")
            return

    try:
        client = bigquery.Client(project=project_id)
        
        # Eliminar completamente las tablas para asegurar que se creen desde cero con los esquemas más recientes
        queries = [
            f"DROP TABLE IF EXISTS `{project_id}.{dataset_id}.prescripciones`",
            f"DROP TABLE IF EXISTS `{project_id}.{dataset_id}.prescripciones_gerencia`"
        ]
        
        for query in queries:
            logger.info(f"Ejecutando trabajo de purga en BigQuery: {query}")
            query_job = client.query(query)
            query_job.result()
        
        print(f"\n✅ ¡Limpieza exitosa! Las tablas de prueba en {project_id}.{dataset_id} han sido eliminadas y se recrearán limpias en la siguiente ejecución.")

    except Exception as e:
        logger.error(f"Error ejecutando la consulta de limpieza en BigQuery: {e}")
        print(f"\n❌ Falló el intento de truncar la tabla. Detalles del error:\n{e}")

if __name__ == "__main__":
    limpiar_tabla_prescripciones()
