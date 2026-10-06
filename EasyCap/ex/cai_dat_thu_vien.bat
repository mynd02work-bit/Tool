@echo off
chcp 65001 >nul
echo ========================================================
echo    DANG CAI DAT CAC THU VIEN CHO UNG DUNG MYSHOT
echo ========================================================
echo.
echo [1/2] Cai dat cac thu vien Python...
python -m pip install --upgrade pip
python -m pip install PyQt6 winocr pillow requests keyboard mss

echo.
echo [2/2] Dang thiet lap khoi dong cung Windows (chay ngam khi bat may)...
python -c "import config; config.set_run_on_startup(True)"

echo.
echo ========================================================
echo   CAI DAT HOAN TAT! UNG DUNG DA DUOC BAT CHAY NGAM KHI MO MAY.
echo   BAN CO THE CHAY NGAY BANG FILE RUN.BAT
echo ========================================================
pause
