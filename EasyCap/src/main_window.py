from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen

CAPSULE_STYLE = """
QWidget#DynamicIsland {
    background-color: rgba(14, 18, 27, 0.92);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 22px;
}
QLabel#LogoTag {
    color: #F8FAFC;
    font-size: 13px;
    font-weight: 800;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', -apple-system, sans-serif;
    letter-spacing: 0.5px;
    padding-left: 6px;
    padding-right: 4px;
}
QLabel#DotGlow {
    color: #38BDF8;
    font-size: 16px;
}
QPushButton {
    background-color: rgba(255, 255, 255, 0.05);
    color: #CBD5E1;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 15px;
    padding: 5px 12px;
    font-size: 12px;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
    font-weight: 600;
}
QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.12);
    border-color: rgba(255, 255, 255, 0.22);
    color: #FFFFFF;
}
QPushButton:pressed {
    background-color: rgba(255, 255, 255, 0.18);
}
QPushButton#PrimaryCapBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #06B6D4);
    color: #FFFFFF;
    border: none;
    font-weight: 700;
}
QPushButton#PrimaryCapBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369A1, stop:1 #0891B2);
}
QPushButton#AIGlowBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:0.5 #8B5CF6, stop:1 #EC4899);
    color: #FFFFFF;
    border: none;
    font-weight: 700;
    padding: 5px 14px;
}
QPushButton#AIGlowBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:0.5 #7C3AED, stop:1 #DB2777);
}
QPushButton#IconOnlyBtn {
    padding: 4px 8px;
    border: none;
    background: transparent;
    color: #64748B;
    font-size: 13px;
    border-radius: 14px;
}
QPushButton#IconOnlyBtn:hover {
    background-color: rgba(255, 255, 255, 0.1);
    color: #F8FAFC;
}
QPushButton#CloseBtn {
    padding: 4px 8px;
    border: none;
    background: transparent;
    color: #64748B;
    font-size: 13px;
    border-radius: 14px;
}
QPushButton#CloseBtn:hover {
    background-color: rgba(239, 68, 68, 0.18);
    color: #F87171;
}
"""

class MainControlBar(QWidget):
    """
    Thanh điều khiển Dynamic Island siêu tinh gọn, hiện đại và chuẩn Gen Z
    """
    capture_clicked = pyqtSignal()
    translate_clicked = pyqtSignal()
    ai_clicked = pyqtSignal()
    open_file_clicked = pyqtSignal()
    file_dropped = pyqtSignal(str)
    settings_clicked = pyqtSignal()
    minimize_clicked = pyqtSignal()
    close_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DynamicIsland")
        self.setStyleSheet(CAPSULE_STYLE)
        self.setFixedHeight(44)
        self.setAcceptDrops(True)
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        self.drag_position = QPoint()
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 8, 4)
        layout.setSpacing(6)

        # Dot + Logo
        dot = QLabel("●")
        dot.setObjectName("DotGlow")
        layout.addWidget(dot)

        logo = QLabel("Myshot")
        logo.setObjectName("LogoTag")
        layout.addWidget(logo)

        # Ngăn cách mỏng
        sep0 = QFrame()
        sep0.setFrameShape(QFrame.Shape.VLine)
        sep0.setStyleSheet("background-color: rgba(255, 255, 255, 0.1);")
        sep0.setFixedWidth(1)
        sep0.setFixedHeight(18)
        layout.addWidget(sep0)

        # 1. Chụp màn hình (F3)
        self.btn_cap = QPushButton("📸 Chụp [F3]")
        self.btn_cap.setToolTip("Chụp màn hình & vẽ ghi chú (F3)")
        self.btn_cap.clicked.connect(self.capture_clicked.emit)
        layout.addWidget(self.btn_cap)

        # 2. Dịch nhanh (F4)
        self.btn_trans = QPushButton("🌐 Dịch [F4]")
        self.btn_trans.setObjectName("PrimaryCapBtn")
        self.btn_trans.setToolTip("Khoanh vùng dịch sang tiếng Việt (F4)")
        self.btn_trans.clicked.connect(self.translate_clicked.emit)
        layout.addWidget(self.btn_trans)

        # 3. Trợ lý AI Gemini (F9) - Gradient sắc màu nổi bật
        self.btn_ai = QPushButton("✨ AI [F9]")
        self.btn_ai.setObjectName("AIGlowBtn")
        self.btn_ai.setToolTip("Trợ lý AI Gemini: Dịch ngữ cảnh, Tóm tắt, Phân tích & Chat với ảnh (F9)")
        self.btn_ai.clicked.connect(self.ai_clicked.emit)
        layout.addWidget(self.btn_ai)

        # 4. Dịch từ File tài liệu & ảnh (Ctrl+O)
        self.btn_open_file = QPushButton("📁 File")
        self.btn_open_file.setToolTip("Dịch file tài liệu (Excel, Word, PowerPoint, PDF) hoặc file ảnh (Ctrl+O) - Kéo thả file vào đây")
        self.btn_open_file.clicked.connect(self.open_file_clicked.emit)
        layout.addWidget(self.btn_open_file)

        # Ngăn cách mỏng
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("background-color: rgba(255, 255, 255, 0.1);")
        sep1.setFixedWidth(1)
        sep1.setFixedHeight(18)
        layout.addWidget(sep1)

        # 4. Cài đặt
        self.btn_settings = QPushButton("⚙️")
        self.btn_settings.setObjectName("IconOnlyBtn")
        self.btn_settings.setToolTip("Cài đặt API Key, Phím tắt, Lưu ảnh...")
        self.btn_settings.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.btn_settings)

        # 5. Thu nhỏ
        btn_min = QPushButton("─")
        btn_min.setObjectName("IconOnlyBtn")
        btn_min.setToolTip("Thu nhỏ xuống khay hệ thống")
        btn_min.clicked.connect(self.minimize_clicked.emit)
        layout.addWidget(btn_min)

        # 6. Thu gọn / Đóng thanh nổi
        btn_close = QPushButton("✕")
        btn_close.setObjectName("CloseBtn")
        btn_close.setToolTip("Thu gọn xuống khay hệ thống (phím tắt vẫn hoạt động)")
        btn_close.clicked.connect(self.close_clicked.emit)
        layout.addWidget(btn_close)

        self.adjustSize()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def dragEnterEvent(self, event):
        SUPPORTED_EXTS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.xlsx', '.xlsm', '.docx', '.pptx', '.pdf')
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                fpath = url.toLocalFile().lower()
                if fpath.endswith(SUPPORTED_EXTS):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        SUPPORTED_EXTS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.xlsx', '.xlsm', '.docx', '.pptx', '.pdf')
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                fpath = url.toLocalFile()
                if fpath.lower().endswith(SUPPORTED_EXTS):
                    self.file_dropped.emit(fpath)
                    event.acceptProposedAction()
                    return
