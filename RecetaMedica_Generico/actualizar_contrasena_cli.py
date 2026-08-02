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

import sys
import os
from dotenv import load_dotenv

# Cargar las variables de entorno para tener acceso al proyecto de GCP
load_dotenv()

from logica.firebase_auth import actualizar_contrasena

def main():
    if len(sys.argv) < 3:
        print("\n=== Utilidad CLI para Actualizar Contraseñas en Firestore ===")
        print("Uso:")
        print("  python actualizar_contrasena_cli.py <usuario> <nueva_contraseña>\n")
        print("Ejemplo:")
        print("  python actualizar_contrasena_cli.py admin mi_nueva_clave_segura\n")
        sys.exit(1)
        
    usuario = sys.argv[1]
    contrasena = sys.argv[2]
    
    if len(contrasena) < 6:
        print("Error: La contraseña debe tener al menos 6 caracteres por seguridad.")
        sys.exit(1)
        
    print(f"Actualizando contraseña para el usuario '{usuario}' en el proyecto '{os.getenv('GOOGLE_CLOUD_PROJECT')}'...")
    
    if actualizar_contrasena(usuario, contrasena):
        print(f"¡Éxito! Contraseña de '{usuario}' actualizada de forma segura en Firestore.")
    else:
        print(f"Fallo: El usuario '{usuario}' no fue encontrado en la colección de Firestore.")

if __name__ == "__main__":
    main()
