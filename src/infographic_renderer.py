import re
import html
from PyQt6.QtCore import Qt, QRectF, QPointF, QSize
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QPixmap, QPainterPath
)

CARD_PALETTES = [
    {"border": QColor(99, 102, 241, 160), "bg": QColor(24, 31, 56), "title_color": QColor(167, 139, 250), "bullet_color": QColor(129, 140, 248)},
    {"border": QColor(14, 165, 233, 160), "bg": QColor(19, 35, 56), "title_color": QColor(56, 189, 248), "bullet_color": QColor(2, 132, 199)},
    {"border": QColor(16, 185, 129, 160), "bg": QColor(19, 45, 40), "title_color": QColor(52, 211, 153), "bullet_color": QColor(16, 185, 129)},
    {"border": QColor(245, 158, 11, 160), "bg": QColor(40, 35, 23), "title_color": QColor(251, 191, 36), "bullet_color": QColor(245, 158, 11)},
    {"border": QColor(236, 72, 153, 160), "bg": QColor(42, 24, 40), "title_color": QColor(244, 114, 182), "bullet_color": QColor(236, 72, 153)},
]

def parse_infographic_data(raw_text: str) -> dict:
    """
    Phân tích văn bản thô từ AI thành đối tượng Infographic có cấu trúc:
    {
        "title": str,
        "tldr": str,
        "sections": [{"title": str, "items": [str, ...]}],
        "conclusion": {"title": str, "items": [str, ...]} or None
    }
    """
    raw_clean = (raw_text or "").strip()
    lines = [line.strip() for line in raw_clean.split('\n') if line.strip()]
    if not lines:
        return {"title": "Báo Cáo Infographic", "tldr": "", "sections": [], "conclusion": None}

    title = ""
    tldr = ""
    sections = []
    conclusion = None

    current_sec_title = ""
    current_sec_items = []

    for line in lines:
        if line.startswith('# ') and not title:
            title = line[2:].strip()
            continue
        elif line.startswith('> ') and not tldr:
            tldr = line[2:].strip()
            continue
        elif line.startswith('### ') or line.startswith('## '):
            if current_sec_title:
                sec_data = {"title": current_sec_title, "items": list(current_sec_items)}
                if any(k in current_sec_title.lower() for k in ['kết luận', 'lưu ý', 'khuyến nghị', 'bài học', 'takeaway']):
                    conclusion = sec_data
                else:
                    sections.append(sec_data)
                current_sec_items.clear()

            h_marker = '### ' if line.startswith('### ') else '## '
            current_sec_title = line[len(h_marker):].strip()
        elif line.startswith('- ') or line.startswith('* ') or re.match(r'^\d+\.\s', line):
            item_text = re.sub(r'^[-*]\s+|\d+\.\s+', '', line).strip()
            if item_text:
                current_sec_items.append(item_text)
        else:
            if not title and len(line) < 120 and not line.startswith('-'):
                title = line
            elif not tldr and not current_sec_title:
                tldr = line
            else:
                if current_sec_title:
                    current_sec_items.append(line)
                else:
                    current_sec_items.append(line)

    if current_sec_title:
        sec_data = {"title": current_sec_title, "items": list(current_sec_items)}
        if any(k in current_sec_title.lower() for k in ['kết luận', 'lưu ý', 'khuyến nghị', 'bài học', 'takeaway']):
            conclusion = sec_data
        else:
            sections.append(sec_data)

    if not sections and not conclusion and current_sec_items:
        sections.append({"title": "💡 Điểm Nhấn Phân Tích", "items": current_sec_items})

    if not title:
        title = "📊 Báo Cáo Phân Tích Infographic"

    return {
        "title": title,
        "tldr": tldr,
        "sections": sections,
        "conclusion": conclusion
    }

def format_infographic_data_to_markdown(data: dict) -> str:
    """Chuyển đổi dữ liệu Infographic thành văn bản Markdown để người dùng dễ chỉnh sửa"""
    parts = []
    if data.get("title"):
        parts.append(f"# {data['title']}")
    if data.get("tldr"):
        parts.append(f"> {data['tldr']}")
    
    parts.append("")
    for sec in data.get("sections", []):
        parts.append(f"### {sec['title']}")
        for it in sec.get("items", []):
            parts.append(f"- {it}")
        parts.append("")

    if data.get("conclusion"):
        con = data["conclusion"]
        parts.append(f"### {con['title']}")
        for it in con.get("items", []):
            parts.append(f"- {it}")

    return "\n".join(parts).strip()

def render_infographic_pixmap(data: dict, width: int = 760) -> QPixmap:
    """
    Kết xuất cấu trúc Infographic thành một bức ảnh QPixmap đồ họa sắc nét (High-Resolution Visual Poster):
    - Background gradient cao cấp tối giản
    - Header Banner với icon to rõ
    - Thẻ Thông điệp cốt lõi (TL;DR)
    - Các khối Visual Cards bo tròn, màu accent sang trọng
    - Thẻ Kết luận / Lưu ý màu ngọc lục bảo
    - Footer bản quyền
    """
    pad_h = 24
    inner_w = width - pad_h * 2

    # 1. Tính toán trước chiều cao các khối
    font_family = "Segoe UI Variable Text"
    font_title = QFont(font_family, 14, QFont.Weight.Bold)
    font_tldr = QFont(font_family, 11, QFont.Weight.Normal)
    font_sec_title = QFont(font_family, 12, QFont.Weight.Bold)
    font_body = QFont(font_family, 10, QFont.Weight.Normal)
    font_footer = QFont(font_family, 9, QFont.Weight.Normal)

    # Chiều cao Header Banner
    title_text = data.get("title", "📊 Báo Cáo Infographic")
    fm_title = QFontMetrics(font_title)
    title_rect = fm_title.boundingRect(0, 0, inner_w - 32, 2000, int(Qt.TextFlag.TextWordWrap), title_text)
    header_h = 32 + title_rect.height() + 24

    # Chiều cao TL;DR
    tldr_text = data.get("tldr", "")
    tldr_h = 0
    if tldr_text:
        fm_tldr = QFontMetrics(font_tldr)
        tldr_rect = fm_tldr.boundingRect(0, 0, inner_w - 28, 2000, int(Qt.TextFlag.TextWordWrap), tldr_text)
        tldr_h = 24 + tldr_rect.height() + 20

    # Chiều cao từng Section
    sections_layout = []
    fm_sec_title = QFontMetrics(font_sec_title)
    fm_body = QFontMetrics(font_body)

    for i, sec in enumerate(data.get("sections", [])):
        sec_h = 16 + fm_sec_title.height() + 10
        item_layouts = []
        for it in sec.get("items", []):
            clean_it = re.sub(r'[*_`]', '', it)
            it_rect = fm_body.boundingRect(0, 0, inner_w - 48, 2000, int(Qt.TextFlag.TextWordWrap), clean_it)
            item_h = max(22, it_rect.height() + 6)
            item_layouts.append((it, it_rect.height(), item_h))
            sec_h += item_h
        sec_h += 14
        sections_layout.append((sec, item_layouts, sec_h))

    # Chiều cao Conclusion
    conclusion = data.get("conclusion")
    con_layout = None
    con_h = 0
    if conclusion:
        con_h = 16 + fm_sec_title.height() + 10
        con_items = []
        for it in conclusion.get("items", []):
            clean_it = re.sub(r'[*_`]', '', it)
            it_rect = fm_body.boundingRect(0, 0, inner_w - 48, 2000, int(Qt.TextFlag.TextWordWrap), clean_it)
            item_h = max(22, it_rect.height() + 6)
            con_items.append((it, it_rect.height(), item_h))
            con_h += item_h
        con_h += 14
        con_layout = (conclusion, con_items, con_h)

    # Tổng chiều cao ảnh
    footer_h = 36
    gap = 14
    total_h = 24 + header_h + (gap + tldr_h if tldr_h else 0)
    for _, _, sh in sections_layout:
        total_h += gap + sh
    if con_h:
        total_h += gap + con_h
    total_h += gap + footer_h + 16

    # 2. Bắt đầu vẽ trên QPixmap
    pixmap = QPixmap(width, int(total_h))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    # Nền Canvas tổng thể: Dark Modern Gradient
    bg_rect = QRectF(0, 0, width, total_h)
    painter.fillRect(bg_rect, QColor(13, 17, 26))

    # Viền nhẹ bên ngoài
    painter.setPen(QPen(QColor(255, 255, 255, 20), 1.0))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(bg_rect.adjusted(1, 1, -1, -1), 4, 4)

    curr_y = 22.0

    # (A) HEADER BANNER
    h_rect = QRectF(pad_h, curr_y, inner_w, header_h)
    painter.setPen(QPen(QColor(99, 102, 241, 200), 1.5))
    painter.setBrush(QBrush(QColor(30, 27, 75)))
    painter.drawRoundedRect(h_rect, 12, 12)

    # Tag 'INFOGRAPHIC INSIGHT'
    tag_rect = QRectF(h_rect.left() + 16, h_rect.top() + 12, 142, 20)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(79, 70, 229)))
    painter.drawRoundedRect(tag_rect, 5, 5)

    painter.setFont(QFont(font_family, 8, QFont.Weight.Bold))
    painter.setPen(QColor(255, 255, 255))
    painter.drawText(tag_rect, int(Qt.AlignmentFlag.AlignCenter), "📊 INFOGRAPHIC INSIGHT")

    # Brand text
    painter.setFont(QFont(font_family, 8, QFont.Weight.Normal))
    painter.setPen(QColor(165, 180, 252))
    brand_rect = QRectF(h_rect.right() - 130, h_rect.top() + 14, 114, 18)
    painter.drawText(brand_rect, int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), "✦ Gemini Vision")

    # Title text
    painter.setFont(font_title)
    painter.setPen(QColor(255, 255, 255))
    title_box = QRectF(h_rect.left() + 16, h_rect.top() + 38, inner_w - 32, title_rect.height() + 8)
    painter.drawText(title_box, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap), title_text)

    curr_y += header_h + gap

    # (B) CORE TAKEAWAY / TL;DR
    if tldr_h:
        tldr_rect = QRectF(pad_h, curr_y, inner_w, tldr_h)
        painter.setPen(QPen(QColor(56, 189, 248, 120), 1.0))
        painter.setBrush(QBrush(QColor(30, 41, 59)))
        painter.drawRoundedRect(tldr_rect, 10, 10)

        # Thanh màu nổi bật bên trái
        bar_rect = QRectF(tldr_rect.left(), tldr_rect.top(), 5, tldr_h)
        painter.fillRect(bar_rect, QColor(56, 189, 248))

        painter.setFont(QFont(font_family, 9, QFont.Weight.Bold))
        painter.setPen(QColor(56, 189, 248))
        label_rect = QRectF(tldr_rect.left() + 16, tldr_rect.top() + 8, 200, 18)
        painter.drawText(label_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), "🎯 THÔNG ĐIỆP CỐT LÕI:")

        painter.setFont(font_tldr)
        painter.setPen(QColor(241, 245, 249))
        tldr_text_rect = QRectF(tldr_rect.left() + 16, tldr_rect.top() + 28, inner_w - 32, tldr_rect.height() - 32)
        painter.drawText(tldr_text_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap), tldr_text)

        curr_y += tldr_h + gap

    # (C) VISUAL CARDS
    for i, (sec, item_layouts, sh) in enumerate(sections_layout):
        pal = CARD_PALETTES[i % len(CARD_PALETTES)]
        sec_rect = QRectF(pad_h, curr_y, inner_w, sh)

        painter.setPen(QPen(pal["border"], 1.2))
        painter.setBrush(QBrush(pal["bg"]))
        painter.drawRoundedRect(sec_rect, 11, 11)

        # Section Title
        painter.setFont(font_sec_title)
        painter.setPen(pal["title_color"])
        sec_title_box = QRectF(sec_rect.left() + 16, sec_rect.top() + 12, inner_w - 32, 22)
        painter.drawText(sec_title_box, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), sec["title"])

        # Items
        item_y = sec_rect.top() + 38
        painter.setFont(font_body)
        for raw_item, text_h, block_h in item_layouts:
            # Bullet arrow
            painter.setPen(pal["bullet_color"])
            arrow_rect = QRectF(sec_rect.left() + 16, item_y + 1, 16, 18)
            painter.drawText(arrow_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop), "➜")

            # Clean item text (highlight keyword)
            clean_item = re.sub(r'[*_`]', '', raw_item)
            painter.setPen(QColor(226, 232, 240))
            text_box = QRectF(sec_rect.left() + 36, item_y, inner_w - 52, block_h)
            painter.drawText(text_box, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap), clean_item)

            item_y += block_h

        curr_y += sh + gap

    # (D) CONCLUSION CARD
    if con_layout:
        con_data, con_item_layouts, ch = con_layout
        con_rect = QRectF(pad_h, curr_y, inner_w, ch)

        painter.setPen(QPen(QColor(16, 185, 129, 180), 1.2))
        painter.setBrush(QBrush(QColor(6, 78, 59)))
        painter.drawRoundedRect(con_rect, 11, 11)

        painter.setFont(font_sec_title)
        painter.setPen(QColor(110, 231, 183))
        con_title_box = QRectF(con_rect.left() + 16, con_rect.top() + 12, inner_w - 32, 22)
        painter.drawText(con_title_box, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), con_data["title"])

        con_item_y = con_rect.top() + 38
        painter.setFont(font_body)
        for raw_item, text_h, block_h in con_item_layouts:
            painter.setPen(QColor(16, 185, 129))
            star_rect = QRectF(con_rect.left() + 16, con_item_y + 1, 16, 18)
            painter.drawText(star_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop), "✦")

            clean_item = re.sub(r'[*_`]', '', raw_item)
            painter.setPen(QColor(236, 253, 245))
            text_box = QRectF(con_rect.left() + 36, con_item_y, inner_w - 52, block_h)
            painter.drawText(text_box, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap), clean_item)

            con_item_y += block_h

        curr_y += ch + gap

    # (E) FOOTER
    painter.setFont(font_footer)
    painter.setPen(QColor(100, 116, 139))
    foot_rect = QRectF(pad_h, curr_y, inner_w, footer_h)
    painter.drawText(foot_rect, int(Qt.AlignmentFlag.AlignCenter), "⚡ Myshot AI Infographic Studio • Được tạo tự động bằng Gemini Vision")

    painter.end()
    return pixmap
