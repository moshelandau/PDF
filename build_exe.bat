@echo off
echo ==========================================
echo   Building PDF Editor .exe
echo ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed.
    pause
    exit /b 1
)

echo [1/3] Installing PyInstaller...
pip install pyinstaller
echo.

echo [2/3] Building PDF Editor.exe...
echo This may take a few minutes...
echo.
pyinstaller --onefile --windowed --name "PDF Editor" --clean pdf_editor.py
echo.

if exist "dist\PDF Editor.exe" (
    echo [3/3] Creating desktop shortcut...
    copy "dist\PDF Editor.exe" "%USERPROFILE%\Desktop\PDF Editor.exe" >nul
    echo.
    echo ==========================================
    echo   BUILD COMPLETE!
    echo ==========================================
    echo.
    echo   EXE location: dist\PDF Editor.exe
    echo   Also copied to your Desktop.
    echo.
    echo   You can copy "PDF Editor.exe" to any
    echo   Windows PC and it will run without
    echo   Python installed!
    echo ==========================================
) else (
    echo.
    echo BUILD FAILED. Check errors above.
)
echo.
pause
