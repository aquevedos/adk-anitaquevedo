# Dockerfile para desplegar la aplicación en Google Cloud Agent Engine
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema para procesamiento de PDF (PyMuPDF) y SSL
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias
COPY requirements.txt /app/

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente de la aplicación
COPY . /app/

# Exponer el puerto estándar para Cloud Run / Agent Engine
ENV PORT=8080
EXPOSE $PORT

# Iniciar el servidor ASGI de Agent Engine mediante uvicorn
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
