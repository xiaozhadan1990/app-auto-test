@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "APP_NAME=mobile-auto-test-ui"
set "INSTALL_DEPS=0"

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--install" set "INSTALL_DEPS=1"
shift
goto parse_args
:args_done

cd /d "%~dp0"
set "PROJECT_ROOT=%CD%"
set "BUILD_ASSETS=%PROJECT_ROOT%\build-assets"

echo ============================================================
echo  Flask Web UI build script
echo  APP_NAME       : %APP_NAME%
echo  INSTALL_DEPS   : %INSTALL_DEPS%
echo  PACKAGE_ADB    : NO
echo  PACKAGE_APPIUM : NO
echo ============================================================
echo.

if "%INSTALL_DEPS%"=="1" (
    echo [Step] Installing requirements...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install requirements
        exit /b 1
    )
)

echo [Step] Installing PyInstaller...
python -m pip install pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller
    exit /b 1
)

echo [Step] Preparing build-assets directory...
if exist "%BUILD_ASSETS%" rmdir /s /q "%BUILD_ASSETS%"
mkdir "%BUILD_ASSETS%" >nul 2>nul

echo [Step] Running PyInstaller...
if not exist ".env" if exist ".env.example" copy /y ".env.example" ".env" >nul

set "PYARGS=--noconfirm --clean --onedir --name ""%APP_NAME%"""
set "PYARGS=%PYARGS% --add-data ""ui;ui"""
set "PYARGS=%PYARGS% --add-data ""tests;tests"""
set "PYARGS=%PYARGS% --add-data ""conftest.py;."""
set "PYARGS=%PYARGS% --add-data ""pytest.ini;."""
if exist ".env" set "PYARGS=%PYARGS% --add-data "".env;."""
if exist ".env.example" set "PYARGS=%PYARGS% --add-data "".env.example;."""

python -m PyInstaller %PYARGS% desktop_web_app.py
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller build failed
    exit /b 1
)

echo.
echo ============================================================
echo  Build completed
echo  Output: %PROJECT_ROOT%\dist\%APP_NAME%
echo ============================================================
endlocal
