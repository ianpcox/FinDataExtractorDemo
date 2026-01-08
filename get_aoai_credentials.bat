@echo off
echo ============================================================
echo FETCH AZURE OPENAI CREDENTIALS
echo ============================================================
echo.

echo Getting Azure OpenAI resource details...
echo.

REM Get the resource group and resource name
set RESOURCE_NAME=aoai-dio-findataextract-east

echo Resource: %RESOURCE_NAME%
echo.

echo Fetching endpoint...
az cognitiveservices account show --name %RESOURCE_NAME% --resource-group rg-dio-findataextractor-cace --query "properties.endpoint" -o tsv > temp_endpoint.txt
set /p AOAI_ENDPOINT=<temp_endpoint.txt
echo Endpoint: %AOAI_ENDPOINT%

echo.
echo Fetching API key...
az cognitiveservices account keys list --name %RESOURCE_NAME% --resource-group rg-dio-findataextractor-cace --query "key1" -o tsv > temp_key.txt
set /p AOAI_KEY=<temp_key.txt
echo Key: %AOAI_KEY:~0,4%...%AOAI_KEY:~-4%

echo.
echo ============================================================
echo UPDATE YOUR .ENV FILE WITH THESE VALUES:
echo ============================================================
echo AOAI_ENDPOINT=%AOAI_ENDPOINT%
echo AOAI_API_KEY=%AOAI_KEY%
echo AOAI_DEPLOYMENT_NAME=gpt-4.1
echo ============================================================

REM Cleanup
del temp_endpoint.txt
del temp_key.txt

pause
