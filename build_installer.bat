@echo off
echo ==========================================
echo   PDF Editor - Build Installer
echo ==========================================
echo.
echo This builds a proper Windows installer (.exe)
echo that installs like a regular app.
echo.
echo Requirements:
echo   1. Python (with pip)
echo   2. Inno Setup (free): https://jrsoftware.org/isdl.php
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check Inno Setup
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if "%ISCC%"=="" (
    echo ============================================
    echo   Inno Setup 6 is NOT installed!
    echo ============================================
    echo.
    echo   1. Download free from: https://jrsoftware.org/isdl.php
    echo   2. Install it (default settings are fine)
    echo   3. Run this script again
    echo.
    pause
    exit /b 1
)

echo Python found:
python --version
echo Inno Setup found: %ISCC%
echo.

:: Step 1: Install dependencies
echo [1/4] Installing Python packages...
pip install PyPDF2>=3.0.0 PyMuPDF>=1.23.0 Pillow>=9.0.0 pytesseract>=0.3.10 pyinstaller
echo.

:: Step 2: Build exe files
echo [2/4] Building PDF Editor.exe...
pyinstaller --onefile --windowed --name "PDFEditor" --clean --noconfirm pdf_editor.py
echo.

echo [3/4] Building PDF Editor Lite.exe...
pyinstaller --onefile --windowed --name "PDFEditorLite" --clean --noconfirm pdf_editor_lite.py
echo.

:: Step 3: Build installer
echo [4/4] Building installer...
"%ISCC%" installer.iss
echo.

:: Check result
if exist "installer_output\PDFEditor_Setup.exe" (
    echo ==========================================
    echo   SUCCESS!
    echo ==========================================
    echo.
    echo   Installer created:
    echo     installer_output\PDFEditor_Setup.exe
    echo.
    echo   Share this single file with anyone.
    echo   They double-click it to install PDF Editor
    echo   like a normal Windows app:
    echo.
    echo     - Installs to Program Files
    echo     - Start Menu shortcut
    echo     - Desktop shortcut
    echo     - Uninstall from Add/Remove Programs
    echo.
    echo   No Python needed on their PC!
    echo ==========================================
    echo.

    :: Copy to Desktop for easy access
    copy "installer_output\PDFEditor_Setup.exe" "%USERPROFILE%\Desktop\PDFEditor_Setup.exe" >nul 2>nul
    if not errorlevel 1 (
        echo   Also copied to your Desktop.
        echo.
    )
) else (
    echo ==========================================
    echo   FAILED - Installer was not created.
    echo   Check the errors above.
    echo ==========================================
)

pause
