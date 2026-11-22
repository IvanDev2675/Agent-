# Runbook de gestión de incidentes

## Severidades
- SEV1: servicio caído o pérdida de datos. Se notifica al ingeniero de guardia en un máximo de 15 minutos y se abre una sala de crisis.
- SEV2: degradación importante con workaround. Se atiende en la siguiente hora.
- SEV3: afectación menor. Se gestiona como solicitud normal.

## Escalamiento
Si un SEV1 no tiene mitigación en 60 minutos se escala a la Gerencia de Tecnología.

## Postmortem
Todo SEV1 y SEV2 requiere un postmortem sin culpables publicado en un máximo de 5 días hábiles, con acciones correctivas y responsables.
