@echo off
setlocal
set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"
cd /d "%APP_DIR%"
title Myshot AI (Debug Console Mode)

echo ========================================================
echo          MYSHOT AI - CHE DO DEBUG / KIEM TRA LOI
echo ========================================================
echo.

set "PY_EXE="
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
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
    echo [ERROR] Khong tim thay Python!
    pause
    exit /b 1
)

echo Dang khoi chay bang: %PY_EXE%
echo Neu ung dung gap loi, toan bo chi tiet loi se hien thi o ben duoi:
echo ----------------------------------------------------------------------
"%PY_EXE%" main.py
echo ----------------------------------------------------------------------
echo Ung dung da dong.
pause
