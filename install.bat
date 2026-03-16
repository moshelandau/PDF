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

echo [1/3] Installing dependencies...
pip install PyPDF2>=3.0.0 PyMuPDF>=1.23.0 Pillow>=9.0.0 pytesseract>=0.3.10
if errorlevel 1 (
    echo.
    echo WARNING: Some packages failed. Trying one by one...
    pip install PyPDF2>=3.0.0
    pip install PyMuPDF>=1.23.0
    pip install Pillow>=9.0.0
    pip install pytesseract>=0.3.10
)
echo.

echo [2/3] Quick test...
python -c "from PyPDF2 import PdfReader; print('  PyPDF2 OK')" 2>nul || echo   PyPDF2 MISSING
python -c "import fitz; print('  PyMuPDF OK')" 2>nul || echo   PyMuPDF MISSING
python -c "from PIL import Image; print('  Pillow OK')" 2>nul || echo   Pillow MISSING
python -c "import pytesseract; print('  pytesseract OK')" 2>nul || echo   pytesseract MISSING (optional, for OCR)
echo.

echo [3/3] Creating desktop shortcut...
python create_shortcut.py
echo.

echo ==========================================
echo   Setup complete!
echo   Look for "PDF Editor" on your Desktop.
echo ==========================================
echo.
echo NOTE: For smart OCR auto-rotate, also install Tesseract:
echo   https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe
echo   (The app works fine without it)
echo.
pause
