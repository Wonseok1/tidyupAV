@echo off
set PYI=%LOCALAPPDATA%\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe
if not exist "%PYI%" set PYI=pyinstaller

"%PYI%" --onefile --windowed --name TidyupAV --hidden-import dotenv --hidden-import psycopg2 --hidden-import psycopg2.extras --collect-all dotenv organizer.py

if %ERRORLEVEL% NEQ 0 (
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo Build complete: dist\TidyupAV.exe
echo.
pause
