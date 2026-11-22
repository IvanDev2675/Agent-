# Asistente RAG de solicitudes internas

Agente RAG empresarial con API FastAPI, modelos OpenAI en **Azure AI Foundry** y **Azure AI Search**, desplegado como demostración en **Azure Container Apps**.

- Responde con base en documentos cargados y devuelve las fuentes recuperadas; la cita textual depende de la respuesta del modelo.
- Usa herramientas: `search_documents` (RAG), `get_request_status`, `classify_priority`, `estimate_effort`.
- Registra cada interacción (pregunta, respuesta, fuentes, tools, latencia, estado) y la expone en `/history`.

Documentación: [arquitectura](docs/arquitectura.md) · [decisiones técnicas](docs/decisiones.md) · [riesgos y producción](docs/riesgos_produccion.md) · [uso de AI en el desarrollo](docs/uso_ai.md) · evidencia de pruebas en `eval/results.md` (se genera al ejecutar la evaluación)

## Requisitos
- Python 3.11+
- Azure AI Foundry con dos despliegues compatibles: chat con herramientas (prueba realizada con `gpt-4.1-mini`) y embeddings (`text-embedding-3-small`)
- Azure AI Search (tier Free sirve). Para desarrollo sin Search: `VECTOR_BACKEND=local`

## Ejecución local
```powershell
cd agente-rag
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # completar endpoint base, nombres de despliegue y credenciales
uvicorn app.main:app --reload
```
Para el endpoint Foundry `*.services.ai.azure.com`, la implementación actual requiere `AZURE_OPENAI_API_KEY`; `az login` no sustituye esa clave en este modo. Para Azure AI Search se puede usar su clave o una identidad con permisos. No subir `.env` al repositorio.

Swagger: http://localhost:8000/docs

## API
Si `API_KEY` está definida, enviar el header `X-API-Key`.

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/documents` | Sube un `.txt`/`.md` (multipart `file`, máx. 1 MB). Chunking + embeddings + indexado. Re-subir el mismo nombre lo reemplaza. |
| GET | `/documents` | Lista documentos indexados y número de chunks. |
| POST | `/ask` | `{"question": "...", "session_id": "opcional"}` → respuesta, fuentes, tools usadas, latencia. |
| GET | `/history?limit=50&session_id=` | Trazabilidad de interacciones. |
| GET | `/health` | Estado del servicio. |

Desde Swagger, introducir la clave en el campo `X-API-Key` de cada operación protegida. En `POST /documents` seleccionar un archivo de `data/docs/`; en `POST /ask` enviar, por ejemplo, `{"question": "¿Qué aprobación requiere un cambio de más de 5 días y cuál es el estado de REQ-1003?"}`.
Códigos de error: 400 (archivo inválido), 401 (API key), 413 (archivo grande), 422 (validación), 502 (falla del servicio de AI), 500 (inesperado, sin detalles internos).

## Pruebas
```powershell
pytest                                   # unitarias y de API, sin Azure (LLM simulado)
python eval/run_eval.py --base-url http://localhost:8000 --output eval/nuevos_resultados.md
python -m eval.run_eval --isolated-injection  # solo Q8, almacenamiento local temporal y Foundry real
```
La evaluación incluye 8 casos: RAG, herramientas, pregunta mixta, **sin información suficiente**, **prompt injection directa** e **indirecta**. La tasa de aprobación se basa en palabras, tools y presencia de fuentes; esta última no demuestra que cada afirmación esté sustentada. El script carga también un documento envenenado: usar un índice de prueba aislado y no ejecutarlo sobre un índice compartido. La opción `--isolated-injection` realiza solo Q8, usa un almacenamiento temporal sin modificar Azure AI Search y sí consume Foundry. Si la API del modo normal exige clave, el evaluador necesita `API_KEY` en el entorno del proceso; no carga automáticamente `.env`. La opción `--output` evita sobrescribir la evidencia y las observaciones existentes.

**Evidencia ejecutada:** 13 pruebas automáticas aprobadas con un modelo simulado; ocho casos ejecutados localmente con Foundry bajo los criterios originales; y una prueba posterior de inyección indirecta con almacenamiento aislado. También se comprobaron por separado RAG, herramientas, autenticación e historial en Azure. El resultado histórico de Q8 no verificaba la recuperación del documento; la prueba aislada posterior sí lo hizo. Detalles, respuestas y observaciones: [resultados de evaluación](eval/results.md).

## Despliegue en Azure
La demostración usa Azure Container Registry para la imagen, Container Apps para FastAPI, Foundry para chat y embeddings y Azure AI Search para el índice. La app obtiene la imagen de ACR mediante identidad administrada; las claves de Foundry, Search y la API son secretos de Container Apps referenciados por variables de entorno. La entrada externa usa HTTPS y `X-API-Key` en los endpoints protegidos; `/health` y `/docs` son públicos.

Se construyó la imagen con `az acr build` y se creó la aplicación desde el portal. Se verificaron una consulta RAG autenticada y el rechazo sin clave. La guía de pasos está en [GUIA_EJECUCION.md](GUIA_EJECUCION.md). El script `deploy/deploy.ps1` corresponde a una propuesta anterior para Azure OpenAI tradicional y **no se validó para el despliegue de Foundry realizado**; no ejecutarlo como receta de este entorno.

El historial usa SQLite en el filesystem efímero del contenedor y puede perderse al reiniciar o cambiar de réplica. Los logs se transmiten sin almacenamiento configurado. Para producción ver [riesgos_produccion.md](docs/riesgos_produccion.md).

## Estructura
```
app/        main.py (API) · agent.py · tools.py · rag.py · vectorstore.py · llm.py · history.py · chunking.py
data/       requests.json (mock) · docs/ (documentos de ejemplo)
eval/       questions.json · run_eval.py · documento_inyectado.md
tests/      pruebas unitarias y de API
deploy/     deploy.ps1 (Azure Container Apps)
```
