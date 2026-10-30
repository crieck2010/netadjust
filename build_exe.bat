@echo off
REM Build NetAdjust.exe on Windows: creates a venv, installs deps, runs PyInstaller.
setlocal
if not exist .venv (
    py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -e .[dev]
python build.py
echo.
echo Built: dist\NetAdjust.exe
endlocal
