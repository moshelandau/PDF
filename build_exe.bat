@echo off
echo ==========================================
echo   PDF Editor - Full Setup + Build .exe
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

echo Python found:
python --version
echo.

echo [1/4] Installing all dependencies...
pip install PyPDF2>=3.0.0 PyMuPDF>=1.23.0 Pillow>=9.0.0 pytesseract>=0.3.10 pyinstaller
if errorlevel 1 (
    echo Retrying with trusted hosts...
    pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org PyPDF2>=3.0.0 PyMuPDF>=1.23.0 Pillow>=9.0.0 pytesseract>=0.3.10 pyinstaller
)
echo.

echo [2/4] Verifying packages...
python -c "from PyPDF2 import PdfReader; print('  PyPDF2 ........... OK')" 2>nul || echo   PyPDF2 ........... FAILED
python -c "import fitz; print('  PyMuPDF .......... OK')" 2>nul || echo   PyMuPDF .......... FAILED
python -c "from PIL import Image; print('  Pillow ........... OK')" 2>nul || echo   Pillow ........... FAILED
python -c "import PyInstaller; print('  PyInstaller ...... OK')" 2>nul || echo   PyInstaller ...... FAILED
echo.

echo [3/4] Building PDF Editor.exe...
echo This may take a few minutes, please wait...
echo.
pyinstaller --onefile --windowed --name "PDF Editor" --clean --noconfirm pdf_editor.py
echo.

if exist "dist\PDF Editor.exe" (
    echo [4/4] Copying to Desktop...
    copy "dist\PDF Editor.exe" "%USERPROFILE%\Desktop\PDF Editor.exe" >nul 2>nul
    echo.
    echo ==========================================
    echo   ALL DONE!
    echo ==========================================
    echo.
    echo   "PDF Editor.exe" is on your Desktop.
    echo   Double-click it to run - no Python needed!
    echo.
    echo   You can copy this .exe to any Windows PC
    echo   and it will work without installing anything.
    echo ==========================================
) else (
    echo.
    echo BUILD FAILED. Check errors above.
)
echo.
pause
