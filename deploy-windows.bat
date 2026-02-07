@echo off
REM =============================================================================
REM RRG Streamlit App - Windows VPS Deployment Script
REM =============================================================================
REM Run as Administrator
REM =============================================================================

echo ==========================================
echo   RRG Streamlit App - Windows Deployment
echo ==========================================

REM Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found! Please install Python 3.11 from python.org
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate and install dependencies
echo Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt

REM Create startup script
echo Creating startup script...
echo @echo off > start-rrg.bat
echo call venv\Scripts\activate.bat >> start-rrg.bat
echo streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true >> start-rrg.bat

echo.
echo ==========================================
echo   Deployment Complete!
echo ==========================================
echo.
echo To start the app manually:
echo   start-rrg.bat
echo.
echo To run as Windows Service, run:
echo   install-service.bat (as Administrator)
echo.
echo Your app will be available at:
echo   http://YOUR_VPS_IP:8501
echo.
echo IMPORTANT: Open port 8501 in Windows Firewall!
echo.
pause
