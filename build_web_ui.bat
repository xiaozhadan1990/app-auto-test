@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "APP_NAME=mobile-auto-test-ui"
set "INSTALL_DEPS=0"
set "NPM_CMD=npm"

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--install" set "INSTALL_DEPS=1"
shift
goto parse_args
:args_done

cd /d "%~dp0"
set "PROJECT_ROOT=%CD%"
set "BUILD_ASSETS=%PROJECT_ROOT%\build-assets"
set "FRONTEND_DIR=%PROJECT_ROOT%\web-ui"
set "UI_DIR=%PROJECT_ROOT%\ui"

echo ============================================================
echo  Flask Web UI build script
echo  APP_NAME       : %APP_NAME%
echo  INSTALL_DEPS   : %INSTALL_DEPS%
echo  PACKAGE_ADB    : NO
echo  PACKAGE_APPIUM : NO
echo  FRONTEND_DIR   : %FRONTEND_DIR%
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

echo [Step] Checking Node.js / npm...
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] node is required but not found in PATH
    exit /b 1
)
where %NPM_CMD% >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm is required but not found in PATH
    exit /b 1
)

if not exist "%FRONTEND_DIR%\package.json" (
    echo [ERROR] Frontend project not found: %FRONTEND_DIR%\package.json
    exit /b 1
)

echo [Step] Building frontend UI...
pushd "%FRONTEND_DIR%"
if "%INSTALL_DEPS%"=="1" (
    echo [Step] Installing frontend dependencies...
    call %NPM_CMD% install
    if errorlevel 1 (
        popd
        echo [ERROR] Failed to install frontend dependencies
        exit /b 1
    )
) else (
    if not exist "node_modules" (
        echo [Step] node_modules not found, installing frontend dependencies...
        call %NPM_CMD% install
        if errorlevel 1 (
            popd
            echo [ERROR] Failed to install frontend dependencies
            exit /b 1
        )
    )
)

call %NPM_CMD% run build
if errorlevel 1 (
    popd
    echo [ERROR] Frontend build failed
    exit /b 1
)
popd

if not exist "%UI_DIR%\index.html" (
    echo [ERROR] Frontend output missing: %UI_DIR%\index.html
    exit /b 1
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

echo [Step] Stopping running packaged app if exists...
taskkill /F /IM "%APP_NAME%.exe" >nul 2>nul

echo [Step] Running PyInstaller...
if not exist ".env" if exist ".env.example" copy /y ".env.example" ".env" >nul

set "PYARGS=--noconfirm --clean --onedir --name ""%APP_NAME%"""
set "PYARGS=%PYARGS% --add-data ""ui;ui"""
set "PYARGS=%PYARGS% --add-data ""tests;tests"""
set "PYARGS=%PYARGS% --add-data ""conftest.py;."""
set "PYARGS=%PYARGS% --add-data ""pytest.ini;."""
set "PYARGS=%PYARGS% --collect-all ""appium"""
set "PYARGS=%PYARGS% --collect-all ""selenium"""
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
