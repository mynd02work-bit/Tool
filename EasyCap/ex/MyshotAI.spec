# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('myshot_config.json', '.'), ('app_icon.ico', '.'), ('assets', 'assets')]
binaries = []
hiddenimports = [
    'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.QtPrintSupport',
    'keyboard', 'mss', 'PIL', 'requests', 'winocr'
]

# Chỉ collect_all cho winrt (cần thiết cho Windows Media OCR)
# TUYỆT ĐỐI KHÔNG collect_all('winocr') vì winocr có code dự phòng import cv2, uvicorn, fastapi
# khiến PyInstaller tự động kéo theo OpenCV (~112MB) và FastAPI/Uvicorn/Pydantic
tmp_ret = collect_all('winrt')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

excludes = [
    'cv2', 'opencv',
    'uvicorn', 'fastapi', 'starlette', 'pydantic', 'pydantic_core', 'watchfiles',
    'scipy', 'matplotlib', 'pandas', 'IPython', 'notebook', 'sphinx',
    'tkinter', '_tkinter',
    'unittest', 'test', 'pydoc', 'pydoc_data',
    'sqlite3',
    'PyQt6.QtQml', 'PyQt6.QtQuick', 'PyQt6.QtPdf', 'PyQt6.QtWebEngine',
    'PyQt6.QtSql', 'PyQt6.QtTest', 'PyQt6.QtDesigner', 'PyQt6.QtXml',
    'PyQt6.QtMultimedia', 'PyQt6.QtBluetooth', 'PyQt6.QtPositioning',
    'PyQt6.QtNfc', 'PyQt6.QtSensors', 'PyQt6.QtSerialPort', 'PyQt6.QtRemoteObjects',
]

a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=2,
)

# Lọc bỏ các thư viện cồng kềnh không dùng của Qt6 khỏi binaries (tiết kiệm ~25MB)
# 1. opengl32sw.dll: Driver Mesa CPU OpenGL của Qt (rất nặng ~20MB, không cần trên Windows 10/11)
# 2. Qt6Pdf.dll: Thư viện PDF viewer của Qt (~5.3MB, không sử dụng)
a.binaries = [
    b for b in a.binaries
    if not any(excluded in b[0].lower() for excluded in ['opengl32sw', 'qt6pdf'])
]

pyz = PYZ(a.pure, optimize=2)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MyshotAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app_icon.ico'],
)
