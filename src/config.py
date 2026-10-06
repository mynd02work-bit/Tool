import os
import sys
import json

if getattr(sys, 'frozen', False):
    CONFIG_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, '_MEIPASS', CONFIG_DIR)
else:
    this_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(this_dir).lower() == "src":
        CONFIG_DIR = os.path.dirname(this_dir)
    else:
        CONFIG_DIR = this_dir
    BUNDLE_DIR = CONFIG_DIR

CONFIG_FILE = os.path.join(CONFIG_DIR, "myshot_config.json")
BUNDLE_CONFIG_FILE = os.path.join(BUNDLE_DIR, "myshot_config.json")

DEFAULT_CONFIG = {
    "hotkey_capture": "f3",
    "hotkey_translate": "f4",
    "hotkey_ai": "f9",
    "save_dir": os.path.join(os.path.expanduser("~"), "Downloads"),
    "save_format": "PNG",  # PNG, JPEG, BMP
    "default_color": "#FF3344",
    "default_pen_width": 3,
    "default_font_size": 16,
    "highlight_opacity": 90,
    "ocr_lang": "en-US",
    "target_lang": "vi",
    "auto_copy_after_save": True,
    "sound_enabled": True,
    
    # Cấu hình AI Gemini & Trợ lý Monica
    "gemini_api_key": "",
    "gemini_model": "gemini-flash-lite-latest",  # gemini-flash-lite-latest, gemini-3.8-flash, gemini-flash-latest, gemini-pro-latest
    "ai_provider": "official",  # official, local_proxy
    "local_proxy_url": "http://127.0.0.1:8000/v1",
    "use_ai_for_default_translate": False,
    "show_floating_bar": False,  # Mặc định chạy ngầm trong khay hệ thống, không hiện thanh nổi
    "auto_start": True,          # Tự động chạy ngầm khi mở máy tính
    "default_hide_capture_toolbar": False  # Mặc định HIỆN thanh công cụ vẽ khi chụp ảnh
}

APP_NAME = "MyshotAI"

DEFAULT_GEMINI_API_KEY = ""

def get_effective_gemini_api_key(cfg=None):
    if cfg is None:
        cfg = load_config()
    key = cfg.get("gemini_api_key", "").strip()
    return key

def is_default_gemini_api_key(key: str) -> bool:
    return not key or not key.strip()

def set_run_on_startup(enable: bool = True) -> bool:
    """
    Bật hoặc Tắt tính năng tự khởi động cùng Windows (chạy ngầm khi mở máy):
    Ghi vào Registry: HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
    """
    import sys
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                if getattr(sys, 'frozen', False):
                    # Nếu chạy file đóng gói .exe
                    exe_cmd = f'"{sys.executable}"'
                else:
                    # Nếu chạy từ source Python
                    dir_path = os.path.dirname(os.path.abspath(__file__))
                    script_path = os.path.join(dir_path, "main.py")
                    python_exe = sys.executable.replace("python.exe", "pythonw.exe")
                    if not os.path.exists(python_exe):
                        python_exe = sys.executable
                    exe_cmd = f'"{python_exe}" "{script_path}"'
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print("Lỗi thiết lập khởi động cùng Windows:", e)
        return False

def is_run_on_startup_enabled() -> bool:
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(val)
    except Exception:
        return False

def load_config():
    target = CONFIG_FILE if os.path.exists(CONFIG_FILE) else (BUNDLE_CONFIG_FILE if os.path.exists(BUNDLE_CONFIG_FILE) else None)
    if target and os.path.exists(target):
        try:
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(data)
                return config
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print("Lỗi lưu cấu hình:", e)
        return False
