# Portal Médico - Extracción Inteligente de Recetas Médicas ➕

Este proyecto consiste en un agente inteligente desarrollado con el **ADK (Agent Development Kit)** y potenciado por modelos **Gemini Enterprise** para automatizar la interpretación y extracción estructurada de recetas médicas (formatos PDF e imagen) para **Farmacias Quevedo**. La información procesada se guarda automáticamente en tablas analíticas de **Google Cloud BigQuery** y la gestión de acceso está protegida bajo un sistema seguro integrado con **Firebase Firestore**.

---

## 📂 Estructura del Proyecto

*   `main.py`: Consola interactiva principal que reúne todos los modos de ejecución local.
*   `web_app.py`: Servidor web principal (FastAPI) para el portal de recetas (Puerto 8000).
*   `demo_gerencia.py`: Servidor alternativo con esquemas avanzados de empaque y etiquetas orientado a demostraciones ejecutivas (Puerto 8085).
*   `actualizar_contrasena_cli.py`: Herramienta CLI para cambiar contraseñas de usuarios en Firestore de forma segura.
*   `cloud_function.py`: Código para pruebas de Cloud Function localmente con Functions Framework.
*   `requirements.txt`: Dependencias del entorno de desarrollo local.
*   `logica/`: Paquete de backend.
    *   `firebase_auth.py`: Rutinas de autenticación, hash seguro (scrypt) y Firestore.
    *   `agent.py`: Definición del agente de IA con ADK.
    *   `tools/extraction_tools.py`: Definición de la estructura JSON de la receta (`BaseModel`) y la herramienta de extracción de Gemini.
*   `templates/`: Vistas HTML interactivas con estilo moderno premium (glassmorphism).
*   `despliegue_Cloud_functions/`: Carpeta con dependencias y recursos listos para subir a producción como una Cloud Run Function.

---

## 🛠️ Requisitos Previos y Configuración de GCP

### 1. Autenticación en Google Cloud
Antes de ejecutar el agente o las bases de datos, debes autenticar tu terminal con un proyecto GCP válido (ej. `agentspace-demos-466121`):

```bash
# Iniciar sesión en gcloud
gcloud auth login

# Configurar el ID de tu proyecto
gcloud config set project agentspace-demos-466121

# Configurar credenciales predeterminadas de aplicación (ADC)
gcloud auth application-default login

# Establecer proyecto de cuota para cobro de API
gcloud auth application-default set-quota-project agentspace-demos-466121
gcloud config set billing/quota_project agentspace-demos-466121
```

### 2. Configurar Entorno Virtual de Python
Asegúrate de estar en el directorio raíz del proyecto y preparar el entorno de ejecución:

```bash
# Crear entorno virtual
python3 -m venv .venv

# Activar entorno virtual
source .venv/bin/activate

# Instalar dependencias requeridas
pip install -r requirements.txt
```

---

## 🚀 Modos de Ejecución Local

Para lanzar la consola de pruebas unificada, ejecuta:
```bash
python main.py
```
Se presentará un menú con las siguientes opciones:

### Opción 1: Interfaz Web Principal (FastAPI) - *Recomendado*
*   **Puerto**: `http://localhost:8000`
*   Inicia la aplicación web interactiva con la interfaz de login moderna. Permite arrastrar múltiples PDFs/imágenes de recetas y procesarlas concurrentemente hacia BigQuery.

### Opción 2: Simulación del Agente ADK en Consola
*   Corre una simulación de conversación con el Agente ADK utilizando `InMemoryRunner`.
*   *Uso*: `python main.py /ruta/a/tu/receta.pdf`

### Opción 3: Validación de la Herramienta en Consola
*   Ejecuta directamente la función de extracción estructurada usando la API de Gemini, sin el flujo conversacional del agente.

### Opción 4: Vaciar Tabla de BigQuery
*   Elimina la tabla de prescripciones (`recetamedicas.prescripciones`) para limpiar los datos de prueba rápidamente.

### Opción 5: Demo de Validación para Gerencia
*   **Puerto**: `http://localhost:8085`
*   Lanza una interfaz web alternativa que además calcula la cantidad de etiquetas de dispensación que requiere la farmacia y clasifica el tipo de empaque.

### Opción 6: Emulador de Cloud Run Function (Local)
*   **Puerto**: `http://localhost:8088`
*   Inicia un emulador de Cloud Function local con `functions-framework` para probar el despliegue serverless localmente.

---

## 🔒 Gestión de Usuarios (Firebase Firestore)

El portal web almacena de forma segura los usuarios y hashes de contraseñas (utilizando **scrypt** y salts criptográficos) en una colección de **Firebase Firestore**.

Al iniciar el servidor por primera vez, se creará automáticamente un usuario administrador predeterminado basado en las variables del archivo `.env` (generalmente `admin` / `admin`).

### Actualizar o Crear Contraseñas por Consola
Si deseas actualizar o cambiar la clave de un usuario existente, utiliza la herramienta CLI dedicada:
```bash
python actualizar_contrasena_cli.py <usuario> <nueva_contraseña>
```
*Ejemplo:*
```bash
python actualizar_contrasena_cli.py admin 8uj90,#
```

---

## ☁️ Despliegue en Producción (Serverless)

La carpeta `despliegue_Cloud_functions` contiene un paquete optimizado exclusivamente para Cloud Functions (2nd Gen).

### Despliegue con Un Solo Comando
1.  Ingresa a la carpeta de despliegue:
    ```bash
    cd despliegue_Cloud_functions
    ```
2.  Ejecuta el script automatizado de despliegue:
    ```bash
    ./desplegar.sh
    ```
3.  Confirma la acción presionando `s`. El script configurará automáticamente las variables de entorno de producción y generará tu URL HTTPS pública.
