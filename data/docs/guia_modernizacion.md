# Guía de modernización de aplicaciones legadas

## Estrategia recomendada
Se recomienda el patrón Strangler Fig: se reemplazan funcionalidades por servicios nuevos de forma gradual detrás de una fachada, sin reescribir toda la aplicación de una vez.

## Plataforma objetivo
Las aplicaciones modernizadas se empaquetan en contenedores y se despliegan en Azure Container Apps. Las bases de datos relacionales se migran a Azure SQL Database y los secretos se guardan en Azure Key Vault.

## Principios
- Autenticación con Microsoft Entra ID y identidades administradas, sin credenciales en el código.
- Observabilidad con Application Insights desde el primer despliegue.
- Pipelines de CI/CD con pruebas automáticas antes de cada despliegue.
