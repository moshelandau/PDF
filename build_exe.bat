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

echo [3/5] Building PDF Editor (Full)...
pyinstaller --onefile --windowed --name "PDF Editor" --clean --noconfirm pdf_editor.py
echo.

echo [4/5] Building PDF Editor Lite...
pyinstaller --onefile --windowed --name "PDF Editor Lite" --clean --noconfirm pdf_editor_lite.py
echo.

echo [5/5] Copying to Desktop...
if exist "dist\PDF Editor.exe" (
    copy "dist\PDF Editor.exe" "%USERPROFILE%\Desktop\PDF Editor.exe" >nul 2>nul
    echo   PDF Editor.exe .......... OK
) else (
    echo   PDF Editor.exe .......... FAILED
)
if exist "dist\PDF Editor Lite.exe" (
    copy "dist\PDF Editor Lite.exe" "%USERPROFILE%\Desktop\PDF Editor Lite.exe" >nul 2>nul
    echo   PDF Editor Lite.exe ..... OK
) else (
    echo   PDF Editor Lite.exe ..... FAILED
)

echo.
echo ==========================================
echo   DONE! Check your Desktop for:
echo.
echo   PDF Editor.exe      - Full version
echo     (thumbnails, page preview, OCR, dark theme)
echo.
echo   PDF Editor Lite.exe - Lite version
echo     (fast, lightweight, list view, minimal)
echo.
echo   Copy either .exe to any PC - no install needed!
echo ==========================================
echo.
pause
