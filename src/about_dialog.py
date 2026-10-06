import sys
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QGridLayout, QApplication
)
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QBrush, QPen,
    QPainterPath, QPixmap
)

def get_asset_path(filename: str) -> str:
    """Tìm đường dẫn tài nguyên hình ảnh an toàn cả khi dev lẫn khi đóng gói"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "assets", filename),
        os.path.join(base_dir, filename),
    ]
    if hasattr(sys, "_MEIPASS"):
        candidates.extend([
            os.path.join(sys._MEIPASS, "assets", filename),
            os.path.join(sys._MEIPASS, filename)
        ])
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]

ABOUT_DIALOG_STYLE = """
QDialog {
    background-color: #0A0F1D;
    color: #F8FAFC;
    border: 1px solid #232F48;
    border-radius: 16px;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, sans-serif;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}
QScrollBar:vertical {
    border: none;
    background: rgba(255, 255, 255, 0.03);
    width: 5px;
    border-radius: 3px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.18);
    border-radius: 3px;
    min-height: 25px;
}
QScrollBar::handle:vertical:hover {
    background: #6366F1;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QPushButton#CloseIconBtn {
    background: transparent;
    color: #94A3B8;
    border: none;
    font-size: 16px;
    font-weight: bold;
    border-radius: 10px;
}
QPushButton#CloseIconBtn:hover {
    color: #F87171;
    background-color: rgba(239, 68, 68, 0.2);
}
QPushButton#PrimaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:1 #8B5CF6);
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 8px 28px;
    font-weight: 700;
    font-size: 13px;
}
QPushButton#PrimaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED);
}
QPushButton#CopyStkBtn {
    background: rgba(236, 72, 153, 0.22);
    color: #F472B6;
    border: 1px solid rgba(236, 72, 153, 0.55);
    border-radius: 8px;
    padding: 5px 12px;
    font-size: 11px;
    font-weight: 800;
}
QPushButton#CopyStkBtn:hover {
    background: rgba(236, 72, 153, 0.38);
    border-color: #EC4899;
    color: #FFFFFF;
}
"""

class QuickFeatureItem(QFrame):
    """Mục tính năng gọn gàng, hiện đại với khung phím tắt tương phản cao, nổi bật chữ"""
    def __init__(self, icon: str, title: str, hotkey: str, desc: str, tag_color: str = "#38BDF8", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #111827;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }}
            QFrame:hover {{
                background-color: #172033;
                border-color: rgba(99, 102, 241, 0.4);
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(11, 9, 11, 9)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(6)

        lbl_title = QLabel(f"{icon} <b>{title}</b>")
        lbl_title.setStyleSheet("color: #FFFFFF; font-size: 12.5px;")
        header.addWidget(lbl_title)
        header.addStretch()

        if hotkey:
            # Khung phím tắt (Keycap badge) tương phản cao: nền tối đậm, viền sáng, chữ rực rỡ
            lbl_key = QLabel(hotkey)
            lbl_key.setStyleSheet(f"""
                background-color: #1E293B;
                color: {tag_color};
                font-size: 10.5px;
                font-weight: 900;
                padding: 3px 8px;
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.22);
                border-bottom: 2px solid rgba(255, 255, 255, 0.3);
                font-family: 'Consolas', 'Segoe UI', monospace;
            """)
            header.addWidget(lbl_key)

        layout.addLayout(header)

        lbl_desc = QLabel(desc)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #94A3B8; font-size: 11px; line-height: 1.35;")
        layout.addWidget(lbl_desc)


class DonateSupportCard(QFrame):
    """
    Thẻ kêu gọi quyên góp và tiếp lửa cho freely team:
    - Nhấn mạnh vào hệ sinh thái nhiều ứng dụng hữu ích mà nhóm đang xây dựng.
    - Lời ngỏ chân thành, tinh tế, tự nguyện, ấm áp.
    - Hiển thị QR Code Momo/VietQR sắc nét, có nút sao chép STK tiện lợi.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DonateCard")
        self.setStyleSheet("""
            QFrame#DonateCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 rgba(236, 72, 153, 0.10), 
                    stop:0.5 rgba(99, 102, 241, 0.08), 
                    stop:1 rgba(168, 85, 247, 0.11));
                border: 1px solid rgba(236, 72, 153, 0.35);
                border-radius: 14px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(16)

        # Cột trái: Lời ngỏ tinh tế & thông tin tài khoản
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)

        # Tiêu đề lời ngỏ
        title_box = QHBoxLayout()
        title_box.setSpacing(8)
        
        lbl_title = QLabel("Tiếp lửa cho freely team & Các dự án hữu ích")
        lbl_title.setStyleSheet("color: #F472B6; font-size: 13.5px; font-weight: 800; letter-spacing: 0.3px;")
        title_box.addWidget(lbl_title)
        title_box.addStretch()
        left_layout.addLayout(title_box)

        # Lời nhắn tinh tế theo đúng ý người dùng
        lbl_msg = QLabel(
            "Ngoài <b>Myshot AI</b>, nhóm còn đang ấp ủ và phát triển nhiều công cụ, ứng dụng hữu ích khác hoàn toàn miễn phí phục vụ cộng đồng.<br><br>"
            "Nếu bạn thấy những sản phẩm này hay và mang lại giá trị cho bạn, hãy ủng hộ nhóm một ly cà phê nhỏ nhé! "
            "Sự tiếp sức của bạn chính là nguồn động lực to lớn giúp chúng mình trang trải chi phí máy chủ và có thêm năng lượng để sáng tạo nhiều sản phẩm hữu ích hơn nữa. Cảm ơn bạn rất nhiều! ❤️"
        )
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("color: #E2E8F0; font-size: 11px; line-height: 1.45;")
        left_layout.addWidget(lbl_msg)

        # Khung thông tin tài khoản & nút sao chép
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 23, 42, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 9px;
            }
        """)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(10, 6, 10, 6)
        info_layout.setSpacing(10)

        bank_details = QVBoxLayout()
        bank_details.setSpacing(2)

        lbl_holder = QLabel("<b>Chủ TK:</b> NGO DIEM MY  •  <b>Ví / NH:</b> MoMo (VietQR / Napas247)")
        lbl_holder.setStyleSheet("color: #CBD5E1; font-size: 11px;")
        bank_details.addWidget(lbl_holder)

        lbl_stk = QLabel("<b>Số tài khoản:</b> <font color='#38BDF8' face='Consolas'><b>PSG2615919500000028</b></font>")
        lbl_stk.setStyleSheet("color: #E2E8F0; font-size: 11.5px;")
        bank_details.addWidget(lbl_stk)

        info_layout.addLayout(bank_details)
        info_layout.addStretch()

        self.btn_copy_stk = QPushButton("📋 Sao chép STK")
        self.btn_copy_stk.setObjectName("CopyStkBtn")
        self.btn_copy_stk.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_stk.clicked.connect(self.copy_account_number)
        info_layout.addWidget(self.btn_copy_stk)

        left_layout.addWidget(info_frame)

        # Chữ ký tinh tế
        lbl_thanks = QLabel("<i>\"Mỗi sự sẻ chia là một bước đệm giúp các dự án của nhóm ngày càng hoàn thiện hơn.\"</i> ✨")
        lbl_thanks.setStyleSheet("color: #94A3B8; font-size: 10.5px;")
        left_layout.addWidget(lbl_thanks)

        layout.addLayout(left_layout, stretch=3)

        # Cột phải: Mã QR MoMo
        qr_col = QVBoxLayout()
        qr_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_col.setSpacing(5)

        qr_box = QFrame()
        qr_box.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 2px solid rgba(236, 72, 153, 0.45);
                border-radius: 12px;
                padding: 3px;
            }
        """)
        qr_box_layout = QVBoxLayout(qr_box)
        qr_box_layout.setContentsMargins(4, 4, 4, 4)

        qr_label = QLabel()
        qr_path = get_asset_path("donate_qr.png")
        if os.path.exists(qr_path):
            pix = QPixmap(qr_path)
            scaled_pix = pix.scaled(130, 162, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            qr_label.setPixmap(scaled_pix)
        else:
            qr_label.setText("QR MoMo")
            qr_label.setStyleSheet("color: #000; font-weight: bold;")
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_box_layout.addWidget(qr_label)

        qr_col.addWidget(qr_box)

        lbl_scan_hint = QLabel("Quét mã MoMo / Ngân hàng")
        lbl_scan_hint.setStyleSheet("color: #F472B6; font-size: 10px; font-weight: 700;")
        lbl_scan_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_col.addWidget(lbl_scan_hint)

        layout.addLayout(qr_col, stretch=1)

    def copy_account_number(self):
        cb = QApplication.clipboard()
        cb.setText("PSG2615919500000028")
        self.btn_copy_stk.setText("✓ Đã chép!")
        self.btn_copy_stk.setStyleSheet("""
            background: #10B981;
            color: #FFFFFF;
            border: 1px solid #059669;
            border-radius: 8px;
            padding: 5px 12px;
            font-size: 11px;
            font-weight: 800;
        """)
        QTimer.singleShot(2500, self._reset_copy_btn)

    def _reset_copy_btn(self):
        self.btn_copy_stk.setText("📋 Sao chép STK")
        self.btn_copy_stk.setStyleSheet("")


class AboutDialog(QDialog):
    """
    Cửa sổ Giới thiệu & Hướng dẫn sử dụng Myshot AI
    Người xây dựng: Freya thuộc freely team
    Copyright © Tháng 10 năm 2026 - freely team
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Giới thiệu & Hướng dẫn Myshot AI")
        self.setFixedSize(860, 720)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(ABOUT_DIALOG_STYLE)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(22, 16, 22, 16)
        main_layout.setSpacing(12)

        # 1. Header cao cấp: Đã bỏ viền vuông avatar, bỏ icon tên lửa, bỏ khung v2.5 Pro thô kệch
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        # Avatar chú chim không viền, không khung hộp
        logo_label = QLabel()
        logo_path = get_asset_path("team_logo.png")
        if os.path.exists(logo_path):
            pix_logo = QPixmap(logo_path)
            scaled_logo = pix_logo.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_logo)
        else:
            logo_label.setText("🕊️")
            logo_label.setStyleSheet("font-size: 24px;")
        
        logo_label.setStyleSheet("background: transparent; border: none;")
        logo_label.setFixedSize(40, 40)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(logo_label)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)

        app_title = QLabel("Myshot AI")
        app_title.setStyleSheet("color: #FFFFFF; font-size: 19px; font-weight: 900; letter-spacing: 0.5px;")
        
        app_sub = QLabel("Phát triển bởi freely team  •  Chụp màn hình • Dịch đè tiệp nền • Trợ lý AI Gemini")
        app_sub.setStyleSheet("color: #94A3B8; font-size: 11px;")

        title_col.addWidget(app_title)
        title_col.addWidget(app_sub)
        header_layout.addLayout(title_col)
        header_layout.addStretch()

        ver_tag = QLabel("v2.5")
        ver_tag.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 700; margin-right: 6px;")
        header_layout.addWidget(ver_tag)

        btn_close = QPushButton("✕")
        btn_close.setObjectName("CloseIconBtn")
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        header_layout.addWidget(btn_close)

        main_layout.addLayout(header_layout)

        # 2. Vùng cuộn mượt mà
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.viewport().setStyleSheet("background: transparent;")

        content_widget = QWidget()
        content_widget.setObjectName("ContentWidget")
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 4, 0)
        content_layout.setSpacing(11)

        # (A) HƯỚNG DẪN NHANH: Đã bỏ icon tia sét thừa, các badge phím tắt phối màu tương phản cao
        sec_title = QLabel("TÍNH NĂNG & THAO TÁC CỐT LÕI")
        sec_title.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 800; letter-spacing: 0.6px;")
        content_layout.addWidget(sec_title)

        grid = QGridLayout()
        grid.setSpacing(8)

        # 6 tính năng cốt lõi với phím tắt tương phản cực cao, rõ nét
        items = [
            ("📸", "Chụp & Quét Vùng", "F1 / F3", "Kéo chuột chọn khu vực cần chụp. Nhấp đúp chuột sao chép nhanh.", "#38BDF8"),
            ("🌐", "Dịch Đè Tiệp Nền", "F4", "Tự xóa chữ gốc, đè tiếng Việt tiệp màu 100%. Bấm Tab để đổi kiểu đè.", "#4ADE80"),
            ("🤖", "Trợ Lý AI Gemini", "F9", "Trích xuất chữ OCR, giải toán, tóm tắt nội dung & giải thích hình ảnh.", "#C084FC"),
            ("🎨", "Vẽ & Chú Thích", "Thanh công cụ", "Bút vẽ, mũi tên, hình hộp, dạ quang & đánh số thứ tự (Badge).", "#FBBF24"),
            ("🧹", "Cục Tẩy Bôi Xóa", "Phím E", "Click hoặc rê chuột xóa hình vẽ; tự động dồn giảm số thứ tự tiếp theo.", "#F472B6"),
            ("📋", "Sao Chép & Lưu", "Ctrl+C / S", "Sao chép nhanh vào Clipboard hoặc lưu file ảnh chất lượng cao.", "#FACC15")
        ]

        for idx, (icon, title, hotkey, desc, color) in enumerate(items):
            row = idx // 2
            col = idx % 2
            card = QuickFeatureItem(icon, title, hotkey, desc, color)
            grid.addWidget(card, row, col)

        content_layout.addLayout(grid)

        # (B) KHU VỰC PHÍM TẮT TIỆN ÍCH & TÍNH NĂNG ẨN (Lưới 4 cột x 2 hàng gọn gàng)
        shortcuts_box = QFrame()
        shortcuts_box.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)
        shortcuts_layout = QVBoxLayout(shortcuts_box)
        shortcuts_layout.setContentsMargins(12, 8, 12, 8)
        shortcuts_layout.setSpacing(6)

        lbl_sc_title = QLabel("PHÍM TẮT TIỆN ÍCH & TÍNH NĂNG ẨN")
        lbl_sc_title.setStyleSheet("color: #94A3B8; font-size: 10.5px; font-weight: 800; letter-spacing: 0.5px;")
        shortcuts_layout.addWidget(lbl_sc_title)

        sc_grid = QGridLayout()
        sc_grid.setSpacing(8)

        sc_items = [
            ("Ctrl+Z", "Hoàn tác (Undo)", "#38BDF8"),
            ("Ctrl+Y", "Làm lại (Redo)", "#38BDF8"),
            ("Ctrl+B", "In đậm chữ", "#4ADE80"),
            ("Ctrl+I", "In nghiêng chữ", "#4ADE80"),
            ("Ctrl+U", "Gạch chân chữ", "#4ADE80"),
            ("Tab", "Đổi kiểu đè dịch", "#C084FC"),
            ("Space", "Ẩn/Hiện thanh vẽ", "#FBBF24"),
            ("Esc", "Hủy chụp / Thoát", "#F87171")
        ]

        for s_idx, (key_t, label_t, color_t) in enumerate(sc_items):
            s_row = s_idx // 4
            s_col = s_idx % 4
            pill = QLabel(f"<font color='{color_t}' face='Consolas'><b>[{key_t}]</b></font> <font color='#CBD5E1'>{label_t}</font>")
            pill.setStyleSheet("""
                background: #1E293B;
                padding: 4px 8px;
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.14);
                font-size: 11px;
            """)
            sc_grid.addWidget(pill, s_row, s_col)

        shortcuts_layout.addLayout(sc_grid)
        content_layout.addWidget(shortcuts_box)

        # (C) THẺ QUYÊN GÓP ỦNG HỘ NHÓM freely team
        donate_card = DonateSupportCard(self)
        content_layout.addWidget(donate_card)

        # (D) THÔNG TIN TÁC GIẢ & BẢN QUYỀN
        credit_box = QFrame()
        credit_box.setStyleSheet("""
            QFrame {
                background: rgba(99, 102, 241, 0.08);
                border: 1px solid rgba(139, 92, 246, 0.25);
                border-radius: 10px;
                padding: 6px 12px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)
        credit_layout = QHBoxLayout(credit_box)
        credit_layout.setContentsMargins(8, 4, 8, 4)
        credit_layout.setSpacing(10)

        credit_logo = QLabel()
        if os.path.exists(logo_path):
            pix_mini = QPixmap(logo_path).scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            credit_logo.setPixmap(pix_mini)
        credit_logo.setStyleSheet("background: transparent; border: none;")
        credit_layout.addWidget(credit_logo)

        lbl_author = QLabel("👤 <b>Phát triển:</b> Freya thuộc <b>freely team</b>  •  🛡️ Copyright © Tháng 10 năm 2026. Mọi quyền được bảo lưu.")
        lbl_author.setStyleSheet("color: #CBD5E1; font-size: 11px;")
        credit_layout.addWidget(lbl_author)
        credit_layout.addStretch()

        content_layout.addWidget(credit_box)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # 3. Footer: Đã bỏ icon ✓ thừa theo yêu cầu
        footer = QHBoxLayout()
        footer.addStretch()

        btn_done = QPushButton("Đã hiểu")
        btn_done.setObjectName("PrimaryBtn")
        btn_done.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_done.clicked.connect(self.accept)
        footer.addWidget(btn_done)

        main_layout.addLayout(footer)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
