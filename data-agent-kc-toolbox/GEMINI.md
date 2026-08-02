# Guía del Agente de Programación

## Documentación de Referencia

Si tienes habilidades (skills) de ADK disponibles, utilízalas en lugar de consultar las URLs a continuación.

De lo contrario, consulta estos recursos según sea necesario:
- **ADK Cheatsheet**:
https://raw.githubusercontent.com/GoogleCloudPlatform/agent-starter-pack/refs/heads/main/agent_starter_pack/resources/docs/adk-cheatsheet.md
— Definiciones de agentes, herramientas, callbacks, orquestación
- **Guía de Evaluación**:
https://raw.githubusercontent.com/GoogleCloudPlatform/agent-starter-pack/refs/heads/main/agent_starter_pack/resources/docs/adk-eval-guide.md
— Configuración de evaluación, métricas, aspectos a tener en cuenta
- **Guía de Despliegue**:
https://raw.githubusercontent.com/GoogleCloudPlatform/agent-starter-pack/refs/heads/main/agent_starter_pack/resources/docs/adk-deploy-guide.md
— Infraestructura, CI/CD, pruebas de agentes desplegados
- **Guía de Desarrollo**:
https://raw.githubusercontent.com/GoogleCloudPlatform/agent-starter-pack/refs/heads/main/docs/guide/development-guide.md
— Flujo de trabajo de desarrollo completo
- **Documentación de ADK**:
https://google.github.io/adk-docs/llms.txt

--------------------------------------------------------------------------------

## Fases de Desarrollo

### Fase 1: Comprender los Requisitos

Antes de escribir cualquier código, comprende los requisitos, restricciones y criterios de éxito del proyecto.

### Fase 2: Construir e Implementar

Implementa la lógica del agente en `app/`. Utiliza `make playground` para pruebas interactivas. Itera según los comentarios del usuario.

### Fase 3: El Bucle de Evaluación (Fase Principal de Iteración)

Comienza con 1 o 2 casos de evaluación, ejecuta `make eval` e itera. Se esperan más de 5 a 10 iteraciones. Consulta la **Guía de Evaluación** para conocer las métricas, el esquema de evalset, la configuración de LLM como juez y los problemas comunes.

### Fase 4: Pruebas Previas al Despliegue

Ejecuta `make test`. Corrige los problemas hasta que pasen todas las pruebas.

### Fase 5: Desplegar en Desarrollo (Dev)

**Requiere aprobación humana explícita.** Ejecuta `make deploy` únicamente después de que el usuario lo confirme. Consulta la **Guía de Despliegue** para más detalles.

### Fase 6: Despliegue en Producción

Pregunta al usuario: Opción A (un solo proyecto simple) u Opción B (canalización de CI/CD completa con `uvx agent-starter-pack setup-cicd`). Consulta la [documentación de despliegue](https://raw.githubusercontent.com/GoogleCloudPlatform/agent-starter-pack/refs/heads/main/docs/guide/deployment.md) para ver instrucciones paso a paso.

## Comandos de Desarrollo

Comando              | Propósito
-------------------- | ---------------------------------------------------
`make playground`    | Pruebas interactivas locales
`make test`          | Ejecutar pruebas unitarias y de integración
`make eval`          | Ejecutar evaluación con conjuntos de evaluación (evalsets)
`make eval-all`      | Ejecutar todos los conjuntos de evaluación (evalsets)
`make lint`          | Verificar la calidad del código
`make setup-dev-env` | Configurar infraestructura de desarrollo (Terraform)
`make deploy`        | Desplegar en desarrollo (dev)
`make deploy-mcp`    | Desplegar sidecar de MCP Toolbox
`make deploy-all`    | Configuración inicial: desplegar MCP Toolbox y luego el agente

--------------------------------------------------------------------------------

## Pautas Operativas para Agentes de Programación

-   **Preservación de código**: Modifica únicamente el código directamente solicitado por el usuario. Conserva todo el código circundante, los valores de configuración (por ejemplo, `model`), los comentarios y el formato.
-   **NUNCA cambies el modelo** a menos que se solicite explícitamente. Usa `gemini-3-flash-preview` o `gemini-3.1-pro-preview` para nuevos agentes.
-   **Errores 404 de modelo**: Corrige `GOOGLE_CLOUD_LOCATION` (por ejemplo, `global` en lugar de `us-central1`), no el nombre del modelo.
-   **Importaciones de herramientas de ADK**: Importa la instancia de la herramienta, no el módulo: `from google.adk.tools.load_web_page import load_web_page`
-   **Ejecutar Python con `uv`**: `uv run python script.py`. Ejecuta `make install` primero.
-   **Detenerse ante errores repetidos**: Si aparece el mismo error 3 o más veces, corrige la causa raíz en lugar de reintentar a ciegas.
-   **Conflictos de Terraform** (Error 409): Usa `terraform import` en lugar de reintentar la creación.
