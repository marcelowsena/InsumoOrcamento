@echo off
echo Instalando dependencias...
pip install flask

echo.
echo Liberando porta no firewall...
netsh advfirewall firewall add rule name="Webhook Sienge" dir=in action=allow protocol=tcp localport=5000 >nul 2>&1

echo.
echo Iniciando servidor...
python servidor.py
pause
