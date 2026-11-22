# Riesgos y consideraciones para producción

## Riesgos identificados y mitigaciones implementadas
| Riesgo | Mitigación actual |
|---|---|
| **Prompt injection directa** (pedir el prompt, claves) | Reglas en el prompt de sistema con prioridad máxima; sin secretos en el contexto del modelo; marca canario `CANARY-7F3A` verificada en la evaluación (Q7) |
| **Prompt injection indirecta** (instrucciones dentro de un documento) | Los fragmentos y salidas de tools se declaran datos no confiables; prueba con documento envenenado (Q8) |
| **Respuestas no fundamentadas** | Instrucción al modelo para usar `search_documents`, citar y reconocer falta de información; no es una garantía y el evaluador solo comprueba presencia de fuentes |
| **Argumentos maliciosos hacia tools** | Validación estricta en código (regex de ID, enums, rangos); errores devueltos al modelo, nunca ejecución dinámica |
| **Fuga de datos / abuso de la API** | API key (`X-API-Key`, comparación en tiempo constante), límites de tamaño y longitud, nombres de archivo saneados, mensajes de error sin detalles internos |
| **Secretos** | `.env` excluido de la imagen; Foundry, Search y API usan secretos de Container Apps. Identidad administrada para la descarga desde ACR |

## Pendiente para producción
1. **Autenticación real:** reemplazar la API key por Microsoft Entra ID (OAuth2) con roles; filtrar documentos por permisos del usuario (security trimming en Azure AI Search) para evitar fuga entre áreas.
2. **Secretos:** Azure Key Vault referenciado desde Container Apps; rotación de llaves.
3. **Persistencia del historial:** Cosmos DB o Azure SQL (SQLite se pierde al reiniciar el contenedor). Retención y anonimización de PII en logs.
4. **Observabilidad:** Application Insights con trazas por `request_id`, métricas de latencia, costo de tokens y tasa de "sin información"; alertas.
5. **Seguridad de contenido:** Azure AI Content Safety / Prompt Shields delante del modelo; filtrado de PII en entradas y salidas.
6. **Resiliencia y costo:** reintentos con backoff y timeouts hacia Azure OpenAI, rate limiting por usuario, cuotas de tokens, caché de embeddings.
7. **Red:** endpoints privados para OpenAI y Search, WAF/API Management delante de la API.
8. **Calidad continua:** pipeline CI/CD que ejecute `pytest` y `eval/run_eval.py` con umbral mínimo de precisión; conjunto de evaluación ampliado.
9. **Ingesta:** soportar PDF/DOCX, ingesta asíncrona para archivos grandes, versionado de documentos.
10. **Integración corporativa:** reemplazar el JSON mock por la API real de la aplicación legada detrás de las mismas firmas de tools; las tools que modifiquen datos requerirán confirmación humana.

En la demo los logs se transmiten sin almacenamiento configurado. Confirmar la revocación de las credenciales expuestas durante la configuración y actualizar todos los secretos dependientes antes de entregar.

## Mejoras futuras
Memoria de conversación, re-ranking semántico, respuestas en streaming, interfaz de chat, feedback del usuario (pulgar arriba/abajo) para mejorar la evaluación.
