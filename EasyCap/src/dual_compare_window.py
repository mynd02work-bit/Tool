import os
import re
import threading
from PIL import Image

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QPushButton, QSplitter, QFileDialog, QApplication, QFrame,
    QCheckBox, QMessageBox, QComboBox, QMenu, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QPoint, QSize, QRectF, QTimer
from PyQt6.QtGui import (
    QPixmap, QPainter, QColor, QFont, QPen, QBrush, QKeySequence,
    QShortcut, QWheelEvent
)

import config as app_config
from canvas_elements import BlockOverlayElement
from overlay import sample_block_colors, cluster_lines_into_blocks
from ocr_translate import perform_ocr, is_ocr_reliable, translate_text
from ai_engine import (
    extract_ocr_paragraphs, ai_translate_image, ai_translate_image_blocks,
    SUPPORTED_TARGET_LANGUAGES, get_target_lang_display_name
)

DUAL_WINDOW_STYLE = """
QWidget#DualCompareWindow {
    background-color: #0E121B;
    color: #F8FAFC;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, sans-serif;
}
QFrame#TopBar {
    background-color: #141A26;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding: 6px 12px;
    max-height: 46px;
}
QLabel#WindowTitle {
    color: #F8FAFC;
    font-size: 13px;
    font-weight: 800;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
}
QLabel#PaneHeaderLeft {
    background-color: #1E293B;
    color: #94A3B8;
    font-size: 11px;
    font-weight: 700;
    padding: 6px 14px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
QLabel#PaneHeaderRight {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(99, 102, 241, 0.25), stop:1 rgba(139, 92, 246, 0.25));
    color: #C084FC;
    font-size: 11px;
    font-weight: 700;
    padding: 6px 14px;
    border-bottom: 1px solid rgba(139, 92, 246, 0.3);
}
QPushButton {
    background-color: rgba(255, 255, 255, 0.06);
    color: #CBD5E1;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.14);
    color: #FFFFFF;
    border-color: rgba(255, 255, 255, 0.25);
}
QPushButton#PrimaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:1 #8B5CF6);
    color: #FFFFFF;
    border: none;
    font-weight: 700;
}
QPushButton#PrimaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED);
}
QComboBox {
    background-color: rgba(255, 255, 255, 0.08);
    color: #F8FAFC;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
}
QComboBox:hover {
    background-color: rgba(255, 255, 255, 0.12);
    border-color: #8B5CF6;
}
QComboBox::drop-down {
    border: none;
    width: 16px;
}
QComboBox QAbstractItemView {
    background-color: #1E293B;
    color: #F8FAFC;
    selection-background-color: #6366F1;
    selection-color: #FFFFFF;
    border: 1px solid rgba(255, 255, 255, 0.1);
    outline: none;
    padding: 4px;
}
QSplitter::handle {
    background-color: rgba(255, 255, 255, 0.08);
    width: 3px;
}
QSplitter::handle:hover {
    background-color: #8B5CF6;
}
QScrollArea {
    border: none;
    background-color: #0A0D14;
}
"""

class FileTranslationWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, pil_image, target_lang="vi"):
        super().__init__()
        self.pil_image = pil_image
        self.target_lang = target_lang
        self._is_cancelled = False

    def start(self):
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def cancel(self):
        self._is_cancelled = True

    def _run(self):
        try:
            if self._is_cancelled:
                return

            cfg = app_config.load_config()
            api_key = app_config.get_effective_gemini_api_key(cfg)
            model = cfg.get("gemini_model", "gemini-flash-lite-latest")
            ocr_lang = cfg.get("ocr_lang", "auto")

            # 1. Ưu tiên hàng đầu: Gemini Multimodal Vision API nhận diện bounding box & dịch đè 1:1 chuẩn xác mọi ngôn ngữ
            blocks = []
            if api_key and not api_key.startswith("AIzaSyDummy"):
                try:
                    blocks = ai_translate_image_blocks(
                        self.pil_image,
                        target_lang=self.target_lang,
                        api_key=api_key,
                        model=model
                    )
                except Exception as e:
                    print("ai_translate_image_blocks error in FileTranslationWorker:", e)

            # 2. Dự phòng ngoại tuyến: Windows OCR nếu AI không khả dụng hoặc không có mạng
            if not blocks:
                try:
                    ocr_res = perform_ocr(self.pil_image, lang=ocr_lang)
                    _, blocks = extract_ocr_paragraphs(self.pil_image, lang=ocr_lang)
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
                except Exception as e:
                    print("OCR error in FileTranslationWorker:", e)

            # 3. Lọc khối hợp lệ
            valid_blocks = []
            for blk in blocks:
                orig = blk.get('original', '').strip()
                trans = blk.get('translated', '').strip()
                if len(orig) < 1 and len(trans) < 1:
                    continue
                bw = float(blk.get('w', 0.0))
                bh = float(blk.get('h', 0.0))
                if bw < 4.0 or bh < 4.0:
                    continue
                valid_blocks.append(blk)

            # 4. Dịch những block chưa có bản dịch (nếu lấy từ Windows OCR)
            needs_translation = [b for b in valid_blocks if not b.get('translated')]
            if needs_translation:
                orig_texts = [b['original'].replace('\n', ' ').strip() for b in needs_translation]
                from document_translator import batch_translate_texts
                trans_map = batch_translate_texts(orig_texts, target_lang=self.target_lang)
                for blk in needs_translation:
                    cleaned = blk['original'].replace('\n', ' ').strip()
                    blk['translated'] = trans_map.get(cleaned, cleaned)

            # 5. Tổng hợp toàn văn để copy
            if valid_blocks:
                full_text = "\n\n".join([b.get('translated', '') for b in valid_blocks if b.get('translated')])
            else:
                full_text = ""
                if api_key and not api_key.startswith("AIzaSyDummy"):
                    try:
                        full_text = ai_translate_image(
                            self.pil_image,
                            target_lang=self.target_lang,
                            api_key=api_key,
                            model=model
                        )
                    except Exception:
                        pass
                if not full_text or full_text.startswith("❌"):
                    full_text = "Không tìm thấy nội dung văn bản để dịch."

            if not self._is_cancelled:
                self.finished.emit({
                    "full_text": full_text,
                    "blocks": valid_blocks
                })
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))

class DualCompareWindow(QWidget):
    """
    Cửa sổ Dịch File Ảnh & Tài Liệu (In-place Translation):
    - Đè chữ bản dịch chuẩn xác 100% theo từng vị trí khối (BlockOverlayElement),
      giữ nguyên bố cục ảnh, icon, màu sắc và typography.
    - Phím Tab hoặc nút chuyển đổi: Đổi nhanh giữa Bản dịch đè 1:1 <-> Ảnh gốc.
    - Hỗ trợ cả 2 chế độ: Xem đơn (1 ảnh lớn) hoặc So sánh song song (2 ảnh).
    - Hỗ trợ đổi ngôn ngữ đích trực tiếp trên thanh công cụ.
    - Cuộn và zoom mượt mà, ghim trên cùng, copy chữ và lưu ảnh.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DualCompareWindow")
        self.setStyleSheet(DUAL_WINDOW_STYLE)
        self.setWindowTitle("🪟 Dịch File Ảnh (In-place Translation) - Myshot AI")
        self.resize(1180, 750)

        cfg = app_config.load_config()
        self.target_lang = cfg.get("target_lang", "vi")

        self.current_file_path = ""
        self.original_pixmap = None
        self.translated_pixmap = None
        self.translated_text = ""
        self.overlay_mode = "blocks"  # "blocks" hoặc "original"
        self._cached_block_pixmap = None

        self.is_single_view = False
        self.zoom_factor = 1.0
        self.sync_scroll_enabled = True
        self._syncing_scroll = False
        self.is_always_on_top = False
        self.worker = None

        self.init_ui()
        self.setup_shortcuts()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Thanh công cụ điều khiển trên cùng (Top Bar)
        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        top_bar.setFixedHeight(46)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(14, 6, 14, 6)
        top_layout.setSpacing(8)

        logo = QLabel("🪟 Dịch File")
        logo.setObjectName("WindowTitle")
        top_layout.addWidget(logo)

        self.lbl_mode_badge = QLabel("[Đè chữ vị trí 1:1]")
        self.lbl_mode_badge.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 11px;")
        top_layout.addWidget(self.lbl_mode_badge)

        top_layout.addSpacing(6)

        # Nút chuyển đổi Tab: Đè chữ 1:1 <-> Bản gốc
        self.btn_switch_mode = QPushButton("↩️ Về ảnh gốc (Tab)")
        self.btn_switch_mode.setObjectName("PrimaryBtn")
        self.btn_switch_mode.setToolTip("Bấm phím Tab để lật nhanh giữa Bản dịch đè vị trí và Ảnh gốc")
        self.btn_switch_mode.clicked.connect(self.cycle_overlay_mode)
        top_layout.addWidget(self.btn_switch_mode)

        # Nút chuyển kiểu bố cục: Xem đơn (1 ảnh) <-> So sánh song song (2 ảnh)
        self.btn_view_layout = QPushButton("🖼️ Xem đơn (1 ảnh)")
        self.btn_view_layout.setToolTip("Chuyển đổi giữa Chế độ xem 1 ảnh lớn và So sánh 2 bên song song")
        self.btn_view_layout.clicked.connect(self.toggle_view_layout)
        top_layout.addWidget(self.btn_view_layout)

        top_layout.addSpacing(10)

        # Dropdown chọn Ngôn ngữ dịch đích
        lbl_lang = QLabel("🌐 Đích:")
        lbl_lang.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        top_layout.addWidget(lbl_lang)

        self.cbo_lang = QComboBox()
        self.cbo_lang.setToolTip("Chọn ngôn ngữ muốn dịch sang cho ảnh/tài liệu này")
        for code, name in SUPPORTED_TARGET_LANGUAGES:
            self.cbo_lang.addItem(name, code)
        
        idx = self.cbo_lang.findData(self.target_lang)
        if idx >= 0:
            self.cbo_lang.setCurrentIndex(idx)
        self.cbo_lang.currentIndexChanged.connect(self.on_language_changed)
        top_layout.addWidget(self.cbo_lang)

        top_layout.addSpacing(10)

        # Điều khiển Zoom
        btn_zoom_out = QPushButton("−")
        btn_zoom_out.setFixedSize(28, 26)
        btn_zoom_out.setToolTip("Thu nhỏ ảnh (Ctrl + -)")
        btn_zoom_out.clicked.connect(self.zoom_out)
        top_layout.addWidget(btn_zoom_out)

        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700; min-width: 42px; text-align: center;")
        self.lbl_zoom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(self.lbl_zoom)

        btn_zoom_in = QPushButton("+")
        btn_zoom_in.setFixedSize(28, 26)
        btn_zoom_in.setToolTip("Phóng to ảnh (Ctrl + +)")
        btn_zoom_in.clicked.connect(self.zoom_in)
        top_layout.addWidget(btn_zoom_in)

        btn_zoom_reset = QPushButton("1:1")
        btn_zoom_reset.setToolTip("Đặt lại cỡ gốc 100% (Ctrl + 0)")
        btn_zoom_reset.clicked.connect(self.zoom_reset)
        top_layout.addWidget(btn_zoom_reset)

        btn_zoom_fit = QPushButton("Phóng vừa")
        btn_zoom_fit.setToolTip("Tự động co dãn vừa vặn khung nhìn")
        btn_zoom_fit.clicked.connect(self.zoom_fit)
        top_layout.addWidget(btn_zoom_fit)

        # Tùy chọn đồng bộ cuộn
        self.chk_sync = QCheckBox("🔗 Đồng bộ")
        self.chk_sync.setStyleSheet("color: #E2E8F0; font-size: 11px; font-weight: 600;")
        self.chk_sync.setChecked(True)
        self.chk_sync.toggled.connect(self.toggle_sync_scroll)
        top_layout.addWidget(self.chk_sync)

        top_layout.addStretch()

        # Nút Mở file mới
        btn_open = QPushButton("📁 Mở file...")
        btn_open.setToolTip("Mở file ảnh khác từ máy tính để dịch (Ctrl+O)")
        btn_open.clicked.connect(self.open_new_file)
        top_layout.addWidget(btn_open)

        # Nút Copy chữ dịch
        self.btn_copy = QPushButton("📋 Copy chữ")
        self.btn_copy.setToolTip("Copy toàn bộ nội dung dịch vào bộ nhớ tạm")
        self.btn_copy.clicked.connect(self.copy_translation_text)
        top_layout.addWidget(self.btn_copy)

        # Nút Lưu ảnh
        self.btn_save = QPushButton("💾 Lưu ảnh...")
        self.btn_save.setToolTip("Lưu bản dịch đè vị trí hoặc lưu ảnh ghép so sánh")
        self.btn_save.clicked.connect(self.save_image_menu)
        top_layout.addWidget(self.btn_save)

        # Nút Ghim trên cùng
        self.btn_pin = QPushButton("📌 Ghim")
        self.btn_pin.setToolTip("Ghim cửa sổ luôn nổi lên trên cùng màn hình")
        self.btn_pin.clicked.connect(self.toggle_always_on_top)
        top_layout.addWidget(self.btn_pin)

        main_layout.addWidget(top_bar, 0)

        # 2. Khung hiển thị Splitter chia đôi 2 bên
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(4)

        # --- Pane Trái: Ảnh gốc ---
        self.left_container = QWidget()
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.header_left = QLabel("📷 ẢNH GỐC (ORIGINAL)")
        self.header_left.setObjectName("PaneHeaderLeft")
        self.header_left.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        left_layout.addWidget(self.header_left, 0)

        self.scroll_left = QScrollArea()
        self.scroll_left.setWidgetResizable(True)
        self.scroll_left.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_image_left = QLabel()
        self.lbl_image_left.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_left.setWidget(self.lbl_image_left)
        left_layout.addWidget(self.scroll_left, 1)
        left_layout.setStretch(0, 0)
        left_layout.setStretch(1, 1)

        self.splitter.addWidget(self.left_container)

        # --- Pane Phải: Bản dịch ---
        self.right_container = QWidget()
        right_layout = QVBoxLayout(self.right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        lang_name = get_target_lang_display_name(self.target_lang)
        self.header_right = QLabel(f"🌐 BẢN DỊCH {lang_name.upper()} (ĐÈ VỊ TRÍ 1:1)")
        self.header_right.setObjectName("PaneHeaderRight")
        self.header_right.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        right_layout.addWidget(self.header_right, 0)

        self.scroll_right = QScrollArea()
        self.scroll_right.setWidgetResizable(True)
        self.scroll_right.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_image_right = QLabel()
        self.lbl_image_right.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_right.setWidget(self.lbl_image_right)
        right_layout.addWidget(self.scroll_right, 1)
        right_layout.setStretch(0, 0)
        right_layout.setStretch(1, 1)

        self.splitter.addWidget(self.right_container)

        # Chia đều 50% - 50%
        self.splitter.setSizes([590, 590])
        main_layout.addWidget(self.splitter, 1)
        main_layout.setStretch(0, 0)
        main_layout.setStretch(1, 1)

        # Thiết lập kết nối đồng bộ thanh cuộn
        self.scroll_left.verticalScrollBar().valueChanged.connect(self._sync_scroll_left_to_right)
        self.scroll_right.verticalScrollBar().valueChanged.connect(self._sync_scroll_right_to_left)
        self.scroll_left.horizontalScrollBar().valueChanged.connect(self._sync_h_scroll_left_to_right)
        self.scroll_right.horizontalScrollBar().valueChanged.connect(self._sync_h_scroll_right_to_left)

    def setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.close)
        QShortcut(QKeySequence(Qt.Key.Key_Tab), self, self.cycle_overlay_mode)
        QShortcut(QKeySequence("Ctrl+O"), self, self.open_new_file)
        QShortcut(QKeySequence("Ctrl+="), self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl++"), self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, self.zoom_reset)
        QShortcut(QKeySequence("Ctrl+C"), self, self.copy_translation_text)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_image_menu)

    def on_language_changed(self, index):
        code = self.cbo_lang.itemData(index)
        if code and code != self.target_lang:
            self.target_lang = code
            cfg = app_config.load_config()
            cfg["target_lang"] = code
            app_config.save_config(cfg)
            if self.current_file_path and os.path.exists(self.current_file_path):
                self.translate_image_file(self.current_file_path)

    def toggle_view_layout(self):
        """
        Chuyển đổi giữa chế độ xem 1 ảnh lớn và so sánh 2 bên
        """
        self.is_single_view = not self.is_single_view
        if self.is_single_view:
            self.left_container.hide()
            self.chk_sync.hide()
            self.btn_view_layout.setText("🪟 So sánh song song")
            self.btn_view_layout.setToolTip("Chuyển sang chế độ xem so sánh 2 bên (ảnh gốc & bản dịch)")
        else:
            self.left_container.show()
            self.chk_sync.show()
            self.splitter.setSizes([self.width() // 2, self.width() // 2])
            self.btn_view_layout.setText("🖼️ Xem đơn (1 ảnh)")
            self.btn_view_layout.setToolTip("Phóng to 1 khung ảnh duy nhất (Bấm Tab để lật qua lại ảnh gốc và bản dịch)")
        self.update_display_images()

    def set_content(self, original_pixmap: QPixmap, translated_pixmap: QPixmap = None,
                    translated_text: str = "", block_pixmap: QPixmap = None, sheet_pixmap: QPixmap = None):
        """
        Nhận ảnh và hiển thị so sánh ngay lập tức
        """
        self.original_pixmap = original_pixmap
        self.translated_text = translated_text or ""
        self._cached_block_pixmap = block_pixmap or translated_pixmap
        self.translated_pixmap = self._cached_block_pixmap or self.original_pixmap

        self.overlay_mode = "blocks" if self._cached_block_pixmap else "original"
        self._update_mode_label()
        self.update_display_images()

    def translate_image_file(self, file_path: str, target_lang: str = None):
        """
        Mở một file ảnh từ máy tính, nhận diện khối văn bản và dịch đè vị trí 1:1 y như dịch màn hình
        """
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Lỗi", "File ảnh không tồn tại!")
            return

        if target_lang:
            self.target_lang = target_lang
            idx = self.cbo_lang.findData(target_lang)
            if idx >= 0:
                self.cbo_lang.blockSignals(True)
                self.cbo_lang.setCurrentIndex(idx)
                self.cbo_lang.blockSignals(False)

        try:
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                QMessageBox.warning(self, "Lỗi", "Không thể đọc định dạng file ảnh này!")
                return
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể tải ảnh: {e}")
            return

        self.current_file_path = file_path
        self.original_pixmap = pixmap
        self._cached_block_pixmap = None
        self.translated_pixmap = None
        self.translated_text = ""

        # Hiển thị ảnh gốc bên trái
        self.zoom_factor = 1.0
        self.update_display_images()
        QTimer.singleShot(60, self.zoom_fit)

        lang_name = get_target_lang_display_name(self.target_lang)
        # Hiển thị hiệu ứng chờ dịch bên phải
        self.lbl_image_right.setText(
            f"<html><div style='text-align: center; color: #A78BFA; font-size: 14px; padding: 40px;'>"
            f"<p style='font-size: 28px;'>⏳</p>"
            f"<p><b>Đang nhận diện văn bản & Dịch đè vị trí sang {lang_name}...</b></p>"
            f"<p style='color: #64748B; font-size: 12px;'>Bản dịch đè chữ tiệp màu 1:1 chuẩn vị trí sẽ hiển thị sau giây lát</p>"
            f"</div></html>"
        )

        try:
            pil_img = Image.open(file_path).convert("RGB")
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể mở ảnh bằng PIL: {e}")
            return

        if self.worker:
            self.worker.cancel()

        self.worker = FileTranslationWorker(pil_img, target_lang=self.target_lang)
        self.worker.finished.connect(lambda data, p=pixmap, img=pil_img: self._on_file_translation_finished(data, p, img))
        self.worker.error.connect(self._on_file_translation_error)
        self.worker.start()

    def _on_file_translation_finished(self, data: dict, orig_pixmap: QPixmap, pil_img: Image.Image):
        full_text = data.get("full_text", "")
        valid_blocks = data.get("blocks", [])
        self.translated_text = full_text

        # Tạo Block Pixmap đè vị trí 1:1 (In-place Block Overlay)
        if valid_blocks:
            block_pix = orig_pixmap.copy()
            painter = QPainter(block_pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

            for blk in valid_blocks:
                para = blk.get('translated', '').strip()
                if not para:
                    continue
                bx = float(blk.get('x', 0.0))
                by = float(blk.get('y', 0.0))
                bw = float(blk.get('w', 40.0))
                bh = float(blk.get('h', 16.0))

                bg_c, txt_c, is_photo = sample_block_colors(pil_img, bx, by, bw, bh)
                # Đảm bảo độ tương phản màu sắc tốt giữa nền và chữ
                if is_photo or abs(bg_c.lightness() - txt_c.lightness()) < 35:
                    if bg_c.lightness() > 128:
                        txt_c = QColor(15, 23, 42)
                    else:
                        txt_c = QColor(248, 250, 252)

                avg_line_h = float(blk.get('avg_line_h', bh / max(1, blk.get('num_lines', 1))))
                base_fsize = max(8, int(avg_line_h * 0.72))

                el = BlockOverlayElement(
                    QRectF(bx, by, bw, bh),
                    blk.get('original', ''),
                    para,
                    bg_color=bg_c,
                    text_color=txt_c,
                    base_font_size=base_fsize
                )
                el.draw(painter)
            painter.end()
            self._cached_block_pixmap = block_pix
            self.translated_pixmap = self._cached_block_pixmap
            self.overlay_mode = "blocks"
            self._update_mode_label()
            self.update_display_images()
            QTimer.singleShot(60, self.zoom_fit)
        else:
            self._cached_block_pixmap = None
            self.translated_pixmap = None
            self.overlay_mode = "original"
            self._update_mode_label()
            self.update_display_images()
            self.lbl_image_right.setText(
                "<html><div style='text-align: center; color: #F59E0B; padding: 40px;'>"
                "<p style='font-size: 28px;'>ℹ️</p>"
                "<p><b>Không phát hiện thấy văn bản trong ảnh để dịch</b></p>"
                "<p style='color: #94A3B8; font-size: 12px;'>Ảnh có thể chỉ chứa hình minh họa thuần túy hoặc độ tương phản chưa rõ chữ.</p>"
                "</div></html>"
            )

    def _on_file_translation_error(self, err_msg: str):
        self.lbl_image_right.setText(f"<html><div style='text-align: center; color: #EF4444; padding: 30px;'>❌ Lỗi dịch thuật: {err_msg}</div></html>")

    def cycle_overlay_mode(self):
        """
        Bấm Tab hoặc nút để đổi qua lại giữa Đè chữ vị trí 1:1 và Ảnh gốc
        """
        if self.overlay_mode == "blocks":
            self.overlay_mode = "original"
            self.translated_pixmap = self.original_pixmap
        else:
            self.overlay_mode = "blocks"
            self.translated_pixmap = self._cached_block_pixmap or self.original_pixmap

        self._update_mode_label()
        self.update_display_images()

    def _update_mode_label(self):
        lang_display = get_target_lang_display_name(self.target_lang)
        if self.overlay_mode == "blocks":
            self.lbl_mode_badge.setText(f"[Đè chữ 1:1 ({lang_display})]")
            self.lbl_mode_badge.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 11px;")
            self.btn_switch_mode.setText("↩️ Về ảnh gốc (Tab)")
            self.header_right.setText(f"🌐 BẢN DỊCH {lang_display.upper()} (ĐÈ VỊ TRÍ 1:1)")
        else:
            self.lbl_mode_badge.setText("[Ảnh gốc]")
            self.lbl_mode_badge.setStyleSheet("color: #94A3B8; font-weight: bold; font-size: 11px;")
            self.btn_switch_mode.setText("🔤 Dịch đè vị trí (Tab)")
            self.header_right.setText("📷 ẢNH GỐC (Bấm Tab để xem bản dịch)")

    def update_display_images(self):
        if not self.original_pixmap:
            return

        w = int(self.original_pixmap.width() * self.zoom_factor)
        h = int(self.original_pixmap.height() * self.zoom_factor)
        size = QSize(max(1, w), max(1, h))

        # Hiển thị ảnh trái
        if not self.is_single_view:
            scaled_left = self.original_pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_image_left.setPixmap(scaled_left)
            self.lbl_image_left.setFixedSize(scaled_left.size())

        # Hiển thị ảnh phải (hoặc ảnh duy nhất khi ở Single View)
        if self.translated_pixmap:
            scaled_right = self.translated_pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_image_right.setPixmap(scaled_right)
            self.lbl_image_right.setFixedSize(scaled_right.size())

        self.lbl_zoom.setText(f"{int(self.zoom_factor * 100)}%")

    # --- Đồng bộ cuộn ---
    def _sync_scroll_left_to_right(self, val):
        if self._syncing_scroll or not self.sync_scroll_enabled or self.is_single_view:
            return
        self._syncing_scroll = True
        try:
            self._sync_scrollbars(self.scroll_left.verticalScrollBar(), self.scroll_right.verticalScrollBar())
        finally:
            self._syncing_scroll = False

    def _sync_scroll_right_to_left(self, val):
        if self._syncing_scroll or not self.sync_scroll_enabled or self.is_single_view:
            return
        self._syncing_scroll = True
        try:
            self._sync_scrollbars(self.scroll_right.verticalScrollBar(), self.scroll_left.verticalScrollBar())
        finally:
            self._syncing_scroll = False

    def _sync_h_scroll_left_to_right(self, val):
        if self._syncing_scroll or not self.sync_scroll_enabled or self.is_single_view:
            return
        self._syncing_scroll = True
        try:
            self._sync_scrollbars(self.scroll_left.horizontalScrollBar(), self.scroll_right.horizontalScrollBar())
        finally:
            self._syncing_scroll = False

    def _sync_h_scroll_right_to_left(self, val):
        if self._syncing_scroll or not self.sync_scroll_enabled or self.is_single_view:
            return
        self._syncing_scroll = True
        try:
            self._sync_scrollbars(self.scroll_right.horizontalScrollBar(), self.scroll_left.horizontalScrollBar())
        finally:
            self._syncing_scroll = False

    def _sync_scrollbars(self, src_bar, tgt_bar):
        max_s = src_bar.maximum()
        max_t = tgt_bar.maximum()
        if max_s > 0 and max_t > 0:
            ratio = src_bar.value() / max_s
            tgt_bar.setValue(int(ratio * max_t))
        else:
            tgt_bar.setValue(src_bar.value())

    def toggle_sync_scroll(self, checked: bool):
        self.sync_scroll_enabled = checked

    # --- Điều khiển Zoom ---
    def zoom_in(self):
        if self.zoom_factor < 4.0:
            self.zoom_factor = min(4.0, self.zoom_factor + 0.15)
            self.update_display_images()

    def zoom_out(self):
        if self.zoom_factor > 0.2:
            self.zoom_factor = max(0.2, self.zoom_factor - 0.15)
            self.update_display_images()

    def zoom_reset(self):
        self.zoom_factor = 1.0
        self.update_display_images()

    def zoom_fit(self):
        if not self.original_pixmap:
            return
        target_scroll = self.scroll_right if self.is_single_view else self.scroll_left
        viewport_w = target_scroll.viewport().width() - 20
        viewport_h = target_scroll.viewport().height() - 20
        if viewport_w <= 0 or viewport_h <= 0:
            return
        ratio_w = viewport_w / self.original_pixmap.width()
        ratio_h = viewport_h / self.original_pixmap.height()
        self.zoom_factor = max(0.1, min(3.0, min(ratio_w, ratio_h)))
        self.update_display_images()

    def showEvent(self, event):
        super().showEvent(event)
        if self.original_pixmap:
            QTimer.singleShot(80, self.zoom_fit)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
            return
        super().wheelEvent(event)

    def toggle_always_on_top(self):
        self.is_always_on_top = not self.is_always_on_top
        flags = self.windowFlags()
        if self.is_always_on_top:
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
            self.btn_pin.setText("📌 Đang ghim")
            self.btn_pin.setStyleSheet("background-color: #8B5CF6; color: #FFFFFF;")
        else:
            self.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
            self.btn_pin.setText("📌 Ghim")
            self.btn_pin.setStyleSheet("")
        self.show()

    def open_new_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file ảnh để dịch",
            "",
            "Image Files (*.png *.jpg *.jpeg *.webp *.bmp *.tiff)"
        )
        if file_path:
            self.translate_image_file(file_path)

    def copy_translation_text(self):
        if self.translated_text:
            QApplication.clipboard().setText(self.translated_text)
            prev = self.btn_copy.text()
            self.btn_copy.setText("✓ Đã copy")
            QTimer.singleShot(1500, lambda: self.btn_copy.setText(prev))

    def save_image_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 7px 18px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
            }
            QMenu::item:selected {
                background-color: #6366F1;
            }
        """)
        act_trans = menu.addAction("🖼️ Lưu bản dịch đè vị trí 1:1")
        act_trans.triggered.connect(self.save_translated_image)
        act_dual = menu.addAction("🪟 Lưu ảnh so sánh song song (Cả 2 ảnh)")
        act_dual.triggered.connect(self.save_dual_image)
        menu.exec(self.btn_save.mapToGlobal(QPoint(0, self.btn_save.height() + 4)))

    def save_translated_image(self):
        pix = self._cached_block_pixmap or self.translated_pixmap
        if not pix:
            return
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu bản dịch đè vị trí",
            os.path.join(os.path.expanduser("~"), "Desktop", "ban_dich_de_vi_tri.png"),
            "PNG Image (*.png);;JPEG Image (*.jpg)"
        )
        if save_path:
            pix.save(save_path)
            QMessageBox.information(self, "Thành công", f"Đã lưu bản dịch đè vị trí vào:\n{save_path}")

    def save_dual_image(self):
        """
        Ghép cả 2 ảnh trái và phải thành một file ảnh so sánh song song duy nhất
        """
        trans_pix = self._cached_block_pixmap or self.translated_pixmap
        if not self.original_pixmap or not trans_pix:
            return

        w1, h1 = self.original_pixmap.width(), self.original_pixmap.height()
        w2, h2 = trans_pix.width(), trans_pix.height()
        gap = 8
        header_h = 32

        comb_w = w1 + w2 + gap
        comb_h = max(h1, h2) + header_h

        combined = QPixmap(comb_w, comb_h)
        combined.fill(QColor("#0E121B"))

        painter = QPainter(combined)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Header Titles
        f = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(f)

        painter.setPen(QPen(QColor("#94A3B8")))
        painter.drawText(QRectF(0, 0, w1, header_h), int(Qt.AlignmentFlag.AlignCenter), "📷 ẢNH GỐC")

        lang_name = get_target_lang_display_name(self.target_lang)
        painter.setPen(QPen(QColor("#C084FC")))
        painter.drawText(QRectF(w1 + gap, 0, w2, header_h), int(Qt.AlignmentFlag.AlignCenter), f"🌐 BẢN DỊCH {lang_name.upper()} (ĐÈ VỊ TRÍ 1:1)")

        # Divider
        painter.setPen(QPen(QColor(139, 92, 246, 120), 2))
        painter.drawLine(w1 + gap // 2, 0, w1 + gap // 2, comb_h)

        # Draw Pixmaps
        painter.drawPixmap(0, header_h, self.original_pixmap)
        painter.drawPixmap(w1 + gap, header_h, trans_pix)
        painter.end()

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu ảnh so sánh song song",
            os.path.join(os.path.expanduser("~"), "Desktop", "so_sanh_ban_dich.png"),
            "PNG Image (*.png);;JPEG Image (*.jpg)"
        )
        if save_path:
            combined.save(save_path)
            QMessageBox.information(self, "Thành công", f"Đã lưu ảnh so sánh song song vào:\n{save_path}")

    def closeEvent(self, event):
        if self.worker:
            self.worker.cancel()
        super().closeEvent(event)
