@echo off
REM =============================================================================
REM Open Windows Firewall for RRG App
REM Run as Administrator
REM =============================================================================

echo Opening firewall ports...

REM Check if running as admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Please run this script as Administrator!
    pause
    exit /b 1
)

REM Add firewall rules
netsh advfirewall firewall add rule name="RRG Streamlit HTTP" dir=in action=allow protocol=tcp localport=8501
netsh advfirewall firewall add rule name="RRG Streamlit HTTP 80" dir=in action=allow protocol=tcp localport=80
netsh advfirewall firewall add rule name="RRG Streamlit HTTPS" dir=in action=allow protocol=tcp localport=443

echo.
echo Firewall rules added successfully!
echo Ports opened: 80, 443, 8501
echo.
pause
