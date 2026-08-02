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
import hashlib
import logging
import datetime
from google.cloud import firestore

logger = logging.getLogger(__name__)

# Configuración de Firestore
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "agentspace-demos-466121")
COLLECTION_NAME = "usuarios"

def get_firestore_client():
    """Retorna el cliente de Firestore inicializado."""
    try:
        return firestore.Client(project=PROJECT_ID)
    except Exception as e:
        logger.error(f"Error al conectar con Firestore en el proyecto {PROJECT_ID}: {e}")
        raise e

def hash_password(password: str) -> str:
    """Aplica el algoritmo scrypt para hash de contraseña de forma segura."""
    salt = os.urandom(16)
    # scrypt con parámetros estándar de alta seguridad
    key = hashlib.scrypt(
        password.encode('utf-8'),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        dklen=64
    )
    return f"{salt.hex()}:{key.hex()}"

def verify_password(stored_password: str, provided_password: str) -> bool:
    """Verifica si la contraseña ingresada coincide con la guardada usando scrypt."""
    try:
        salt_hex, key_hex = stored_password.split(':')
        salt = bytes.fromhex(salt_hex)
        key = bytes.fromhex(key_hex)
        new_key = hashlib.scrypt(
            provided_password.encode('utf-8'),
            salt=salt,
            n=16384,
            r=8,
            p=1,
            dklen=64
        )
        return new_key == key
    except Exception as e:
        logger.error(f"Error al verificar la contraseña: {e}")
        return False

def registrar_usuario(username: str, password: str) -> bool:
    """Registra un nuevo usuario en la base de datos de Firestore."""
    db = get_firestore_client()
    username_clean = username.strip().lower()
    
    # Referencia al documento del usuario
    user_ref = db.collection(COLLECTION_NAME).document(username_clean)
    doc = user_ref.get()
    
    if doc.exists:
        logger.warning(f"Intento de registro fallido: El usuario '{username_clean}' ya existe.")
        return False
    
    password_hash = hash_password(password)
    user_ref.set({
        "username": username_clean,
        "password_hash": password_hash,
        "fecha_creacion": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })
    logger.info(f"Usuario '{username_clean}' registrado exitosamente en Firestore.")
    return True

def autenticar_usuario(username: str, password: str) -> bool:
    """Autentica a un usuario verificando sus credenciales contra Firestore."""
    db = get_firestore_client()
    username_clean = username.strip().lower()
    
    user_ref = db.collection(COLLECTION_NAME).document(username_clean)
    doc = user_ref.get()
    
    if not doc.exists:
        logger.warning(f"Fallo de autenticación: El usuario '{username_clean}' no existe.")
        return False
    
    datos = doc.to_dict()
    password_hash = datos.get("password_hash")
    
    if not password_hash:
        return False
        
    return verify_password(password_hash, password)

def actualizar_contrasena(username: str, nueva_contrasena: str) -> bool:
    """Actualiza la contraseña de un usuario en Firestore."""
    db = get_firestore_client()
    username_clean = username.strip().lower()
    
    user_ref = db.collection(COLLECTION_NAME).document(username_clean)
    doc = user_ref.get()
    
    if not doc.exists:
        logger.warning(f"Intento de actualizar contraseña fallido: El usuario '{username_clean}' no existe.")
        return False
        
    password_hash = hash_password(nueva_contrasena)
    user_ref.update({
        "password_hash": password_hash,
        "fecha_actualizacion": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })
    logger.info(f"Contraseña del usuario '{username_clean}' actualizada exitosamente.")
    return True


def inicializar_base_de_datos() -> None:
    """
    Inicializa la base de datos de Firestore en la colección de usuarios.
    Crea un usuario administrador por defecto si la base de datos está vacía.
    """
    try:
        db = get_firestore_client()
        docs = db.collection(COLLECTION_NAME).limit(1).get()
        
        # Si no existe ningún usuario registrado, crear el admin por defecto
        if not list(docs):
            default_user = os.getenv("PORTAL_USERNAME", "admin")
            default_pass = os.getenv("PORTAL_PASSWORD", "admin")
            
            logger.info("Base de datos de usuarios vacía. Registrando administrador por defecto...")
            registrar_usuario(default_user, default_pass)
        else:
            logger.info("Base de datos de usuarios en Firestore ya cuenta con registros.")
    except Exception as e:
        logger.error(f"Error inicializando la base de datos: {e}")

def validar_sesion(session_token: str) -> bool:
    """Verifica si el token de sesión (nombre de usuario) existe en Firestore."""
    if not session_token:
        return False
    try:
        db = get_firestore_client()
        user_ref = db.collection(COLLECTION_NAME).document(session_token.strip().lower())
        return user_ref.get().exists
    except Exception as e:
        logger.error(f"Error al validar sesión en Firestore: {e}")
        return False

