@echo off
setlocal
set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"
cd /d "%APP_DIR%"
title Myshot AI Launcher

set "PY_EXE="
if exist "%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe"
    goto :FOUND
)
where pythonw >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_EXE=pythonw"
    goto :FOUND
)
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_EXE=python"
    goto :FOUND
)
where py >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_EXE=py"
    goto :FOUND
)

:FOUND
if not defined PY_EXE (
    echo [ERROR] Khong tim thay Python tren he thong!
    echo Vui long cai dat Python va tick vao "Add Python to PATH".
    pause
    exit /b 1
)

echo [OK] Dang khoi dong Myshot AI...
start "" "%PY_EXE%" main.py
timeout /t 1 >nul
exit /b 0
