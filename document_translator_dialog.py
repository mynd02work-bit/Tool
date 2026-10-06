import os
import subprocess
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFileDialog, QComboBox, QFrame, QMessageBox,
    QApplication, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QSize
from PyQt6.QtGui import QFont, QColor, QDragEnterEvent, QDropEvent, QIcon

import config as app_config
from document_translator import translate_document_file

DOC_TRANSLATOR_STYLE = """
QDialog#DocumentTranslatorDialog {
    background-color: #0E121B;
    color: #F8FAFC;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, sans-serif;
}
QFrame#HeaderCard {
    background-color: #141A26;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 16px 20px;
}
QLabel#MainTitle {
    color: #F8FAFC;
    font-size: 16px;
    font-weight: 800;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
}
QLabel#SubTitle {
    color: #94A3B8;
    font-size: 12px;
    margin-top: 4px;
}
QFrame#DropZone {
    background-color: rgba(30, 41, 59, 0.4);
    border: 2px dashed rgba(139, 92, 246, 0.45);
    border-radius: 16px;
    padding: 24px;
}
QFrame#DropZone[has_file="true"] {
    background-color: rgba(99, 102, 241, 0.08);
    border: 2px solid #8B5CF6;
}
QLabel#DropIcon {
    font-size: 36px;
}
QLabel#DropText {
    color: #F1F5F9;
    font-size: 14px;
    font-weight: 700;
}
QLabel#DropHint {
    color: #64748B;
    font-size: 11px;
}
QFrame#SettingsBox {
    background-color: #141A26;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 14px 18px;
}
QLabel#SettingLabel {
    color: #94A3B8;
    font-size: 12px;
    font-weight: 600;
}
QComboBox {
    background-color: #1E293B;
    color: #FFFFFF;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
    min-width: 140px;
}
QComboBox:hover {
    border-color: #8B5CF6;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QProgressBar {
    background-color: #1E293B;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    height: 14px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:1 #8B5CF6);
    border-radius: 7px;
}
QPushButton#TranslateActionBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:0.5 #8B5CF6, stop:1 #A855F7);
    color: #FFFFFF;
    border: none;
    border-radius: 12px;
    padding: 10px 24px;
    font-size: 13px;
    font-weight: 700;
}
QPushButton#TranslateActionBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:0.5 #7C3AED, stop:1 #9333EA);
}
QPushButton#TranslateActionBtn:disabled {
    background: #334155;
    color: #64748B;
}
QPushButton#SecondaryBtn {
    background-color: rgba(255, 255, 255, 0.06);
    color: #E2E8F0;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    padding: 7px 16px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#SecondaryBtn:hover {
    background-color: rgba(255, 255, 255, 0.12);
    border-color: rgba(255, 255, 255, 0.25);
    color: #FFFFFF;
}
QPushButton#SuccessActionBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10B981);
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 700;
}
QPushButton#SuccessActionBtn:hover {
    background: #047857;
}
"""

class DocTranslationWorker(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, input_path: str, output_path: str, target_lang: str):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.target_lang = target_lang
        self._is_cancelled = False

    def start(self):
        import threading
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def cancel(self):
        self._is_cancelled = True

    def _run(self):
        try:
            def on_progress(pct, msg):
                if not self._is_cancelled:
                    self.progress.emit(pct, msg)

            saved_path = translate_document_file(
                self.input_path,
                output_path=self.output_path,
                target_lang=self.target_lang,
                progress_callback=on_progress
            )
            if not self._is_cancelled:
                self.finished.emit(saved_path)
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))


class DocumentTranslatorDialog(QDialog):
    """
    Cửa sổ Dịch Toàn Diện Tài Liệu Office (Excel, Word, PowerPoint) và PDF
    """
    def __init__(self, initial_file: str = None, parent=None):
        super().__init__(parent)
        self.setObjectName("DocumentTranslatorDialog")
        self.setStyleSheet(DOC_TRANSLATOR_STYLE)
        self.setWindowTitle("📁 Dịch Tài Liệu: Excel, Word, PowerPoint, PDF - Myshot AI")
        self.resize(680, 560)
        self.setAcceptDrops(True)

        self.current_input_file = initial_file
        self.current_output_file = ""
        self.worker = None

        self.init_ui()
        if initial_file:
            self.set_selected_file(initial_file)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # 1. Header Card
        header = QFrame()
        header.setObjectName("HeaderCard")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(3)

        title = QLabel("📁 Dịch Tài Liệu & File (Word, Excel, PPTX, PDF, Ảnh)")
        title.setObjectName("MainTitle")
        h_layout.addWidget(title)

        subtitle = QLabel("Hỗ trợ trọn vẹn: PDF (.pdf), Word (.docx), Excel (.xlsx), PowerPoint (.pptx), File ảnh - Bảo toàn 100% định dạng gốc")
        subtitle.setObjectName("SubTitle")
        h_layout.addWidget(subtitle)
        main_layout.addWidget(header)

        # 2. Drop Zone (Kéo thả hoặc Chọn File)
        self.drop_zone = QFrame()
        self.drop_zone.setObjectName("DropZone")
        self.drop_zone.setCursor(Qt.CursorShape.PointingHandCursor)
        self.drop_zone.mousePressEvent = lambda e: self.browse_file()

        dz_layout = QVBoxLayout(self.drop_zone)
        dz_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dz_layout.setSpacing(6)

        self.lbl_drop_icon = QLabel("📂")
        self.lbl_drop_icon.setObjectName("DropIcon")
        self.lbl_drop_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dz_layout.addWidget(self.lbl_drop_icon)

        self.lbl_drop_title = QLabel("Nhấp để chọn file hoặc Kéo & Thả file vào đây")
        self.lbl_drop_title.setObjectName("DropText")
        self.lbl_drop_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dz_layout.addWidget(self.lbl_drop_title)

        self.lbl_drop_hint = QLabel("Hỗ trợ: PDF (.pdf), Word (.docx), Excel (.xlsx), PowerPoint (.pptx), Ảnh (.png, .jpg...) - Giữ nguyên bố cục & định dạng")
        self.lbl_drop_hint.setObjectName("DropHint")
        self.lbl_drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dz_layout.addWidget(self.lbl_drop_hint)

        main_layout.addWidget(self.drop_zone)

        # 3. Settings Box (Ngôn ngữ & Tùy chọn)
        settings_box = QFrame()
        settings_box.setObjectName("SettingsBox")
        s_layout = QHBoxLayout(settings_box)
        s_layout.setContentsMargins(4, 4, 4, 4)
        s_layout.setSpacing(12)

        lbl_lang = QLabel("🌐 Ngôn ngữ dịch sang:")
        lbl_lang.setObjectName("SettingLabel")
        s_layout.addWidget(lbl_lang)

        self.cbo_lang = QComboBox()
        langs = [
            ("vi", "Tiếng Việt (Vietnamese)"),
            ("en", "English (Tiếng Anh)"),
            ("zh", "中文 (Tiếng Trung)"),
            ("ja", "日本語 (Tiếng Nhật)"),
            ("ko", "한국어 (Tiếng Hàn)"),
            ("fr", "Français (Tiếng Pháp)"),
            ("de", "Deutsch (Tiếng Đức)"),
            ("ru", "Русский (Tiếng Nga)"),
        ]
        cfg = app_config.load_config()
        def_lang = cfg.get("target_lang", "vi")
        for code, name in langs:
            self.cbo_lang.addItem(name, code)
        # Select default
        idx = [c for c, _ in langs].index(def_lang) if def_lang in [c for c, _ in langs] else 0
        self.cbo_lang.setCurrentIndex(idx)
        self.cbo_lang.currentIndexChanged.connect(self._on_lang_changed)
        s_layout.addWidget(self.cbo_lang)

        s_layout.addStretch()

        btn_browse = QPushButton("📁 Chọn file khác...")
        btn_browse.setObjectName("SecondaryBtn")
        btn_browse.clicked.connect(self.browse_file)
        s_layout.addWidget(btn_browse)

        main_layout.addWidget(settings_box)

        # 4. Progress Area
        self.progress_container = QWidget()
        prog_layout = QVBoxLayout(self.progress_container)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        prog_layout.setSpacing(6)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        prog_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Chưa chọn file")
        self.lbl_status.setStyleSheet("color: #94A3B8; font-size: 12px;")
        prog_layout.addWidget(self.lbl_status)

        self.progress_container.hide()
        main_layout.addWidget(self.progress_container)

        # 5. Success Action Area (Hiện ra sau khi dịch thành công)
        self.success_container = QFrame()
        self.success_container.setStyleSheet("""
            QFrame {
                background-color: rgba(16, 185, 129, 0.1);
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 12px;
                padding: 10px 14px;
            }
        """)
        suc_layout = QHBoxLayout(self.success_container)
        suc_layout.setContentsMargins(8, 8, 8, 8)
        suc_layout.setSpacing(10)

        self.lbl_success = QLabel("✓ Đã dịch và lưu file thành công!")
        self.lbl_success.setStyleSheet("color: #34D399; font-weight: bold; font-size: 13px;")
        suc_layout.addWidget(self.lbl_success)

        suc_layout.addStretch()

        self.btn_open_folder = QPushButton("📂 Mở thư mục")
        self.btn_open_folder.setObjectName("SecondaryBtn")
        self.btn_open_folder.clicked.connect(self.open_output_folder)
        suc_layout.addWidget(self.btn_open_folder)

        self.btn_open_file = QPushButton("📄 Mở file ngay")
        self.btn_open_file.setObjectName("SuccessActionBtn")
        self.btn_open_file.clicked.connect(self.open_output_file)
        suc_layout.addWidget(self.btn_open_file)

        self.success_container.hide()
        main_layout.addWidget(self.success_container)

        # 6. Bottom Buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        self.btn_cancel = QPushButton("Đóng")
        self.btn_cancel.setObjectName("SecondaryBtn")
        self.btn_cancel.clicked.connect(self.close)
        bottom_layout.addWidget(self.btn_cancel)

        bottom_layout.addStretch()

        self.btn_start = QPushButton("🚀 Bắt Đầu Dịch & Lưu File")
        self.btn_start.setObjectName("TranslateActionBtn")
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.start_translation)
        bottom_layout.addWidget(self.btn_start)

        main_layout.addLayout(bottom_layout)

    def set_selected_file(self, file_path: str):
        if not os.path.exists(file_path):
            return

        self.current_input_file = file_path
        ext = os.path.splitext(file_path)[1].lower()
        size_kb = os.path.getsize(file_path) / 1024

        badge = "📄"
        if ext in (".xlsx", ".xlsm", ".xltx", ".xls"):
            badge = "📗 Excel"
        elif ext in (".docx", ".docm", ".doc"):
            badge = "📘 Word"
        elif ext in (".pptx", ".pptm", ".ppt"):
            badge = "📙 PowerPoint"
        elif ext == ".pdf":
            badge = "📕 PDF"
        elif ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"):
            badge = "🖼️ File Ảnh"

        file_name = os.path.basename(file_path)
        self.drop_zone.setProperty("has_file", "true")
        self.drop_zone.style().unpolish(self.drop_zone)
        self.drop_zone.style().polish(self.drop_zone)

        self.lbl_drop_icon.setText(badge.split()[0])
        self.lbl_drop_title.setText(f"{badge}: {file_name}")
        self.lbl_drop_hint.setText(f"Dung lượng: {size_kb:.1f} KB | Đường dẫn: {file_path}")

        self.btn_start.setEnabled(True)
        self.success_container.hide()
        self.progress_container.hide()

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file tài liệu hoặc ảnh để dịch",
            "",
            "Tất cả file hỗ trợ (*.pdf *.docx *.xlsx *.pptx *.png *.jpg *.jpeg *.webp);;"
            "File PDF (*.pdf);;"
            "File Word (*.docx);;"
            "File Excel (*.xlsx *.xls);;"
            "File PowerPoint (*.pptx);;"
            "File ảnh (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if file_path:
            self.set_selected_file(file_path)

    def _on_lang_changed(self):
        pass

    def start_translation(self):
        if not self.current_input_file or not os.path.exists(self.current_input_file):
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn file tài liệu hợp lệ!")
            return

        target_lang = self.cbo_lang.currentData() or "vi"
        ext = os.path.splitext(self.current_input_file)[1].lower()
        base_name = os.path.splitext(self.current_input_file)[0]

        # Bảo toàn 100% định dạng gốc của file (PDF ra PDF, Word ra Word, Excel ra Excel, PPTX ra PPTX, Ảnh ra Ảnh)
        out_ext = ext
        default_out = f"{base_name}_{target_lang}{out_ext}"

        filter_str = f"File cùng định dạng (*{out_ext});;Tất cả file (*.*)"
        if ext == ".pdf":
            filter_str = "File PDF (*.pdf);;Tài liệu Word (*.docx);;Tất cả file (*.*)"
        elif ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
            filter_str = f"File ảnh (*{out_ext});;Tất cả file (*.*)"

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Chọn nơi lưu file dịch",
            default_out,
            filter_str
        )
        if not save_path:
            return

        self.current_output_file = save_path
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.success_container.hide()
        self.progress_container.show()
        self.progress_bar.setValue(0)
        self.lbl_status.setText("⏳ Đang chuẩn bị đọc và phân tích cấu trúc file...")

        self.worker = DocTranslationWorker(self.current_input_file, self.current_output_file, target_lang)
        self.worker.progress.connect(self._on_worker_progress)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.error.connect(self._on_worker_error)
        self.worker.start()

    def _on_worker_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(msg)

    def _on_worker_finished(self, saved_path: str):
        self.current_output_file = saved_path
        self.progress_bar.setValue(100)
        self.lbl_status.setText("✓ Đã dịch và lưu file thành công!")
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self.success_container.show()
        self.lbl_success.setText(f"✓ Đã lưu file: {os.path.basename(saved_path)}")

    def _on_worker_error(self, err_msg: str):
        self.progress_bar.setValue(0)
        self.lbl_status.setText(f"❌ Lỗi: {err_msg}")
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        QMessageBox.critical(self, "Lỗi dịch tài liệu", f"Không thể hoàn thành dịch file:\n\n{err_msg}")

    def open_output_folder(self):
        if self.current_output_file and os.path.exists(self.current_output_file):
            folder = os.path.dirname(self.current_output_file)
            subprocess.Popen(["explorer", f"/select,{os.path.normpath(self.current_output_file)}"])
        elif self.current_output_file:
            folder = os.path.dirname(self.current_output_file)
            if os.path.exists(folder):
                subprocess.Popen(["explorer", folder])

    def open_output_file(self):
        if self.current_output_file and os.path.exists(self.current_output_file):
            ext = os.path.splitext(self.current_output_file)[1].lower()
            if ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                try:
                    from dual_compare_window import DualCompareWindow
                    if not hasattr(self, '_dual_win') or not self._dual_win:
                        self._dual_win = DualCompareWindow()
                    self._dual_win.show()
                    self._dual_win.raise_()
                    target_l = self.cbo_lang.currentData() or "vi"
                    self._dual_win.translate_image_file(self.current_input_file, target_lang=target_l)
                except Exception:
                    os.startfile(self.current_output_file)
            else:
                try:
                    os.startfile(self.current_output_file)
                except Exception as e:
                    QMessageBox.warning(self, "Lỗi", f"Không thể mở file: {e}")

    # --- Hỗ trợ Kéo & Thả (Drag and Drop) ---
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                fpath = url.toLocalFile().lower()
                if fpath.endswith((".xlsx", ".xlsm", ".docx", ".pptx", ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp")):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                fpath = url.toLocalFile()
                if fpath.lower().endswith((".xlsx", ".xlsm", ".docx", ".pptx", ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp")):
                    self.set_selected_file(fpath)
                    event.acceptProposedAction()
                    return

    def closeEvent(self, event):
        if self.worker:
            self.worker.cancel()
        super().closeEvent(event)
