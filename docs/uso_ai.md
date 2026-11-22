# Uso de AI en el desarrollo

Se utilizó GitHub Copilot en VS Code como asistente para construir, revisar y explicar la solución. El candidato conserva la responsabilidad de las decisiones, la revisión y la entrega.

## Tareas apoyadas con AI
- Propuesta inicial de arquitectura, código FastAPI, RAG, herramientas, pruebas y documentación.
- Adaptación del cliente para el endpoint OpenAI v1 de Azure AI Foundry y una prueba unitaria de esa configuración.
- Apoyo durante las pruebas locales y el despliegue en Azure, con explicación de los recursos y sus costos.

## Validaciones realizadas
- Se ejecutaron 13 pruebas automáticas de API y lógica con un modelo simulado, sin llamar a Azure.
- Se ejecutaron ocho casos de evaluación contra la API local con Foundry y almacenamiento vectorial local; el reporte se encuentra en `eval/results.md`.
- Se probó manualmente la carga, búsqueda con fuentes, herramientas y trazabilidad; también se comprobó una consulta RAG en Container Apps con Azure AI Search.
- Se comprobó que la API desplegada rechazara una petición sin clave y aceptara una petición autenticada; se probaron en Azure las herramientas de estado y prioridad y la consulta del historial.

## Riesgos y revisión
- La salida de AI puede contener errores de SDK, configuración, seguridad o afirmaciones no verificadas. Se revisaron las pruebas y resultados reales en lugar de considerar correcto el código solo por haber sido generado.
- Durante la configuración, un archivo local con credenciales se adjuntó al contexto del chat. Se solicitó la rotación de las claves y se continuó sin mostrar sus valores; antes de entregar se debe confirmar que las claves expuestas quedaron invalidadas y que los secretos activos fueron actualizados.
- Se detectó que el evaluador original podía aprobar la inyección indirecta sin recuperar el documento. Se añadió una prueba que reproduce ese falso positivo y se ejecutó una prueba real aislada con Foundry; la evidencia y la ausencia de cita textual constan en el reporte.
- Las pruebas de prompt injection y la comprobación de fuentes cubren casos concretos, no garantizan protección completa ni fundamentación semántica.
- La propuesta de identidad administrada para servicios de AI debe validarse antes de presentarla como implementada: el despliegue actual usa secretos de Container Apps para Foundry y Search.
