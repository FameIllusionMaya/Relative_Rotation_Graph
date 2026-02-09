@echo off
REM =============================================================================
REM Update data from GitHub using Python
REM =============================================================================

cd /d %~dp0
call venv\Scripts\activate.bat
python fetch_from_github.py
