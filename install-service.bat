@echo off
REM =============================================================================
REM Install RRG App as Windows Service using NSSM
REM Run as Administrator
REM =============================================================================

echo ==========================================
echo   Installing RRG as Windows Service
echo ==========================================

REM Check if running as admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Please run this script as Administrator!
    pause
    exit /b 1
)

REM Download NSSM if not exists
if not exist "nssm.exe" (
    echo Downloading NSSM (Non-Sucking Service Manager)...
    powershell -Command "Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile 'nssm.zip'"
    powershell -Command "Expand-Archive -Path 'nssm.zip' -DestinationPath 'nssm-temp' -Force"
    copy "nssm-temp\nssm-2.24\win64\nssm.exe" "nssm.exe"
    rmdir /s /q nssm-temp
    del nssm.zip
)

REM Get current directory
set APP_DIR=%~dp0
set VENV_PYTHON=%APP_DIR%venv\Scripts\python.exe

REM Remove existing service if exists
nssm stop RRG-Streamlit >nul 2>&1
nssm remove RRG-Streamlit confirm >nul 2>&1

REM Install the service
echo Installing service...
nssm install RRG-Streamlit "%VENV_PYTHON%"
nssm set RRG-Streamlit AppParameters "-m streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true"
nssm set RRG-Streamlit AppDirectory "%APP_DIR%"
nssm set RRG-Streamlit DisplayName "RRG Streamlit App"
nssm set RRG-Streamlit Description "Relative Rotation Graph - SET Sectors"
nssm set RRG-Streamlit Start SERVICE_AUTO_START
nssm set RRG-Streamlit AppStdout "%APP_DIR%logs\service.log"
nssm set RRG-Streamlit AppStderr "%APP_DIR%logs\error.log"

REM Create logs directory
if not exist "logs" mkdir logs

REM Start the service
echo Starting service...
nssm start RRG-Streamlit

echo.
echo ==========================================
echo   Service Installed Successfully!
echo ==========================================
echo.
echo Service Name: RRG-Streamlit
echo Status: Running
echo.
echo Commands:
echo   nssm status RRG-Streamlit   - Check status
echo   nssm stop RRG-Streamlit     - Stop service
echo   nssm start RRG-Streamlit    - Start service
echo   nssm restart RRG-Streamlit  - Restart service
echo   nssm remove RRG-Streamlit   - Uninstall service
echo.
echo Logs: %APP_DIR%logs\
echo.
pause
