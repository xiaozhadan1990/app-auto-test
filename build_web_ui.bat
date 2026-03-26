@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "APP_NAME=mobile-auto-test-ui"
set "INSTALL_DEPS=0"
set "NPM_CMD=npm"
set "UV_CMD=uv"
set "UV_CACHE_DIR=.uv-cache"

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--install" set "INSTALL_DEPS=1"
shift
goto parse_args
:args_done

cd /d "%~dp0"
set "PROJECT_ROOT=%CD%"
set "FRONTEND_DIR=%PROJECT_ROOT%\web-ui"
set "UI_DIR=%PROJECT_ROOT%\ui"
set "DIST_DIR=%PROJECT_ROOT%\dist\%APP_NAME%"
set "BUILD_DIR=%PROJECT_ROOT%\build\%APP_NAME%"

echo ============================================================
echo  Flask Web UI build script
echo  APP_NAME       : %APP_NAME%
echo  INSTALL_DEPS   : %INSTALL_DEPS%
echo  PACKAGE_ADB    : NO
echo  PACKAGE_APPIUM : NO
echo  PYTHON_TOOL    : %UV_CMD%
echo  UV_CACHE_DIR   : %UV_CACHE_DIR%
echo  FRONTEND_DIR   : %FRONTEND_DIR%
echo ============================================================
echo.

if "%INSTALL_DEPS%"=="1" (
    echo [Step] Syncing Python dependencies with uv...
    call %UV_CMD% sync --cache-dir "%UV_CACHE_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to sync Python dependencies
        exit /b 1
    )
)

echo [Step] Checking uv / Node.js / npm...
where %UV_CMD% >nul 2>nul
if errorlevel 1 (
    echo [ERROR] uv is required but not found in PATH
    exit /b 1
)
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
call %UV_CMD% sync --cache-dir "%UV_CACHE_DIR%"
if errorlevel 1 (
    echo [ERROR] Failed to sync dependencies for build
    exit /b 1
)

echo [Step] Stopping running packaged app if exists...
taskkill /F /IM "%APP_NAME%.exe" >nul 2>nul

echo [Step] Cleaning previous build outputs...
if exist "%DIST_DIR%" (
    rmdir /s /q "%DIST_DIR%"
    if exist "%DIST_DIR%" (
        echo [ERROR] Failed to remove old dist output: %DIST_DIR%
        echo         Please close the packaged app and retry.
        exit /b 1
    )
)
if exist "%BUILD_DIR%" (
    rmdir /s /q "%BUILD_DIR%"
    if exist "%BUILD_DIR%" (
        echo [ERROR] Failed to remove old build output: %BUILD_DIR%
        echo         Please close any process locking files under that directory and retry.
        exit /b 1
    )
)

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

call %UV_CMD% run --with pyinstaller --cache-dir "%UV_CACHE_DIR%" pyinstaller %PYARGS% desktop_web_app.py
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller build failed
    exit /b 1
)

echo [Step] Copying runtime env files...
if exist "dist\%APP_NAME%" (
    if exist ".env" copy /y ".env" "dist\%APP_NAME%\.env" >nul
    if exist ".env.example" copy /y ".env.example" "dist\%APP_NAME%\.env.example" >nul
)

echo.
echo ============================================================
echo  Build completed
echo  Output: %PROJECT_ROOT%\dist\%APP_NAME%
echo ============================================================
endlocal
