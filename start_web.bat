@echo off
setlocal
cd /d "%~dp0"

rem ---- Locate Python (prefer project venv .venv) ----
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

rem ---- Dependency self-check ----
"%PY%" -c "import fastapi, uvicorn, animaflux" >nul 2>nul
if errorlevel 1 (
    echo.
    echo  [ERROR] Missing dependencies: fastapi / uvicorn / animaflux.
    echo  Run: pip install -e ".[web]"
    echo.
    pause
    exit /b 1
)

rem ---- Defaults (overridable via environment) ----
if not defined ANIMAFLUX_HOST set "ANIMAFLUX_HOST=127.0.0.1"
if not defined ANIMAFLUX_PORT set "ANIMAFLUX_PORT=8000"
if not defined ANIMAFLUX_DB   set "ANIMAFLUX_DB=animaflux.db"
if not defined PYTHONPATH     set "PYTHONPATH=%~dp0src"

set "URL=http://%ANIMAFLUX_HOST%:%ANIMAFLUX_PORT%/"

echo.
echo  ==================================================
echo    AnimaFlux - Local Web Console
echo  --------------------------------------------------
echo    Web UI:     %URL%
echo    API docs:   %URL%docs
echo    Database:   %ANIMAFLUX_DB%
echo    Stop:       close this window or press Ctrl+C
echo  ==================================================
echo.

rem ---- Open the default browser after a short delay ----
start "" /min cmd /c "ping -n 5 127.0.0.1 >nul & start %URL%"

rem ---- Run the server in the foreground ----
"%PY%" -m uvicorn animaflux.web.asgi:app --host %ANIMAFLUX_HOST% --port %ANIMAFLUX_PORT%

echo.
echo  Server stopped.
pause
endlocal
