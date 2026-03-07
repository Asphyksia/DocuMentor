@echo off
:: DocuMentor Dashboard Launcher (Windows)
:: Finds the venv automatically and launches Streamlit

set "VENV=%USERPROFILE%\.openclaw\workspace\.venv"
set "VENV2=%~dp0.venv"
set "DASHBOARD=%~dp0dashboard\app.py"

if exist "%VENV%\Scripts\streamlit.exe" (
    "%VENV%\Scripts\streamlit.exe" run "%DASHBOARD%"
) else if exist "%VENV2%\Scripts\streamlit.exe" (
    "%VENV2%\Scripts\streamlit.exe" run "%DASHBOARD%"
) else (
    echo.
    echo  [!] Streamlit no encontrado.
    echo  Habla con el bot primero para que instale las dependencias.
    echo  O ejecuta manualmente: pip install streamlit
    echo.
    pause
)
