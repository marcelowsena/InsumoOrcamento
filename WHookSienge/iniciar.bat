@echo off
echo Instalando dependencias...
pip install flask waitress python-dotenv

echo.
if not exist .env (
    echo ERRO: crie o arquivo .env com WEBHOOK_TOKEN antes de iniciar. Veja .env.example
    pause
    exit /b 1
)

REM A regra de firewall NAO e mais criada automaticamente.
REM A exposicao externa deve ser feita pela TI, de preferencia via proxy reverso com HTTPS.

echo.
echo Iniciando servidor...
python servidor.py
pause
