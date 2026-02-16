@echo off
set "PEON_ROOT=%~dp0.."
python "%PEON_ROOT%\hooks\scripts\peon.py" %*
