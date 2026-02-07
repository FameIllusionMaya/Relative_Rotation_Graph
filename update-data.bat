@echo off
REM =============================================================================
REM Update data from GitHub
REM Add to Windows Task Scheduler for automatic updates
REM =============================================================================

cd /d %~dp0
echo %date% %time%: Updating data from GitHub...

git fetch origin master
git checkout origin/master -- data/

echo %date% %time%: Data updated successfully!
