# Despliegue en Azure Container Apps
# Requisitos: Azure CLI logueado (az login), recursos Azure OpenAI (con los 2 modelos desplegados) y Azure AI Search ya creados.
# Uso: .\deploy\deploy.ps1 -ResourceGroup rg-agente-rag -OpenAIName <aoai> -SearchName <search>
param(
    [Parameter(Mandatory)] [string] $ResourceGroup,
    [Parameter(Mandatory)] [string] $OpenAIName,
    [Parameter(Mandatory)] [string] $SearchName,
    [string] $Location = "eastus2",
    [string] $AcrName = "acragenterag$((Get-Random -Maximum 99999))",
    [string] $AppName = "agente-rag",
    [string] $EnvName = "cae-agente-rag"
)
$ErrorActionPreference = "Stop"

az extension add --name containerapp --upgrade | Out-Null
az group create -n $ResourceGroup -l $Location | Out-Null

# 1. Imagen en ACR (build remoto, no requiere Docker local)
az acr create -g $ResourceGroup -n $AcrName --sku Basic | Out-Null
az acr build -r $AcrName -t "${AppName}:v1" .

# 2. Entorno y app con identidad administrada
az containerapp env create -g $ResourceGroup -n $EnvName -l $Location | Out-Null

$apiKey = [guid]::NewGuid().ToString("N")
$aoaiEndpoint = az cognitiveservices account show -g $ResourceGroup -n $OpenAIName --query properties.endpoint -o tsv
$searchEndpoint = "https://$SearchName.search.windows.net"

az containerapp create -g $ResourceGroup -n $AppName --environment $EnvName `
    --image "$AcrName.azurecr.io/${AppName}:v1" --registry-server "$AcrName.azurecr.io" --registry-identity system `
    --system-assigned --target-port 8000 --ingress external --min-replicas 1 --max-replicas 2 `
    --secrets "service-api-key=$apiKey" `
    --env-vars "AZURE_OPENAI_ENDPOINT=$aoaiEndpoint" "AZURE_SEARCH_ENDPOINT=$searchEndpoint" `
               "API_KEY=secretref:service-api-key" "VECTOR_BACKEND=azure_search" | Out-Null

# 3. Permisos de la identidad administrada (sin llaves en la app)
$principal = az containerapp show -g $ResourceGroup -n $AppName --query identity.principalId -o tsv
$aoaiId = az cognitiveservices account show -g $ResourceGroup -n $OpenAIName --query id -o tsv
$searchId = az search service show -g $ResourceGroup -n $SearchName --query id -o tsv
az role assignment create --assignee $principal --role "Cognitive Services OpenAI User" --scope $aoaiId | Out-Null
az role assignment create --assignee $principal --role "Search Index Data Contributor" --scope $searchId | Out-Null
az role assignment create --assignee $principal --role "Search Service Contributor" --scope $searchId | Out-Null

$fqdn = az containerapp show -g $ResourceGroup -n $AppName --query properties.configuration.ingress.fqdn -o tsv
Write-Host "URL:     https://$fqdn/docs"
Write-Host "API_KEY: $apiKey   (guárdala; header X-API-Key)"
Write-Host "Nota: Azure AI Search debe permitir autenticación por RBAC (aadOrApiKey)."
