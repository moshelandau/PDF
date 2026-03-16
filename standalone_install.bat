@echo off
echo ==========================================
echo   PDF Editor - Standalone Setup
echo ==========================================
echo.
echo This will set up PDF Editor on this PC.
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ============================================
    echo   Python is NOT installed!
    echo ============================================
    echo.
    echo   1. Go to: https://www.python.org/downloads/
    echo   2. Download and run the installer
    echo   3. IMPORTANT: Check "Add Python to PATH" at the bottom!
    echo   4. After installing, run this script again.
    echo.
    pause
    exit /b 1
)

echo Python found:
python --version
echo.

echo [1/4] Installing required packages...
pip install PyPDF2>=3.0.0 PyMuPDF>=1.23.0 Pillow>=9.0.0 pytesseract>=0.3.10
echo.

echo [2/4] Verifying packages...
python -c "from PyPDF2 import PdfReader; print('  PyPDF2 ........... OK')" 2>nul || echo   PyPDF2 ........... FAILED
python -c "import fitz; print('  PyMuPDF .......... OK')" 2>nul || echo   PyMuPDF .......... FAILED
python -c "from PIL import Image; print('  Pillow ........... OK')" 2>nul || echo   Pillow ........... FAILED
python -c "import pytesseract; print('  pytesseract ...... OK')" 2>nul || echo   pytesseract ...... OK (optional)
echo.

echo [3/4] Creating desktop shortcut...
python create_shortcut.py
echo.

echo [4/4] Done!
echo.
echo ==========================================
echo   PDF Editor is ready!
echo   Double-click "PDF Editor" on your Desktop.
echo ==========================================
echo.
echo OPTIONAL: For smart OCR auto-rotate, install Tesseract:
echo   https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe
echo.
pause
