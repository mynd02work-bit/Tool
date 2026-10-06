import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFileDialog, QSpinBox, QCheckBox,
    QTabWidget, QWidget, QGroupBox, QFormLayout, QFrame
)
import threading
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QFont
import config as app_config
from ai_engine import test_gemini_connection

SETTINGS_STYLE = """
QDialog {
    background-color: #0E121B;
    color: #E2E8F0;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, sans-serif;
}
QTabWidget::pane {
    border: 1px solid rgba(255, 255, 255, 0.08);
    background-color: rgba(20, 26, 38, 0.6);
    border-radius: 12px;
    padding: 12px;
}
QTabBar::tab {
    background-color: transparent;
    color: #94A3B8;
    padding: 8px 16px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 12px;
    margin-right: 4px;
}
QTabBar::tab:hover {
    background-color: rgba(255, 255, 255, 0.05);
    color: #FFFFFF;
}
QTabBar::tab:selected {
    background-color: rgba(255, 255, 255, 0.1);
    color: #38BDF8;
}
QGroupBox {
    color: #38BDF8;
    font-weight: 700;
    font-size: 12px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 16px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #141A26;
}
QLabel {
    color: #CBD5E1;
    font-size: 12px;
}
QLineEdit, QComboBox, QSpinBox {
    background-color: rgba(255, 255, 255, 0.05);
    color: #F8FAFC;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #38BDF8;
    background-color: rgba(255, 255, 255, 0.08);
}
QPushButton {
    background-color: rgba(255, 255, 255, 0.06);
    color: #E2E8F0;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.12);
    color: #FFFFFF;
}
QPushButton#PrimaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #06B6D4);
    color: #FFFFFF;
    border: none;
}
QPushButton#PrimaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369A1, stop:1 #0891B2);
}
QCheckBox {
    color: #CBD5E1;
    font-size: 12px;
    spacing: 8px;
}
"""

class TestConnectionWorker(QObject):
    result_signal = pyqtSignal(bool, str)

    def __init__(self, api_key, model):
        super().__init__()
        self.api_key = api_key
        self.model = model
        self._is_cancelled = False
        self._thread = None

    def cancel(self):
        self._is_cancelled = True
        try:
            self.result_signal.disconnect()
        except Exception:
            pass

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            success, msg = test_gemini_connection(self.api_key, self.model)
        except Exception as e:
            success, msg = False, str(e)

        if not self._is_cancelled:
            try:
                self.result_signal.emit(success, msg)
            except Exception:
                pass

class SettingsDialog(QDialog):
    settings_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cài Đặt & Cấu Hình Myshot")
        self.setMinimumWidth(620)
        self.resize(620, 530)
        self.setStyleSheet(SETTINGS_STYLE)
        self.cfg = app_config.load_config()
        self.test_worker = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self.create_ai_tab(), "🤖 Gemini AI")
        tabs.addTab(self.create_hotkey_tab(), "⌨️ Phím Tắt")
        tabs.addTab(self.create_save_tab(), "📁 Lưu Trữ")
        tabs.addTab(self.create_drawing_tab(), "🎨 Vẽ & Ghi Chú")
        main_layout.addWidget(tabs)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Hủy bỏ")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Lưu Cài Đặt")
        btn_save.setObjectName("PrimaryBtn")
        btn_save.clicked.connect(self.save_and_close)
        btn_layout.addWidget(btn_save)

        main_layout.addLayout(btn_layout)

    def create_ai_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(10)

        box = QGroupBox("Cấu Hình Google Gemini Multimodal AI")
        form = QFormLayout(box)
        form.setSpacing(10)

        # Ô nhập API Key
        key_layout = QHBoxLayout()
        raw_key = self.cfg.get("gemini_api_key", "").strip()
        is_default = (not raw_key) or (raw_key == app_config.DEFAULT_GEMINI_API_KEY)
        display_key = "" if is_default else raw_key

        self.txt_gemini_key = QLineEdit(display_key)
        self.txt_gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_gemini_key.setPlaceholderText("Đang dùng API mặc định của hệ thống (Dán key riêng vào đây)")

        self.btn_toggle_key = QPushButton("👁️")
        self.btn_toggle_key.setFixedWidth(36)
        self.btn_toggle_key.setToolTip("Hiện / Ẩn API Key")
        self.btn_toggle_key.clicked.connect(self.toggle_key_visibility)

        key_layout.addWidget(self.txt_gemini_key)
        key_layout.addWidget(self.btn_toggle_key)
        form.addRow("Gemini API Key:", key_layout)

        # Hướng dẫn & Dòng thông báo
        guide_text = (
            "<div style='color: #94A3B8; font-size: 11px; line-height: 1.6;'>"
            "👉 Chưa có Key? <a href='https://aistudio.google.com/app/apikey' style='color: #38BDF8; font-weight: 600;'>Nhấp vào đây để lấy API Key MIỄN PHÍ từ Google AI Studio</a>.<br>"
            "<span style='color: #FCD34D; font-weight: 600;'>💡 Sử dụng API của riêng bạn sẽ hạn chế các vấn đề giới hạn</span>"
            "</div>"
        )
        link_lbl = QLabel(guide_text)
        link_lbl.setOpenExternalLinks(True)
        form.addRow("", link_lbl)

        # Nút bật / tắt hướng dẫn chi tiết cách lấy API Key (Mặc định ẩn)
        self.btn_toggle_guide = QPushButton("📖 Hướng dẫn chi tiết cách lấy API Key miễn phí (Nhấn để xem) ▼")
        self.btn_toggle_guide.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_guide.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.08);
                color: #38BDF8;
                border: 1px dashed rgba(56, 189, 248, 0.3);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
                text-align: left;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.16);
                color: #FFFFFF;
                border: 1px solid #38BDF8;
            }
        """)
        self.btn_toggle_guide.clicked.connect(self.toggle_api_guide)
        form.addRow("", self.btn_toggle_guide)

        # Khung nội dung hướng dẫn chi tiết (Mặc định ẨN)
        self.guide_box = QFrame()
        self.guide_box.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 23, 42, 0.85);
                border: 1px solid rgba(56, 189, 248, 0.25);
                border-radius: 8px;
                padding: 8px 12px;
            }
        """)
        guide_box_layout = QVBoxLayout(self.guide_box)
        guide_box_layout.setContentsMargins(6, 6, 6, 6)
        guide_box_layout.setSpacing(4)

        detail_guide_html = (
            "<div style='color: #CBD5E1; font-size: 11px; line-height: 1.6;'>"
            "<b style='color: #38BDF8;'>Các bước lấy API Key Gemini miễn phí vĩnh viễn:</b><br>"
            "<b>1.</b> Truy cập <a href='https://aistudio.google.com/app/apikey' style='color: #38BDF8; text-decoration: underline;'>Google AI Studio (aistudio.google.com)</a> và đăng nhập tài khoản Google.<br>"
            "<b>2.</b> Bấm nút màu xanh <b>\"Create API key\"</b> (Tạo khóa API mới).<br>"
            "<b>3.</b> Chọn <b>\"Create API key in new project\"</b> (hoặc chọn dự án Google Cloud có sẵn).<br>"
            "<b>4.</b> Bấm biểu tượng <b>Copy</b> (Sao chép) để copy chuỗi API Key vừa tạo.<br>"
            "<b>5.</b> Quay lại đây, dán (Ctrl + V) vào ô <b>Gemini API Key</b> ở trên rồi bấm <b>\"Lưu Cài Đặt\"</b>.<br>"
            "<span style='color: #10B981;'>✓ Hoàn toàn MIỄN PHÍ 100%, không cần thẻ ngân hàng, hạn mức dồi dào cho cá nhân!</span>"
            "</div>"
        )
        self.lbl_detail_guide = QLabel(detail_guide_html)
        self.lbl_detail_guide.setOpenExternalLinks(True)
        self.lbl_detail_guide.setWordWrap(True)
        guide_box_layout.addWidget(self.lbl_detail_guide)
        self.guide_box.setVisible(False)  # Mặc định ẩn
        form.addRow("", self.guide_box)

        # Lựa chọn Model hiện đại và ổn định nhất
        self.cb_gemini_model = QComboBox()
        self.cb_gemini_model.addItem("gemini-flash-lite-latest (Khuyên dùng: Siêu tốc 1-2s & Phản hồi tức thì)", "gemini-flash-lite-latest")
        self.cb_gemini_model.addItem("gemini-3.5-flash-lite (Mô hình thế hệ 3.5 siêu tốc)", "gemini-3.5-flash-lite")
        self.cb_gemini_model.addItem("gemini-flash-latest (Bản Flash tiêu chuẩn)", "gemini-flash-latest")
        self.cb_gemini_model.addItem("gemini-3.8-flash (Mô hình thế hệ mới nhất của Google)", "gemini-3.8-flash")
        self.cb_gemini_model.addItem("gemini-3.7-flash (Bản suy luận thông minh)", "gemini-3.7-flash")
        self.cb_gemini_model.addItem("gemini-pro-latest (Phân tích chuyên sâu)", "gemini-pro-latest")

        curr_m = self.cfg.get("gemini_model", "gemini-flash-lite-latest")
        for i in range(self.cb_gemini_model.count()):
            if self.cb_gemini_model.itemData(i) == curr_m:
                self.cb_gemini_model.setCurrentIndex(i)
                break
        form.addRow("Mô hình AI:", self.cb_gemini_model)

        # Nút Kiểm Tra Kết Nối
        test_layout = QHBoxLayout()
        self.btn_test_conn = QPushButton("⚡ Kiểm Tra Kết Nối")
        self.btn_test_conn.clicked.connect(self.test_connection)
        test_layout.addWidget(self.btn_test_conn)

        self.lbl_conn_status = QLabel("")
        self.lbl_conn_status.setWordWrap(True)
        self.lbl_conn_status.setStyleSheet("font-size: 11px; font-weight: bold;")
        test_layout.addWidget(self.lbl_conn_status)
        test_layout.addStretch()
        form.addRow("", test_layout)

        # Checkbox
        self.chk_use_ai_translate = QCheckBox("Sử dụng Gemini Vision làm bộ máy dịch mặc định cho phím F4")
        self.chk_use_ai_translate.setChecked(self.cfg.get("use_ai_for_default_translate", False))
        form.addRow("", self.chk_use_ai_translate)

        layout.addWidget(box)
        layout.addStretch()
        return w

    def toggle_api_guide(self):
        is_visible = not self.guide_box.isVisible()
        self.guide_box.setVisible(is_visible)
        if is_visible:
            self.btn_toggle_guide.setText("📖 Hướng dẫn chi tiết cách lấy API Key miễn phí (Nhấn để thu gọn) ▲")
        else:
            self.btn_toggle_guide.setText("📖 Hướng dẫn chi tiết cách lấy API Key miễn phí (Nhấn để xem) ▼")
        self.adjustSize()

    def toggle_key_visibility(self):
        # Nếu đang dùng API mặc định (ô trống), không hiển thị
        if not self.txt_gemini_key.text():
            return
        if self.txt_gemini_key.echoMode() == QLineEdit.EchoMode.Password:
            self.txt_gemini_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_key.setText("🙈")
        else:
            self.txt_gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_key.setText("👁️")

    def test_connection(self):
        api_key = self.txt_gemini_key.text().strip()
        model = self.cb_gemini_model.currentData()

        using_default = False
        if not api_key:
            api_key = app_config.get_effective_gemini_api_key(self.cfg)
            using_default = True

        self.btn_test_conn.setEnabled(False)
        self.lbl_conn_status.setText("⏳ Đang kiểm tra kết nối tới Gemini...")
        self.lbl_conn_status.setStyleSheet("color: #38BDF8;")

        if self.test_worker:
            self.test_worker.cancel()

        self.test_worker = TestConnectionWorker(api_key, model)
        self.test_worker.result_signal.connect(lambda s, m: self.on_test_finished(s, m, using_default))
        self.test_worker.start()

    def on_test_finished(self, success, message, using_default=False):
        self.btn_test_conn.setEnabled(True)
        if success:
            tag = " (API mặc định của hệ thống)" if using_default else ""
            self.lbl_conn_status.setText(f"✓ {message}{tag}")
            self.lbl_conn_status.setStyleSheet("color: #10B981; font-weight: bold;")
        else:
            self.lbl_conn_status.setText(f"❌ {message}")
            self.lbl_conn_status.setStyleSheet("color: #EF4444; font-weight: bold;")

    def create_hotkey_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        
        box = QGroupBox("Cấu Hình Phím Tắt Toàn Cục")
        form = QFormLayout(box)
        form.setSpacing(10)

        self.cb_hotkey_cap = QComboBox()
        self.cb_hotkey_cap.addItems(["f3", "f1", "f2", "print screen", "`", "ctrl+shift+s", "alt+c"])
        curr_cap = self.cfg.get("hotkey_capture", "f3")
        idx = self.cb_hotkey_cap.findText(curr_cap, Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            self.cb_hotkey_cap.setCurrentIndex(idx)
        else:
            self.cb_hotkey_cap.setEditText(curr_cap)
        self.cb_hotkey_cap.setEditable(True)
        form.addRow("📸 Chụp màn hình & vẽ:", self.cb_hotkey_cap)

        self.cb_hotkey_trans = QComboBox()
        self.cb_hotkey_trans.addItems(["f4", "alt+d", "ctrl+alt+t", "ctrl+shift+d", "f9"])
        curr_trans = self.cfg.get("hotkey_translate", "f4")
        idx2 = self.cb_hotkey_trans.findText(curr_trans, Qt.MatchFlag.MatchFixedString)
        if idx2 >= 0:
            self.cb_hotkey_trans.setCurrentIndex(idx2)
        else:
            self.cb_hotkey_trans.setEditText(curr_trans)
        self.cb_hotkey_trans.setEditable(True)
        form.addRow("🌐 Dịch màn hình trực tiếp:", self.cb_hotkey_trans)

        self.cb_hotkey_ai = QComboBox()
        self.cb_hotkey_ai.addItems(["f9", "f8", "alt+a", "ctrl+shift+a", "f10"])
        curr_ai = self.cfg.get("hotkey_ai", "f9")
        idx3 = self.cb_hotkey_ai.findText(curr_ai, Qt.MatchFlag.MatchFixedString)
        if idx3 >= 0:
            self.cb_hotkey_ai.setCurrentIndex(idx3)
        else:
            self.cb_hotkey_ai.setEditText(curr_ai)
        self.cb_hotkey_ai.setEditable(True)
        form.addRow("✨ Trợ lý AI Gemini:", self.cb_hotkey_ai)

        # Checkbox hiển thị thanh nổi
        self.chk_show_floating_bar = QCheckBox("Hiển thị thanh điều khiển nổi trên màn hình")
        self.chk_show_floating_bar.setChecked(self.cfg.get("show_floating_bar", True))
        self.chk_show_floating_bar.setToolTip("Nếu bỏ chọn, thanh nổi sẽ ẩn đi, ứng dụng chỉ chạy ngầm dưới khay hệ thống.")
        form.addRow("", self.chk_show_floating_bar)

        # Checkbox khởi động cùng Windows
        self.chk_auto_start = QCheckBox("Khởi động cùng Windows (chạy ngầm khi mở máy)")
        self.chk_auto_start.setChecked(self.cfg.get("auto_start", True))
        self.chk_auto_start.setToolTip("Tự động chạy ngầm Myshot AI trong khay hệ thống ngay khi bạn bật máy tính.")
        form.addRow("", self.chk_auto_start)

        hint = QLabel("💡 Phím tắt hoạt động toàn hệ thống dù thanh điều khiển có ẩn hay hiện.")
        hint.setStyleSheet("color: #64748B; font-size: 11px;")
        layout.addWidget(box)
        layout.addWidget(hint)
        layout.addStretch()
        return w

    def create_save_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        box = QGroupBox("Đường Dẫn & Định Dạng Lưu Trữ")
        form = QFormLayout(box)
        form.setSpacing(10)

        dir_layout = QHBoxLayout()
        self.txt_save_dir = QLineEdit(self.cfg.get("save_dir", ""))
        btn_browse = QPushButton("Chọn Thư Mục...")
        btn_browse.clicked.connect(self.browse_folder)
        dir_layout.addWidget(self.txt_save_dir)
        dir_layout.addWidget(btn_browse)
        form.addRow("Thư mục lưu mặc định:", dir_layout)

        self.cb_format = QComboBox()
        self.cb_format.addItems(["PNG", "JPEG", "BMP"])
        self.cb_format.setCurrentText(self.cfg.get("save_format", "PNG"))
        form.addRow("Định dạng ảnh mặc định:", self.cb_format)

        self.chk_autocopy = QCheckBox("Tự động sao chép ảnh vào Clipboard sau khi lưu")
        self.chk_autocopy.setChecked(self.cfg.get("auto_copy_after_save", True))
        form.addRow("", self.chk_autocopy)

        layout.addWidget(box)
        layout.addStretch()
        return w

    def create_drawing_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        box = QGroupBox("Mặc Định Công Cụ Vẽ & Ghi Chú")
        form = QFormLayout(box)
        form.setSpacing(10)

        self.spin_pen_width = QSpinBox()
        self.spin_pen_width.setRange(1, 15)
        self.spin_pen_width.setValue(self.cfg.get("default_pen_width", 3))
        form.addRow("Độ dày nét bút (px):", self.spin_pen_width)

        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(8, 48)
        self.spin_font_size.setValue(self.cfg.get("default_font_size", 16))
        form.addRow("Kích thước chữ mặc định (pt):", self.spin_font_size)

        color_layout = QHBoxLayout()
        self.txt_color = QLineEdit(self.cfg.get("default_color", "#FF3344"))
        self.txt_color.setFixedWidth(100)
        btn_pick_color = QPushButton("Chọn Màu")
        btn_pick_color.clicked.connect(self.pick_default_color)
        color_layout.addWidget(self.txt_color)
        color_layout.addWidget(btn_pick_color)
        color_layout.addStretch()
        form.addRow("Màu sắc mặc định:", color_layout)

        layout.addWidget(box)
        layout.addStretch()
        return w

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu mặc định", self.txt_save_dir.text())
        if folder:
            self.txt_save_dir.setText(folder)

    def pick_default_color(self):
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(QColor(self.txt_color.text()), self, "Chọn màu mặc định")
        if color.isValid():
            self.txt_color.setText(color.name().upper())

    def save_and_close(self):
        entered_key = self.txt_gemini_key.text().strip()
        if not entered_key or entered_key == app_config.DEFAULT_GEMINI_API_KEY:
            self.cfg["gemini_api_key"] = ""
        else:
            self.cfg["gemini_api_key"] = entered_key
        self.cfg["gemini_model"] = self.cb_gemini_model.currentData()
        self.cfg["use_ai_for_default_translate"] = self.chk_use_ai_translate.isChecked()

        self.cfg["hotkey_capture"] = self.cb_hotkey_cap.currentText().strip().lower()
        self.cfg["hotkey_translate"] = self.cb_hotkey_trans.currentText().strip().lower()
        self.cfg["hotkey_ai"] = self.cb_hotkey_ai.currentText().strip().lower()
        self.cfg["show_floating_bar"] = self.chk_show_floating_bar.isChecked()

        auto_start = self.chk_auto_start.isChecked()
        self.cfg["auto_start"] = auto_start
        app_config.set_run_on_startup(auto_start)

        self.cfg["save_dir"] = self.txt_save_dir.text().strip()
        self.cfg["save_format"] = self.cb_format.currentText()
        self.cfg["auto_copy_after_save"] = self.chk_autocopy.isChecked()
        self.cfg["default_pen_width"] = self.spin_pen_width.value()
        self.cfg["default_font_size"] = self.spin_font_size.value()
        self.cfg["default_color"] = self.txt_color.text().strip()

        app_config.save_config(self.cfg)
        self.settings_saved.emit()
        self.accept()

    def closeEvent(self, event):
        if self.test_worker:
            self.test_worker.cancel()
        super().closeEvent(event)
