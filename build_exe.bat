@echo off
echo ==========================================
echo   PDF Editor - Build .exe
echo ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not installed. Get it from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python found:
python --version
echo.

echo [1/5] Installing dependencies...
pip install PyPDF2>=3.0.0 PyMuPDF>=1.23.0 Pillow>=9.0.0 pytesseract>=0.3.10 pyinstaller
if errorlevel 1 (
    pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org PyPDF2>=3.0.0 PyMuPDF>=1.23.0 Pillow>=9.0.0 pytesseract>=0.3.10 pyinstaller
)
echo.

echo [2/5] Verifying...
python -c "from PyPDF2 import PdfReader; print('  PyPDF2 ........... OK')" 2>nul || echo   PyPDF2 ........... FAILED
python -c "import fitz; print('  PyMuPDF .......... OK')" 2>nul || echo   PyMuPDF .......... FAILED
python -c "from PIL import Image; print('  Pillow ........... OK')" 2>nul || echo   Pillow ........... FAILED
python -c "import PyInstaller; print('  PyInstaller ...... OK')" 2>nul || echo   PyInstaller ...... FAILED
echo.

echo [3/4] Building PDF Editor...
pyinstaller --onefile --windowed --name "PDFEditor" --clean --noconfirm pdf_editor.py
echo.

echo [4/4] Copying to Desktop...
if exist "dist\PDFEditor.exe" (
    copy "dist\PDFEditor.exe" "%USERPROFILE%\Desktop\PDFEditor.exe" >nul 2>nul
    echo   PDFEditor.exe .......... OK
) else (
    echo   PDFEditor.exe .......... FAILED
)

echo.
echo ==========================================
echo   DONE! Check your Desktop for:
echo.
echo   PDFEditor.exe
echo     (thumbnails, page preview, OCR, dark/light theme)
echo.
echo   Copy the .exe to any PC - no install needed!
echo ==========================================
echo.
pause
