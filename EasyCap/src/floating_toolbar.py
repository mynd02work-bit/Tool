from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QColorDialog,
    QFrame, QMenu, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRectF
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QAction, QPainterPath

from line_icons import LineIconButton
from ai_engine import SUPPORTED_TARGET_LANGUAGES, get_target_lang_display_name

UNIFIED_TOOLBAR_STYLE = """
QWidget#UnifiedToolbar {
    background-color: rgba(13, 17, 26, 0.98);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 16px;
}
QPushButton {
    background-color: rgba(255, 255, 255, 0.05);
    color: #CBD5E1;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    font-size: 11px;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, sans-serif;
    font-weight: 600;
    padding: 3px 10px;
    min-height: 24px;
}
QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.13);
    border-color: rgba(255, 255, 255, 0.22);
    color: #FFFFFF;
}
QPushButton#AIPillBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:1 #8B5CF6);
    color: #FFFFFF;
    border: none;
    font-weight: 700;
    padding: 3px 12px;
}
QPushButton#AIPillBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED);
}
QPushButton#TranslatePillBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #06B6D4);
    color: #FFFFFF;
    border: none;
    font-weight: 700;
    padding: 3px 11px;
}
QPushButton#TranslatePillBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369A1, stop:1 #0891B2);
}
QPushButton#CancelPillBtn {
    background: transparent;
    color: #64748B;
    border: none;
    font-size: 13px;
    font-weight: bold;
    padding: 3px 8px;
}
QPushButton#CancelPillBtn:hover {
    background-color: rgba(239, 68, 68, 0.2);
    color: #F87171;
}
"""

DARK_MENU_STYLE = """
QMenu {
    background-color: #0F172A;
    color: #F8FAFC;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 12px;
    padding: 6px;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, sans-serif;
    font-size: 12px;
    font-weight: 500;
}
QMenu::item {
    padding: 7px 18px 7px 12px;
    border-radius: 8px;
    margin: 2px 2px;
}
QMenu::item:selected {
    background-color: #4F46E5;
    color: #FFFFFF;
}
QMenu::separator {
    height: 1px;
    background: rgba(255, 255, 255, 0.12);
    margin: 5px 6px;
}
"""

class ColorButton(QPushButton):
    color_chosen = pyqtSignal(QColor)

    def __init__(self, color=QColor("#FF3344"), parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color = color
        self.setFixedSize(26, 26)
        self.setToolTip("Chọn màu vẽ (Click chuột phải để chọn bảng màu nhanh)")

    def set_color(self, color):
        self.color = color
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.show_quick_palette(event.globalPosition().toPoint())
            return
        super().mousePressEvent(event)

    def show_quick_palette(self, pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet(DARK_MENU_STYLE)
        presets = [
            ("🔴 Đỏ tươi (#EF4444)", "#EF4444"),
            ("🟠 Cam rực (#F97316)", "#F97316"),
            ("🟡 Vàng tươi (#FACC15)", "#FACC15"),
            ("🟢 Xanh lá (#22C55E)", "#22C55E"),
            ("🔵 Xanh dương (#0EA5E9)", "#0EA5E9"),
            ("🟣 Tím Indigo (#6366F1)", "#6366F1"),
            ("⚪ Trắng tinh (#FFFFFF)", "#FFFFFF"),
            ("⚫ Đen tuyền (#0F172A)", "#0F172A"),
        ]
        for name, hex_code in presets:
            act = menu.addAction(name)
            act.triggered.connect(lambda checked, h=hex_code: self.choose_hex(h))

        menu.addSeparator()
        act_more = menu.addAction("🎨 Bảng màu chi tiết...")
        act_more.triggered.connect(self.choose_custom_color)
        menu.exec(pos)

    def choose_hex(self, hex_code: str):
        color = QColor(hex_code)
        self.set_color(color)
        self.color_chosen.emit(color)

    def choose_custom_color(self):
        color = QColorDialog.getColor(self.color, self, "Chọn màu vẽ")
        if color.isValid():
            self.set_color(color)
            self.color_chosen.emit(color)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(4, 4, -4, -4)
        painter.setBrush(QBrush(self.color))
        painter.setPen(QPen(QColor(255, 255, 255, 220), 1.5))
        painter.drawEllipse(rect)


class ActionPillButton(QPushButton):
    """
    Nút bấm pill có hỗ trợ chuột phải để cấu hình nhanh trực tiếp
    """
    right_clicked = pyqtSignal(QPoint)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(event.globalPosition().toPoint())
            return
        super().mousePressEvent(event)


class UnifiedFloatingToolbar(QWidget):
    """
    Thanh công cụ HỢP NHẤT duy nhất (Unified Toolbar) tích hợp cả nhóm vẽ (Drawing)
    và nhóm hành động (Actions + AI) trên cùng một thanh capsule tối giản, hiện đại.
    """
    tool_changed = pyqtSignal(str)
    color_changed = pyqtSignal(QColor)
    pen_width_changed = pyqtSignal(int)
    highlighter_width_changed = pyqtSignal(int)
    font_size_changed = pyqtSignal(int)
    badge_reset_requested = pyqtSignal(int)
    undo_requested = pyqtSignal()
    redo_requested = pyqtSignal()

    ai_requested = pyqtSignal()
    ai_mode_requested = pyqtSignal(str)
    translate_requested = pyqtSignal()
    cancel_overlay_requested = pyqtSignal()
    switch_mode_requested = pyqtSignal()
    dual_view_requested = pyqtSignal()
    target_lang_changed = pyqtSignal(str)
    copy_requested = pyqtSignal()
    save_requested = pyqtSignal()
    print_requested = pyqtSignal()
    cancel_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setObjectName("UnifiedToolbar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(UNIFIED_TOOLBAR_STYLE)
        self.setFixedWidth(72)
        self.setCursor(Qt.CursorShape.ArrowCursor)

        self.current_tool = "pencil"
        self.current_shape = "rect"
        self.current_pen_width = 3
        self.current_highlighter_width = 20
        self.current_font_size = 16
        self.target_lang = "vi"
        self.is_overlaid = False

        self.buttons = {}
        self.init_ui()

    def init_ui(self):
        # Thiết kế 2 cột cạnh nhau (2 Columns Grid) tinh gọn, giảm 50% chiều dài
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        # Cột 1 (Bên trái: Công cụ vẽ)
        col1 = QVBoxLayout()
        col1.setSpacing(4)
        col1.setContentsMargins(0, 0, 0, 0)

        # (a) Bút vẽ (Pencil)
        self.btn_pencil = LineIconButton("pencil", tooltip="Bút vẽ tự do (P) - Chuột phải chỉnh nét", size=28, has_submenu=True, parent=self)
        self.btn_pencil.clicked.connect(lambda: self.select_tool("pencil"))
        self.btn_pencil.right_clicked.connect(self.show_pencil_menu)
        col1.addWidget(self.btn_pencil)
        self.buttons["pencil"] = self.btn_pencil

        # (b) HÌNH KHỐI (SHAPE)
        self.btn_shape = LineIconButton("rect", tooltip="Hình vẽ (R) - Click hoặc Chuột phải để chọn Đường thẳng, Mũi tên, Hình khối...", size=28, has_submenu=True, parent=self)
        self.btn_shape.clicked.connect(self.on_shape_clicked)
        self.btn_shape.right_clicked.connect(self.show_shape_menu)
        col1.addWidget(self.btn_shape)
        self.buttons["shape"] = self.btn_shape

        # (c) Dạ quang (Highlighter)
        self.btn_hl = LineIconButton("highlighter", tooltip="Bút dạ quang (H) - Chuột phải chỉnh cỡ", size=28, has_submenu=True, parent=self)
        self.btn_hl.clicked.connect(lambda: self.select_tool("highlighter"))
        self.btn_hl.right_clicked.connect(self.show_highlighter_menu)
        col1.addWidget(self.btn_hl)
        self.buttons["highlighter"] = self.btn_hl

        # (d) Văn bản (Text)
        self.btn_text = LineIconButton("text", tooltip="Văn bản chữ (T) - Chuột phải chỉnh cỡ font", size=28, has_submenu=True, parent=self)
        self.btn_text.clicked.connect(lambda: self.select_tool("text"))
        self.btn_text.right_clicked.connect(self.show_text_menu)
        col1.addWidget(self.btn_text)
        self.buttons["text"] = self.btn_text

        # (e) Số thứ tự (Step Badge)
        self.btn_badge = LineIconButton("badge", tooltip="Số thứ tự (N) - Chuột phải đặt lại số", size=28, has_submenu=True, parent=self)
        self.btn_badge.clicked.connect(lambda: self.select_tool("badge"))
        self.btn_badge.right_clicked.connect(self.show_badge_menu)
        col1.addWidget(self.btn_badge)
        self.buttons["badge"] = self.btn_badge

        # (f) Nút chọn màu
        self.color_btn = ColorButton(QColor("#FF3344"), self)
        self.color_btn.clicked.connect(self.color_btn.choose_custom_color)
        self.color_btn.color_chosen.connect(self.color_changed.emit)
        col1.addWidget(self.color_btn)

        # (g) Undo (ẩn nút trên toolbar, phím tắt Ctrl+Z vẫn hoạt động)
        self.btn_undo = LineIconButton("undo", tooltip="Hoàn tác (Ctrl + Z)", size=26, parent=self)
        self.btn_undo.clicked.connect(self.undo_requested.emit)
        self.btn_undo.hide()

        main_layout.addLayout(col1)

        # Vách ngăn dọc mỏng giữa 2 cột
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.12); max-width: 1px; margin: 3px 0px;")
        sep.setFixedWidth(1)
        main_layout.addWidget(sep)

        # Cột 2 (Bên phải: Tiện ích & Trợ lý AI)
        col2 = QVBoxLayout()
        col2.setSpacing(4)
        col2.setContentsMargins(0, 0, 0, 0)

        # (h) Redo (ẩn nút trên toolbar, phím tắt Ctrl+Y vẫn hoạt động)
        self.btn_redo = LineIconButton("redo", tooltip="Làm lại (Ctrl + Y)", size=26, parent=self)
        self.btn_redo.clicked.connect(self.redo_requested.emit)
        self.btn_redo.hide()

        # (i) Nút Trợ lý AI & Dịch thuật
        self.btn_ai = LineIconButton("sparkle", tooltip="Trợ lý AI & Dịch thuật (F4 / F9) - Chuột phải chọn tác vụ", size=28, has_submenu=True, parent=self)
        self.btn_ai.clicked.connect(self.on_ai_clicked)
        self.btn_ai.right_clicked.connect(self.show_ai_menu)
        col2.addWidget(self.btn_ai)
        self.btn_translate = self.btn_ai

        # (j) Copy
        self.btn_copy = LineIconButton("copy", tooltip="Sao chép vào Clipboard (Ctrl + C)", size=28, parent=self)
        self.btn_copy.clicked.connect(self.copy_requested.emit)
        col2.addWidget(self.btn_copy)

        # (k) Lưu ảnh
        self.btn_save = LineIconButton("save", tooltip="Lưu ảnh (Ctrl + S)", size=28, parent=self)
        self.btn_save.clicked.connect(self.save_requested.emit)
        col2.addWidget(self.btn_save)

        # (l) In
        self.btn_print = LineIconButton("print", tooltip="In ảnh (Ctrl + P)", size=28, parent=self)
        self.btn_print.clicked.connect(self.print_requested.emit)
        col2.addWidget(self.btn_print)

        # (m) Đóng / Hủy
        self.btn_cancel = LineIconButton("close", tooltip="Hủy chụp / Thoát (Esc)", size=28, parent=self)
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        col2.addWidget(self.btn_cancel)

        # (n) Cục tẩy / Cục bôi (Eraser) - Xóa shape, kéo rê để xóa nhiều, số thứ tự tự giảm
        self.btn_eraser = LineIconButton("eraser", tooltip="Cục tẩy / Bôi xóa (E) - Click hoặc kéo chuột qua shape để xóa", size=28, parent=self)
        self.btn_eraser.clicked.connect(lambda: self.select_tool("eraser"))
        col2.addWidget(self.btn_eraser)
        self.buttons["eraser"] = self.btn_eraser

        main_layout.addLayout(col2)

        self.select_tool("pencil")
        self.adjustSize()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)
        painter.fillPath(path, QColor(13, 17, 26, 252))
        painter.setPen(QPen(QColor(255, 255, 255, 45), 1.2))
        painter.drawPath(path)

    # --- Tool Selection Logic ---

    def select_tool(self, tool_id: str):
        self.current_tool = tool_id

        # Mapped key cho nút Shape
        shape_types = ("rect", "rect_fill", "ellipse", "ellipse_fill", "triangle", "trapezoid", "parallelogram", "line", "arrow", "double_arrow", "blur")
        if tool_id in shape_types:
            self.current_shape = tool_id
            active_btn_key = "shape"
        else:
            active_btn_key = tool_id

        for tid, btn in self.buttons.items():
            btn.set_active(tid == active_btn_key)

        self.tool_changed.emit(tool_id)

    def on_shape_clicked(self):
        # Click vào nút Shape sẽ dùng luôn shape hiện tại
        self.select_tool(self.current_shape)

    # --- Shape Menu: Tích hợp Đường thẳng, Mũi tên, Hình chữ nhật, Hình tròn, v.v. ---

    def show_shape_menu(self, pos_f):
        pos = pos_f.toPoint() if hasattr(pos_f, 'toPoint') else pos_f
        menu = QMenu(self)
        menu.setStyleSheet(DARK_MENU_STYLE)

        shapes = [
            ("🔲 Khung chữ nhật rỗng (R)", "rect", "Khung chữ nhật rỗng"),
            ("⬛ Hình chữ nhật đặc (Fill)", "rect_fill", "Hình chữ nhật có màu nền"),
            ("🔺 Hình tam giác (Triangle)", "triangle", "Hình tam giác"),
            ("⏢ Hình thang cân (Trapezoid)", "trapezoid", "Hình thang cân"),
            ("▰ Hình bình hành (Parallelogram)", "parallelogram", "Hình bình hành"),
            ("⭕ Hình tròn / Elip rỗng", "ellipse", "Hình tròn hoặc elip rỗng"),
            ("🔴 Hình tròn đặc (Fill)", "ellipse_fill", "Hình tròn đặc màu"),
            ("➡️ Mũi tên đơn (Arrow)", "arrow", "Mũi tên đơn"),
            ("↔️ Mũi tên 2 đầu", "double_arrow", "Mũi tên hai đầu"),
            ("➖ Đoạn thẳng (Line)", "line", "Đoạn thẳng"),
            ("🏁 Che mờ thông tin (Blur)", "blur", "Làm mờ / Che nội dung nhạy cảm"),
        ]

        for label, sid, tip in shapes:
            act = menu.addAction(label)
            if self.current_shape == sid:
                act.setText(f"✓ {label}")
            act.triggered.connect(lambda checked, s=sid, t=tip: self.apply_shape(s, t))

        menu.exec(pos)

    def apply_shape(self, shape_id: str, tooltip: str):
        self.current_shape = shape_id
        # Đổi icon đại diện trên nút Shape
        self.btn_shape.set_icon_type(shape_id, f"{tooltip} (Chuột phải đổi dạng)")
        self.select_tool(shape_id)

    # --- Các Menu Chuột Phải Cho Từng Công Cụ ---

    def show_pencil_menu(self, pos_f):
        pos = pos_f.toPoint() if hasattr(pos_f, 'toPoint') else pos_f
        menu = QMenu(self)
        menu.setStyleSheet(DARK_MENU_STYLE)

        widths = [
            ("1px (Rất mảnh)", 1),
            ("2px (Mảnh)", 2),
            ("3px (Chuẩn - Mặc định)", 3),
            ("5px (Dày)", 5),
            ("8px (Rất đậm)", 8),
        ]
        for label, w in widths:
            act = menu.addAction(label)
            if w == self.current_pen_width:
                act.setText(f"✓ {label}")
            act.triggered.connect(lambda checked, width=w: self.set_pen_width(width))

        menu.exec(pos)

    def set_pen_width(self, width: int):
        self.current_pen_width = width
        self.pen_width_changed.emit(width)
        self.select_tool("pencil")

    def show_highlighter_menu(self, pos_f):
        pos = pos_f.toPoint() if hasattr(pos_f, 'toPoint') else pos_f
        menu = QMenu(self)
        menu.setStyleSheet(DARK_MENU_STYLE)

        widths = [
            ("12px (Bút dạ mảnh)", 12),
            ("20px (Bút dạ chuẩn)", 20),
            ("32px (Bút dạ bản to)", 32),
        ]
        for label, w in widths:
            act = menu.addAction(label)
            if w == self.current_highlighter_width:
                act.setText(f"✓ {label}")
            act.triggered.connect(lambda checked, width=w: self.set_highlighter_width(width))

        menu.exec(pos)

    def set_highlighter_width(self, width: int):
        self.current_highlighter_width = width
        self.highlighter_width_changed.emit(width)
        self.select_tool("highlighter")

    def show_text_menu(self, pos_f):
        pos = pos_f.toPoint() if hasattr(pos_f, 'toPoint') else pos_f
        menu = QMenu(self)
        menu.setStyleSheet(DARK_MENU_STYLE)

        sizes = [
            ("12pt (Chữ nhỏ)", 12),
            ("16pt (Chữ chuẩn)", 16),
            ("20pt (Chữ lớn)", 20),
            ("28pt (Tiêu đề lớn)", 28),
        ]
        for label, s in sizes:
            act = menu.addAction(label)
            if s == self.current_font_size:
                act.setText(f"✓ {label}")
            act.triggered.connect(lambda checked, sz=s: self.set_font_size(sz))

        menu.exec(pos)

    def set_font_size(self, size: int):
        self.current_font_size = size
        self.font_size_changed.emit(size)
        self.select_tool("text")

    def show_badge_menu(self, pos_f):
        pos = pos_f.toPoint() if hasattr(pos_f, 'toPoint') else pos_f
        menu = QMenu(self)
        menu.setStyleSheet(DARK_MENU_STYLE)

        act1 = menu.addAction("🔄 Đặt lại số thứ tự về 1")
        act1.triggered.connect(lambda: self.badge_reset_requested.emit(1))

        act0 = menu.addAction("🔄 Đặt lại số thứ tự về 0")
        act0.triggered.connect(lambda: self.badge_reset_requested.emit(0))

        menu.addSeparator()
        act_custom = menu.addAction("🔢 Nhập số bắt đầu tùy chỉnh...")
        act_custom.triggered.connect(self.ask_custom_badge_number)

        menu.exec(pos)

    def ask_custom_badge_number(self):
        val, ok = QInputDialog.getInt(self, "Số Thứ Tự", "Bắt đầu đánh số từ:", 1, 0, 9999)
        if ok:
            self.badge_reset_requested.emit(val)

    def set_color(self, color: QColor):
        self.color_btn.set_color(color)

    def on_ai_clicked(self):
        if self.is_overlaid:
            self.cancel_overlay_requested.emit()
        else:
            self.ai_requested.emit()

    def set_overlay_state(self, is_overlaid: bool):
        self.is_overlaid = is_overlaid
        if is_overlaid:
            self.btn_ai.setText("↩")
            self.btn_ai.setToolTip("Khôi phục ảnh gốc (Hủy ghi đè) | Phím Tab: Đổi kiểu đè")
            self.btn_ai.setStyleSheet("""
                QPushButton#AIPillBtn {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #DC2626, stop:1 #EF4444);
                    color: #FFFFFF;
                    border: 1px solid #F87171;
                    border-radius: 8px;
                    font-weight: 700;
                    font-size: 13px;
                    padding: 0px;
                }
                QPushButton#AIPillBtn:hover {
                    background: #B91C1C;
                }
            """)
        else:
            self.btn_ai.setText("✦")
            self.btn_ai.setToolTip("Trợ lý AI & Dịch thuật (F4 / F9) - Chuột phải chọn tác vụ")
            self.btn_ai.setStyleSheet("""
                QPushButton#AIPillBtn {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366F1, stop:1 #8B5CF6);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                    font-weight: 700;
                    font-size: 13px;
                    padding: 0px;
                }
                QPushButton#AIPillBtn:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4F46E5, stop:1 #7C3AED);
                }
            """)

    def show_ai_menu(self, pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet(DARK_MENU_STYLE)

        if self.is_overlaid:
            act_cancel = menu.addAction("↩️ Về ảnh gốc (Tab)")
            act_cancel.triggered.connect(self.cancel_overlay_requested.emit)
            menu.addSeparator()
        else:
            act_trans = menu.addAction("🔤 Dịch đè theo vị trí (Tab)")
            act_trans.triggered.connect(self.ai_requested.emit)
            menu.addSeparator()

        modes = [
            ("🌐 Dịch ngữ cảnh AI (F4)", "translate"),
            ("⚡ Tóm tắt nội dung chính", "summary"),
            ("📊 Phân tích & Infographic", "explain"),
            ("💬 Hỏi đáp & Trò chuyện với ảnh (F9)", "chat"),
        ]
        for label, m in modes:
            act = menu.addAction(label)
            act.triggered.connect(lambda checked, mode=m: self.ai_mode_requested.emit(mode))

        menu.addSeparator()

        # Menu con: Chọn ngôn ngữ đích
        curr_lang_name = get_target_lang_display_name(self.target_lang)
        lang_menu = menu.addMenu(f"🌐 Dịch sang: {curr_lang_name}")
        lang_menu.setStyleSheet(DARK_MENU_STYLE)
        for code, name in SUPPORTED_TARGET_LANGUAGES:
            act_l = lang_menu.addAction(name)
            if code.lower() == self.target_lang.lower():
                act_l.setText(f"✓ {name}")
            act_l.triggered.connect(lambda checked, c=code: self.change_target_lang(c))

        menu.exec(pos)

    def change_target_lang(self, code: str):
        self.target_lang = code
        self.target_lang_changed.emit(code)

    def show_translate_menu(self, pos: QPoint):
        self.show_ai_menu(pos)


# Backward compatibility aliases
VerticalEditToolbar = UnifiedFloatingToolbar
HorizontalActionToolbar = UnifiedFloatingToolbar
