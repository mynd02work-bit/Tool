@echo off
chcp 65001 >nul
title Cập Nhật EasyCap Mobile Sang Điện Thoại
echo ==========================================================
echo       🚀 ĐỒNG BỘ & CẬP NHẬT EASYCAP SANG ĐIỆN THOẠI
echo ==========================================================
echo.

set "ADB_EXE=adb"
if exist "C:\Program Files\platform-tools\adb.exe" (
    set "ADB_EXE=C:\Program Files\platform-tools\adb.exe"
)

echo [1/4] Đang kiểm tra kết nối thiết bị Android...
"%ADB_EXE%" devices > "%TEMP%\adb_devices.txt"
findstr /R /C:"device$" "%TEMP%\adb_devices.txt" >nul
if %errorlevel% neq 0 (
    echo.
    echo [!] Chua phat hien dien thoai nao cam qua cap USB!
    echo.
    set /p PHONE_IP="Nhap dia chi IP dien thoai de ket noi qua Wi-Fi (hoac enter de bo qua): "
    if defined PHONE_IP (
        echo Dang ket noi toi %PHONE_IP%...
        "%ADB_EXE%" connect %PHONE_IP%
    )
)

echo.
echo [2/4] Đang biên dịch bản cập nhật Android APK mới nhất...
cd /d "%~dp0EasyCap-Mobile"
if exist "gradlew.bat" (
    call gradlew.bat assembleDebug
) else (
    echo [THÔNG BÁO] Bạn có thể mở Android Studio và bấm 'Build APK' hoặc dùng lệnh Gradle.
)

echo.
echo [3/4] Đang cài đặt bản cập nhật trực tiếp lên điện thoại...
set "APK_PATH=app\build\outputs\apk\debug\app-debug.apk"
if exist "%APK_PATH%" (
    "%ADB_EXE%" install -r -d "%APK_PATH%"
    echo.
    echo [4/4] Khởi động lại ứng dụng EasyCap trên điện thoại...
    "%ADB_EXE%" shell am start -n com.easycap.mobile/.MainActivity
    echo.
    echo ==========================================================
    echo ✅ CẬP NHẬT THÀNH CÔNG! Điện thoại của bạn đã có bản mới nhất.
    echo ==========================================================
) else (
    echo [LƯU Ý] Chưa tìm thấy file APK biên dịch sẵn.
    echo Ứng dụng điện thoại cũng sẽ TỰ ĐỘNG TẢI BẢN MỚI qua tính năng OTA 
    echo khi bạn đẩy phiên bản mới lên GitHub!
)

echo.
pause
