@echo off
echo ==========================================
echo   PDF Editor - Windows Setup
echo ==========================================
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

echo [1/3] Installing core dependencies...
pip install PyPDF2>=3.0.0 PyMuPDF>=1.23.0 Pillow>=9.0.0
echo.

echo [2/3] Installing OCR for smart auto-rotate...
pip install pytesseract>=0.3.10
echo.
echo NOTE: For OCR auto-rotate, you also need Tesseract installed:
echo   1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
echo   2. Run the installer
echo   3. The app will find it automatically
echo   (The app works fine without it - OCR auto-rotate just won't be available.)
echo.

echo [3/3] Creating desktop shortcut...
python create_shortcut.py
echo.

echo ==========================================
echo   Setup complete!
echo   Look for "PDF Editor" on your Desktop.
echo ==========================================
echo.
echo Features:
echo   - Page thumbnails with real previews
echo   - Click to select, Ctrl+Click multi-select
echo   - Double-click any page to expand full size
echo   - Size slider to adjust thumbnail size
echo   - OCR smart auto-rotate (if Tesseract installed)
echo.
pause
