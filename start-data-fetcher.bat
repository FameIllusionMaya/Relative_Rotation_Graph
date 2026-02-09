@echo off
REM =============================================================================
REM Start Auto Data Fetcher - Runs continuously and fetches data on schedule
REM =============================================================================

cd /d %~dp0
call venv\Scripts\activate.bat
python auto_fetch_data.py --schedule
