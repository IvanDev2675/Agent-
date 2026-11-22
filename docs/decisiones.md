# Decisiones técnicas

| Decisión | Elección | Por qué | Alternativa descartada |
|---|---|---|---|
| Plataforma | Azure | Despliegue natural de punto a punto y equipo con experiencia | AWS Bedrock (equivalente, sin ventaja aquí) |
| LLM | Azure AI Foundry `gpt-4.1-mini` | Modelo de chat probado con function calling | Otros modelos compatibles, sujetos a cuota y precio |
| Embeddings | `text-embedding-3-small` (1536 dim) | Buena relación costo/calidad | `-large`: más costo e índice más pesado |
| Vector store | Azure AI Search, búsqueda **híbrida** | Administrado, persistente, tier gratuito; híbrido mejora recall con códigos y términos exactos | Chroma/FAISS: más simples pero sin persistencia gestionada en la nube |
| Agente | Un solo agente con function calling nativo, sin framework | Menos dependencias, comportamiento depurable y fácil de explicar | LangChain/multiagente: complejidad sin beneficio claro |
| RAG como tool | `search_documents` es una herramienta más del agente | Permite preguntas mixtas (documento + estado de solicitud) en una sola llamada | Pipeline RAG fijo previo a cada pregunta |
| Tools | Lógica determinista en código (prioridad, esfuerzo, estado) | Resultados auditables y repetibles; el LLM no "calcula" | Dejar que el LLM calcule |
| Historial | SQLite | Cero infraestructura para el alcance de la prueba | Cosmos DB / Azure SQL (ver producción) |
| Autenticación a Azure | Identidad administrada para ACR; claves de Foundry y Search como secretos de Container Apps | No incluir claves en la imagen; mantener simple la demo | Identidad administrada para todos los servicios y Key Vault, pendientes de validar |
| Despliegue | Container Apps + ACR | Serverless para contenedores, escala simple, ingress HTTPS incluido | AKS (excesivo), Functions (menos natural para FastAPI) |
| Chunking | Por párrafos, 800 caracteres, solape 120 | Mantiene unidades semánticas de los documentos de política | Tamaño fijo ciego |

## Alcance excluido a propósito
Sin interfaz gráfica, sin memoria de conversación entre turnos (cada pregunta es independiente; `session_id` solo agrupa trazabilidad), solo `.txt`/`.md` en la carga.

La API y el historial se probaron localmente. En Azure se verificaron salud, autenticación y una consulta RAG sobre Search; la evaluación de ocho casos registrada se ejecutó localmente con Foundry y vector store local. Los logs de Container Apps no tienen destino persistente y SQLite puede perderse al reiniciar.
