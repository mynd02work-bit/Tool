import math
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QPainter, QPainterPath, QPen, QColor, QBrush, QFont
from PyQt6.QtCore import Qt, QPointF, QRectF, QSize, pyqtSignal

class LineIconButton(QPushButton):
    """
    Nút bấm vẽ Icon dạng Line / Stroke tối giản, sắc nét tuyệt đối (Figma / Linear Style)
    """
    right_clicked = pyqtSignal(QPointF)

    def __init__(self, icon_type: str, tooltip: str = "", size: int = 32, has_submenu: bool = False, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.icon_type = icon_type
        self.setFixedSize(size, size)
        if tooltip:
            self.setToolTip(tooltip)
        self.is_active = False
        self.has_submenu = has_submenu

    def set_active(self, active: bool):
        self.is_active = active
        self.update()

    def set_icon_type(self, icon_type: str, tooltip: str = ""):
        self.icon_type = icon_type
        if tooltip:
            self.setToolTip(tooltip)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(event.globalPosition())
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        rect = self.rect()

        # Nền khi Hover hoặc Active hoặc Normal
        is_hovered = self.underMouse()
        if self.is_active:
            # Active: Nền tím Indigo nổi bật
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(99, 102, 241)))  # Indigo #6366F1
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 7, 7)
            stroke_color = QColor(255, 255, 255)
            pen_width = 2.2
        elif is_hovered:
            # Hover: Nền sáng nhẹ với viền sáng
            painter.setPen(QPen(QColor(99, 102, 241, 180), 1))
            painter.setBrush(QBrush(QColor(99, 102, 241, 60)))
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 7, 7)
            stroke_color = QColor(255, 255, 255)
            pen_width = 2.2
        else:
            # Bình thường: Nền mờ tối nhẹ và viền mỏng giúp icon nổi bật rõ nét trên mọi nền
            painter.setPen(QPen(QColor(255, 255, 255, 20), 1))
            painter.setBrush(QBrush(QColor(255, 255, 255, 12)))
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 7, 7)
            stroke_color = QColor(248, 250, 252)  # Trắng sáng rõ ràng, đậm đà
            pen_width = 2.0

        # Cài đặt bút vẽ line icon đậm và sắc nét
        pen = QPen(stroke_color, pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        cx = w / 2.0
        cy = h / 2.0

        t = self.icon_type
        if t == "pencil":
            path = QPainterPath()
            path.moveTo(cx - 6, cy + 6)
            path.lineTo(cx + 4, cy - 4)
            path.lineTo(cx + 6, cy - 2)
            path.lineTo(cx - 4, cy + 8)
            path.closeSubpath()
            painter.drawPath(path)
            # Đầu bút
            painter.drawLine(QPointF(cx - 6, cy + 6), QPointF(cx - 7, cy + 7))

        elif t == "line":
            painter.drawLine(QPointF(cx - 7, cy + 7), QPointF(cx + 7, cy - 7))

        elif t == "arrow":
            # Đường thân mũi tên
            painter.drawLine(QPointF(cx - 7, cy + 6), QPointF(cx + 6, cy - 7))
            # Đầu mũi tên
            path = QPainterPath()
            path.moveTo(cx + 1, cy - 7)
            path.lineTo(cx + 6, cy - 7)
            path.lineTo(cx + 6, cy - 2)
            painter.drawPath(path)

        elif t == "double_arrow":
            painter.drawLine(QPointF(cx - 5, cy + 5), QPointF(cx + 5, cy - 5))
            p1 = QPainterPath()
            p1.moveTo(cx + 1, cy - 5)
            p1.lineTo(cx + 5, cy - 5)
            p1.lineTo(cx + 5, cy - 1)
            painter.drawPath(p1)
            p2 = QPainterPath()
            p2.moveTo(cx - 1, cy + 5)
            p2.lineTo(cx - 5, cy + 5)
            p2.lineTo(cx - 5, cy + 1)
            painter.drawPath(p2)

        elif t == "rect":
            painter.drawRoundedRect(QRectF(cx - 7, cy - 6, 14, 12), 2, 2)

        elif t == "rect_fill":
            painter.setBrush(QBrush(stroke_color))
            painter.drawRoundedRect(QRectF(cx - 7, cy - 6, 14, 12), 2, 2)
            painter.setBrush(Qt.BrushStyle.NoBrush)

        elif t == "ellipse":
            painter.drawEllipse(QPointF(cx, cy), 7, 7)

        elif t == "ellipse_fill":
            painter.setBrush(QBrush(stroke_color))
            painter.drawEllipse(QPointF(cx, cy), 7, 7)
            painter.setBrush(Qt.BrushStyle.NoBrush)

        elif t == "triangle":
            path = QPainterPath()
            path.moveTo(cx, cy - 7)
            path.lineTo(cx + 7, cy + 6)
            path.lineTo(cx - 7, cy + 6)
            path.closeSubpath()
            painter.drawPath(path)

        elif t == "trapezoid":
            path = QPainterPath()
            path.moveTo(cx - 4, cy - 6)
            path.lineTo(cx + 4, cy - 6)
            path.lineTo(cx + 7, cy + 6)
            path.lineTo(cx - 7, cy + 6)
            path.closeSubpath()
            painter.drawPath(path)

        elif t == "parallelogram":
            path = QPainterPath()
            path.moveTo(cx - 3, cy - 6)
            path.lineTo(cx + 7, cy - 6)
            path.lineTo(cx + 3, cy + 6)
            path.lineTo(cx - 7, cy + 6)
            path.closeSubpath()
            painter.drawPath(path)

        elif t == "blur":
            # Icon mosaic 4 chấm vuông tinh tế
            for gx in (-4, 3):
                for gy in (-4, 3):
                    painter.fillRect(QRectF(cx + gx - 1.5, cy + gy - 1.5, 3.5, 3.5), stroke_color)

        elif t == "highlighter":
            # Đầu bút dạ quang xéo
            path = QPainterPath()
            path.moveTo(cx - 5, cy + 5)
            path.lineTo(cx + 3, cy - 3)
            path.lineTo(cx + 7, cy + 1)
            path.lineTo(cx - 1, cy + 9)
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawLine(QPointF(cx - 5, cy + 5), QPointF(cx - 7, cy + 7))

        elif t == "text":
            # Chữ T đậm nét hiện đại
            font = QFont("Segoe UI", 11, QFont.Weight.Black)
            painter.setFont(font)
            painter.setPen(stroke_color)
            painter.drawText(QRectF(cx - 8, cy - 8, 16, 16), Qt.AlignmentFlag.AlignCenter, "T")

        elif t == "badge":
            # Vòng tròn đậm nét với số 1 bên trong
            painter.drawEllipse(QPointF(cx, cy), 7, 7)
            font = QFont("Segoe UI", 8, QFont.Weight.Black)
            painter.setFont(font)
            painter.setPen(stroke_color)
            painter.drawText(QRectF(cx - 7, cy - 7, 14, 14), Qt.AlignmentFlag.AlignCenter, "1")

        elif t == "undo":
            # Mũi tên cong quay lại
            path = QPainterPath()
            path.moveTo(cx + 5, cy + 4)
            path.cubicTo(cx + 5, cy - 5, cx - 4, cy - 5, cx - 4, cy)
            painter.drawPath(path)
            painter.drawLine(QPointF(cx - 7, cy - 3), QPointF(cx - 4, cy))
            painter.drawLine(QPointF(cx - 1, cy - 3), QPointF(cx - 4, cy))

        elif t == "redo":
            # Mũi tên cong làm lại
            path = QPainterPath()
            path.moveTo(cx - 5, cy + 4)
            path.cubicTo(cx - 5, cy - 5, cx + 4, cy - 5, cx + 4, cy)
            painter.drawPath(path)
            painter.drawLine(QPointF(cx + 7, cy - 3), QPointF(cx + 4, cy))
            painter.drawLine(QPointF(cx + 1, cy - 3), QPointF(cx + 4, cy))

        elif t == "sparkle":
            # Nền tím AI nổi bật
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(139, 92, 246, 220)))
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 7, 7)

            # Ngôi sao 4 cánh AI sắc nét
            path = QPainterPath()
            path.moveTo(cx, cy - 7)
            path.quadTo(cx, cy, cx + 7, cy)
            path.quadTo(cx, cy, cx, cy + 7)
            path.quadTo(cx, cy, cx - 7, cy)
            path.quadTo(cx, cy, cx, cy - 7)
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawPath(path)
            painter.setBrush(Qt.BrushStyle.NoBrush)

        elif t == "globe":
            # Quả địa cầu line icon
            painter.drawEllipse(QPointF(cx, cy), 7, 7)
            painter.drawLine(QPointF(cx - 7, cy), QPointF(cx + 7, cy))
            painter.drawEllipse(QRectF(cx - 3.5, cy - 7, 7, 14))

        elif t == "copy":
            # 2 hình vuông lồng nhau
            painter.drawRoundedRect(QRectF(cx - 6, cy - 4, 9, 10), 1.5, 1.5)
            path = QPainterPath()
            path.moveTo(cx - 3, cy - 4)
            path.lineTo(cx - 3, cy - 7)
            path.lineTo(cx + 6, cy - 7)
            path.lineTo(cx + 6, cy + 3)
            path.lineTo(cx + 3, cy + 3)
            painter.drawPath(path)

        elif t == "save":
            # Đĩa mềm / Khay tải xuống line icon
            path = QPainterPath()
            path.moveTo(cx - 6, cy - 6)
            path.lineTo(cx + 4, cy - 6)
            path.lineTo(cx + 6, cy - 4)
            path.lineTo(cx + 6, cy + 6)
            path.lineTo(cx - 6, cy + 6)
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawLine(QPointF(cx - 3, cy + 6), QPointF(cx - 3, cy + 2))
            painter.drawLine(QPointF(cx + 3, cy + 6), QPointF(cx + 3, cy + 2))

        elif t == "print":
            # Máy in line icon
            painter.drawRoundedRect(QRectF(cx - 7, cy - 3, 14, 8), 1.5, 1.5)
            painter.drawLine(QPointF(cx - 4, cy - 3), QPointF(cx - 4, cy - 6))
            painter.drawLine(QPointF(cx - 4, cy - 6), QPointF(cx + 4, cy - 6))
            painter.drawLine(QPointF(cx + 4, cy - 6), QPointF(cx + 4, cy - 3))
            painter.drawLine(QPointF(cx - 4, cy + 5), QPointF(cx + 4, cy + 5))

        elif t == "close":
            # Dấu X mảnh dẻ
            painter.drawLine(QPointF(cx - 4, cy - 4), QPointF(cx + 4, cy + 4))
            painter.drawLine(QPointF(cx + 4, cy - 4), QPointF(cx - 4, cy + 4))

        elif t == "eraser":
            # Cục tẩy nghiêng hiện đại phong cách Figma
            path = QPainterPath()
            path.moveTo(cx - 6, cy + 1)
            path.lineTo(cx - 1, cy + 6)
            path.lineTo(cx + 6, cy - 1)
            path.lineTo(cx + 1, cy - 6)
            path.closeSubpath()
            painter.drawPath(path)
            # Vạch chia ngăn phần đầu tẩy và thân tẩy
            painter.drawLine(QPointF(cx - 2, cy - 3), QPointF(cx + 3, cy + 2))
            # Đường gạch chân đáy tẩy
            painter.drawLine(QPointF(cx - 7, cy + 6), QPointF(cx - 1, cy + 6))
