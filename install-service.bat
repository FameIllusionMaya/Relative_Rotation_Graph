@echo off
REM =============================================================================
REM Install RRG App as Windows Service using NSSM
REM Run as Administrator
REM =============================================================================

echo ==========================================
echo   Installing RRG as Windows Service
echo ==========================================

REM Get current directory
set "APP_DIR=%~dp0"
set "VENV_PYTHON=%APP_DIR%venv\Scripts\python.exe"

REM Create logs directory
if not exist "%APP_DIR%logs" mkdir "%APP_DIR%logs"

REM Download NSSM if not exists
if not exist "%APP_DIR%nssm.exe" (
    echo Downloading NSSM...
    powershell -Command "Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile '%APP_DIR%nssm.zip'"
    powershell -Command "Expand-Archive -Path '%APP_DIR%nssm.zip' -DestinationPath '%APP_DIR%nssm-temp' -Force"
    copy "%APP_DIR%nssm-temp\nssm-2.24\win64\nssm.exe" "%APP_DIR%nssm.exe"
    rmdir /s /q "%APP_DIR%nssm-temp"
    del "%APP_DIR%nssm.zip"
    echo NSSM downloaded.
)

REM Stop and remove existing service if exists
echo Removing old service if exists...
"%APP_DIR%nssm.exe" stop RRG-Streamlit 2>nul
"%APP_DIR%nssm.exe" remove RRG-Streamlit confirm 2>nul

REM Install the service
echo Installing service...
"%APP_DIR%nssm.exe" install RRG-Streamlit "%VENV_PYTHON%"
"%APP_DIR%nssm.exe" set RRG-Streamlit AppParameters "-m streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true"
"%APP_DIR%nssm.exe" set RRG-Streamlit AppDirectory "%APP_DIR%"
"%APP_DIR%nssm.exe" set RRG-Streamlit DisplayName "RRG Streamlit App"
"%APP_DIR%nssm.exe" set RRG-Streamlit Description "Relative Rotation Graph - SET Sectors"
"%APP_DIR%nssm.exe" set RRG-Streamlit Start SERVICE_AUTO_START
"%APP_DIR%nssm.exe" set RRG-Streamlit AppStdout "%APP_DIR%logs\service.log"
"%APP_DIR%nssm.exe" set RRG-Streamlit AppStderr "%APP_DIR%logs\error.log"

REM Start the service
echo Starting service...
"%APP_DIR%nssm.exe" start RRG-Streamlit

echo.
echo ==========================================
echo   Service Installed Successfully!
echo ==========================================
echo.
echo Service Name: RRG-Streamlit
echo.
echo Commands:
echo   nssm status RRG-Streamlit   - Check status
echo   nssm stop RRG-Streamlit     - Stop service
echo   nssm start RRG-Streamlit    - Start service
echo   nssm restart RRG-Streamlit  - Restart service
echo.
echo Logs folder: %APP_DIR%logs\
echo.
pause
