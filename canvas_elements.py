import math
from PyQt6.QtCore import QPointF, QRectF, QRect, Qt
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath, QFontMetrics, QPixmap, QPolygonF, QTextDocument
)

def dist_point_to_segment(p: QPointF, a: QPointF, b: QPointF) -> float:
    """Tính khoảng cách vuông góc từ điểm p đến đoạn thẳng nối 2 điểm a và b"""
    px, py = p.x(), p.y()
    ax, ay = a.x(), a.y()
    bx, by = b.x(), b.y()
    dx = bx - ax
    dy = by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    closest_x = ax + t * dx
    closest_y = ay + t * dy
    return math.hypot(px - closest_x, py - closest_y)

class CanvasElement:
    def draw(self, painter: QPainter):
        pass

    def contains_point(self, pt: QPointF, tolerance: float = 8.0) -> bool:
        return False

class PencilElement(CanvasElement):
    def __init__(self, color: QColor, width: int):
        self.color = color
        self.width = width
        self.points = []

    def add_point(self, pt: QPointF):
        self.points.append(pt)

    def draw(self, painter: QPainter):
        if len(self.points) < 2:
            if len(self.points) == 1:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(self.color))
                painter.drawEllipse(self.points[0], self.width / 2, self.width / 2)
            return

        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        path = QPainterPath()
        path.moveTo(self.points[0])
        for i in range(1, len(self.points)):
            p0 = self.points[i - 1]
            p1 = self.points[i]
            mid = QPointF((p0.x() + p1.x()) / 2, (p0.y() + p1.y()) / 2)
            path.quadTo(p0, mid)
        path.lineTo(self.points[-1])
        painter.drawPath(path)

    def contains_point(self, pt: QPointF, tolerance: float = 8.0) -> bool:
        thresh = self.width / 2.0 + tolerance
        if not self.points:
            return False
        if len(self.points) == 1:
            return math.hypot(pt.x() - self.points[0].x(), pt.y() - self.points[0].y()) <= thresh
        for i in range(len(self.points) - 1):
            if dist_point_to_segment(pt, self.points[i], self.points[i + 1]) <= thresh:
                return True
        return False

class HighlighterElement(CanvasElement):
    def __init__(self, color: QColor, width: int = 20):
        c = QColor(color)
        c.setAlpha(95)  # Bút dạ quang bán trong suốt
        self.color = c
        self.width = width
        self.points = []

    def add_point(self, pt: QPointF):
        self.points.append(pt)

    def draw(self, painter: QPainter):
        if len(self.points) < 2:
            return
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        path = QPainterPath()
        path.moveTo(self.points[0])
        for p in self.points[1:]:
            path.lineTo(p)
        painter.drawPath(path)

    def contains_point(self, pt: QPointF, tolerance: float = 8.0) -> bool:
        thresh = self.width / 2.0 + tolerance
        if not self.points:
            return False
        if len(self.points) == 1:
            return math.hypot(pt.x() - self.points[0].x(), pt.y() - self.points[0].y()) <= thresh
        for i in range(len(self.points) - 1):
            if dist_point_to_segment(pt, self.points[i], self.points[i + 1]) <= thresh:
                return True
        return False

class LineElement(CanvasElement):
    def __init__(self, p1: QPointF, p2: QPointF, color: QColor, width: int):
        self.p1 = p1
        self.p2 = p2
        self.color = color
        self.width = width

    def draw(self, painter: QPainter):
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(self.p1, self.p2)

    def contains_point(self, pt: QPointF, tolerance: float = 8.0) -> bool:
        return dist_point_to_segment(pt, self.p1, self.p2) <= (self.width / 2.0 + tolerance)

class ArrowElement(CanvasElement):
    def __init__(self, p1: QPointF, p2: QPointF, color: QColor, width: int):
        self.p1 = p1
        self.p2 = p2
        self.color = color
        self.width = width

    def draw(self, painter: QPainter):
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(self.p1, self.p2)

        # Vẽ mũi tên ở p2
        dx = self.p2.x() - self.p1.x()
        dy = self.p2.y() - self.p1.y()
        length = math.hypot(dx, dy)
        if length < 5:
            return

        angle = math.atan2(dy, dx)
        arrow_size = max(14.0, self.width * 3.5)
        arrow_angle = math.pi / 6  # 30 độ

        p_arrow1 = QPointF(
            self.p2.x() - arrow_size * math.cos(angle - arrow_angle),
            self.p2.y() - arrow_size * math.sin(angle - arrow_angle)
        )
        p_arrow2 = QPointF(
            self.p2.x() - arrow_size * math.cos(angle + arrow_angle),
            self.p2.y() - arrow_size * math.sin(angle + arrow_angle)
        )

        arrow_path = QPainterPath()
        arrow_path.moveTo(self.p2)
        arrow_path.lineTo(p_arrow1)
        arrow_path.lineTo(p_arrow2)
        arrow_path.closeSubpath()

        painter.setBrush(QBrush(self.color))
        painter.drawPath(arrow_path)

    def contains_point(self, pt: QPointF, tolerance: float = 8.0) -> bool:
        return dist_point_to_segment(pt, self.p1, self.p2) <= (max(self.width, 14) / 2.0 + tolerance)

class RectElement(CanvasElement):
    def __init__(self, p1: QPointF, p2: QPointF, color: QColor, width: int):
        self.p1 = p1
        self.p2 = p2
        self.color = color
        self.width = width

    def draw(self, painter: QPainter):
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap, Qt.PenJoinStyle.MiterJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        rect = QRectF(self.p1, self.p2).normalized()
        painter.drawRoundedRect(rect, 2, 2)

    def contains_point(self, pt: QPointF, tolerance: float = 8.0) -> bool:
        r = QRectF(self.p1, self.p2).normalized().adjusted(-tolerance, -tolerance, tolerance, tolerance)
        return r.contains(pt)

class FilledRectElement(CanvasElement):
    def __init__(self, p1: QPointF, p2: QPointF, color: QColor, width: int = 1, alpha: int = 70):
        self.p1 = p1
        self.p2 = p2
        self.color = color
        self.width = width
        self.alpha = alpha

    def draw(self, painter: QPainter):
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap, Qt.PenJoinStyle.MiterJoin)
        painter.setPen(pen)
        fill_color = QColor(self.color)
        fill_color.setAlpha(self.alpha)
        painter.setBrush(QBrush(fill_color))
        rect = QRectF(self.p1, self.p2).normalized()
        painter.drawRoundedRect(rect, 4, 4)

    def contains_point(self, pt: QPointF, tolerance: float = 8.0) -> bool:
        r = QRectF(self.p1, self.p2).normalized().adjusted(-tolerance, -tolerance, tolerance, tolerance)
        return r.contains(pt)

class EllipseElement(CanvasElement):
    def __init__(self, p1: QPointF, p2: QPointF, color: QColor, width: int):
        self.p1 = p1
        self.p2 = p2
        self.color = color
        self.width = width

    def draw(self, painter: QPainter):
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        rect = QRectF(self.p1, self.p2).normalized()
        painter.drawEllipse(rect)

    def contains_point(self, pt: QPointF, tolerance: float = 8.0) -> bool:
        r = QRectF(self.p1, self.p2).normalized()
        rx = r.width() / 2.0 + tolerance
        ry = r.height() / 2.0 + tolerance
        if rx <= 0 or ry <= 0: return False
        cx, cy = r.center().x(), r.center().y()
        return (((pt.x() - cx) / rx) ** 2 + ((pt.y() - cy) / ry) ** 2) <= 1.0

class FilledEllipseElement(CanvasElement):
    def __init__(self, p1: QPointF, p2: QPointF, color: QColor, width: int = 1, alpha: int = 70):
        self.p1 = p1
        self.p2 = p2
        self.color = color
        self.width = width
        self.alpha = alpha

    def draw(self, painter: QPainter):
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        fill_color = QColor(self.color)
        fill_color.setAlpha(self.alpha)
        painter.setBrush(QBrush(fill_color))
        rect = QRectF(self.p1, self.p2).normalized()
        painter.drawEllipse(rect)

    def contains_point(self, pt: QPointF, tolerance: float = 8.0) -> bool:
        r = QRectF(self.p1, self.p2).normalized()
        rx = r.width() / 2.0 + tolerance
        ry = r.height() / 2.0 + tolerance
        if rx <= 0 or ry <= 0: return False
        cx, cy = r.center().x(), r.center().y()
        return (((pt.x() - cx) / rx) ** 2 + ((pt.y() - cy) / ry) ** 2) <= 1.0

class TriangleElement(CanvasElement):
    """Hình tam giác"""
    def __init__(self, p1: QPointF, p2: QPointF, color: QColor, width: int):
        self.p1 = p1
        self.p2 = p2
        self.color = color
        self.width = width

    def _get_points(self):
        r = QRectF(self.p1, self.p2).normalized()
        top_p = QPointF(r.center().x(), r.top())
        bl_p = QPointF(r.left(), r.bottom())
        br_p = QPointF(r.right(), r.bottom())
        return top_p, br_p, bl_p

    def draw(self, painter: QPainter):
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        top_p, br_p, bl_p = self._get_points()
        painter.drawPolygon(QPolygonF([top_p, br_p, bl_p]))

    def contains_point(self, pt: QPointF, tolerance: float = 8.0) -> bool:
        top_p, br_p, bl_p = self._get_points()
        poly = QPolygonF([top_p, br_p, bl_p])
        if poly.containsPoint(pt, Qt.FillRule.OddEvenFill):
            return True
        thresh = self.width / 2.0 + tolerance
        if dist_point_to_segment(pt, top_p, br_p) <= thresh: return True
        if dist_point_to_segment(pt, br_p, bl_p) <= thresh: return True
        if dist_point_to_segment(pt, bl_p, top_p) <= thresh: return True
        return False

class TrapezoidElement(CanvasElement):
    """Hình thang cân"""
    def __init__(self, p1: QPointF, p2: QPointF, color: QColor, width: int):
        self.p1 = p1
        self.p2 = p2
        self.color = color
        self.width = width

    def _get_points(self):
        r = QRectF(self.p1, self.p2).normalized()
        inset = r.width() * 0.22
        tl = QPointF(r.left() + inset, r.top())
        tr = QPointF(r.right() - inset, r.top())
        br = QPointF(r.right(), r.bottom())
        bl = QPointF(r.left(), r.bottom())
        return tl, tr, br, bl

    def draw(self, painter: QPainter):
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        tl, tr, br, bl = self._get_points()
        painter.drawPolygon(QPolygonF([tl, tr, br, bl]))

    def contains_point(self, pt: QPointF, tolerance: float = 8.0) -> bool:
        tl, tr, br, bl = self._get_points()
        poly = QPolygonF([tl, tr, br, bl])
        if poly.containsPoint(pt, Qt.FillRule.OddEvenFill):
            return True
        thresh = self.width / 2.0 + tolerance
        if dist_point_to_segment(pt, tl, tr) <= thresh: return True
        if dist_point_to_segment(pt, tr, br) <= thresh: return True
        if dist_point_to_segment(pt, br, bl) <= thresh: return True
        if dist_point_to_segment(pt, bl, tl) <= thresh: return True
        return False

class ParallelogramElement(CanvasElement):
    """Hình bình hành"""
    def __init__(self, p1: QPointF, p2: QPointF, color: QColor, width: int):
        self.p1 = p1
        self.p2 = p2
        self.color = color
        self.width = width

    def _get_points(self):
        r = QRectF(self.p1, self.p2).normalized()
        skew = r.width() * 0.25
        tl = QPointF(r.left() + skew, r.top())
        tr = QPointF(r.right(), r.top())
        br = QPointF(r.right() - skew, r.bottom())
        bl = QPointF(r.left(), r.bottom())
        return tl, tr, br, bl

    def draw(self, painter: QPainter):
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        tl, tr, br, bl = self._get_points()
        painter.drawPolygon(QPolygonF([tl, tr, br, bl]))

    def contains_point(self, pt: QPointF, tolerance: float = 8.0) -> bool:
        tl, tr, br, bl = self._get_points()
        poly = QPolygonF([tl, tr, br, bl])
        if poly.containsPoint(pt, Qt.FillRule.OddEvenFill):
            return True
        thresh = self.width / 2.0 + tolerance
        if dist_point_to_segment(pt, tl, tr) <= thresh: return True
        if dist_point_to_segment(pt, tr, br) <= thresh: return True
        if dist_point_to_segment(pt, br, bl) <= thresh: return True
        if dist_point_to_segment(pt, bl, tl) <= thresh: return True
        return False

class DoubleArrowElement(CanvasElement):
    def __init__(self, p1: QPointF, p2: QPointF, color: QColor, width: int):
        self.p1 = p1
        self.p2 = p2
        self.color = color
        self.width = width

    def draw(self, painter: QPainter):
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(self.p1, self.p2)

        dx = self.p2.x() - self.p1.x()
        dy = self.p2.y() - self.p1.y()
        length = math.hypot(dx, dy)
        if length < 8:
            return

        angle = math.atan2(dy, dx)
        arrow_size = max(13.0, self.width * 3.5)
        arrow_angle = math.pi / 6

        # Mũi tên ở p2
        p2_a1 = QPointF(self.p2.x() - arrow_size * math.cos(angle - arrow_angle), self.p2.y() - arrow_size * math.sin(angle - arrow_angle))
        p2_a2 = QPointF(self.p2.x() - arrow_size * math.cos(angle + arrow_angle), self.p2.y() - arrow_size * math.sin(angle + arrow_angle))
        path2 = QPainterPath()
        path2.moveTo(self.p2)
        path2.lineTo(p2_a1)
        path2.lineTo(p2_a2)
        path2.closeSubpath()

        # Mũi tên ở p1
        p1_a1 = QPointF(self.p1.x() + arrow_size * math.cos(angle - arrow_angle), self.p1.y() + arrow_size * math.sin(angle - arrow_angle))
        p1_a2 = QPointF(self.p1.x() + arrow_size * math.cos(angle + arrow_angle), self.p1.y() + arrow_size * math.sin(angle + arrow_angle))
        path1 = QPainterPath()
        path1.moveTo(self.p1)
        path1.lineTo(p1_a1)
        path1.lineTo(p1_a2)
        path1.closeSubpath()

        painter.setBrush(QBrush(self.color))
        painter.drawPath(path2)
        painter.drawPath(path1)

    def contains_point(self, pt: QPointF, tolerance: float = 8.0) -> bool:
        return dist_point_to_segment(pt, self.p1, self.p2) <= (max(self.width, 14) / 2.0 + tolerance)

class BlurElement(CanvasElement):
    """
    Che mờ / làm mờ vùng thông tin nhạy cảm (Mosaic / Blur Box)
    """
    def __init__(self, p1: QPointF, p2: QPointF, color: QColor = None, width: int = 1):
        self.p1 = p1
        self.p2 = p2

    def draw(self, painter: QPainter):
        rect = QRectF(self.p1, self.p2).normalized()
        if rect.width() < 2 or rect.height() < 2:
            return
        painter.save()
        # Nền che thông tin mờ sang trọng với họa tiết sọc chéo
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(15, 23, 42, 235)))
        painter.drawRoundedRect(rect, 4, 4)

        # Viền đứt nét tinh tế
        painter.setPen(QPen(QColor(148, 163, 184, 120), 1.2, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 4, 4)

        # Biểu tượng con mắt khóa / che mờ nhỏ ở giữa nếu đủ chỗ
        if rect.width() > 24 and rect.height() > 16:
            painter.setPen(QPen(QColor(255, 255, 255, 160)))
            font = QFont("Segoe UI", 9)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "•••")
        painter.restore()

    def contains_point(self, pt: QPointF, tolerance: float = 8.0) -> bool:
        r = QRectF(self.p1, self.p2).normalized().adjusted(-tolerance, -tolerance, tolerance, tolerance)
        return r.contains(pt)

class TextElement(CanvasElement):
    def __init__(
        self,
        pos: QPointF,
        text: str,
        color: QColor,
        font_size: int = 16,
        is_bold: bool = True,
        is_italic: bool = False,
        is_underline: bool = False,
        html: str = None
    ):
        self.pos = pos
        self.text = text
        self.color = color
        self.font_size = font_size
        self.is_bold = is_bold
        self.is_italic = is_italic
        self.is_underline = is_underline
        self.html = html

    def draw(self, painter: QPainter):
        if not self.text and not self.html:
            return

        painter.save()
        if self.html:
            # 1. Vẽ bóng mờ chữ sang trọng dễ đọc
            doc_shadow = QTextDocument()
            doc_shadow.setDefaultFont(QFont("Segoe UI", self.font_size))
            c_shadow_css = f"* {{ color: rgba(0, 0, 0, 0.85); font-family: 'Segoe UI', Arial; font-size: {self.font_size}pt; }}"
            doc_shadow.setDefaultStyleSheet(c_shadow_css)
            doc_shadow.setHtml(self.html)

            painter.save()
            painter.translate(self.pos.x() + 1.2, self.pos.y() + 1.2)
            doc_shadow.drawContents(painter)
            painter.restore()

            # 2. Vẽ chữ chính đúng định dạng riêng từng chữ
            doc = QTextDocument()
            doc.setDefaultFont(QFont("Segoe UI", self.font_size))
            c_hex = self.color.name() if hasattr(self.color, 'name') else "#FF3344"
            doc.setDefaultStyleSheet(f"* {{ color: {c_hex}; font-family: 'Segoe UI', Arial; font-size: {self.font_size}pt; }}")
            doc.setHtml(self.html)

            painter.translate(self.pos)
            doc.drawContents(painter)
        else:
            font = QFont("Segoe UI", self.font_size)
            font.setBold(self.is_bold)
            font.setItalic(self.is_italic)
            font.setUnderline(self.is_underline)
            painter.setFont(font)
            
            # Viền bóng mờ cho chữ dễ đọc
            painter.setPen(QPen(QColor(0, 0, 0, 180)))
            painter.drawText(int(self.pos.x() + 1), int(self.pos.y() + 1), self.text)
            
            # Chữ chính
            painter.setPen(QPen(self.color))
            painter.drawText(int(self.pos.x()), int(self.pos.y()), self.text)
        painter.restore()

    def contains_point(self, pt: QPointF, tolerance: float = 8.0) -> bool:
        if self.html:
            doc = QTextDocument()
            doc.setDefaultFont(QFont("Segoe UI", self.font_size))
            doc.setHtml(self.html)
            w = max(doc.idealWidth(), doc.size().width(), 30.0)
            h = max(doc.size().height(), 20.0)
            r = QRectF(self.pos.x(), self.pos.y(), w, h).adjusted(-tolerance, -tolerance, tolerance, tolerance)
            return r.contains(pt)
        else:
            font = QFont("Segoe UI", self.font_size)
            font.setBold(self.is_bold)
            font.setItalic(self.is_italic)
            font.setUnderline(self.is_underline)
            fm = QFontMetrics(font)
            w = max(fm.horizontalAdvance(self.text), 30)
            h = max(fm.height(), 20)
            r = QRectF(self.pos.x(), self.pos.y() - fm.ascent(), w, h).adjusted(-tolerance, -tolerance, tolerance, tolerance)
            return r.contains(pt)

class StepBadgeElement(CanvasElement):
    """
    Số thứ tự tự động tăng / giảm (Step Badge)
    """
    def __init__(self, center: QPointF, number: int, color: QColor, radius: float = 14.0):
        self.center = center
        self.number = number
        self.color = color
        self.radius = radius

    def draw(self, painter: QPainter):
        # Đổ bóng nhẹ
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 70)))
        painter.drawEllipse(self.center, self.radius + 1.5, self.radius + 1.5)

        # Vòng tròn chính
        painter.setBrush(QBrush(self.color))
        painter.drawEllipse(self.center, self.radius, self.radius)

        # Viền trắng
        painter.setPen(QPen(QColor(255, 255, 255, 220), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(self.center, self.radius, self.radius)

        # Số trắng chính giữa
        font = QFont("Segoe UI", int(self.radius * 0.9), QFont.Weight.ExtraBold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 255, 255)))
        
        rect = QRectF(
            self.center.x() - self.radius,
            self.center.y() - self.radius,
            self.radius * 2,
            self.radius * 2
        )
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(self.number))

    def contains_point(self, pt: QPointF, tolerance: float = 8.0) -> bool:
        dx = pt.x() - self.center.x()
        dy = pt.y() - self.center.y()
        return math.hypot(dx, dy) <= (self.radius + tolerance)

def _make_overlay_font(fsize: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    f = QFont("Segoe UI", fsize, weight)
    f.setStyleHint(QFont.StyleHint.SansSerif)
    f.setFamilies(["Segoe UI", "Malgun Gothic", "Microsoft YaHei", "Meiryo", "Arial", "sans-serif"])
    return f

class BlockOverlayElement(CanvasElement):
    """
    Đè bản dịch lên ảnh theo khối đoạn văn (Smart In-place Style-Matched Overlay):
    - Tự động lấy mẫu màu nền (bg_color) và màu chữ (text_color) từ ảnh gốc để tệp màu hoàn toàn.
    - Căn chỉnh font chữ, line-height và cỡ chữ tự động vừa vặn vào khung cũ.
    - Hỗ trợ căn giữa hoàn hảo cho các dòng chữ giao diện/nút bấm đơn dòng và tự động mở rộng bề ngang nếu chữ dịch dài hơn.
    - Vẽ lớp nền khử răng cưa mượt mà, che sạch chữ gốc mà không tạo mảng vá lộ liễu.
    """
    def __init__(
        self,
        rect: QRectF,
        original_text: str,
        translated_text: str,
        bg_color: QColor = None,
        text_color: QColor = None,
        base_font_size: int = 12
    ):
        self.rect = rect
        self.original_text = original_text
        self.translated_text = translated_text.strip()
        self.bg_color = bg_color if bg_color is not None else QColor(255, 255, 255)
        self.text_color = text_color if text_color is not None else QColor(17, 24, 39)
        self.base_font_size = base_font_size

    def contains_point(self, pt: QPointF, tolerance: float = 8.0) -> bool:
        r = self.rect.adjusted(-tolerance, -tolerance, tolerance, tolerance)
        return r.contains(pt)

    def draw(self, painter: QPainter):
        if not self.translated_text:
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        bg = QColor(self.bg_color)
        bg.setAlpha(255)
        txt_c = QColor(self.text_color)
        txt_c.setAlpha(255)

        bw = float(self.rect.width())
        bh = float(self.rect.height())

        # Ước tính số dòng gốc thực tế
        num_orig_lines = max(1, self.original_text.count('\n') + 1)
        if num_orig_lines == 1 and len(self.original_text) > 35 and bh >= 48:
            num_orig_lines = max(2, int(round(bh / 32.0)))

        # Trọng số font: In đậm nếu là tiêu đề lớn, viết hoa, số đếm, hoặc tiêu đề card
        is_bold = (
            (bh >= 38.0 and bh >= 75.0) or
            self.original_text.isupper() or
            (len(self.original_text.strip()) <= 25 and bh >= 30.0) or
            self.original_text.strip().isdigit()
        )
        font_weight = QFont.Weight.Bold if is_bold else QFont.Weight.Normal

        pad_h = max(3.0, bw * 0.015)
        pad_v = max(2.0, bh * 0.02)
        inner_w = max(20.0, bw - pad_h * 2)

        # 1. Kiểm tra xem khối có thực sự là nhãn dòng đơn (badge, counter, nút bấm, nhãn ngắn)
        can_be_single = False
        single_fs = max(8, int(bh * 0.72))
        f_single = _make_overlay_font(single_fs, font_weight)
        fm_single = QFontMetrics(f_single)
        adv_single = fm_single.horizontalAdvance(self.translated_text)

        if '\n' not in self.translated_text and adv_single <= inner_w * 1.02 and (num_orig_lines == 1 or bh < 65):
            can_be_single = True
            best_fs = single_fs
            font = f_single
        elif '\n' not in self.translated_text and bh < 55:
            # Ruy-băng hoặc dải nhãn siêu mỏng (không thể chứa 2 dòng)
            can_be_single = True
            ratio = inner_w / max(1, adv_single)
            best_fs = max(8, int(single_fs * ratio))
            font = _make_overlay_font(best_fs, font_weight)
        else:
            # 2. Khối đoạn văn bản hoặc tiêu đề: Tự động xuống dòng (Word Wrap) và tối ưu cỡ font lớn nhất
            can_be_single = False
            max_fs = max(10, int((bh / num_orig_lines) * 0.88))
            if num_orig_lines == 1:
                max_fs = max(10, int(bh * 0.75))

            low = 8
            high = max(low, max_fs)
            best_fs = low

            while low <= high:
                mid = (low + high) // 2
                test_f = _make_overlay_font(mid, font_weight)
                test_fm = QFontMetrics(test_f)
                br = test_fm.boundingRect(0, 0, int(inner_w), 0, int(Qt.TextFlag.TextWordWrap), self.translated_text)

                # Cho phép dung sai 12% chiều cao để bám sát không gian thực của ảnh
                if br.height() <= bh * 1.12 and br.width() <= inner_w * 1.05:
                    best_fs = mid
                    low = mid + 1
                else:
                    high = mid - 1
            font = _make_overlay_font(best_fs, font_weight)

        fm = QFontMetrics(font)
        if can_be_single:
            draw_rect = QRectF(self.rect.x() - pad_h, self.rect.y() - pad_v, bw + pad_h * 2, bh + pad_v * 2)
        else:
            br = fm.boundingRect(0, 0, int(inner_w), 0, int(Qt.TextFlag.TextWordWrap), self.translated_text)
            draw_h = max(bh + pad_v * 2, float(br.height() + pad_v * 2))
            draw_rect = QRectF(self.rect.x() - pad_h, self.rect.y() - pad_v, bw + pad_h * 2, draw_h)

        # Vẽ nền tiệp màu che sạch 100% chữ gốc
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(draw_rect, 4.0, 4.0)

        painter.setFont(font)
        painter.setPen(QPen(txt_c))

        if can_be_single:
            align = Qt.AlignmentFlag.AlignVCenter
            if len(self.translated_text) <= 6 or (bw > adv_single * 1.6 and len(self.translated_text) <= 15):
                align |= Qt.AlignmentFlag.AlignHCenter
            else:
                align |= Qt.AlignmentFlag.AlignLeft
            text_rect = draw_rect.adjusted(pad_h, 0, -pad_h, 0)
            painter.save()
            painter.setClipRect(draw_rect)
            painter.drawText(text_rect, int(align), self.translated_text)
            painter.restore()
        else:
            text_rect = draw_rect.adjusted(pad_h, pad_v, -pad_h, -pad_v)
            painter.save()
            painter.setClipRect(draw_rect)
            painter.drawText(
                text_rect,
                int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap),
                self.translated_text
            )
            painter.restore()

def parse_structured_sections(text: str):
    """
    Phân tích nội dung bản dịch thành Tiêu đề chính (Title) và danh sách các Cột/Phân mục (Sections):
    - Tự động nhận diện dòng tiêu đề bài học/bài viết ở đầu.
    - Nhận diện các đề mục cột (IN ẤN, NGHE, ĐỌC, NGỮ PHÁP, CHÍNH TẢ, TỪ VỰNG...).
    - Bóc tách các mục con danh sách thuộc về từng cột đó.
    """
    import re
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    if not lines:
        return "", []

    title = ""
    sections = []
    curr_heading = None
    curr_items = []

    def is_heading(line: str) -> bool:
        clean = re.sub(r'[*_#]', '', line).strip()
        if re.match(r'^(?:[-*•]|\d+[\.\)])\s*', clean):
            return False
        if len(clean) > 35:
            return False
        if clean.isupper() and len(clean.split()) <= 4:
            return True
        if clean.endswith(':') and len(clean.split()) <= 4:
            return True
        return False

    idx = 0
    if not is_heading(lines[0]) or len(lines[0]) > 25:
        title = lines[0]
        idx = 1

    while idx < len(lines):
        line = lines[idx]
        if is_heading(line):
            if curr_heading or curr_items:
                sections.append({"heading": curr_heading or "", "items": curr_items})
            curr_heading = re.sub(r'[*_#:]', '', line).strip()
            curr_items = []
        else:
            item = re.sub(r'^(?:[-*•]|\d+[\.\)])\s*', '', line).strip()
            if item:
                curr_items.append(item)
        idx += 1

    if curr_heading or curr_items:
        sections.append({"heading": curr_heading or "", "items": curr_items})

    return title, sections

class UnifiedSheetOverlayElement(CanvasElement):
    """
    Lớp phủ dịch thuật thông minh toàn diện & Đa Cột Tự Động (Smart Multi-Column Grid & Glass Sheet):
    - Tự động nhận diện cấu trúc Đa Cột (Multi-Column Layout) từ bản dịch để dàn đều các mục theo chiều ngang,
      tái hiện hoàn hảo giao diện gốc của website/bài học thay vì dồn cục vào 1 cột bên trái.
    - Tách riêng thanh Tiêu đề (Header Banner) với màu nền đậm nguyên bản và chữ trắng nổi bật.
    - Nền đục 100% (alpha 255) khử sạch hoàn toàn bóng mờ chữ tiếng Anh bên dưới.
    """
    def __init__(
        self,
        rect: QRectF,
        translated_text: str,
        is_dark_theme: bool = False,
        bg_color: QColor = None,
        text_color: QColor = None,
        banner_bg: QColor = None
    ):
        self.rect = rect
        self.translated_text = translated_text.strip()
        self.is_dark_theme = is_dark_theme

        # Nền đặc 100% (alpha 255) triệt tiêu hoàn toàn bóng mờ chữ gốc
        if bg_color is not None:
            self.bg_color = QColor(bg_color.red(), bg_color.green(), bg_color.blue(), 255)
        elif is_dark_theme:
            self.bg_color = QColor(15, 23, 42, 255)
        else:
            self.bg_color = QColor(248, 250, 252, 255)

        if text_color is not None:
            self.text_color = text_color
        elif is_dark_theme:
            self.text_color = QColor(241, 245, 249)
        else:
            self.text_color = QColor(15, 23, 42)

        # Màu banner tiêu đề ở trên cùng
        if banner_bg is not None:
            self.banner_bg = QColor(banner_bg.red(), banner_bg.green(), banner_bg.blue(), 255)
        elif is_dark_theme:
            self.banner_bg = QColor(10, 14, 26, 255)
        else:
            self.banner_bg = QColor(10, 25, 111, 255)

    def contains_point(self, pt: QPointF, tolerance: float = 8.0) -> bool:
        r = self.rect.adjusted(-tolerance, -tolerance, tolerance, tolerance)
        return r.contains(pt)

    def draw(self, painter: QPainter):
        if not self.translated_text:
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        r = self.rect
        title, sections = parse_structured_sections(self.translated_text)

        # Chỉ dùng bố cục đa cột nếu thực sự là bảng từ vựng / đề mục ngắn (tất cả các mục < 60 ký tự)
        is_multi_column = (
            len(sections) >= 2 and r.width() >= 550.0 and
            all(all(len(item) < 60 for item in sec['items']) for sec in sections) and
            all(len(sec['items']) >= 1 for sec in sections)
        )
        if is_multi_column:
            self._draw_multi_column_grid(painter, r, title, sections)
        else:
            self._draw_standard_sheet(painter, r, title)

    def _draw_multi_column_grid(self, painter: QPainter, r: QRectF, title: str, sections: list):
        # 1. Vẽ thanh Header Banner ở trên cùng
        has_title = bool(title.strip())
        header_h = min(40.0, max(28.0, r.height() * 0.18)) if has_title else 0.0

        if has_title:
            banner_rect = QRectF(r.left(), r.top(), r.width(), header_h)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(self.banner_bg))
            painter.drawRect(banner_rect)

            # Tiêu đề chữ trắng đậm nét
            title_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            painter.setFont(title_font)
            painter.setPen(QPen(QColor(255, 255, 255)))
            title_text_rect = banner_rect.adjusted(12.0, 0, -120.0, 0)
            painter.drawText(title_text_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), title)

            # Phím tắt gợi ý ở góc phải banner
            hint_font = QFont("Segoe UI", 7, QFont.Weight.Normal)
            painter.setFont(hint_font)
            painter.setPen(QPen(QColor(200, 220, 255)))
            hint_rect = banner_rect.adjusted(0, 0, -10.0, 0)
            painter.drawText(hint_rect, int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), "Esc: Hủy | Tab: Đổi kiểu")

        # 2. Vẽ nền phân vùng nội dung (Body Area) đặc 100% chống xuyên thấu
        body_y = r.top() + header_h
        body_h = r.bottom() - body_y
        body_rect = QRectF(r.left(), body_y, r.width(), body_h)

        painter.setPen(QPen(QColor(0, 0, 0, 30), 1.0))
        painter.setBrush(QBrush(self.bg_color))
        painter.drawRect(body_rect)

        # 3. Dàn đều các cột theo chiều ngang
        n_cols = len(sections)
        gap = 8.0
        pad_x = 10.0
        avail_w = r.width() - pad_x * 2.0
        col_w = (avail_w - gap * (n_cols - 1)) / max(1, n_cols)

        # Bộ màu sắc tiêu đề cột trang nhã, tương phản tốt
        col_colors = [
            QColor(185, 28, 28),   # Đỏ đô (PRINT / IN ẤN)
            QColor(13, 148, 136),  # Xanh mòng két (LISTEN / NGHE)
            QColor(217, 119, 6),   # Nâu hổ phách (READ / ĐỌC)
            QColor(37, 99, 235),   # Xanh dương (GRAMMAR / NGỮ PHÁP)
            QColor(147, 51, 234),  # Tím (SPELL / CHÍNH TẢ)
            QColor(16, 185, 129),  # Xanh lục (WORDS / TỪ VỰNG)
        ]

        item_font_size = 8 if r.height() >= 180 else 7.5
        item_font = QFont("Segoe UI", item_font_size, QFont.Weight.Normal)
        fm = QFontMetrics(item_font)

        for i, sec in enumerate(sections):
            cx = r.left() + pad_x + i * (col_w + gap)

            # Tiêu đề cột
            h_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
            painter.setFont(h_font)
            painter.setPen(QPen(col_colors[i % len(col_colors)] if not self.is_dark_theme else QColor(147, 197, 253)))
            head_r = QRectF(cx, body_y + 4.0, col_w, 18.0)
            painter.drawText(head_r, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), sec['heading'])

            # Đường gạch chân nhẹ dưới tiêu đề cột
            sep_line_color = QColor(255, 255, 255, 25) if self.is_dark_theme else QColor(226, 232, 240)
            painter.setPen(QPen(sep_line_color, 1.0))
            painter.drawLine(int(cx), int(body_y + 22.0), int(cx + col_w - 2.0), int(body_y + 22.0))

            # Danh sách các mục con trong cột
            item_y = body_y + 26.0
            painter.setFont(item_font)
            painter.setPen(QPen(self.text_color))

            for item in sec['items']:
                if item_y >= body_rect.bottom() - 10:
                    break
                text_r = QRectF(cx, item_y, col_w, 40.0)
                painter.drawText(
                    text_r,
                    int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap),
                    f"• {item}"
                )
                br = fm.boundingRect(0, 0, int(col_w), 100, int(Qt.TextFlag.TextWordWrap), f"• {item}")
                item_y += br.height() + 2.0

            # Đường ngăn cách giữa các cột
            if i < n_cols - 1:
                sep_x = cx + col_w + gap / 2.0
                painter.setPen(QPen(sep_line_color, 1.0))
                painter.drawLine(int(sep_x), int(body_y + 4.0), int(sep_x), int(body_rect.bottom() - 4.0))

    def _draw_standard_sheet(self, painter: QPainter, r: QRectF, title: str):
        import re

        # 1. Phân tích các dòng văn bản để tái hiện định dạng chuẩn xác 100% như tài liệu gốc
        raw_lines = [l.strip() for l in self.translated_text.split('\n') if l.strip()]
        if not raw_lines:
            return

        parsed_items = []
        for l in raw_lines:
            clean = re.sub(r'^\s*\[?(?:Đoạn\s*)?\d+\]?[\.:\-\s]*', '', l).strip()
            if not clean:
                continue
            if clean.startswith('**') and clean.endswith('**') and len(clean) < 160:
                heading_content = clean[2:-2].strip()
                parsed_items.append(('heading', heading_content))
            elif clean.startswith('# ') or clean.startswith('## ') or clean.startswith('### '):
                heading_content = re.sub(r'^#{1,3}\s*', '', clean).strip()
                parsed_items.append(('heading', heading_content))
            elif clean in ['---', '***', '___']:
                parsed_items.append(('separator', ''))
            elif clean.startswith('•') or clean.startswith('- ') or clean.startswith('* '):
                bullet_content = re.sub(r'^[•\-\*]\s*', '', clean).strip()
                parsed_items.append(('bullet', bullet_content))
            elif clean.endswith(':') and len(clean) < 60:
                parsed_items.append(('heading', clean))
            else:
                clean_para = re.sub(r'\*\*(.*?)\*\*', r'\1', clean)
                parsed_items.append(('para', clean_para))

        # 2. Tính toán cỡ font chữ tối ưu để vừa vặn hoàn hảo trong khung vùng chọn
        pad_x = 18.0
        pad_y = 14.0
        content_w = int(max(40.0, r.width() - pad_x * 2))
        max_h = max(30.0, r.height() - pad_y * 2)

        best_fsize = 11
        for fsize in range(12, 7, -1):
            font_head = QFont("Segoe UI", fsize + 1, QFont.Weight.Bold)
            font_body = QFont("Segoe UI", fsize, QFont.Weight.Normal)
            fm_head = QFontMetrics(font_head)
            fm_body = QFontMetrics(font_body)

            total_h = 0.0
            for itype, itext in parsed_items:
                if itype == 'heading':
                    br = fm_head.boundingRect(0, 0, content_w, 2000, int(Qt.TextFlag.TextWordWrap), itext)
                    total_h += br.height() + 10.0
                elif itype == 'bullet':
                    br = fm_body.boundingRect(0, 0, content_w - 20, 2000, int(Qt.TextFlag.TextWordWrap), itext)
                    total_h += br.height() + 5.0
                elif itype == 'separator':
                    total_h += 14.0
                else:
                    br = fm_body.boundingRect(0, 0, content_w, 2000, int(Qt.TextFlag.TextWordWrap), itext)
                    total_h += br.height() + 8.0

            if total_h <= max_h:
                best_fsize = fsize
                break
            best_fsize = fsize

        # 3. Tính toán sheet_rect vừa khít với nội dung thực tế (không phủ đè lên khoảng trống hay hình ảnh bên dưới)
        sheet_h = min(r.height(), total_h + pad_y * 2 + 16.0)
        sheet_rect = QRectF(r.left(), r.top(), r.width(), sheet_h)
        self._last_drawn_rect = sheet_rect

        # 4. Vẽ nền kính mờ cao cấp (Translucent Frosted Glass), không xóa lấp thô bạo hình ảnh bên dưới
        bg_r = self.bg_color.red()
        bg_g = self.bg_color.green()
        bg_b = self.bg_color.blue()
        glass_bg = QColor(bg_r, bg_g, bg_b, 230)
        border_c = QColor(0, 0, 0, 40) if not self.is_dark_theme else QColor(255, 255, 255, 35)
        painter.setPen(QPen(border_c, 1.2))
        painter.setBrush(QBrush(glass_bg))
        painter.drawRoundedRect(sheet_rect, 10.0, 10.0)

        # 5. Vẽ từng phần tử với phong cách typography trang nhã, đúng định dạng
        font_head = QFont("Segoe UI", best_fsize + 1, QFont.Weight.Bold)
        font_body = QFont("Segoe UI", best_fsize, QFont.Weight.Normal)
        font_bullet = QFont("Segoe UI", best_fsize, QFont.Weight.Medium if not self.is_dark_theme else QFont.Weight.Normal)
        fm_head = QFontMetrics(font_head)
        fm_body = QFontMetrics(font_body)

        curr_y = sheet_rect.top() + pad_y
        bullet_dot_color = QColor(37, 99, 235) if not self.is_dark_theme else QColor(96, 165, 250)
        bullet_text_color = QColor(29, 78, 216) if not self.is_dark_theme else QColor(147, 197, 253)

        painter.save()
        painter.setClipRect(sheet_rect.adjusted(4.0, 4.0, -4.0, -4.0))

        for idx, (itype, itext) in enumerate(parsed_items):
            if curr_y >= sheet_rect.bottom() - 10.0:
                break

            if itype == 'heading':
                painter.setFont(font_head)
                painter.setPen(QPen(self.text_color))
                br = fm_head.boundingRect(0, 0, content_w, 2000, int(Qt.TextFlag.TextWordWrap), itext)
                draw_r = QRectF(sheet_rect.left() + pad_x, curr_y, content_w, br.height())
                painter.drawText(draw_r, int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap), itext)
                curr_y += br.height() + 8.0

            elif itype == 'bullet':
                painter.setFont(font_head)
                painter.setPen(QPen(bullet_dot_color))
                dot_r = QRectF(sheet_rect.left() + pad_x, curr_y, 16.0, 20.0)
                painter.drawText(dot_r, int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft), "•")

                painter.setFont(font_bullet)
                painter.setPen(QPen(bullet_text_color))
                br = fm_body.boundingRect(0, 0, content_w - 20, 2000, int(Qt.TextFlag.TextWordWrap), itext)
                text_r = QRectF(sheet_rect.left() + pad_x + 16.0, curr_y, content_w - 20, br.height())
                painter.drawText(text_r, int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap), itext)
                curr_y += br.height() + 5.0

            elif itype == 'separator':
                sep_y = curr_y + 4.0
                painter.setPen(QPen(QColor(0, 0, 0, 25) if not self.is_dark_theme else QColor(255, 255, 255, 25), 1.0))
                painter.drawLine(int(sheet_rect.left() + pad_x), int(sep_y), int(sheet_rect.right() - pad_x), int(sep_y))
                curr_y += 12.0

            else:
                painter.setFont(font_body)
                painter.setPen(QPen(self.text_color))
                br = fm_body.boundingRect(0, 0, content_w, 2000, int(Qt.TextFlag.TextWordWrap), itext)
                draw_r = QRectF(sheet_rect.left() + pad_x, curr_y, content_w, br.height())
                painter.drawText(draw_r, int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap), itext)
                curr_y += br.height() + 7.0

        painter.restore()

        # 6. Phím tắt gợi ý tinh tế ở góc dưới phải (Minimalist Subtle Hint)
        hint_w = 120.0
        hint_h = 16.0
        hint_r = QRectF(sheet_rect.right() - hint_w - 8.0, sheet_rect.bottom() - hint_h - 4.0, hint_w, hint_h)
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Normal))
        painter.setPen(QPen(QColor(148, 163, 184, 160)))
        painter.drawText(hint_r, int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), "Esc: Hủy | Tab: Đổi kiểu")

class InfographicImageElement(CanvasElement):
    """
    Vẽ ảnh Infographic trực tiếp lên vùng chọn trên Overlay màn hình:
    - Hỗ trợ co giãn / căn giữa vừa vặn với vùng chụp của người dùng.
    - Cho phép người dùng dùng các công cụ vẽ (bút, highlight, mũi tên, text...) vẽ đè và chỉnh sửa trực tiếp.
    """
    def __init__(self, rect: QRectF, pixmap: QPixmap):
        self.rect = rect
        self.pixmap = pixmap

    def contains_point(self, pt: QPointF, tolerance: float = 8.0) -> bool:
        r = self.rect.adjusted(-tolerance, -tolerance, tolerance, tolerance)
        return r.contains(pt)

    def draw(self, painter: QPainter):
        if not self.pixmap or self.pixmap.isNull():
            return
        r = self.rect
        # 1. Vẽ nền tối mờ
        painter.fillRect(r, QColor(10, 14, 22, 245))

        # 2. Scale ảnh Infographic vừa vặn với vùng chọn
        scaled = self.pixmap.scaled(
            int(r.width()), int(r.height()),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        x = r.left() + (r.width() - scaled.width()) / 2.0
        y = r.top() + (r.height() - scaled.height()) / 2.0
        painter.drawPixmap(int(x), int(y), scaled)

        # 3. Gợi ý phím tắt
        hint_w = 140.0
        hint_h = 16.0
        hint_r = QRectF(r.right() - hint_w - 8.0, r.bottom() - hint_h - 4.0, hint_w, hint_h)
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Normal))
        painter.setPen(QPen(QColor(148, 163, 184, 180)))
        painter.drawText(hint_r, int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), "Esc: Hủy đè Infographic")
