import subprocess
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser,
    QPushButton, QFrame, QApplication, QTabWidget, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

CARD_STYLE = """
QWidget#TranslationCard {
    background-color: rgba(13, 17, 26, 0.96);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 20px;
}
QTabWidget::pane {
    border: 1px solid rgba(255, 255, 255, 0.08);
    background-color: rgba(20, 26, 38, 0.6);
    border-radius: 12px;
}
QTabBar::tab {
    background-color: transparent;
    color: #94A3B8;
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
    margin-right: 4px;
}
QTabBar::tab:hover {
    color: #FFFFFF;
    background-color: rgba(255, 255, 255, 0.06);
}
QTabBar::tab:selected {
    background: rgba(56, 189, 248, 0.15);
    color: #38BDF8;
}
QTextBrowser, QTextEdit {
    background-color: transparent;
    color: #F8FAFC;
    border: none;
    padding: 10px 14px;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
    line-height: 1.65;
}
QPushButton#ActionButton {
    background-color: rgba(255, 255, 255, 0.05);
    color: #94A3B8;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 5px 12px;
    font-size: 11px;
    font-weight: 600;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', Arial;
}
QPushButton#ActionButton:hover {
    background-color: rgba(255, 255, 255, 0.12);
    color: #FFFFFF;
}
QPushButton#PrimaryButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #06B6D4);
    color: #FFFFFF;
    border: none;
    border-radius: 12px;
    padding: 5px 14px;
    font-size: 11px;
    font-weight: bold;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', Arial;
}
QPushButton#PrimaryButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369A1, stop:1 #0891B2);
}
QPushButton#CloseBtn {
    background: transparent;
    color: #64748B;
    border: none;
    font-size: 14px;
    font-weight: bold;
    border-radius: 12px;
}
QPushButton#CloseBtn:hover {
    color: #F87171;
    background-color: rgba(239, 68, 68, 0.18);
}
QPushButton#SizeBtn {
    background-color: rgba(255, 255, 255, 0.05);
    color: #94A3B8;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    font-weight: bold;
    font-size: 11px;
    padding: 2px 7px;
    min-width: 22px;
}
QPushButton#SizeBtn:hover {
    color: #FFFFFF;
    background-color: #0284C7;
}
"""

class TranslationCard(QWidget):
    """
    Thẻ Đọc Dịch Thuật Nhanh siêu tinh gọn, hiện đại và chuẩn Gen Z
    """
    overlay_requested = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TranslationCard")
        self.setStyleSheet(CARD_STYLE)
        self.setFixedSize(560, 380)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.current_font_size = 13
        self.is_overlaid = False
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        header.setSpacing(6)

        title_lbl = QLabel("🌐 Bản Dịch Nhanh")
        title_lbl.setStyleSheet("color: #38BDF8; font-weight: 800; font-size: 13px; font-family: 'Segoe UI Variable Display', 'Segoe UI';")
        header.addWidget(title_lbl)

        self.lang_badge = QLabel("Tiếng Anh ➔ Tiếng Việt")
        self.lang_badge.setStyleSheet("""
            background-color: rgba(56, 189, 248, 0.12);
            color: #38BDF8;
            border-radius: 9px;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: 700;
        """)
        header.addWidget(self.lang_badge)
        header.addStretch()

        # Nút điều chỉnh cỡ chữ A- và A+
        lbl_size = QLabel("Cỡ chữ:")
        lbl_size.setStyleSheet("color: #64748B; font-size: 11px;")
        header.addWidget(lbl_size)

        btn_font_minus = QPushButton("A-")
        btn_font_minus.setObjectName("SizeBtn")
        btn_font_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_font_minus.clicked.connect(lambda: self.change_font_size(-1))
        header.addWidget(btn_font_minus)

        btn_font_plus = QPushButton("A+")
        btn_font_plus.setObjectName("SizeBtn")
        btn_font_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_font_plus.clicked.connect(lambda: self.change_font_size(1))
        header.addWidget(btn_font_plus)

        # Nút đóng
        close_btn = QPushButton("✕")
        close_btn.setObjectName("CloseBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close_card)
        header.addWidget(close_btn)
        main_layout.addLayout(header)

        # Trạng thái
        self.status_lbl = QLabel("Đang nhận diện chữ và dịch...")
        self.status_lbl.setStyleSheet("color: #FCD34D; font-size: 11px; font-weight: 500;")
        main_layout.addWidget(self.status_lbl)

        # Tabs
        self.tabs = QTabWidget()
        
        # Tab 1: Đọc Bản Dịch
        self.tab_reading = QWidget()
        tab1_layout = QVBoxLayout(self.tab_reading)
        tab1_layout.setContentsMargins(4, 4, 4, 4)
        
        self.txt_translated = QTextBrowser()
        self.txt_translated.setOpenExternalLinks(False)
        self.txt_translated.setCursor(Qt.CursorShape.ArrowCursor)
        self.txt_translated.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        self.update_font()
        tab1_layout.addWidget(self.txt_translated)
        self.tabs.addTab(self.tab_reading, "📖 Bản Dịch Tiếng Việt")

        # Tab 2: So Sánh Đối Chiếu
        self.tab_compare = QWidget()
        tab2_layout = QHBoxLayout(self.tab_compare)
        tab2_layout.setContentsMargins(4, 4, 4, 4)
        tab2_layout.setSpacing(6)

        box_orig = QVBoxLayout()
        lbl_orig = QLabel("Văn bản gốc:")
        lbl_orig.setStyleSheet("color: #64748B; font-size: 11px; font-weight: bold;")
        box_orig.addWidget(lbl_orig)
        self.txt_original = QTextEdit()
        self.txt_original.setCursor(Qt.CursorShape.IBeamCursor)
        box_orig.addWidget(self.txt_original)
        tab2_layout.addLayout(box_orig)

        box_trans = QVBoxLayout()
        lbl_trans = QLabel("Bản dịch:")
        lbl_trans.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: bold;")
        box_trans.addWidget(lbl_trans)
        self.txt_compare_trans = QTextEdit()
        self.txt_compare_trans.setCursor(Qt.CursorShape.IBeamCursor)
        box_trans.addWidget(self.txt_compare_trans)
        tab2_layout.addLayout(box_trans)

        self.tabs.addTab(self.tab_compare, "📑 So Sánh Song Ngữ")
        main_layout.addWidget(self.tabs)

        # Bottom Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(6)

        self.btn_copy = QPushButton("📋 Copy")
        self.btn_copy.setObjectName("ActionButton")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.clicked.connect(self.copy_translation)
        bottom_bar.addWidget(self.btn_copy)

        bottom_bar.addStretch()

        self.btn_overlay = QPushButton("🔤 Đè lên ảnh")
        self.btn_overlay.setObjectName("PrimaryButton")
        self.btn_overlay.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_overlay.clicked.connect(self.overlay_requested.emit)
        bottom_bar.addWidget(self.btn_overlay)

        main_layout.addLayout(bottom_bar)

    def change_font_size(self, delta):
        self.current_font_size = max(11, min(22, self.current_font_size + delta))
        self.update_font()

    def update_font(self):
        font = QFont("Segoe UI Variable Text", self.current_font_size)
        self.txt_translated.setFont(font)
        if hasattr(self, 'txt_compare_trans'):
            self.txt_compare_trans.setFont(font)
            self.txt_original.setFont(font)

    def set_overlay_state(self, is_overlaid: bool):
        self.is_overlaid = is_overlaid
        if is_overlaid:
            self.btn_overlay.setText("↩️ Hủy ghi đè")
            self.btn_overlay.setToolTip("Khôi phục ảnh gốc (xóa các khối chữ dịch đè)")
            self.btn_overlay.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #DC2626, stop:1 #EF4444);
                    color: #FFFFFF;
                    border: 1px solid #F87171;
                    border-radius: 10px;
                    font-weight: 700;
                    font-size: 11px;
                    padding: 6px 14px;
                }
                QPushButton:hover {
                    background: #B91C1C;
                    border-color: #EF4444;
                }
            """)
        else:
            self.btn_overlay.setText("🔤 Đè lên ảnh")
            self.btn_overlay.setToolTip("Ghi đè chữ dịch trực tiếp lên ảnh chụp")
            self.btn_overlay.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #38BDF8);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 10px;
                    font-weight: 700;
                    font-size: 11px;
                    padding: 6px 14px;
                }
                QPushButton:hover {
                    background: #0369A1;
                }
            """)

    def set_loading(self, text="Đang nhận diện chữ và dịch..."):
        self.set_overlay_state(False)
        self.status_lbl.setText(f"⏳ {text}")
        self.status_lbl.setStyleSheet("color: #FCD34D; font-size: 11px; font-weight: 500;")
        self.status_lbl.show()
        self.txt_translated.setPlainText("")
        self.txt_original.setPlainText("")
        self.txt_compare_trans.setPlainText("")

    def set_data(self, original_text, translated_text):
        self.status_lbl.hide()
        formatted_translation = translated_text.replace("\n\n", "<br><br>").replace("\n", "<br>")
        html_content = f"""
        <div style="font-family: 'Segoe UI Variable Text', Arial; font-size: {self.current_font_size}pt; line-height: 1.65; color: #F8FAFC;">
            {formatted_translation}
        </div>
        """
        self.txt_translated.setHtml(html_content)
        self.txt_original.setPlainText(original_text)
        self.txt_compare_trans.setPlainText(translated_text)
        self.tabs.setCurrentIndex(0)

    def set_error(self, err_msg):
        self.status_lbl.setText(f"❌ {err_msg}")
        self.status_lbl.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: bold;")
        self.status_lbl.show()

    def copy_translation(self):
        text = self.txt_compare_trans.toPlainText() or self.txt_translated.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.btn_copy.setText("✓ Đã copy")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self.btn_copy.setText("📋 Copy"))

    def close_card(self):
        self.hide()
        self.closed.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close_card()
            event.accept()
            return
        super().keyPressEvent(event)
