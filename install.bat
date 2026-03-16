@echo off
echo ================================
echo   PDF Editor - Windows Setup
echo ================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Download it from: https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during install!
    pause
    exit /b 1
)

echo [1/2] Installing dependencies...
pip install PyPDF2>=3.0.0 Pillow>=9.0.0
echo.

echo [2/2] Creating desktop shortcut...
python create_shortcut.py
echo.

echo ================================
echo   Setup complete!
echo   Look for "PDF Editor" on your Desktop.
echo ================================
pause
