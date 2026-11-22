# Guía de ejecución — Asistente RAG (Azure)

## Despliegue realizado

La demostración se construyó con Azure AI Foundry (`gpt-4.1-mini` y `text-embedding-3-small`), Azure AI Search, Azure Container Registry y Azure Container Apps. Se construyó la imagen con `az acr build` desde esta carpeta y se seleccionó en Container Apps desde el portal. La identidad administrada del entorno se usa para extraer la imagen de ACR; Foundry, Search y la API utilizan secretos de Container Apps referenciados en las variables `AZURE_OPENAI_API_KEY`, `AZURE_SEARCH_API_KEY` y `API_KEY`.

El endpoint base Foundry y los nombres reales de despliegue deben configurarse en `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_CHAT_DEPLOYMENT` y `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`. Para el endpoint Foundry `*.services.ai.azure.com` el cliente actual requiere API key. Configurar también `VECTOR_BACKEND=azure_search` y `AZURE_SEARCH_ENDPOINT`. No publicar secretos en documentación, imágenes o repositorio.

La entrada es HTTPS externa al puerto 8000, con `API_KEY` configurada antes de habilitarla. `/health` y `/docs` son públicos; para las rutas protegidas se envía `X-API-Key`. Se comprobó una consulta RAG autenticada en Azure y un rechazo sin clave. La evaluación completa registrada se realizó localmente; no se ha validado completa contra el despliegue Azure. SQLite es efímero y los logs de contenedor no tienen almacenamiento configurado.

## Guion de video (aprox. 5-6 minutos, máximo 7)

Este guion es una ayuda para explicar las decisiones con tus propias palabras. Prepara las peticiones de Postman antes de grabar y no muestres los valores de las variables, los headers resueltos, los secretos del portal ni el archivo `.env`. Usa solo documentos y preguntas de ejemplo.

### 0:00-0:35 — Problema y solución
**Mostrar:** el README y, después, el diagrama de `docs/arquitectura.md`.

**Decir:** "El caso es una aplicación legada de solicitudes internas donde la información se busca manualmente. Construí una API que consulta documentos, utiliza herramientas para las solicitudes y registra las interacciones. La demostración está desplegada en Azure."

### 0:35-1:35 — Arquitectura y decisiones
**Mostrar:** el diagrama. Señalar cada recurso siguiendo el recorrido, sin enseñar claves.

**Decir:** "FastAPI corre en Container Apps. Azure Container Registry guarda la imagen y una identidad administrada permite descargarla. Azure AI Foundry aporta el modelo de chat y el de embeddings. Azure AI Search guarda los fragmentos y vectores para buscarlos. El estado de solicitudes se simula con un JSON. Elegí un solo agente y herramientas deterministas para mantener la solución simple."

**Aclarar:** la API divide el documento, solicita los embeddings a Foundry y los envía a Search. Foundry no indexa directamente los documentos en este proyecto.

### 1:35-2:45 — Backend y RAG
**Mostrar:** en Postman, `POST /documents` o el documento ya listado en `GET /documents`. Luego `POST /ask` con: "¿Cuál es el tiempo de primera respuesta para una solicitud de prioridad alta?" Mostrar `answer`, `sources` y `search_documents`.

**Decir:** "La API recibe documentos, los divide en fragmentos y genera embeddings. Para una pregunta crea otro embedding, recupera contexto con búsqueda híbrida y el modelo redacta la respuesta usando los fragmentos. Aquí responde un día hábil y devuelve la fuente."

### 2:45-3:40 — Agente y herramientas
**Mostrar:** `POST /ask` con "¿Cuál es el estado de REQ-1002?" y después la pregunta de impacto alto, 600 usuarios y sin workaround. Señalar `get_request_status` y `classify_priority` en `tool_calls`.

**Decir:** "El modelo decide cuándo invocar herramientas. La consulta de estado usa datos simulados y la clasificación aplica reglas en código, no cálculos inventados por el modelo. Estas herramientas podrían sustituirse por integraciones corporativas."

### 3:40-4:30 — Seguridad y trazabilidad
**Mostrar:** `GET /history` con las interacciones de ejemplo; después, la respuesta 401 al desactivar el header de clave. No abrir el entorno de Postman ni revelar headers con la clave.

**Decir:** "La API valida entradas y exige una clave en los endpoints protegidos; las claves están guardadas como secretos de Container Apps. El historial registra pregunta, respuesta, fuentes, herramientas, estado y latencia. Los logs se emiten en JSON. En esta demo SQLite es temporal y los logs del contenedor no tienen retención configurada."

### 4:30-5:20 — Evaluación
**Mostrar:** `eval/results.md`, incluyendo la prueba sin información, la inyección directa y la prueba indirecta aislada.

**Decir:** "Ejecuté 13 pruebas automáticas con un modelo simulado y ocho preguntas de evaluación local con Foundry. En una prueba adicional aislada comprobé que se recuperó un documento con una instrucción maliciosa y no se obedeció. La respuesta devolvió la fuente estructurada, pero no la citó en el texto. Las métricas son simples y no garantizan resistencia general ni fundamentación semántica."

**Aclarar:** los ocho casos originales no se ejecutaron íntegramente contra Azure AI Search; en el despliegue Azure se probaron por separado RAG, herramientas, autenticación e historial.

### 5:20-6:00 — Producción y uso de AI
**Mostrar:** `docs/riesgos_produccion.md` y `docs/uso_ai.md`.

**Decir:** "Antes de producción propondría persistencia administrada para el historial, logs con retención y alertas, autenticación por usuario con roles y Key Vault o identidades administradas según el servicio. Usé GitHub Copilot como apoyo para construir y revisar; validé con pruebas y ejecución real, sin asumir que una respuesta generada era correcta."

**Cierre:** "La solución demuestra el flujo empresarial, y las limitaciones y mejoras quedan documentadas."

### Correspondencia con la evaluación
- **Arquitectura y simplicidad:** diagrama, recursos y justificación de un solo agente.
- **Backend:** carga, consulta, historial, validación y errores de FastAPI.
- **RAG:** fragmentación, embeddings, búsqueda y fuentes observadas.
- **Agente:** elección de herramientas y dos herramientas de negocio en funcionamiento.
- **Seguridad y operación:** secretos, HTTPS, 401, logs, trazabilidad y límites para producción.
- **Calidad y comunicación:** pruebas, casos de evaluación, inyección y uso responsable de AI.

**Importante:** el camino A y el script `deploy/deploy.ps1` siguientes son una propuesta anterior de Azure OpenAI tradicional. No se usaron ni validaron para este entorno de Foundry y no deben ejecutarse como receta del despliegue actual. Requieren adaptación y revisión de costos y permisos. El camino B sirve como guía local, con las aclaraciones anteriores sobre la clave de Foundry.

---

## Camino A — Directo a la nube (sin Python ni Docker locales)

La imagen se construye en Azure (`az acr build`), y las pruebas se corren desde **Azure Cloud Shell** (https://shell.azure.com, ya trae Python) o desde Swagger.

### 1. Crear los recursos (una vez)
Reemplaza los nombres (deben ser únicos globalmente). Las regiones/cuotas de modelos varían: si falla un modelo, prueba otra región (`eastus2`, `swedencentral`, `eastus`) u otra SKU (`Standard` / `GlobalStandard`).

```powershell
az login
$RG="rg-agente-rag"; $LOC="eastus2"; $AOAI="aoai-agente-<unico>"; $SEARCH="search-agente-<unico>"

az group create -n $RG -l $LOC

# Azure OpenAI + 2 modelos
az cognitiveservices account create -g $RG -n $AOAI -l $LOC --kind OpenAI --sku S0 --custom-domain $AOAI
az cognitiveservices account deployment create -g $RG -n $AOAI --deployment-name gpt-4o-mini `
  --model-name gpt-4o-mini --model-version "2024-07-18" --model-format OpenAI --sku-name GlobalStandard --sku-capacity 10
az cognitiveservices account deployment create -g $RG -n $AOAI --deployment-name text-embedding-3-small `
  --model-name text-embedding-3-small --model-version "1" --model-format OpenAI --sku-name Standard --sku-capacity 10

# Azure AI Search con RBAC habilitado (la app usa identidad administrada)
az search service create -g $RG -n $SEARCH --sku basic -l $LOC
az search service update -g $RG -n $SEARCH --auth-options aadOrApiKey --aad-auth-failure-mode http403
```
> Si no tienes permisos o cuota para crear estos recursos (o Azure OpenAI no está habilitado en tu suscripción), pídelos al administrador, o usa otro proveedor de modelo (la prueba lo permite).
> El tier `free` de Search puede servir para pocos documentos, pero verifica que soporte RBAC en tu suscripción; si no, usa `basic`.

### 2. Desplegar
Desde la carpeta `agente-rag`:
```powershell
cd agente-rag
.\deploy\deploy.ps1 -ResourceGroup $RG -OpenAIName $AOAI -SearchName $SEARCH
```
Al final imprime la **URL** y la **API_KEY**. Guárdalas. (El script asume que el recurso OpenAI está en el mismo resource group.)

Si ves un error de pull de imagen, asigna el rol `AcrPull` a la identidad de la app sobre el ACR y reinicia la revisión.

### 3. Probar
- **Swagger:** `https://<URL>/docs` → botón *Authorize* / header `X-API-Key`.
  1. `POST /documents`: sube los 4 archivos de `data/docs/`.
  2. `POST /ask`: prueba las preguntas de `eval/questions.json`.
  3. `GET /history`: muestra la trazabilidad (para el video).
- **Evaluación automática desde Cloud Shell** (tiene Python):
  ```bash
  # subir la carpeta agente-rag a Cloud Shell (botón Upload) o clonar el repo
  pip install httpx
  export API_KEY=<tu-api-key>
  python eval/run_eval.py --base-url https://<URL>
  ```
  Genera `eval/results.md` (evidencia de pruebas: precisión y groundedness).
- **Pruebas unitarias** (`pytest`) también en Cloud Shell: `pip install -r requirements.txt && pytest`.

### 4. Ver logs
```powershell
az containerapp logs show -g $RG -n agente-rag --follow
```

---

## Camino B — Local en otro PC

Requisitos: Python 3.11+ (https://www.python.org o `winget install Python.Python.3.12`) y recursos Azure OpenAI (y Search, o `VECTOR_BACKEND=local`).

```powershell
cd agente-rag
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env     # completar endpoints; llaves vacías = usa `az login`
pytest                      # no requiere Azure
uvicorn app.main:app --reload
# en otra terminal, con la API arriba:
python eval/run_eval.py --base-url http://localhost:8000
```
Variables importantes del `.env`: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_CHAT_DEPLOYMENT`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`, `AZURE_SEARCH_ENDPOINT`, `API_KEY`, `VECTOR_BACKEND`.

---

## Problemas frecuentes
| Síntoma | Causa probable |
|---|---|
| `DeploymentNotFound` | El nombre del despliegue no coincide con `AZURE_OPENAI_CHAT_DEPLOYMENT` / `..._EMBEDDING_DEPLOYMENT` |
| 403 al indexar/buscar | Faltan roles `Search Index Data Contributor` / `Search Service Contributor`, o Search no tiene `aadOrApiKey` |
| 401 en la API | Falta el header `X-API-Key` |
| 502 en `/ask` | Falla hacia Azure OpenAI (cuota, rol `Cognitive Services OpenAI User`, endpoint); ver logs |
| Historial vacío tras reiniciar | SQLite es efímero en el contenedor (limitación documentada) |

## Checklist de entregables
- [ ] Repositorio con el código
- [ ] README (ya incluido)
- [ ] Diagrama de arquitectura (`docs/arquitectura.md`)
- [ ] Decisiones técnicas (`docs/decisiones.md`)
- [ ] Evidencia de pruebas (`eval/results.md` + captura de `pytest`)
- [ ] Uso de AI documentado (`docs/uso_ai.md`, completar con tus correcciones reales)
- [ ] Riesgos y mejoras futuras (`docs/riesgos_produccion.md`)
- [ ] Video de máximo 7 min: subir doc → pregunta con fuentes → pregunta mixta (doc + estado) → "sin información" → prompt injection → `/history` → URL en Azure

> Nota: existe una prueba RAG de extremo a extremo en Azure; el conjunto completo de evaluación documentado se ejecutó localmente. El guion anterior de despliegue por CLI no se ha validado para el endpoint Foundry actual.
