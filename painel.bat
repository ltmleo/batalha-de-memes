@echo off
rem Abre o painel de duelos (gerar videos, publicar e apurar a rodada).
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
  echo Crie o ambiente antes: veja "Backend" no README.md
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" -m app.cli painel
