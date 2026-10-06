import os
import io
import time
from datetime import datetime
from PIL import Image

from PyQt6.QtWidgets import (
    QWidget, QApplication, QFileDialog, QLineEdit, QLabel, QTextEdit, QPushButton,
    QHBoxLayout, QVBoxLayout, QFrame, QGraphicsDropShadowEffect
)
import threading
from PyQt6.QtCore import (
    Qt, QRect, QRectF, QPoint, QPointF, QSize, pyqtSignal, pyqtSlot, QObject, QTimer, QEvent
)
from PyQt6.QtGui import (
    QPainter, QPainterPath, QColor, QPen, QBrush, QFont, QFontMetrics, QPixmap, QImage,
    QCursor, QGuiApplication, QKeyEvent, QMouseEvent, QShortcut, QKeySequence,
    QTextCharFormat, QTextCursor
)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog

from canvas_elements import (
    PencilElement, HighlighterElement, LineElement, ArrowElement,
    RectElement, TextElement, StepBadgeElement, BlockOverlayElement,
    UnifiedSheetOverlayElement,
    FilledRectElement, EllipseElement, FilledEllipseElement,
    DoubleArrowElement, BlurElement,
    TriangleElement, TrapezoidElement, ParallelogramElement
)
from floating_toolbar import UnifiedFloatingToolbar, VerticalEditToolbar, HorizontalActionToolbar
from translation_card import TranslationCard
from ai_copilot_card import AICopilotCard
from ocr_translate import perform_ocr, translate_text
import config as app_config

HANDLE_SIZE = 8
HANDLE_NONE = 0
HANDLE_TL = 1
HANDLE_T = 2
HANDLE_TR = 3
HANDLE_R = 4
HANDLE_BR = 5
HANDLE_B = 6
HANDLE_BL = 7
HANDLE_L = 8
HANDLE_INSIDE = 9

def cluster_lines_into_blocks(lines):
    if not lines:
        return []

    valid_lines = [l for l in lines if len(l.get("text", "").strip()) >= 1 and l.get('w', 0) >= 4 and l.get('h', 0) >= 4]
    if not valid_lines:
        return []

    # Sắp xếp các dòng theo cột trước (x theo cụm), sau đó theo thứ tự y từ trên xuống
    sorted_lines = sorted(valid_lines, key=lambda l: (round(l.get('x', 0) / 70.0), l.get('y', 0)))

    # Gom các dòng thuộc cùng một đoạn văn bản hoặc tiêu đề
    groups = []
    curr_g = [sorted_lines[0]]

    for l in sorted_lines[1:]:
        prev = curr_g[-1]
        prev_h = prev.get('h', 16)
        gap_y = l.get('y', 0) - (prev.get('y', 0) + prev_h)

        prev_r = prev.get('x', 0) + prev.get('w', 0)
        l_r = l.get('x', 0) + l.get('w', 0)
        overlap = min(prev_r, l_r) - max(prev.get('x', 0), l.get('x', 0))
        is_same_col = abs(l.get('x', 0) - prev.get('x', 0)) <= max(35.0, prev.get('w', 40) * 0.35) or (overlap >= min(prev.get('w', 40), l.get('w', 40)) * 0.40)
        is_tight_gap = (-prev_h * 0.4 <= gap_y <= prev_h * 1.55)

        if is_same_col and is_tight_gap:
            curr_g.append(l)
        else:
            groups.append(curr_g)
            curr_g = [l]

    if curr_g:
        groups.append(curr_g)

    all_blocks = []
    for g in groups:
        min_x = min(item['x'] for item in g)
        min_y = min(item['y'] for item in g)
        max_x = max(item['x'] + item['w'] for item in g)
        max_y = max(item['y'] + item['h'] for item in g)
        combined_text = " ".join(item['text'].strip() for item in g).strip()
        if not combined_text:
            continue
        all_blocks.append({
            "x": float(min_x),
            "y": float(min_y),
            "w": float(max_x - min_x),
            "h": float(max_y - min_y),
            "num_lines": len(g),
            "avg_line_h": float((max_y - min_y) / max(1, len(g))),
            "original": combined_text,
            "translated": ""
        })
    return all_blocks

def sample_block_colors(cropped_img, x, y, w, h):
    """
    Trích xuất màu nền (background) và màu chữ (text) của khối văn bản từ ảnh chụp
    để bản dịch đè lên có màu sắc tệp 100% với ảnh gốc.
    """
    try:
        cw, ch = cropped_img.size
        x1 = max(0, int(x - 2))
        y1 = max(0, int(y - 2))
        x2 = min(cw, int(x + w + 2))
        y2 = min(ch, int(y + h + 2))

        if x2 <= x1 or y2 <= y1:
            return QColor(255, 255, 255), QColor(17, 24, 39), False

        crop = cropped_img.crop((x1, y1, x2, y2)).convert("RGB")
        try:
            import numpy as np
            arr = np.array(crop)
            ch_h, ch_w, _ = arr.shape
            if ch_h >= 2 and ch_w >= 2:
                # 1. Màu nền: Lấy median các pixel ở 4 cạnh rìa ngoài của khung chữ
                border_pixels = np.concatenate([
                    arr[0, :, :],
                    arr[-1, :, :],
                    arr[:, 0, :],
                    arr[:, -1, :]
                ], axis=0)
                bg_rgb = np.median(border_pixels, axis=0).astype(int)

                # Kiểm tra độ biến thiên màu sắc:
                # Nếu > 40% pixel biên gần với màu nền median (khoảng cách màu <= 28.0) -> Là vùng văn bản nền đồng nhất
                # Nếu < 40% pixel biên gần với màu nền median -> Là vùng ảnh chụp/quần áo/khuôn mặt có vân phức tạp
                diffs_border = np.linalg.norm(border_pixels - bg_rgb, axis=1)
                pct_near_bg = float(np.mean(diffs_border <= 28.0))
                is_photo = (pct_near_bg < 0.40)

                # 2. Màu chữ: Tìm các pixel có độ lệch màu cao nhất so với màu nền
                diff = np.linalg.norm(arr - bg_rgb, axis=2)
                p85 = np.percentile(diff, 85)
                text_mask = diff >= max(p85, 30.0)

                if np.any(text_mask):
                    text_rgb = np.median(arr[text_mask], axis=0).astype(int)
                else:
                    lum = 0.299 * bg_rgb[0] + 0.587 * bg_rgb[1] + 0.114 * bg_rgb[2]
                    text_rgb = np.array([0, 0, 0]) if lum > 128 else np.array([255, 255, 255])

                # Đảm bảo độ tương phản rõ ràng giữa màu chữ và màu nền
                bg_lum = 0.299 * bg_rgb[0] + 0.587 * bg_rgb[1] + 0.114 * bg_rgb[2]
                txt_lum = 0.299 * text_rgb[0] + 0.587 * text_rgb[1] + 0.114 * text_rgb[2]
                if abs(bg_lum - txt_lum) < 40:
                    text_rgb = np.array([17, 24, 39]) if bg_lum > 128 else np.array([245, 245, 245])

                return QColor(int(bg_rgb[0]), int(bg_rgb[1]), int(bg_rgb[2])), QColor(int(text_rgb[0]), int(text_rgb[1]), int(text_rgb[2])), is_photo
        except Exception:
            pass

        # Fallback lấy pixel biên không dùng numpy
        w_img, h_img = crop.size
        border_pts = []
        step_x = max(1, w_img // 8)
        step_y = max(1, h_img // 8)
        for bx in range(0, w_img, step_x):
            border_pts.append(crop.getpixel((bx, 0)))
            border_pts.append(crop.getpixel((bx, h_img - 1)))
        for by in range(0, h_img, step_y):
            border_pts.append(crop.getpixel((0, by)))
            border_pts.append(crop.getpixel((w_img - 1, by)))

        if border_pts:
            avg_r = sum(p[0] for p in border_pts) // len(border_pts)
            avg_g = sum(p[1] for p in border_pts) // len(border_pts)
            avg_b = sum(p[2] for p in border_pts) // len(border_pts)
            bg_c = QColor(avg_r, avg_g, avg_b)
            lum = 0.299 * avg_r + 0.587 * avg_g + 0.114 * avg_b
            txt_c = QColor(0, 0, 0) if lum > 128 else QColor(255, 255, 255)
            return bg_c, txt_c, False

        return QColor(255, 255, 255), QColor(17, 24, 39), False
    except Exception:
        return QColor(255, 255, 255), QColor(17, 24, 39), False

def sample_dominant_theme(cropped_img):
    """
    Xác định màu nền tự nhiên và màu chữ từ ảnh chụp thực tế:
    - Lấy mẫu chính xác từ các pixel viền ngoài (border pixels) của vùng chụp.
    - Đảm bảo màu nền trùng khớp 100% với màu nền trang web/tài liệu của người dùng (trắng, kem, xám, đen...).
    """
    try:
        import numpy as np
        arr = np.array(cropped_img.convert("RGB"))
        h, w, _ = arr.shape

        if h >= 2 and w >= 2:
            # Lấy các pixel ở 4 cạnh viền ngoài cùng của vùng chọn (nơi là màu nền chuẩn)
            border_pixels = np.concatenate([
                arr[0, :, :],
                arr[-1, :, :],
                arr[:, 0, :],
                arr[:, -1, :]
            ], axis=0)
            bg_rgb = np.median(border_pixels, axis=0).astype(int)
            med_r, med_g, med_b = int(bg_rgb[0]), int(bg_rgb[1]), int(bg_rgb[2])
        else:
            med_r, med_g, med_b = 255, 255, 255

        lum = 0.299 * med_r + 0.587 * med_g + 0.114 * med_b
        is_dark = (lum < 135)

        # Màu nền chuẩn xác 100% từ trang web/tài liệu của người dùng
        bg_c = QColor(med_r, med_g, med_b, 255)

        # Màu chữ: Nếu nền sáng thì màu chữ đậm sắc nét (#18181B), nếu nền tối thì màu chữ sáng (#F8FAFC)
        txt_c = QColor(24, 24, 27) if not is_dark else QColor(248, 250, 252)
        banner_bg = bg_c

        return is_dark, bg_c, txt_c, banner_bg
    except Exception:
        return False, QColor(255, 255, 255, 255), QColor(24, 24, 27), QColor(255, 255, 255, 255)

class OCRTranslationWorker(QObject):
    finished_signal = pyqtSignal(dict)

    def __init__(self, pil_image, target_lang="vi"):
        super().__init__()
        self.pil_image = pil_image
        self.target_lang = target_lang
        self._is_cancelled = False
        self._thread = None

    def cancel(self):
        self._is_cancelled = True
        try:
            self.finished_signal.disconnect()
        except Exception:
            pass

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            ocr_res = perform_ocr(self.pil_image)
            if not ocr_res.get("success", False):
                if not self._is_cancelled:
                    self.finished_signal.emit({
                        "success": False,
                        "error": ocr_res.get("error", "Lỗi OCR"),
                        "original": "",
                        "translated": "",
                        "blocks": []
                    })
                return

            original_text = ocr_res.get("text", "")
            if not original_text.strip():
                if not self._is_cancelled:
                    self.finished_signal.emit({
                        "success": True,
                        "original": "(Không tìm thấy chữ trong vùng chọn)",
                        "translated": "",
                        "blocks": []
                    })
                return

            blocks = cluster_lines_into_blocks(ocr_res.get("lines", []))
            translated_blocks = []
            full_trans_parts = []
            for blk in blocks:
                if self._is_cancelled:
                    return
                trans = translate_text(blk['original'], target_lang=self.target_lang)
                blk['translated'] = trans
                translated_blocks.append(blk)
                full_trans_parts.append(trans)

            full_translation = "\n\n".join(full_trans_parts) if full_trans_parts else translate_text(original_text, target_lang=self.target_lang)

            if not self._is_cancelled:
                self.finished_signal.emit({
                    "success": True,
                    "original": original_text,
                    "translated": full_translation,
                    "blocks": translated_blocks
                })
        except Exception as e:
            if not self._is_cancelled:
                try:
                    self.finished_signal.emit({
                        "success": False,
                        "error": str(e),
                        "original": "",
                        "translated": "",
                        "blocks": []
                    })
                except Exception:
                    pass

class ToastNotification(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(13, 17, 26, 0.94);
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 16px;
                padding: 7px 16px;
                font-size: 12px;
                font-family: 'Segoe UI Variable Text', 'Segoe UI', Arial;
                font-weight: 700;
            }
        """)
        self.adjustSize()

def create_sniper_cross_cursor() -> QCursor:
    """
    Tạo con trỏ chuột chữ thập siêu tương phản (High-Contrast Sniper Crosshair):
    - Lõi trắng sáng tinh tế được bọc bởi viền đen xung quanh.
    - Đảm bảo trỏ chuột LUÔN LUÔN nhìn thấy 100% rõ ràng trên mọi hình nền (nền đen tuyền, nền trắng, nền xám hoặc nền ảnh phức tạp).
    """
    size = 29
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    center = size // 2

    # Viền đen bên ngoài (Shadow outline)
    pen_black = QPen(QColor(0, 0, 0, 240), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap)
    painter.setPen(pen_black)
    painter.drawLine(center, 3, center, size - 4)
    painter.drawLine(3, center, size - 4, center)

    # Lõi trắng bên trong (Crisp white center)
    pen_white = QPen(QColor(255, 255, 255, 255), 1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap)
    painter.setPen(pen_white)
    painter.drawLine(center, 4, center, size - 5)
    painter.drawLine(4, center, size - 5, center)

    # Tâm ngắm chính xác (Center dot)
    painter.fillRect(center - 1, center - 1, 3, 3, QColor(0, 0, 0, 240))
    painter.fillRect(center, center, 1, 1, QColor(255, 255, 255, 255))
    painter.end()

    return QCursor(pixmap, center, center)

def create_eraser_cursor():
    """Con trỏ cục tẩy vòng tròn chuyên nghiệp báo hiệu thao tác bôi xóa"""
    size = 20
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    center = size / 2.0
    r = 7.0
    # Vòng tròn viền xám tối, nền trắng đục
    painter.setPen(QPen(QColor(15, 23, 42, 220), 1.8))
    painter.setBrush(QBrush(QColor(255, 255, 255, 210)))
    painter.drawEllipse(QPointF(center, center), r, r)
    # Dấu x nhỏ màu hồng/đỏ chính giữa
    painter.setPen(QPen(QColor(239, 68, 68, 230), 1.5))
    d = 2.5
    painter.drawLine(QPointF(center - d, center - d), QPointF(center + d, center + d))
    painter.drawLine(QPointF(center - d, center + d), QPointF(center + d, center - d))
    painter.end()

    return QCursor(pixmap, int(center), int(center))

class FloatingRichTextEditor(QFrame):
    """
    Khung soạn thảo văn bản siêu tối giản:
    1. Không có thanh công cụ rườm rà (người dùng tự dùng Ctrl+B, Ctrl+I, Ctrl+U, Ctrl+Enter).
    2. Có icon mini ✥ và viền kéo để di chuyển tự do đến mọi vị trí.
    3. Hỗ trợ mở lại chữ đã có để sửa nội dung và di chuyển vị trí.
    4. Tự động co giãn kích thước ôm sát nội dung văn bản.
    """
    committed = pyqtSignal(str, str, QPointF)  # plain_text, html, text_pos
    cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.SubWindow)
        self._drag_start_pos = None
        self.current_color = QColor("#FF3344")
        self.current_font_size = 16
        self.editing_element = None
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("RichTextContainer")
        self.setStyleSheet("""
            QFrame#RichTextContainer {
                background: rgba(15, 23, 42, 0.85);
                border: 1.5px dashed #38BDF8;
                border-radius: 6px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 18, 6, 6)
        layout.setSpacing(0)

        # Nút icon mini kéo di chuyển ở góc trên bên trái
        self.drag_grip = QLabel("✥", self)
        self.drag_grip.setFixedSize(18, 14)
        self.drag_grip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drag_grip.setCursor(Qt.CursorShape.SizeAllCursor)
        self.drag_grip.setToolTip("Kéo di chuyển")
        self.drag_grip.setStyleSheet("""
            QLabel {
                color: #94A3B8;
                font-size: 11px;
                background: rgba(255, 255, 255, 0.12);
                border-radius: 2px;
            }
            QLabel:hover {
                color: #38BDF8;
                background: rgba(56, 189, 248, 0.3);
            }
        """)
        self.drag_grip.move(4, 2)
        self.drag_grip.installEventFilter(self)

        # Vùng soạn thảo
        self.text_edit = QTextEdit(self)
        self.text_edit.setAcceptRichText(True)
        self.text_edit.setPlaceholderText("Gõ văn bản...")
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background: transparent;
                color: #FFFFFF;
                border: none;
                padding: 0px;
            }
        """)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_edit.installEventFilter(self)
        self.text_edit.textChanged.connect(self._adjust_size)
        layout.addWidget(self.text_edit)

        self.resize(190, 48)

    def _adjust_size(self):
        doc = self.text_edit.document()
        doc_size = doc.size()
        w = max(190, min(int(doc_size.width()) + 24, 700))
        h = max(48, min(int(doc_size.height()) + 26, 500))
        self.resize(w, h)

    def toggle_bold(self):
        cursor = self.text_edit.textCursor()
        fmt = QTextCharFormat()
        current_weight = cursor.charFormat().fontWeight()
        new_weight = QFont.Weight.Normal if current_weight == QFont.Weight.Bold else QFont.Weight.Bold
        fmt.setFontWeight(new_weight)
        cursor.mergeCharFormat(fmt)
        self.text_edit.mergeCurrentCharFormat(fmt)
        self.text_edit.setFocus()

    def toggle_italic(self):
        cursor = self.text_edit.textCursor()
        fmt = QTextCharFormat()
        is_italic = cursor.charFormat().fontItalic()
        fmt.setFontItalic(not is_italic)
        cursor.mergeCharFormat(fmt)
        self.text_edit.mergeCurrentCharFormat(fmt)
        self.text_edit.setFocus()

    def toggle_underline(self):
        cursor = self.text_edit.textCursor()
        fmt = QTextCharFormat()
        is_under = cursor.charFormat().fontUnderline()
        fmt.setFontUnderline(not is_under)
        cursor.mergeCharFormat(fmt)
        self.text_edit.mergeCurrentCharFormat(fmt)
        self.text_edit.setFocus()

    def open_at(self, pos: QPoint, color: QColor, font_size: int = 16):
        self.editing_element = None
        self.current_color = color
        self.current_font_size = font_size

        if self.parent():
            pr = self.parent().rect()
            x = max(6, min(pos.x() - 6, pr.width() - self.width() - 6))
            y = max(6, min(pos.y() - 18, pr.height() - self.height() - 6))
            self.move(x, y)
        else:
            self.move(pos)

        c_hex = color.name() if hasattr(color, 'name') else "#FF3344"
        self.setStyleSheet(f"""
            QFrame#RichTextContainer {{
                background: rgba(15, 23, 42, 0.85);
                border: 1.5px dashed {c_hex};
                border-radius: 6px;
            }}
        """)
        self.text_edit.clear()

        font = QFont("Segoe UI", font_size)
        self.text_edit.setFont(font)

        fmt = QTextCharFormat()
        fmt.setForeground(QBrush(color))
        fmt.setFontPointSize(font_size)
        fmt.setFontFamily("Segoe UI")
        self.text_edit.setCurrentCharFormat(fmt)

        self._adjust_size()
        self.show()
        self.raise_()
        self.text_edit.setFocus()

    def open_for_element(self, element):
        """Mở lại TextElement đã có để người dùng tiếp tục sửa và di chuyển"""
        self.editing_element = element
        self.current_color = element.color
        self.current_font_size = element.font_size

        pos = element.pos.toPoint()
        offset_x = 6
        offset_y = 18
        if self.parent():
            pr = self.parent().rect()
            x = max(6, min(pos.x() - offset_x, pr.width() - 200))
            y = max(6, min(pos.y() - offset_y, pr.height() - 50))
            self.move(x, y)
        else:
            self.move(pos.x() - offset_x, pos.y() - offset_y)

        c_hex = element.color.name() if hasattr(element.color, 'name') else "#FF3344"
        self.setStyleSheet(f"""
            QFrame#RichTextContainer {{
                background: rgba(15, 23, 42, 0.85);
                border: 1.5px dashed {c_hex};
                border-radius: 6px;
            }}
        """)

        font = QFont("Segoe UI", element.font_size)
        self.text_edit.setFont(font)

        if getattr(element, 'html', None):
            self.text_edit.setHtml(element.html)
        else:
            fmt = QTextCharFormat()
            fmt.setForeground(QBrush(element.color))
            fmt.setFontPointSize(element.font_size)
            fmt.setFontFamily("Segoe UI")
            fmt.setFontWeight(QFont.Weight.Bold if element.is_bold else QFont.Weight.Normal)
            fmt.setFontItalic(element.is_italic)
            fmt.setFontUnderline(element.is_underline)
            self.text_edit.setCurrentCharFormat(fmt)
            self.text_edit.setPlainText(element.text)

        self._adjust_size()
        self.show()
        self.raise_()
        self.text_edit.setFocus()

        # Đưa con trỏ soạn thảo về cuối
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)

    def commit(self):
        plain = self.text_edit.toPlainText().strip()
        if plain:
            text_pos = self.text_edit.mapToParent(QPoint(0, 0))
            final_pos = self.pos() + text_pos
            html = self.text_edit.toHtml()
            self.committed.emit(plain, html, QPointF(final_pos))
        else:
            self.cancelled.emit()
        self.editing_element = None
        self.hide()

    def cancel(self):
        self.cancelled.emit()
        self.editing_element = None
        self.hide()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # Nhấn vào lề trên (y <= 18) hoặc viền xung quanh -> kéo di chuyển
            pos = event.position()
            if pos.y() <= 18 or pos.x() <= 6 or pos.x() >= self.width() - 6 or pos.y() >= self.height() - 6:
                self._drag_start_pos = event.globalPosition().toPoint() - self.pos()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_start_pos is not None:
            new_pos = event.globalPosition().toPoint() - self._drag_start_pos
            if self.parent():
                pr = self.parent().rect()
                x = max(0, min(new_pos.x(), pr.width() - self.width()))
                y = max(0, min(new_pos.y(), pr.height() - self.height()))
                self.move(x, y)
            else:
                self.move(new_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def eventFilter(self, obj, event):
        # Kéo bằng nút icon drag_grip
        if obj == self.drag_grip:
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._drag_start_pos = event.globalPosition().toPoint() - self.pos()
                return True
            elif event.type() == QEvent.Type.MouseMove and self._drag_start_pos is not None:
                new_pos = event.globalPosition().toPoint() - self._drag_start_pos
                if self.parent():
                    pr = self.parent().rect()
                    x = max(0, min(new_pos.x(), pr.width() - self.width()))
                    y = max(0, min(new_pos.y(), pr.height() - self.height()))
                    self.move(x, y)
                else:
                    self.move(new_pos)
                return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_start_pos = None
                return True

        # Phím tắt trong text_edit
        if obj == self.text_edit and event.type() == QEvent.Type.KeyPress:
            modifiers = event.modifiers()
            key = event.key()

            if (modifiers & Qt.KeyboardModifier.ControlModifier):
                if key == Qt.Key.Key_B:
                    self.toggle_bold()
                    return True
                elif key == Qt.Key.Key_I:
                    self.toggle_italic()
                    return True
                elif key == Qt.Key.Key_U:
                    self.toggle_underline()
                    return True
                elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self.commit()
                    return True

            if key == Qt.Key.Key_Escape:
                self.cancel()
                return True

        return super().eventFilter(obj, event)

class ScreenOverlay(QWidget):
    closed = pyqtSignal()

    def __init__(self, capture_mode="normal"):
        super().__init__()
        self.capture_mode = capture_mode  # 'normal', 'translate', 'ai'
        self.cfg = app_config.load_config()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMouseTracking(True)

        self.cross_cursor = create_sniper_cross_cursor()
        self.eraser_cursor = create_eraser_cursor()
        self.setCursor(self.cross_cursor)

        self.screen_pixmap = self.capture_desktop()

        self.selection_rect = QRect()
        self.mouse_pos = QPoint(-1000, -1000)
        self.is_selecting = False
        self.is_resizing = False
        self.is_moving = False
        self.is_erasing = False
        self.active_handle = HANDLE_NONE
        self.drag_start = QPoint()
        self.rect_start = QRect()

        self.elements = []
        self.redo_stack = []
        self.current_tool = "pencil"
        self.current_color = QColor(self.cfg.get("default_color", "#FF3344"))
        self.current_pen_width = self.cfg.get("default_pen_width", 3)
        self.current_highlighter_width = 20
        self.current_font_size = self.cfg.get("default_font_size", 16)
        self.text_is_bold = True
        self.text_is_italic = False
        self.text_is_underline = False
        self.current_element = None

        self.current_badge_number = 1
        self.target_lang = self.cfg.get("target_lang", "vi")
        self.last_ocr_data = None
        self.worker_thread = None

        # Hiệu ứng chớp sáng khung ảnh (Camera Shutter Flash) khi lưu hoặc copy
        self.flash_alpha = 0
        self.flash_timer = QTimer(self)
        self.flash_timer.setInterval(20)
        self.flash_timer.timeout.connect(self._step_flash_animation)
        self._flash_callback = None

        # Trạng thái thanh công cụ: Mặc định hiện (người dùng có thể ẩn/hiện bằng Space hoặc nút bấm)
        self.toolbar_visible = not self.cfg.get("default_hide_capture_toolbar", False)
        self.toolbar_toggle_rect = QRect()

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.init_toolbars()
        self.init_inline_editor()

        self._cached_block_elements = None
        self._cached_sheet_element = None
        self._last_translation_text = None
        self._current_overlay_mode = "original"

        # Phím tắt ESC toàn cục để hủy chụp bất cứ lúc nào
        self.esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.esc_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.esc_shortcut.activated.connect(self.handle_escape_cancel)

        # Cài đặt event filter toàn ứng dụng để phím Tab luôn xoay vòng chế độ dịch mượt mà 0ms
        QApplication.instance().installEventFilter(self)

        screen_geo = QGuiApplication.primaryScreen().geometry()
        self.setGeometry(screen_geo)

    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.setFocus()
        self.setCursor(self.cross_cursor)

    def capture_desktop(self):
        screen = QGuiApplication.primaryScreen()
        return screen.grabWindow(0)

    def init_toolbars(self):
        # Thanh công cụ HỢP NHẤT duy nhất (Unified Toolbar)
        self.toolbar = UnifiedFloatingToolbar(self)
        self.toolbar.target_lang = self.target_lang
        self.v_toolbar = self.toolbar  # alias
        self.h_toolbar = self.toolbar  # alias

        self.toolbar.tool_changed.connect(self.on_tool_changed)
        self.toolbar.color_changed.connect(self.on_color_changed)
        self.toolbar.pen_width_changed.connect(self.on_pen_width_changed)
        self.toolbar.highlighter_width_changed.connect(self.on_highlighter_width_changed)
        self.toolbar.font_size_changed.connect(self.on_font_size_changed)
        self.toolbar.badge_reset_requested.connect(self.on_badge_reset)
        self.toolbar.undo_requested.connect(self.undo)
        self.toolbar.redo_requested.connect(self.redo)

        self.toolbar.ai_requested.connect(self.trigger_ai_copilot)
        self.toolbar.ai_mode_requested.connect(self.trigger_ai_mode)
        self.toolbar.translate_requested.connect(self.trigger_translation)
        self.toolbar.cancel_overlay_requested.connect(self.remove_translation_overlay)
        self.toolbar.switch_mode_requested.connect(self.switch_translation_overlay_mode)
        self.toolbar.dual_view_requested.connect(self.open_dual_compare_window)
        self.toolbar.target_lang_changed.connect(self.on_target_lang_changed)
        self.toolbar.copy_requested.connect(self.copy_to_clipboard)
        self.toolbar.save_requested.connect(self.save_to_file)
        self.toolbar.print_requested.connect(self.print_image)
        self.toolbar.cancel_requested.connect(self.handle_escape_cancel)
        self.toolbar.hide()

        # 3. Thẻ Dịch Nhanh (OCR Reader)
        self.trans_card = TranslationCard(self)
        self.trans_card.overlay_requested.connect(self.toggle_translation_overlay)
        self.trans_card.closed.connect(self.update_toolbars_pos)
        self.trans_card.installEventFilter(self)
        self.trans_card.hide()

        # 4. Thẻ Trợ Lý AI & Dịch Thuật Đa Năng (Gemini Copilot)
        self.ai_card = AICopilotCard(self)
        self.ai_card.set_target_lang(self.target_lang)
        self.ai_card.target_lang_changed.connect(self.on_target_lang_changed)
        self.ai_card.overlay_requested.connect(self.apply_ai_translation_overlay)
        self.ai_card.cancel_overlay_requested.connect(self.remove_translation_overlay)
        self.ai_card.switch_mode_requested.connect(self.switch_translation_overlay_mode)
        self.ai_card.dual_view_requested.connect(self.open_dual_compare_window)
        self.ai_card.closed.connect(self.update_toolbars_pos)
        self.ai_card.installEventFilter(self)
        self.ai_card.hide()

    def init_inline_editor(self):
        self.text_editor = FloatingRichTextEditor(self)
        self.inline_editor = self.text_editor  # alias tương thích
        self.text_editor.committed.connect(self.on_text_committed)
        self.text_editor.cancelled.connect(self.on_text_cancelled)
        self.text_editor.hide()

    def on_text_committed(self, plain_text: str, html: str, pos: QPointF):
        text_el = TextElement(
            pos,
            plain_text,
            self.current_color,
            self.current_font_size,
            html=html
        )
        self.elements.append(text_el)
        self.redo_stack.clear()
        self._update_overlay_button_states()
        self.update()
        self.show_toast("✓ Đã lưu chữ (nhấp vào chữ để sửa hoặc di chuyển)")

    def on_text_cancelled(self):
        self.update()

    def focusNextPrevChild(self, next: bool) -> bool:
        # Ngăn Qt nuốt phím Tab để chuyển focus giữa các nút bấm,
        # giữ phím Tab để xoay vòng chế độ xem bản dịch và ảnh gốc.
        if hasattr(self, 'inline_editor') and self.inline_editor.isVisible():
            return super().focusNextPrevChild(next)
        return False

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self.handle_escape_cancel()
                return True
            elif event.key() == Qt.Key.Key_Tab:
                # Nếu đang gõ text vẽ inline trên canvas thì để editor tự xử lý Tab
                if hasattr(self, 'inline_editor') and self.inline_editor.isVisible():
                    return False
                # Nếu đang gõ câu hỏi trong ô Chat của AI Card thì không chặn Tab
                if hasattr(self, 'ai_card') and self.ai_card.isVisible() and hasattr(self.ai_card, 'input_question') and self.ai_card.input_question.hasFocus():
                    return False

                can_tab = (
                    self.has_translation_overlay()
                    or getattr(self, '_last_translation_text', None)
                    or (hasattr(self, 'ai_card') and getattr(self.ai_card, 'last_ai_result', None))
                    or (hasattr(self, 'trans_card') and getattr(self.trans_card, 'txt_translated', None) and self.trans_card.txt_translated.toPlainText().strip())
                )
                if can_tab:
                    self.switch_translation_overlay_mode()
                    return True

        return super().eventFilter(obj, event)

    def handle_escape_cancel(self):
        """
        Xử lý khi người dùng nhấn phím ESC hoặc nhấn nút hủy:
        1. Nếu đang mở AI Copilot Card -> Đóng card
        2. Nếu đang mở Thẻ Dịch Nhanh -> Đóng card
        3. Nếu đang có lớp dịch đè -> Đóng lớp dịch
        4. Nếu đang gõ văn bản inline -> Hủy văn bản đang gõ dở
        5. Nếu đang kéo vẽ dở dang một nét/hình -> Hủy hình đang vẽ dở
        6. Đang trong chế độ chụp màn hình -> HỦY VÀ THOÁT OVERLAY NGAY LẬP TỨC
        """
        if self.ai_card.isVisible():
            self.ai_card.hide()
            self.update_toolbars_pos()
            return

        if self.trans_card.isVisible():
            self.trans_card.hide()
            self.update_toolbars_pos()
            return

        if self.has_translation_overlay():
            self.remove_translation_overlay()
            return

        if hasattr(self, 'text_editor') and self.text_editor.isVisible():
            self.text_editor.cancel()
            return

        if self.current_element:
            self.current_element = None
            self.update()
            return

        # Thoát / Hủy toàn bộ overlay ngay lập tức
        self.close_overlay()

    def select_full_screen(self):
        """
        Chọn nhanh toàn bộ màn hình (chụp full màn hình):
        - Thanh công cụ mặc định xuất hiện ở góc trên bên trong màn hình.
        - Khi chụp ảnh (lưu/sao chép), thanh công cụ KHÔNG BỊ GHI LẠI VÀO ẢNH.
        """
        self.selection_rect = self.rect()
        self.elements.clear()
        self.redo_stack.clear()
        self._update_overlay_button_states(False)
        self.on_selection_completed()
        self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            pt = QPointF(pos)

            # 1. Nhấp đúp vào văn bản đã có -> Mở lại để sửa chữ và kéo di chuyển
            for i in range(len(self.elements) - 1, -1, -1):
                el = self.elements[i]
                if isinstance(el, TextElement) and el.contains_point(pt, tolerance=12.0):
                    target_el = self.elements.pop(i)
                    self.redo_stack.clear()
                    self.current_tool = "text"
                    self.toolbar.select_tool("text")
                    self.update()
                    self.text_editor.open_for_element(target_el)
                    event.accept()
                    return

            # 2. Nhấp đúp khi chưa có vùng chọn -> Tự động chọn toàn bộ màn hình
            if not self.selection_rect.isValid() or self.selection_rect.isEmpty():
                self.select_full_screen()
                event.accept()
                return

            # 3. Khi đã có vùng chọn: Tuyệt đối KHÔNG tự động đóng trang hay copy làm mất dữ liệu
            # Nếu đang chọn công cụ Chữ (Text) -> Mở khung nhập văn bản tại vị trí nhấp đúp
            if self.current_tool == "text" and self.selection_rect.contains(pos):
                if hasattr(self, 'text_editor') and not self.text_editor.isVisible():
                    self.text_editor.open_at(pos, self.current_color, self.current_font_size)
                event.accept()
                return

            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()

            # 1. Nếu đang chọn công cụ Cục tẩy (Eraser) -> Ưu tiên bôi xóa hình vẽ ngay lập tức
            if self.current_tool == "eraser":
                self.is_erasing = True
                self.erase_at(pos)
                event.accept()
                return

            # 2. Nhấn nút bật / tắt thanh công cụ
            if hasattr(self, 'toolbar_toggle_rect') and self.toolbar_toggle_rect.isValid() and self.toolbar_toggle_rect.contains(pos):
                self.toggle_toolbar()
                event.accept()
                return

            if hasattr(self, 'text_editor') and self.text_editor.isVisible():
                if self.text_editor.geometry().contains(pos):
                    # Click bên trong editor -> để editor tự xử lý
                    return
                else:
                    self.text_editor.commit()

            if self.selection_rect.isValid() and not self.selection_rect.isEmpty():
                handle = self.get_handle_at(pos)
                if handle != HANDLE_NONE:
                    if handle == HANDLE_INSIDE:
                        if self.current_tool == "eraser":
                            self.is_erasing = True
                            self.erase_at(pos)
                            return
                        elif self.current_tool in ["pencil", "highlighter", "line", "arrow", "double_arrow", "rect", "rect_fill", "ellipse", "ellipse_fill", "blur", "text", "badge", "triangle", "trapezoid", "parallelogram"]:
                            self.start_drawing(pos)
                            return
                        else:
                            self.is_moving = True
                            self.drag_start = pos
                            self.rect_start = QRect(self.selection_rect)
                            return
                    else:
                        self.is_resizing = True
                        self.active_handle = handle
                        self.drag_start = pos
                        self.rect_start = QRect(self.selection_rect)
                        return

            self.selection_rect = QRect(pos, QSize(0, 0))
            self.elements.clear()
            self.redo_stack.clear()
            self._cached_block_elements = None
            self._cached_sheet_element = None
            self._last_translation_text = None
            self._current_overlay_mode = "original"
            self._update_overlay_button_states(False)
            self.is_selecting = True
            self.drag_start = pos
            self.toolbar.hide()
            self.trans_card.hide()
            self.ai_card.hide()
            self.update()

        elif event.button() == Qt.MouseButton.RightButton:
            self.handle_escape_cancel()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.pos()

        # Nếu rê chuột qua nút bật/tắt thanh công cụ
        if hasattr(self, 'toolbar_toggle_rect') and self.toolbar_toggle_rect.isValid() and self.toolbar_toggle_rect.contains(pos):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            return

        # Nếu chuột nằm trên AI Card, Toolbar hoặc TranslationCard -> Luôn chuyển sang con trỏ mũi tên Arrow
        for w in (self.ai_card, self.toolbar, self.trans_card):
            if w.isVisible() and w.geometry().contains(pos):
                self.setCursor(Qt.CursorShape.ArrowCursor)
                return

        # Nếu đang ở công cụ Cục tẩy (Eraser)
        if self.current_tool == "eraser":
            self.setCursor(self.eraser_cursor)
            if self.is_erasing or (event.buttons() & Qt.MouseButton.LeftButton):
                self.erase_at(pos)
            return

        if self.current_element:
            self.update_drawing(pos)
            self.update()
            return

        if self.is_selecting:
            self.selection_rect = QRect(self.drag_start, pos).normalized()
            self.update()
            return

        if self.is_moving:
            dx = pos.x() - self.drag_start.x()
            dy = pos.y() - self.drag_start.y()
            new_rect = self.rect_start.translated(dx, dy)
            if self.rect().contains(new_rect):
                self.selection_rect = new_rect
                self.update_toolbars_pos()
                self.update()
            return

        if self.is_resizing:
            self.resize_selection(pos)
            self.update_toolbars_pos()
            self.update()
            return

        if self.selection_rect.isValid() and not self.selection_rect.isEmpty():
            handle = self.get_handle_at(pos)
            self.update_cursor(handle)
        else:
            self.setCursor(self.cross_cursor)
            self.mouse_pos = pos
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_erasing:
                self.is_erasing = False
                return

            if self.current_element:
                self.finish_drawing()
                self.update()
                return

            if self.is_selecting:
                self.is_selecting = False
                if self.selection_rect.width() > 15 and self.selection_rect.height() > 15:
                    self.on_selection_completed()
                else:
                    self.selection_rect = QRect()
                self.update()
                return

            if self.is_moving or self.is_resizing:
                self.is_moving = False
                self.is_resizing = False
                self.active_handle = HANDLE_NONE
                self.update_toolbars_pos()
                self.update()

    def start_drawing(self, pos: QPoint):
        if self.current_tool == "pencil":
            self.current_element = PencilElement(self.current_color, self.current_pen_width)
            self.current_element.add_point(QPointF(pos))
        elif self.current_tool == "highlighter":
            self.current_element = HighlighterElement(self.current_color, width=self.current_highlighter_width)
            self.current_element.add_point(QPointF(pos))
        elif self.current_tool == "line":
            self.current_element = LineElement(QPointF(pos), QPointF(pos), self.current_color, self.current_pen_width)
        elif self.current_tool == "arrow":
            self.current_element = ArrowElement(QPointF(pos), QPointF(pos), self.current_color, self.current_pen_width)
        elif self.current_tool == "double_arrow":
            self.current_element = DoubleArrowElement(QPointF(pos), QPointF(pos), self.current_color, self.current_pen_width)
        elif self.current_tool == "rect":
            self.current_element = RectElement(QPointF(pos), QPointF(pos), self.current_color, self.current_pen_width)
        elif self.current_tool == "rect_fill":
            self.current_element = FilledRectElement(QPointF(pos), QPointF(pos), self.current_color, self.current_pen_width)
        elif self.current_tool == "ellipse":
            self.current_element = EllipseElement(QPointF(pos), QPointF(pos), self.current_color, self.current_pen_width)
        elif self.current_tool == "ellipse_fill":
            self.current_element = FilledEllipseElement(QPointF(pos), QPointF(pos), self.current_color, self.current_pen_width)
        elif self.current_tool == "blur":
            self.current_element = BlurElement(QPointF(pos), QPointF(pos))
        elif self.current_tool == "triangle":
            self.current_element = TriangleElement(QPointF(pos), QPointF(pos), self.current_color, self.current_pen_width)
        elif self.current_tool == "trapezoid":
            self.current_element = TrapezoidElement(QPointF(pos), QPointF(pos), self.current_color, self.current_pen_width)
        elif self.current_tool == "parallelogram":
            self.current_element = ParallelogramElement(QPointF(pos), QPointF(pos), self.current_color, self.current_pen_width)
        elif self.current_tool == "badge":
            badge = StepBadgeElement(QPointF(pos), self.current_badge_number, self.current_color)
            self.elements.append(badge)
            self.redo_stack.clear()
            self.current_badge_number += 1
            self.update()
        elif self.current_tool == "text":
            pt = QPointF(pos)
            found_idx = -1
            for i in range(len(self.elements) - 1, -1, -1):
                el = self.elements[i]
                if isinstance(el, TextElement) and el.contains_point(pt, tolerance=12.0):
                    found_idx = i
                    break
            if found_idx != -1:
                target_el = self.elements.pop(found_idx)
                self.redo_stack.clear()
                self.update()
                self.text_editor.open_for_element(target_el)
            else:
                self.show_inline_editor(pos)

    def update_drawing(self, pos: QPoint):
        if isinstance(self.current_element, (PencilElement, HighlighterElement)):
            self.current_element.add_point(QPointF(pos))
        elif isinstance(self.current_element, (LineElement, ArrowElement, DoubleArrowElement, RectElement, FilledRectElement, EllipseElement, FilledEllipseElement, BlurElement, TriangleElement, TrapezoidElement, ParallelogramElement)):
            self.current_element.p2 = QPointF(pos)

    def finish_drawing(self):
        if self.current_element:
            self.elements.append(self.current_element)
            self.redo_stack.clear()
            self.current_element = None

    def erase_at(self, pos: QPoint):
        """
        Bôi xóa hình vẽ hoặc phần tử trên màn hình:
        - Click hoặc rê chuột qua shape để xóa.
        - ĐẶC BIỆT VỚI SỐ THỰC TỰ (StepBadgeElement): Khi xóa một số thứ tự (ví dụ bước 2),
          các số thứ tự phía sau (3, 4...) tự động giảm 1 (thành 2, 3...)
          và bộ đếm bước tiếp theo (current_badge_number) tự động cập nhật giảm theo.
        """
        if not self.elements:
            return

        from canvas_elements import (
            StepBadgeElement, BlockOverlayElement, UnifiedSheetOverlayElement, InfographicImageElement
        )

        pt = QPointF(pos)
        erased = False

        for i in range(len(self.elements) - 1, -1, -1):
            el = self.elements[i]
            if hasattr(el, 'contains_point') and el.contains_point(pt, tolerance=32.0):
                popped = self.elements.pop(i)
                erased = True

                if isinstance(popped, StepBadgeElement):
                    del_num = popped.number
                    # Tự động giảm tất cả các số thứ tự phía sau đi 1
                    for other in self.elements:
                        if isinstance(other, StepBadgeElement) and other.number > del_num:
                            other.number -= 1

                    # Cập nhật số thứ tự bước tiếp theo đồng bộ
                    remaining = [b.number for b in self.elements if isinstance(b, StepBadgeElement)]
                    self.current_badge_number = max(remaining, default=0) + 1
                    self.show_toast(f"✓ Đã xóa bước {del_num}, các số sau tự động giảm")
                elif isinstance(popped, (BlockOverlayElement, UnifiedSheetOverlayElement, InfographicImageElement)):
                    self.show_toast("✓ Đã xóa khối bản dịch đè")
                else:
                    self.show_toast("✓ Đã xóa hình vẽ")
                break

        if erased:
            self.redo_stack.clear()
            self._update_overlay_button_states()
            self.update()

    def show_inline_editor(self, pos: QPoint):
        self.text_editor.open_at(pos, self.current_color, self.current_font_size)
        self.show_toast("Gõ chữ (Kéo ✥ di chuyển | Ctrl+B, I, U | Click ngoài hoặc Ctrl+Enter để ghim)")

    def commit_inline_text(self):
        if hasattr(self, 'text_editor') and self.text_editor.isVisible():
            self.text_editor.commit()

    def undo(self):
        if not self.elements:
            return

        from canvas_elements import StepBadgeElement, BlockOverlayElement

        popped = self.elements.pop()
        if isinstance(popped, BlockOverlayElement):
            # Gom toàn bộ các khối BlockOverlayElement cùng batch để hủy trong 1 bước duy nhất
            batch = [popped]
            while self.elements and isinstance(self.elements[-1], BlockOverlayElement):
                batch.append(self.elements.pop())
            self.redo_stack.append(batch)
            self._update_overlay_button_states()
            self.update()
            self.show_toast("✓ Đã hoàn tác bản dịch đè (khôi phục ảnh gốc)")
            return

        self.redo_stack.append(popped)
        if isinstance(popped, StepBadgeElement):
            remaining = [b.number for b in self.elements if isinstance(b, StepBadgeElement)]
            self.current_badge_number = max(remaining, default=0) + 1
        self._update_overlay_button_states()
        self.update()

    def redo(self):
        if not self.redo_stack:
            return

        from canvas_elements import StepBadgeElement

        item = self.redo_stack.pop()
        if isinstance(item, list):
            # Khôi phục toàn bộ khối overlay cùng một lượt
            for el in reversed(item):
                self.elements.append(el)
            self._update_overlay_button_states()
            self.update()
            self.show_toast("✓ Đã làm lại bản dịch đè")
            return

        self.elements.append(item)
        if isinstance(item, StepBadgeElement):
            remaining = [b.number for b in self.elements if isinstance(b, StepBadgeElement)]
            self.current_badge_number = max(remaining, default=0) + 1
        self._update_overlay_button_states()
        self.update()

    def on_tool_changed(self, tool_id):
        self.current_tool = tool_id
        if self.current_tool == "eraser":
            self.setCursor(self.eraser_cursor)
            self.show_toast("Chế độ bôi xóa: Click hoặc kéo chuột qua hình/chữ để xóa")
        elif self.selection_rect.isValid() and not self.selection_rect.isEmpty():
            pos = self.mapFromGlobal(QCursor.pos())
            handle = self.get_handle_at(pos)
            self.update_cursor(handle)
        else:
            self.setCursor(self.cross_cursor)

    def on_color_changed(self, color):
        self.current_color = color

    def get_handle_rects(self):
        r = self.selection_rect
        hs = HANDLE_SIZE
        half = hs // 2
        return {
            HANDLE_TL: QRect(r.left() - half, r.top() - half, hs, hs),
            HANDLE_T:  QRect(r.center().x() - half, r.top() - half, hs, hs),
            HANDLE_TR: QRect(r.right() - half, r.top() - half, hs, hs),
            HANDLE_R:  QRect(r.right() - half, r.center().y() - half, hs, hs),
            HANDLE_BR: QRect(r.right() - half, r.bottom() - half, hs, hs),
            HANDLE_B:  QRect(r.center().x() - half, r.bottom() - half, hs, hs),
            HANDLE_BL: QRect(r.left() - half, r.bottom() - half, hs, hs),
            HANDLE_L:  QRect(r.left() - half, r.center().y() - half, hs, hs),
        }

    def get_handle_at(self, pos: QPoint):
        for handle_id, hrect in self.get_handle_rects().items():
            if hrect.contains(pos):
                return handle_id
        if self.selection_rect.contains(pos):
            return HANDLE_INSIDE
        return HANDLE_NONE

    def update_cursor(self, handle):
        # Nếu chuột đang trên thẻ AI, Toolbar hoặc TranslationCard -> Luôn là ArrowCursor
        pos = self.mapFromGlobal(QCursor.pos())
        for w in (self.ai_card, self.toolbar, self.trans_card):
            if w.isVisible() and w.geometry().contains(pos):
                self.setCursor(Qt.CursorShape.ArrowCursor)
                return

        if self.current_tool == "eraser":
            inside_cursor = self.eraser_cursor
        elif self.current_tool and not self.ai_card.isVisible() and not self.trans_card.isVisible():
            inside_cursor = self.cross_cursor
        else:
            inside_cursor = Qt.CursorShape.SizeAllCursor

        cursors = {
            HANDLE_TL: Qt.CursorShape.SizeFDiagCursor,
            HANDLE_BR: Qt.CursorShape.SizeFDiagCursor,
            HANDLE_TR: Qt.CursorShape.SizeBDiagCursor,
            HANDLE_BL: Qt.CursorShape.SizeBDiagCursor,
            HANDLE_T:  Qt.CursorShape.SizeVerCursor,
            HANDLE_B:  Qt.CursorShape.SizeVerCursor,
            HANDLE_L:  Qt.CursorShape.SizeHorCursor,
            HANDLE_R:  Qt.CursorShape.SizeHorCursor,
            HANDLE_INSIDE: inside_cursor,
            HANDLE_NONE: Qt.CursorShape.ArrowCursor
        }
        self.setCursor(cursors.get(handle, self.cross_cursor))

    def resize_selection(self, pos: QPoint):
        r = QRect(self.rect_start)
        h = self.active_handle

        if h in [HANDLE_TL, HANDLE_L, HANDLE_BL]:
            r.setLeft(min(pos.x(), r.right() - 20))
        if h in [HANDLE_TR, HANDLE_R, HANDLE_BR]:
            r.setRight(max(pos.x(), r.left() + 20))
        if h in [HANDLE_TL, HANDLE_T, HANDLE_TR]:
            r.setTop(min(pos.y(), r.bottom() - 20))
        if h in [HANDLE_BL, HANDLE_B, HANDLE_BR]:
            r.setBottom(max(pos.y(), r.top() + 20))

        self.selection_rect = r.normalized()

    def on_selection_completed(self):
        self.update_toolbars_pos()
        if self.toolbar_visible:
            self.toolbar.show()
        else:
            self.toolbar.hide()

        if self.capture_mode == "ai":
            self.trigger_ai_copilot()
        elif self.capture_mode == "translate":
            self.trigger_translation()

    def toggle_toolbar(self):
        """Bật / Tắt thanh công cụ vẽ nhanh"""
        self.toolbar_visible = not self.toolbar.isVisible()
        if self.toolbar_visible:
            self.update_toolbars_pos()
            self.toolbar.show()
            self.toolbar.raise_()
        else:
            self.toolbar.hide()
        self.update()

    def update_toolbars_pos(self):
        if not self.selection_rect.isValid() or self.selection_rect.isEmpty():
            return

        screen_rect = self.rect()
        r = self.selection_rect

        # Đảm bảo kích thước toolbar dọc được tính toán chuẩn
        self.toolbar.adjustSize()
        tb_w = self.toolbar.width()
        tb_h = self.toolbar.height()

        # 1. TỌA ĐỘ X (THANH CÔNG CỤ DỌC):
        # Ưu tiên 1: Đặt sát bên ngoài cạnh phải của vùng chọn
        if r.right() + 8 + tb_w <= screen_rect.right() - 6:
            tb_x = r.right() + 8
        # Ưu tiên 2: Nếu mép phải sát màn hình -> Đặt sát bên ngoài cạnh trái của vùng chọn
        elif r.left() - tb_w - 8 >= 6:
            tb_x = r.left() - tb_w - 8
        # Ưu tiên 3: Nếu cả 2 bên đều không đủ chỗ (ví dụ: chụp full màn hình) -> Đặt nổi gọn gàng bên trong cạnh phải vùng chọn
        else:
            tb_x = min(r.right() - tb_w - 12, screen_rect.right() - tb_w - 12)

        # 2. TỌA ĐỘ Y (THANH CÔNG CỤ DỌC):
        # Căn đỉnh theo đỉnh vùng chọn, đảm bảo luôn nằm an toàn trong màn hình
        tb_y = r.top()
        if tb_y < 12:
            tb_y = 12
        if tb_y + tb_h > screen_rect.bottom() - 12:
            tb_y = screen_rect.bottom() - tb_h - 12

        self.toolbar.move(tb_x, tb_y)
        self.toolbar.raise_()

        # Định vị Thẻ AI Copilot (tránh đè lên vùng chọn và thanh dọc)
        if self.ai_card.isVisible():
            self._position_card(self.ai_card, r, tb_x, tb_y)

    def _position_card(self, card_widget, r, tb_x, tb_y):
        screen_rect = self.rect()
        card_widget.adjustSize()
        tc_w = card_widget.width()
        tc_h = card_widget.height()

        # Tránh đè lên vùng chụp màn hình của người dùng:
        # Ưu tiên 1: Đặt bên phải vùng chọn (sau thanh công cụ dọc)
        if screen_rect.right() - max(tb_x + 48, r.right()) >= tc_w + 12:
            tc_x = max(tb_x + 50, r.right() + 12)
            tc_y = max(10, min(r.top(), screen_rect.bottom() - tc_h - 10))
        # Ưu tiên 2: Đặt bên trái vùng chọn
        elif r.left() >= tc_w + 14:
            tc_x = r.left() - tc_w - 12
            tc_y = max(10, min(r.top(), screen_rect.bottom() - tc_h - 10))
        # Ưu tiên 3: Đặt phía dưới vùng chọn
        elif r.bottom() + 10 + tc_h <= screen_rect.bottom() - 6:
            tc_x = max(10, min(r.left(), screen_rect.right() - tc_w - 10))
            tc_y = r.bottom() + 10
        # Ưu tiên 4: Đặt phía trên vùng chọn
        elif r.top() - tc_h - 10 >= 8:
            tc_x = max(10, min(r.left(), screen_rect.right() - tc_w - 10))
            tc_y = r.top() - tc_h - 10
        # Ưu tiên 5: Nếu vùng chọn chiếm gần hết màn hình, đặt góc dưới phải
        else:
            tc_x = max(10, screen_rect.right() - tc_w - 16)
            tc_y = max(10, screen_rect.bottom() - tc_h - 16)

        card_widget.move(int(tc_x), int(tc_y))
        card_widget.raise_()
        self.toolbar.raise_()

    # --- KÍCH HOẠT TRỢ LÝ AI & DỊCH THUẬT (GEMINI COPILOT) ---

    def trigger_ai_copilot(self, default_task="translate"):
        cropped_img = self.get_cropped_pil_image()
        if not cropped_img:
            return

        self.trans_card.hide()
        self.ai_card.set_target_lang(self.target_lang)
        self.ai_card.show()
        self.ai_card.raise_()
        self.update_toolbars_pos()
        self.ai_card.set_image(cropped_img, default_task=default_task)

    def trigger_ai_mode(self, mode: str):
        self.trigger_ai_copilot(default_task=mode)

    def trigger_translation(self):
        """
        Dịch đè trực tiếp 1:1 lên vùng chụp màn hình theo vị trí khối chữ gốc.
        Bấm Tab để lật nhanh giữa bản dịch đè và ảnh gốc.
        """
        cropped_img = self.get_cropped_pil_image()
        if not cropped_img or not self.selection_rect.isValid() or self.selection_rect.isEmpty():
            return

        self.ai_card.hide()
        self.trans_card.hide()
        self.show_toast("⏳ Đang nhận diện văn bản & Dịch đè vị trí...")

        def worker_task():
            try:
                from ai_engine import ai_translate_image_blocks
                cfg = app_config.load_config()
                api_key = app_config.get_effective_gemini_api_key(cfg)
                model = cfg.get("gemini_model", "gemini-flash-lite-latest")

                blocks = []
                if api_key and not api_key.startswith("AIzaSyDummy"):
                    try:
                        blocks = ai_translate_image_blocks(
                            cropped_img,
                            target_lang=self.target_lang,
                            api_key=api_key,
                            model=model
                        )
                    except Exception as e:
                        print("Lỗi ai_translate_image_blocks in overlay:", e)

                if not blocks:
                    from ocr_translate import perform_ocr, is_ocr_reliable, translate_text
                    from ai_engine import extract_ocr_paragraphs
                    ocr_lang = cfg.get("ocr_lang", "auto")
                    ocr_res = perform_ocr(cropped_img, lang=ocr_lang)
                    _, blocks = extract_ocr_paragraphs(cropped_img, lang=ocr_lang)
                    if not blocks and ocr_res.get("lines"):
                        blocks = cluster_lines_into_blocks(ocr_res.get("lines", []))
                    if not blocks and ocr_res.get("lines"):
                        for l in ocr_res["lines"]:
                            txt = l.get("text", "").strip()
                            if len(txt) >= 1:
                                blocks.append({
                                    "x": float(l.get("x", 0)),
                                    "y": float(l.get("y", 0)),
                                    "w": float(l.get("w", 50)),
                                    "h": float(l.get("h", 20)),
                                    "avg_line_h": float(l.get("h", 20)),
                                    "original": txt,
                                    "translated": ""
                                })

                    valid = []
                    for b in blocks:
                        if len(b.get('original', '').strip()) >= 2:
                            valid.append(b)
                    needs_tr = [b for b in valid if not b.get('translated')]
                    if needs_tr:
                        batch_q = " @@ ".join([b['original'].replace('\n', ' ') for b in needs_tr])
                        tr_batch = translate_text(batch_q, target_lang=self.target_lang)
                        parts = [p.strip() for p in tr_batch.split("@@")]
                        if len(parts) == len(needs_tr):
                            for i, b in enumerate(needs_tr):
                                b['translated'] = parts[i]
                        else:
                            for b in needs_tr:
                                b['translated'] = translate_text(b['original'], target_lang=self.target_lang)
                    blocks = valid

                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(self, "_on_direct_translation_ready", Qt.ConnectionType.QueuedConnection, Q_ARG(list, blocks))
            except Exception as e:
                print("Lỗi direct translation worker:", e)
                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(self, "_on_direct_translation_error", Qt.ConnectionType.QueuedConnection, Q_ARG(str, str(e)))

        t = threading.Thread(target=worker_task, daemon=True)
        t.start()

    @pyqtSlot(str)
    def _on_direct_translation_error(self, err_msg: str):
        self.show_toast(f"❌ Lỗi dịch thuật: {err_msg}")

    @pyqtSlot(list)
    def _on_direct_translation_ready(self, blocks: list):
        if not self.selection_rect.isValid() or self.selection_rect.isEmpty():
            return

        cropped_img = self.get_cropped_pil_image()
        if not cropped_img:
            return

        r = self.selection_rect
        valid_blocks = []
        for blk in blocks:
            orig = blk.get('original', '').strip()
            trans = blk.get('translated', '').strip()
            if len(orig) < 2 and len(trans) < 2:
                continue
            bw = float(blk.get('w', 0.0))
            bh = float(blk.get('h', 0.0))
            if bw < 8.0 or bh < 6.0:
                continue
            valid_blocks.append(blk)

        self._cached_block_elements = []
        if valid_blocks:
            for blk in valid_blocks:
                para = blk.get('translated', '').strip()
                if not para:
                    continue

                orig_bx = float(blk.get('x', 0.0))
                orig_by = float(blk.get('y', 0.0))
                orig_bw = float(blk.get('w', 40.0))
                orig_bh = float(blk.get('h', 16.0))

                bg_c, txt_c, is_photo = sample_block_colors(cropped_img, orig_bx, orig_by, orig_bw, orig_bh)
                if is_photo:
                    continue

                bx = float(r.left() + orig_bx)
                by = float(r.top() + orig_by)
                bw = float(orig_bw)
                bh = float(orig_bh)

                avg_line_h = float(blk.get('avg_line_h', bh / max(1, blk.get('num_lines', 1))))
                base_fsize = max(8, int(avg_line_h * 0.72))

                block_el = BlockOverlayElement(
                    QRectF(bx, by, bw, bh),
                    blk.get('original', ''),
                    para,
                    bg_color=bg_c,
                    text_color=txt_c,
                    base_font_size=base_fsize
                )
                self._cached_block_elements.append(block_el)

        if self._cached_block_elements:
            self.remove_translation_overlay(silent=True)
            self.elements.extend(self._cached_block_elements)
            self._current_overlay_mode = "blocks"
            self.redo_stack.clear()
            self._update_overlay_button_states(True)
            self.update_toolbars_pos()
            self.update()
            from ai_engine import get_target_lang_display_name
            lang_display = get_target_lang_display_name(self.target_lang)
            self.show_toast(f"✓ Đã dịch đè 1:1 sang {lang_display}! (Bấm Tab: Về ảnh gốc)")
        else:
            self.show_toast("⚠️ Không tìm thấy khối văn bản nào để đè vị trí.")

    def has_translation_overlay(self) -> bool:
        from canvas_elements import BlockOverlayElement, UnifiedSheetOverlayElement, InfographicImageElement
        return any(isinstance(el, (BlockOverlayElement, UnifiedSheetOverlayElement, InfographicImageElement)) for el in self.elements)

    def _update_overlay_button_states(self, is_overlaid: bool = None):
        if is_overlaid is None:
            is_overlaid = self.has_translation_overlay()

        curr_mode = getattr(self, '_current_overlay_mode', 'original')
        if hasattr(self, 'ai_card'):
            self.ai_card.set_overlay_state(is_overlaid, current_mode=curr_mode)
        if hasattr(self, 'toolbar'):
            self.toolbar.set_overlay_state(is_overlaid)

    def remove_translation_overlay(self, silent=False):
        """
        Hủy tính năng ghi đè bản dịch lên chữ, khôi phục lại ảnh chụp ban đầu
        """
        from canvas_elements import BlockOverlayElement, UnifiedSheetOverlayElement, InfographicImageElement
        overlays = [el for el in self.elements if isinstance(el, (BlockOverlayElement, UnifiedSheetOverlayElement, InfographicImageElement))]
        if not overlays:
            return

        self.redo_stack.append(overlays)
        self.elements = [el for el in self.elements if not isinstance(el, (BlockOverlayElement, UnifiedSheetOverlayElement, InfographicImageElement))]
        self._update_overlay_button_states(False)
        self.update()
        if not silent:
            self.show_toast("✓ Đã hủy ghi đè, khôi phục ảnh gốc!")

    def apply_infographic_overlay(self, pixmap: QPixmap):
        """
        Đưa ảnh Infographic trực tiếp lên Canvas vùng chụp màn hình để người dùng có thể
        dùng toàn bộ công cụ vẽ (bút, highlight, mũi tên, thêm text...) để chỉnh sửa trực tiếp.
        """
        if not self.selection_rect.isValid() or self.selection_rect.isEmpty() or not pixmap or pixmap.isNull():
            return
        from canvas_elements import InfographicImageElement
        self.remove_translation_overlay(silent=True)
        el = InfographicImageElement(QRectF(self.selection_rect), pixmap)
        self.elements.append(el)
        self.redo_stack.clear()
        self._update_overlay_button_states(True)
        self.update()
        self.show_toast("✓ Đã đưa Infographic lên Canvas! Dùng các công cụ vẽ để chỉnh sửa trực tiếp.")

    def apply_ai_translation_overlay(self, translation_text: str, force_mode: str = None):
        """
        Ghi đè bản dịch trực tiếp lên vùng ảnh chụp màn hình.
        - Hỗ trợ lưu cache thông minh để bấm Tab chuyển đổi 0ms không phải OCR hay dịch lại.
        - Chu trình 3 trạng thái xoay vòng mượt mà:
          1. 'blocks': Đè từng vị trí chữ gốc 1:1
          2. 'sheet': Bảng đọc kính mờ toàn diện
          3. 'original': Khôi phục ảnh gốc không che
        """
        if not translation_text or not self.selection_rect.isValid() or self.selection_rect.isEmpty():
            return

        # Nếu translation_text mới khác text cũ -> reset cache
        if getattr(self, '_last_translation_text', None) != translation_text:
            self._cached_block_elements = None
            self._cached_sheet_element = None

        self._last_translation_text = translation_text

        # 1. Kiểm tra cache nếu đã có sẵn:
        if getattr(self, '_cached_block_elements', None) is not None:
            if len(self._cached_block_elements) > 0:
                self.remove_translation_overlay(silent=True)
                self.elements.extend(self._cached_block_elements)
                self.redo_stack.clear()
                self._current_overlay_mode = "blocks"
                self._update_overlay_button_states(True)
                self.update_toolbars_pos()
                self.update()
                self.show_toast("✓ Đã đè theo từng vị trí (Bấm Tab: Về ảnh gốc)")
                return

        # 2. Xóa overlay cũ đang hiển thị
        self.remove_translation_overlay(silent=True)

        # 3. Làm sạch text
        import re
        clean_text = translation_text.strip()
        clean_text = clean_text.replace('\r\n', '\n').replace('\r', '\n')
        clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_text)
        clean_text = re.sub(r'#{1,6}\s*', '', clean_text)
        clean_text = re.sub(r'`(.*?)`', r'\1', clean_text)

        r = self.selection_rect
        cropped_img = self.get_cropped_pil_image()
        if not cropped_img:
            return

        sel_w = float(r.width())
        sel_h = float(r.height())

        # 4. Tạo UnifiedSheetOverlayElement (Cache cho chế độ 'sheet')
        display_lines = []
        for l in clean_text.split('\n'):
            l_clean = re.sub(r'^\s*\[?(?:Đoạn\s*)?\d+\]?[\.:\-\s]*', '', l).strip()
            display_lines.append(l_clean)
        clean_sheet_text = "\n".join(display_lines).strip()

        is_dark, dom_bg, dom_txt, banner_bg = sample_dominant_theme(cropped_img)
        self._cached_sheet_element = UnifiedSheetOverlayElement(
            QRectF(r.left(), r.top(), sel_w, sel_h),
            clean_sheet_text,
            is_dark_theme=is_dark,
            bg_color=dom_bg,
            text_color=dom_txt,
            banner_bg=banner_bg
        )

        # 5. Tạo BlockOverlayElements (Cache cho chế độ 'blocks')
        from ocr_translate import perform_ocr, is_ocr_reliable, translate_text
        ocr_lang = self.cfg.get("ocr_lang", "auto")
        ocr_res = perform_ocr(cropped_img, lang=ocr_lang)
        reliable = is_ocr_reliable(ocr_res)

        blocks = []
        if reliable:
            from ai_engine import extract_ocr_paragraphs
            _, blocks = extract_ocr_paragraphs(cropped_img, lang=ocr_lang)
            if not blocks:
                blocks = cluster_lines_into_blocks(ocr_res.get("lines", []))

        # Nếu OCR không nhận diện được khối chữ (tiếng Hindi, Nhật, Hàn, Thái, Ả Rập, v.v.),
        # dùng Gemini Vision nhận diện bounding box từng khối chuẩn xác 100%
        if not blocks:
            from ai_engine import ai_translate_image_blocks
            blocks = ai_translate_image_blocks(cropped_img, target_lang=self.target_lang)

        valid_blocks = []
        for blk in blocks:
            orig = blk.get('original', '').strip()
            trans = blk.get('translated', '').strip()
            if len(orig) < 2 and len(trans) < 2:
                continue
            bw = float(blk.get('w', 0.0))
            bh = float(blk.get('h', 0.0))
            if bw < 8.0 or bh < 6.0:
                continue
            valid_blocks.append(blk)

        self._cached_block_elements = []
        if valid_blocks:
            # Dịch những block chưa có bản dịch (nếu lấy từ Windows OCR)
            needs_translation = [b for b in valid_blocks if not b.get('translated')]
            if needs_translation:
                orig_texts = [b['original'].replace('\n', ' ').strip() for b in needs_translation]
                batch_query = " @@ ".join(orig_texts)
                translated_batch = translate_text(batch_query, target_lang=self.target_lang)
                parts = [p.strip() for p in translated_batch.split("@@")]

                if len(parts) == len(needs_translation):
                    for i, blk in enumerate(needs_translation):
                        blk['translated'] = parts[i]
                else:
                    for blk in needs_translation:
                        blk['translated'] = translate_text(blk['original'], target_lang=self.target_lang)

            for blk in valid_blocks:
                para = blk.get('translated', '').strip()
                if not para:
                    continue

                orig_bx = float(blk.get('x', 0.0))
                orig_by = float(blk.get('y', 0.0))
                orig_bw = float(blk.get('w', 40.0))
                orig_bh = float(blk.get('h', 16.0))

                bg_c, txt_c, is_photo = sample_block_colors(cropped_img, orig_bx, orig_by, orig_bw, orig_bh)
                if is_photo:
                    continue

                bx = float(r.left() + orig_bx)
                by = float(r.top() + orig_by)
                bw = float(orig_bw)
                bh = float(orig_bh)

                avg_line_h = float(blk.get('avg_line_h', bh / max(1, blk.get('num_lines', 1))))
                base_fsize = max(8, int(avg_line_h * 0.72))

                block_el = BlockOverlayElement(
                    QRectF(bx, by, bw, bh),
                    blk.get('original', ''),
                    para,
                    bg_color=bg_c,
                    text_color=txt_c,
                    base_font_size=base_fsize
                )
                self._cached_block_elements.append(block_el)

        # 6. Luôn luôn đè theo từng vị trí chữ gốc
        if self._cached_block_elements:
            self.elements.extend(self._cached_block_elements)
            self._current_overlay_mode = "blocks"
            self.show_toast("✓ Đã đè theo từng vị trí (Bấm Tab: Về ảnh gốc)")
        else:
            self.show_toast("⚠️ Không tìm thấy khối văn bản để đè vị trí")

        self.redo_stack.clear()
        self._update_overlay_button_states(bool(self._cached_block_elements))
        self.update_toolbars_pos()
        self.update()

    def switch_translation_overlay_mode(self):
        """
        Chuyển đổi qua lại giữa 2 trạng thái duy nhất bằng phím Tab hoặc nút Đè:
        1. 'blocks': Đè từng vị trí chữ gốc 1:1
        2. 'original': Về ảnh gốc ban đầu
        """
        if self.has_translation_overlay():
            self._current_overlay_mode = "original"
            self.remove_translation_overlay(silent=True)
            self._update_overlay_button_states(False)
            self.show_toast("🔍 Đã về ảnh gốc (Bấm Tab: Dịch đè vị trí)")
            return

        if not hasattr(self, '_last_translation_text') or not self._last_translation_text:
            if hasattr(self, 'ai_card') and getattr(self.ai_card, 'last_ai_result', None):
                self._last_translation_text = self.ai_card.last_ai_result.strip()
            elif hasattr(self, 'trans_card') and hasattr(self.trans_card, 'txt_translated'):
                self._last_translation_text = self.trans_card.txt_translated.toPlainText().strip()

        if hasattr(self, '_last_translation_text') and self._last_translation_text:
            self.apply_ai_translation_overlay(self._last_translation_text, force_mode="blocks")

    def toggle_translation_overlay(self):
        self.switch_translation_overlay_mode()

    def open_dual_compare_window(self):
        """
        Mở Cửa sổ So Sánh Song Song (Dual-Window Split View):
        Bên trái là ảnh gốc, bên phải là bản dịch đã đè chữ/kính mờ
        """
        if not self.selection_rect.isValid() or self.selection_rect.isEmpty():
            self.show_toast("⚠️ Chưa có vùng ảnh được chọn để so sánh!")
            return

        r = self.selection_rect
        orig_pix = self.screen_pixmap.copy(r)

        # 1. Render Block Pixmap
        block_pix = None
        if getattr(self, '_cached_block_elements', None):
            block_pix = orig_pix.copy()
            p = QPainter(block_pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            p.translate(-r.left(), -r.top())
            for el in self._cached_block_elements:
                el.draw(p)
            p.end()

        # 2. Render Sheet Pixmap
        sheet_pix = None
        if getattr(self, '_cached_sheet_element', None):
            sheet_pix = orig_pix.copy()
            p = QPainter(sheet_pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            p.translate(-r.left(), -r.top())
            self._cached_sheet_element.draw(p)
            p.end()

        trans_pix = self.get_rendered_selection_image() or block_pix or sheet_pix or orig_pix
        text = getattr(self, '_last_translation_text', '') or ''
        if not text and hasattr(self, 'ai_card'):
            text = self.ai_card.last_ai_result or ''

        from dual_compare_window import DualCompareWindow
        if not hasattr(self, '_dual_window') or not self._dual_window:
            self._dual_window = DualCompareWindow()

        self._dual_window.set_content(
            orig_pix,
            translated_pixmap=trans_pix,
            translated_text=text,
            block_pixmap=block_pix,
            sheet_pixmap=sheet_pix
        )
        self._dual_window.show()
        self._dual_window.raise_()
        self._dual_window.activateWindow()
        self.show_toast("🪟 Đã mở Cửa sổ So sánh Song song!")

    def get_rendered_selection_image(self):
        if not self.selection_rect.isValid() or self.selection_rect.isEmpty():
            return None

        r = self.selection_rect
        cropped = self.screen_pixmap.copy(r)
        
        painter = QPainter(cropped)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        painter.translate(-r.left(), -r.top())
        for el in self.elements:
            el.draw(painter)
        painter.end()

        return cropped

    def get_cropped_pil_image(self):
        rendered = self.get_rendered_selection_image()
        if not rendered:
            return None
        qimg = rendered.toImage()
        buffer = qimg.bits().asstring(qimg.sizeInBytes())
        pil_img = Image.frombuffer("RGBA", (qimg.width(), qimg.height()), buffer, "raw", "BGRA", 0, 1)
        return pil_img

    def trigger_capture_flash(self, callback=None):
        """Kích hoạt hiệu ứng chớp sáng chói khung ảnh được chọn khi lưu hoặc sao chép"""
        self._flash_callback = callback
        self.flash_alpha = 230
        self.update()
        if not self.flash_timer.isActive():
            self.flash_timer.start()

    def _step_flash_animation(self):
        """Giảm dần độ chói sáng của khung ảnh mượt mà"""
        self.flash_alpha = max(0, self.flash_alpha - 25)
        self.update()
        if self.flash_alpha <= 0:
            self.flash_timer.stop()
            if self._flash_callback:
                cb = self._flash_callback
                self._flash_callback = None
                cb()

    def copy_to_clipboard(self):
        rendered = self.get_rendered_selection_image()
        if rendered:
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(rendered)
            self.show_toast("✓ Đã sao chép ảnh vào Clipboard!")
            self.trigger_capture_flash(callback=lambda: QTimer.singleShot(160, self.close_overlay))

    def save_to_file(self):
        rendered = self.get_rendered_selection_image()
        if not rendered:
            return

        save_dir = self.cfg.get("save_dir", os.path.join(os.path.expanduser("~"), "Downloads"))
        time_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_file = os.path.join(save_dir, f"Myshot_{time_str}.png")

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu ảnh chụp màn hình",
            default_file,
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;Bitmap (*.bmp)"
        )

        if file_path:
            rendered.save(file_path)
            self.show_toast(f"✓ Đã lưu tại: {os.path.basename(file_path)}")
            self.trigger_capture_flash(callback=lambda: QTimer.singleShot(220, self.close_overlay))

    def print_image(self):
        rendered = self.get_rendered_selection_image()
        if not rendered:
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            painter = QPainter(printer)
            rect = painter.viewport()
            size = rendered.size()
            size.scale(rect.size(), Qt.AspectRatioMode.KeepAspectRatio)
            painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
            painter.setWindow(rendered.rect())
            painter.drawPixmap(0, 0, rendered)
            painter.end()
            self.show_toast("✓ Đã gửi đến máy in!")
            QTimer.singleShot(900, self.close_overlay)

    def show_toast(self, message):
        toast = ToastNotification(message, self)
        toast.move((self.width() - toast.width()) // 2, 60)
        toast.show()
        QTimer.singleShot(2200, toast.deleteLater)

    def closeEvent(self, event):
        try:
            QApplication.instance().removeEventFilter(self)
        except Exception:
            pass
        super().closeEvent(event)

    def close_overlay(self):
        try:
            QApplication.instance().removeEventFilter(self)
        except Exception:
            pass
        self.closed.emit()
        self.close()

    def on_color_changed(self, color: QColor):
        self.current_color = color

    def on_pen_width_changed(self, width: int):
        self.current_pen_width = width
        self.show_toast(f"Độ dày nét: {width}px")

    def on_highlighter_width_changed(self, width: int):
        self.current_highlighter_width = width
        self.show_toast(f"Cỡ bút dạ quang: {width}px")

    def on_font_size_changed(self, size: int):
        self.current_font_size = size
        self.show_toast(f"Cỡ chữ văn bản: {size}pt")

    def on_badge_reset(self, start_num: int):
        self.current_badge_number = start_num
        self.show_toast(f"Số thứ tự bắt đầu từ: {start_num}")

    def on_target_lang_changed(self, lang_code: str):
        self.target_lang = lang_code
        self.cfg["target_lang"] = lang_code
        app_config.save_config(self.cfg)
        if hasattr(self, 'toolbar'):
            self.toolbar.target_lang = lang_code
        if hasattr(self, 'ai_card'):
            self.ai_card.set_target_lang(lang_code)
        try:
            from ai_engine import get_target_lang_display_name
            self.show_toast(f"✓ Ngôn ngữ dịch đích: {get_target_lang_display_name(lang_code)}")
        except Exception:
            self.show_toast(f"✓ Ngôn ngữ dịch đích: {lang_code}")

    def trigger_ai_mode(self, mode: str):
        cropped_img = self.get_cropped_pil_image()
        if not cropped_img:
            return

        self.trans_card.hide()
        self.ai_card.show()
        self.ai_card.raise_()
        self.update_toolbars_pos()
        self.ai_card.set_image(cropped_img, default_task=mode)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        modifiers = event.modifiers()

        # 1. Nhấn ESC sẽ HỦY LỆNH (đóng dialog / hủy vẽ / hủy vùng chọn / thoát overlay)
        if key == Qt.Key.Key_Escape:
            self.handle_escape_cancel()
            event.accept()
            return

        # Phím Space: Bật / Tắt thanh công cụ vẽ nhanh
        if key == Qt.Key.Key_Space and not self.inline_editor.isVisible():
            self.toggle_toolbar()
            event.accept()
            return

        # Phím Tab: Xoay vòng đổi kiểu (Đè vị trí ➔ Bảng đọc ➔ Về ảnh gốc)
        if key == Qt.Key.Key_Tab:
            can_tab = (
                self.has_translation_overlay()
                or getattr(self, '_last_translation_text', None)
                or (hasattr(self, 'ai_card') and getattr(self.ai_card, 'last_ai_result', None))
                or (hasattr(self, 'trans_card') and getattr(self.trans_card, 'txt_translated', None) and self.trans_card.txt_translated.toPlainText().strip())
            )
            if can_tab:
                self.switch_translation_overlay_mode()
                event.accept()
                return

        # 2. Phím tắt tổ hợp Ctrl + ...
        elif modifiers & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_A:
            self.select_full_screen()
            event.accept()
            return
        elif modifiers & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_C:
            self.copy_to_clipboard()
            event.accept()
            return
        elif modifiers & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_S:
            self.save_to_file()
            event.accept()
            return
        elif modifiers & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_P:
            self.print_image()
            event.accept()
            return
        elif modifiers & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_Z:
            self.undo()
            event.accept()
            return
        elif modifiers & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_Y:
            self.redo()
            event.accept()
            return

        # 3. Phím tắt chọn công cụ khi không gõ chữ
        if not self.inline_editor.isVisible():
            if key == Qt.Key.Key_P:
                self.v_toolbar.select_tool("pencil")
            elif key == Qt.Key.Key_L:
                self.v_toolbar.select_tool("line")
            elif key == Qt.Key.Key_A:
                self.v_toolbar.select_tool("arrow")
            elif key == Qt.Key.Key_R:
                self.v_toolbar.select_tool(self.v_toolbar.current_shape)
            elif key == Qt.Key.Key_H:
                self.v_toolbar.select_tool("highlighter")
            elif key == Qt.Key.Key_T:
                self.v_toolbar.select_tool("text")
            elif key == Qt.Key.Key_N:
                self.v_toolbar.select_tool("badge")
            elif key == Qt.Key.Key_E:
                self.v_toolbar.select_tool("eraser")
            elif key == Qt.Key.Key_F9 or key == Qt.Key.Key_M:
                self.trigger_ai_copilot()
            elif key == Qt.Key.Key_F4 or key == Qt.Key.Key_D:
                self.trigger_translation()

        super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Vẽ ảnh gốc màn hình sắc nét 100%, sáng rõ nguyên bản (tuyệt đối không bị tối ảnh)
        painter.drawPixmap(0, 0, self.screen_pixmap)

        # 2. Xử lý hiển thị lớp phủ và trạng thái chọn
        if not self.selection_rect.isValid() or self.selection_rect.isEmpty():
            # Chưa có vùng chọn: Giữ nguyên 100% độ sáng gốc của màn hình (chỉ phủ một lớp sương mờ siêu nhẹ 10 alpha để màn hình không bao giờ bị tối xỉn màu)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 10))

            # Thước ngắm chữ thập (Sniper Crosshair Guide Lines) chạy theo con trỏ chuột
            if hasattr(self, 'mouse_pos') and self.mouse_pos.x() >= 0:
                mx, my = self.mouse_pos.x(), self.mouse_pos.y()
                cross_pen = QPen(QColor(99, 102, 241, 140), 1.0, Qt.PenStyle.DashLine)
                painter.setPen(cross_pen)
                painter.drawLine(0, my, self.width(), my)
                painter.drawLine(mx, 0, mx, self.height())

            # Thanh hướng dẫn mini dạng Floating Pill ở đỉnh màn hình
            hint_text = "📸 Kéo chuột để chọn vùng chụp  •  Nhấp đúp: Toàn màn hình  •  ESC: Hủy"
            font = QFont("Segoe UI Variable Display", 9, QFont.Weight.DemiBold)
            painter.setFont(font)
            fm = QFontMetrics(font)
            hw = fm.horizontalAdvance(hint_text) + 28
            hh = 28
            hx = (self.width() - hw) // 2
            hy = 20
            hrect = QRect(hx, hy, hw, hh)

            painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
            painter.setBrush(QBrush(QColor(15, 23, 42, 225)))
            painter.drawRoundedRect(hrect, 14, 14)

            painter.setPen(QPen(QColor(248, 250, 252)))
            painter.drawText(hrect, Qt.AlignmentFlag.AlignCenter, hint_text)
        else:
            # Đã có vùng chọn: Phủ lớp mờ mềm mại bên ngoài, khoét rỗng vùng chọn để bên trong SÁNG RÕ 100%
            r = self.selection_rect
            mask_path = QPainterPath()
            mask_path.addRect(QRectF(self.rect()))
            mask_path.addRect(QRectF(r))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(15, 23, 42, 45)))
            painter.drawPath(mask_path)

            # 3. Vẽ các phần tử vẽ & khối đè bản dịch trên vùng chọn
            painter.save()
            for el in self.elements:
                el.draw(painter)
            if self.current_element:
                self.current_element.draw(painter)
            painter.restore()

            # 4. Viền khung ảnh chọn: viền Neon Indigo kết hợp viền ánh sáng trong suốt tinh tế
            border_pen = QPen(QColor(99, 102, 241, 245), 2.0, Qt.PenStyle.SolidLine)
            painter.setPen(border_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(r)
            # Viền sáng trong giúp khung ảnh luôn nổi bật, sáng rõ không bị tối
            inner_glow_pen = QPen(QColor(255, 255, 255, 90), 1.0)
            painter.setPen(inner_glow_pen)
            painter.drawRect(r.adjusted(1, 1, -1, -1))

            # 5. Hiệu ứng chớp sáng khung ảnh (Camera Shutter Flash) khi lưu hoặc copy
            if self.flash_alpha > 0:
                flash_brush = QBrush(QColor(255, 255, 255, self.flash_alpha))
                painter.fillRect(r, flash_brush)
                flash_pen = QPen(QColor(255, 255, 255, min(255, self.flash_alpha + 50)), 3.5)
                painter.setPen(flash_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(r)

            # 6. Các điểm neo tròn và nhãn kích thước (chỉ hiện khi không chớp sáng)
            if self.flash_alpha <= 0:
                painter.setPen(QPen(QColor(99, 102, 241), 1.5))
                painter.setBrush(QBrush(QColor(255, 255, 255)))
                for hrect in self.get_handle_rects().values():
                    painter.drawEllipse(hrect)

                # Nhãn kích thước dạng Floating Pill
                dim_text = f"{r.width()} × {r.height()}"
                font = QFont("Segoe UI Variable Display", 9, QFont.Weight.Bold)
                painter.setFont(font)
                
                tag_y = r.top() - 26 if r.top() >= 32 else r.top() + 10
                tag_x = r.left() + 10
                tag_rect = QRect(tag_x, tag_y, 90, 22)
                
                painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
                painter.setBrush(QBrush(QColor(13, 17, 26, 230)))
                painter.drawRoundedRect(tag_rect, 11, 11)
                
                painter.setPen(QPen(QColor(248, 250, 252)))
                painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, dim_text)

                # Nút bật / tắt thanh công cụ (Mặc định ẩn, bấm nút hoặc nhấn Space để hiện/ẩn)
                self.toolbar_toggle_rect = QRect(tag_x + 96, tag_y, 140, 22)
                toggle_hover = self.toolbar_toggle_rect.contains(self.mapFromGlobal(QCursor.pos()))
                
                btn_bg = QColor(99, 102, 241, 230) if toggle_hover else (QColor(99, 102, 241, 100) if self.toolbar.isVisible() else QColor(13, 17, 26, 230))
                painter.setPen(QPen(QColor(255, 255, 255, 50), 1))
                painter.setBrush(QBrush(btn_bg))
                painter.drawRoundedRect(self.toolbar_toggle_rect, 11, 11)
                
                painter.setFont(QFont("Segoe UI Variable Display", 8, QFont.Weight.Bold))
                painter.setPen(QColor(255, 255, 255))
                toggle_label = "✕ Ẩn công cụ (Space)" if self.toolbar.isVisible() else "🛠️ Hiện công cụ (Space)"
                painter.drawText(self.toolbar_toggle_rect, Qt.AlignmentFlag.AlignCenter, toggle_label)
            else:
                self.toolbar_toggle_rect = QRect()
