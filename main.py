import sys
import os

from datetime import datetime

try:
    if sys.stdout:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

def global_exception_handler(exc_type, exc_value, exc_traceback):
    import traceback
    err_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    try:
        with open("crash_log.txt", "a", encoding="utf-8") as f:
            f.write(f"\n--- ERROR AT {datetime.now()} ---\n{err_str}\n")
    except Exception:
        pass
    print("Caught unhandled exception safely:", exc_value)

sys.excepthook = global_exception_handler

import ctypes
from ctypes import wintypes
import keyboard

from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QMessageBox, QWidget
)
from PyQt6.QtCore import (
    QObject, pyqtSignal, Qt, QTimer
)
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction, QGuiApplication

import config as app_config
from overlay import ScreenOverlay
from settings_dialog import SettingsDialog
from main_window import MainControlBar

# Windows Hotkey Constants
WM_HOTKEY = 0x0312
HOTKEY_ID_CAPTURE = 1001
HOTKEY_ID_TRANSLATE = 1002
HOTKEY_ID_AI = 1003

user32 = ctypes.windll.user32

class HotkeyListenerWidget(QWidget):
    """
    Cửa sổ nền tàng hình chuyên lắng nghe WM_HOTKEY từ hệ thống Windows.
    Đảm bảo 100% phím tắt hoạt động mọi lúc mọi nơi ngay cả khi ẩn mọi giao diện.
    """
    def __init__(self, signaler):
        super().__init__()
        self.signaler = signaler
        # Ẩn hoàn toàn khỏi Taskbar và Desktop
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        self.hwnd = int(self.winId())

    def nativeEvent(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(message.__int__())
            if msg.message == WM_HOTKEY:
                if msg.wParam == HOTKEY_ID_CAPTURE:
                    self.signaler.capture_triggered.emit()
                    return True, 0
                elif msg.wParam == HOTKEY_ID_TRANSLATE:
                    self.signaler.translate_triggered.emit()
                    return True, 0
                elif msg.wParam == HOTKEY_ID_AI:
                    self.signaler.ai_triggered.emit()
                    return True, 0
        return False, 0

class HotkeySignaler(QObject):
    capture_triggered = pyqtSignal()
    translate_triggered = pyqtSignal()
    ai_triggered = pyqtSignal()

def create_app_icon():
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(99, 102, 241))
    painter.drawRoundedRect(4, 4, size - 8, size - 8, 16, 16)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 255, 255))
    painter.drawRoundedRect(16, 22, 32, 24, 4, 4)
    painter.drawRoundedRect(24, 17, 16, 6, 2, 2)

    painter.setBrush(QColor(99, 102, 241))
    painter.drawEllipse(24, 26, 16, 16)

    painter.setBrush(QColor(255, 255, 255))
    painter.drawEllipse(29, 31, 6, 6)

    painter.end()
    return QIcon(pixmap)

def parse_hotkey_to_vk(key_str):
    key_str = key_str.lower().strip()
    vk_map = {
        "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
        "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
        "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
        "`": 0xC0, "~": 0xC0, "print screen": 0x2C, "prtsc": 0x2C
    }
    return vk_map.get(key_str, 0x72)

class MyshotApplication:
    def __init__(self, app: QApplication):
        self.app = app
        self.cfg = app_config.load_config()
        self.current_overlay = None

        # Signaler xử lý phím tắt
        self.signaler = HotkeySignaler()
        self.signaler.capture_triggered.connect(self.start_capture_normal)
        self.signaler.translate_triggered.connect(self.start_capture_translate)
        self.signaler.ai_triggered.connect(self.start_capture_ai)

        # Cửa sổ nền lắng nghe phím tắt chuyên dụng
        self.listener_widget = HotkeyListenerWidget(self.signaler)

        # 1. Thanh điều khiển chính nổi trên màn hình
        self.control_bar = MainControlBar()
        self.control_bar.capture_clicked.connect(self.start_capture_normal)
        self.control_bar.translate_clicked.connect(self.start_capture_translate)
        self.control_bar.ai_clicked.connect(self.start_capture_ai)
        self.control_bar.open_file_clicked.connect(self.handle_open_file)
        self.control_bar.file_dropped.connect(self.handle_open_file)
        self.control_bar.settings_clicked.connect(self.open_settings)
        self.control_bar.minimize_clicked.connect(self.hide_control_bar)
        self.control_bar.close_clicked.connect(self.on_control_bar_close)

        self.dual_window = None

        screen_geo = QGuiApplication.primaryScreen().geometry()
        cb_x = (screen_geo.width() - self.control_bar.width()) // 2
        cb_y = 20
        self.control_bar.move(cb_x, cb_y)
        
        # Tự động đăng ký khởi động cùng Windows nếu được bật trong cấu hình
        if self.cfg.get("auto_start", True):
            app_config.set_run_on_startup(True)

        # Mặc định luôn hiển thị thanh điều khiển nổi trên màn hình khi mở ứng dụng
        if self.cfg.get("show_floating_bar", True):
            self.control_bar.show()
            self.control_bar.raise_()
            self.control_bar.activateWindow()

        self.setup_single_instance_listener()

        cap_key = self.cfg.get("hotkey_capture", "f1").upper()

        # 2. System Tray (Khay hệ thống chạy ngầm)
        self.tray_icon = QSystemTrayIcon(create_app_icon(), self.app)
        self.tray_icon.setToolTip(f"Myshot AI (Đang chạy ngầm - {cap_key}: Chụp màn hình)")
        self.init_tray_menu()
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

        # 3. Đăng ký phím tắt
        self.registered_keyboard_hk = []
        self.register_global_hotkeys()

    def init_tray_menu(self):
        self.tray_menu = QMenu()
        self.tray_menu.setStyleSheet("""
            QMenu {
                background-color: #0E121B;
                color: #ECEFF4;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI Variable Text', 'Segoe UI', Arial;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 20px 6px 10px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: #6366F1;
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background-color: rgba(255, 255, 255, 0.08);
                margin: 4px 0;
            }
        """)

        cap_key = self.cfg.get("hotkey_capture", "f1").upper()

        # 1. Nút chuyển đổi Hiện / Ẩn thanh điều khiển
        self.act_toggle_bar = QAction("📌 Hiện thanh điều khiển", self.tray_menu)
        self.act_toggle_bar.triggered.connect(self.toggle_control_bar)
        self.tray_menu.addAction(self.act_toggle_bar)

        self.tray_menu.addSeparator()

        # 2. Chụp màn hình & Dịch từ File
        act_capture = QAction(f"📸 Chụp màn hình ({cap_key})", self.tray_menu)
        act_capture.triggered.connect(self.start_capture_normal)
        self.tray_menu.addAction(act_capture)

        act_doc = QAction("📄 Dịch tài liệu & File (Excel, Word, PPTX, PDF, Ảnh)...", self.tray_menu)
        act_doc.triggered.connect(self.handle_open_file)
        self.tray_menu.addAction(act_doc)

        self.tray_menu.addSeparator()

        # 3. Cài đặt & Giới thiệu
        act_settings = QAction("⚙️ Cài đặt & Gemini API...", self.tray_menu)
        act_settings.triggered.connect(self.open_settings)
        self.tray_menu.addAction(act_settings)

        act_about = QAction("📖 Giới thiệu Myshot AI", self.tray_menu)
        act_about.triggered.connect(self.show_about)
        self.tray_menu.addAction(act_about)

        self.tray_menu.addSeparator()

        # 4. Thoát
        act_exit = QAction("✕ Thoát ứng dụng", self.tray_menu)
        act_exit.triggered.connect(self.exit_app)
        self.tray_menu.addAction(act_exit)

        # Cập nhật chữ Hiện / Ẩn mỗi khi menu chuẩn bị mở ra
        self.tray_menu.aboutToShow.connect(self.update_tray_menu_state)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.update_tray_menu_state()

    def update_tray_menu_state(self):
        if self.control_bar.isVisible():
            self.act_toggle_bar.setText("📌 Ẩn thanh điều khiển")
        else:
            self.act_toggle_bar.setText("📌 Hiện thanh điều khiển")

    def hide_control_bar(self):
        self.control_bar.hide()
        self.update_tray_menu_state()

    def on_control_bar_close(self):
        self.hide_control_bar()
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "Myshot AI",
                "Thanh điều khiển đã thu gọn vào khay hệ thống (phím tắt vẫn hoạt động bình thường). Nhấp chuột phải icon khay để Thoát hoàn toàn.",
                QSystemTrayIcon.MessageIcon.Information,
                2500
            )

    def toggle_control_bar(self):
        if self.control_bar.isVisible():
            self.hide_control_bar()
        else:
            self.control_bar.show()
            self.control_bar.raise_()
            self.control_bar.activateWindow()
            self.update_tray_menu_state()

    def on_tray_activated(self, reason):
        if reason in [QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick]:
            self.toggle_control_bar()

    def setup_single_instance_listener(self):
        """Lắng nghe lệnh đánh thức từ instance thứ 2 để đưa thanh điều khiển lên phía trước"""
        global _GLOBAL_LOCK_SOCKET
        if _GLOBAL_LOCK_SOCKET and hasattr(_GLOBAL_LOCK_SOCKET, "accept"):
            import threading
            def listen_loop():
                while True:
                    try:
                        conn, _ = _GLOBAL_LOCK_SOCKET.accept()
                        data = conn.recv(64)
                        if b"SHOW" in data:
                            QTimer.singleShot(0, self.bring_to_front)
                        conn.close()
                    except Exception:
                        break
            t = threading.Thread(target=listen_loop, daemon=True)
            t.start()

    def bring_to_front(self):
        self.control_bar.show()
        self.control_bar.raise_()
        self.control_bar.activateWindow()
        self.update_tray_menu_state()

    def register_global_hotkeys(self):
        hwnd = self.listener_widget.hwnd
        for hid in [HOTKEY_ID_CAPTURE, HOTKEY_ID_TRANSLATE, HOTKEY_ID_AI]:
            user32.UnregisterHotKey(hwnd, hid)
            user32.UnregisterHotKey(None, hid)

        for hk in self.registered_keyboard_hk:
            try:
                keyboard.remove_hotkey(hk)
            except Exception:
                pass
        self.registered_keyboard_hk.clear()

        # 1. Đăng ký trực tiếp vào HWND của listener_widget
        cap_str = self.cfg.get("hotkey_capture", "f3")
        vk_cap = parse_hotkey_to_vk(cap_str)
        user32.RegisterHotKey(hwnd, HOTKEY_ID_CAPTURE, 0, vk_cap)

        trans_str = self.cfg.get("hotkey_translate", "f4")
        vk_trans = parse_hotkey_to_vk(trans_str)
        user32.RegisterHotKey(hwnd, HOTKEY_ID_TRANSLATE, 0, vk_trans)

        ai_str = self.cfg.get("hotkey_ai", "f9")
        vk_ai = parse_hotkey_to_vk(ai_str)
        user32.RegisterHotKey(hwnd, HOTKEY_ID_AI, 0, vk_ai)

        # 2. Đăng ký dự phòng qua keyboard
        for k_str, sig in [(cap_str, self.signaler.capture_triggered),
                           (trans_str, self.signaler.translate_triggered),
                           (ai_str, self.signaler.ai_triggered)]:
            try:
                hk = keyboard.add_hotkey(k_str, lambda s=sig: s.emit())
                self.registered_keyboard_hk.append(hk)
            except Exception:
                pass

    def start_capture_normal(self):
        if self.current_overlay is not None:
            return
        was_visible = self.control_bar.isVisible()
        self.control_bar.hide()
        QTimer.singleShot(120, lambda: self._launch_overlay("normal", was_visible))

    def start_capture_translate(self):
        if self.current_overlay is not None:
            return
        was_visible = self.control_bar.isVisible()
        self.control_bar.hide()
        QTimer.singleShot(120, lambda: self._launch_overlay("translate", was_visible))

    def start_capture_ai(self):
        if self.current_overlay is not None:
            return
        was_visible = self.control_bar.isVisible()
        self.control_bar.hide()
        QTimer.singleShot(120, lambda: self._launch_overlay("ai", was_visible))

    def _launch_overlay(self, mode, was_visible):
        self.current_overlay = ScreenOverlay(capture_mode=mode)
        self.current_overlay.closed.connect(lambda: self.on_overlay_closed(was_visible))
        self.current_overlay.show()
        self.current_overlay.activateWindow()
        self.current_overlay.raise_()
        self.current_overlay.setFocus()

    def on_overlay_closed(self, was_visible):
        self.current_overlay = None
        if was_visible and self.cfg.get("show_floating_bar", True):
            self.control_bar.show()

    def open_settings(self):
        dialog = SettingsDialog()
        dialog.settings_saved.connect(self.on_settings_saved)
        dialog.exec()

    def on_settings_saved(self):
        self.cfg = app_config.load_config()
        self.init_tray_menu()
        self.register_global_hotkeys()
        self.control_bar.btn_cap.setText(f"📸 Chụp [{self.cfg.get('hotkey_capture', 'F3').upper()}]")
        self.control_bar.btn_trans.setText(f"🌐 Dịch [{self.cfg.get('hotkey_translate', 'F4').upper()}]")
        self.control_bar.btn_ai.setText(f"✨ AI [{self.cfg.get('hotkey_ai', 'F9').upper()}]")
        
        if self.cfg.get("show_floating_bar", True):
            self.control_bar.show()
        else:
            self.control_bar.hide()

    def open_document_translator(self, file_path=None):
        from document_translator_dialog import DocumentTranslatorDialog
        dlg = DocumentTranslatorDialog(initial_file=file_path)
        dlg.exec()

    def handle_open_file(self, file_path=None):
        if not file_path or not isinstance(file_path, str):
            from PyQt6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getOpenFileName(
                None,
                "Chọn file tài liệu hoặc ảnh để dịch",
                "",
                "Tất cả file hỗ trợ (*.xlsx *.docx *.pptx *.pdf *.png *.jpg *.jpeg *.webp);;"
                "Tài liệu Office & PDF (*.xlsx *.docx *.pptx *.pdf);;"
                "File ảnh (*.png *.jpg *.jpeg *.webp *.bmp)"
            )
        if file_path and os.path.exists(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            if ext in (".xlsx", ".xlsm", ".docx", ".docm", ".pptx", ".pptm", ".pdf"):
                self.open_document_translator(file_path)
            else:
                from dual_compare_window import DualCompareWindow
                if not self.dual_window:
                    self.dual_window = DualCompareWindow()
                self.dual_window.show()
                self.dual_window.raise_()
                self.dual_window.activateWindow()
                self.dual_window.translate_image_file(file_path)

    def show_about(self):
        from about_dialog import AboutDialog
        dlg = AboutDialog(self.control_bar)
        dlg.exec()

    def exit_app(self):
        hwnd = self.listener_widget.hwnd
        for hid in [HOTKEY_ID_CAPTURE, HOTKEY_ID_TRANSLATE, HOTKEY_ID_AI]:
            user32.UnregisterHotKey(hwnd, hid)
        for hk in self.registered_keyboard_hk:
            try:
                keyboard.remove_hotkey(hk)
            except Exception:
                pass
        self.tray_icon.hide()
        self.control_bar.close()
        self.listener_widget.close()
        self.app.quit()

_GLOBAL_LOCK_SOCKET = None

def acquire_single_instance_lock():
    global _GLOBAL_LOCK_SOCKET
    import socket
    import subprocess
    import time

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1', 49281))
        s.listen(5)
        _GLOBAL_LOCK_SOCKET = s
        return s
    except Exception:
        # Nếu cổng 49281 đã được mở, gửi lệnh SHOW để đánh thức ứng dụng hiện lên màn hình
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(1.5)
            client.connect(('127.0.0.1', 49281))
            client.sendall(b"SHOW\n")
            client.close()
            # Đã đánh thức ứng dụng đang chạy thành công -> Thoát instance trùng lặp
            return None
        except Exception:
            pass

        # Trường hợp cổng bị treo bởi tiến trình cũ bị đơ:
        try:
            res = subprocess.run('netstat -ano | findstr :49281', shell=True, capture_output=True, text=True)
            for line in res.stdout.strip().splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and "LISTENING" in parts:
                    old_pid = parts[-1]
                    if int(old_pid) != os.getpid():
                        subprocess.run(f'taskkill /F /PID {old_pid}', shell=True, capture_output=True)
            time.sleep(0.4)
            s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s2.bind(('127.0.0.1', 49281))
            s2.listen(5)
            _GLOBAL_LOCK_SOCKET = s2
            return s2
        except Exception:
            # Nếu không chiếm được cổng, vẫn cho phép chạy dự phòng
            return True

def main():
    lock = acquire_single_instance_lock()
    if not lock:
        sys.exit(0)

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    myshot = MyshotApplication(app)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
