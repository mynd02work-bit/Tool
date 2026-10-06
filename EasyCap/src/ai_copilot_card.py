import subprocess
import threading
from PIL import Image

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser,
    QPushButton, QLineEdit, QFrame, QApplication, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QUrl
from PyQt6.QtGui import QFont, QColor

import html
import config as app_config
import infographic_renderer
from ai_engine import (
    ai_translate_image, ai_summarize_image, ai_explain_image, ai_chat_with_image,
    get_image_original_text, SUPPORTED_TARGET_LANGUAGES, get_target_lang_display_name
)

AI_PANEL_STYLE = """
QWidget#AICopilotCard {
    background-color: #0F172A;
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 18px;
}
QLabel#PanelTitle {
    color: #F8FAFC;
    font-size: 13px;
    font-weight: 800;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', -apple-system, sans-serif;
    letter-spacing: 0.3px;
}
QLabel#SparkleIcon {
    color: #A855F7;
    font-size: 15px;
}
QComboBox#LangSelector {
    background-color: rgba(255, 255, 255, 0.08);
    color: #F8FAFC;
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 12px;
    padding: 2px 10px 2px 8px;
    font-size: 11px;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
    font-weight: 600;
    min-height: 22px;
}
QComboBox#LangSelector:hover {
    background-color: rgba(255, 255, 255, 0.14);
    border-color: rgba(139, 92, 246, 0.6);
}
QComboBox#LangSelector::drop-down {
    border: none;
    width: 14px;
}
QComboBox#LangSelector::down-arrow {
    image: none;
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-top: 4px solid #CBD5E1;
    margin-right: 4px;
}
QComboBox#LangSelector QAbstractItemView {
    background-color: #0F172A;
    color: #F8FAFC;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 8px;
    selection-background-color: #4F46E5;
    selection-color: #FFFFFF;
    padding: 4px;
    outline: none;
}
QFrame#SegmentedBar {
    background-color: #1E293B;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 12px;
    padding: 3px;
}
QPushButton#PillBtn {
    background-color: transparent;
    color: #94A3B8;
    border: none;
    border-radius: 9px;
    padding: 6px 14px;
    font-size: 11px;
    font-weight: 600;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
}
QPushButton#PillBtn:hover {
    background-color: rgba(255, 255, 255, 0.08);
    color: #FFFFFF;
}
QPushButton#PillBtn[active="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:1 #8B5CF6);
    color: #FFFFFF;
    font-weight: 700;
}
QTextBrowser {
    background-color: #1E293B;
    color: #F8FAFC;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    padding: 14px 16px;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
    font-size: 13px;
    line-height: 1.65;
}
QLineEdit#ChatInput {
    background-color: #1E293B;
    color: #FFFFFF;
    border: 1.5px solid rgba(255, 255, 255, 0.16);
    border-radius: 18px;
    padding: 8px 16px;
    font-size: 12px;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
}
QLineEdit#ChatInput:focus {
    border: 1.5px solid #8B5CF6;
    background-color: #27354A;
}
QPushButton#SendBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:1 #8B5CF6);
    color: #FFFFFF;
    border: none;
    border-radius: 16px;
    padding: 7px 16px;
    font-weight: bold;
    font-size: 12px;
}
QPushButton#SendBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED);
}
QPushButton#ActionBtn {
    background-color: #1E293B;
    color: #CBD5E1;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 6px 14px;
    font-size: 11px;
    font-weight: 600;
}
QPushButton#ActionBtn:hover {
    background-color: rgba(255, 255, 255, 0.14);
    color: #F8FAFC;
}
QPushButton#CloseBtn {
    background: transparent;
    color: #94A3B8;
    border: none;
    font-size: 14px;
    font-weight: bold;
    border-radius: 12px;
}
QPushButton#CloseBtn:hover {
    color: #F87171;
    background-color: rgba(239, 68, 68, 0.2);
}
"""

class AIWorker(QObject):
    finished_signal = pyqtSignal(str)

    def __init__(self, task_type, pil_image, api_key, model, prompt="", chat_history=None, ocr_paras=None, target_lang="vi"):
        super().__init__()
        self.task_type = task_type
        self.pil_image = pil_image
        self.api_key = api_key
        self.model = model
        self.prompt = prompt
        self.chat_history = chat_history or []
        self.ocr_paras = ocr_paras or []
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

    def isRunning(self):
        return bool(self._thread and self._thread.is_alive())

    def _run(self):
        try:
            if self._is_cancelled:
                return
            if self.task_type == "translate":
                res = ai_translate_image(self.pil_image, target_lang=self.target_lang, api_key=self.api_key, model=self.model, ocr_paras=self.ocr_paras)
            elif self.task_type == "summarize":
                res = ai_summarize_image(self.pil_image, target_lang=self.target_lang, api_key=self.api_key, model=self.model)
            elif self.task_type == "explain":
                res = ai_explain_image(self.pil_image, target_lang=self.target_lang, api_key=self.api_key, model=self.model)
            elif self.task_type == "chat":
                res = ai_chat_with_image(self.pil_image, self.prompt, chat_history=self.chat_history, target_lang=self.target_lang, api_key=self.api_key, model=self.model)
            elif self.task_type == "extract_original":
                res = get_image_original_text(self.pil_image, api_key=self.api_key, model=self.model)
            else:
                res = "Tác vụ không xác định."
        except Exception as e:
            res = f"❌ Lỗi xử lý AI: {e}"

        if not self._is_cancelled:
            try:
                self.finished_signal.emit(res)
            except Exception:
                pass

class AICopilotCard(QWidget):
    """
    Thẻ Trợ Lý AI Nổi phong cách Raycast / Arc Browser tối giản & thẩm mỹ cao
    """
    overlay_requested = pyqtSignal(str)
    cancel_overlay_requested = pyqtSignal()
    switch_mode_requested = pyqtSignal()
    dual_view_requested = pyqtSignal()
    closed = pyqtSignal()
    target_lang_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AICopilotCard")
        self.setStyleSheet(AI_PANEL_STYLE)
        self.setFixedSize(620, 520)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        
        cfg = app_config.load_config()
        self.target_lang = cfg.get("target_lang", "vi")
        self.current_task = "translate"
        self.current_image = None
        self.original_image_text = ""
        self.chat_history = []
        self.last_ai_result = ""
        self.worker = None
        self.is_overlaid = False

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(8)

        # 1. Header
        header = QHBoxLayout()
        header.setSpacing(6)

        sparkle = QLabel("✦")
        sparkle.setObjectName("SparkleIcon")
        header.addWidget(sparkle)

        title = QLabel("AI Copilot")
        title.setObjectName("PanelTitle")
        header.addWidget(title)

        self.model_badge = QLabel("Gemini Vision")
        self.model_badge.setStyleSheet("""
            background-color: rgba(139, 92, 246, 0.15);
            color: #C084FC;
            border-radius: 9px;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: 700;
        """)
        header.addWidget(self.model_badge)
        header.addStretch()

        # Bộ chọn ngôn ngữ đích trực quan ngay trên màn hình
        self.lang_combo = QComboBox()
        self.lang_combo.setObjectName("LangSelector")
        self.lang_combo.setToolTip("Chọn ngôn ngữ dịch đích (Target Language)")
        self.lang_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        for code, name in SUPPORTED_TARGET_LANGUAGES:
            self.lang_combo.addItem(name, code)
        cur_idx = self.lang_combo.findData(self.target_lang)
        if cur_idx >= 0:
            self.lang_combo.setCurrentIndex(cur_idx)
        self.lang_combo.currentIndexChanged.connect(self.on_lang_combo_changed)
        header.addWidget(self.lang_combo)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("CloseBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close_card)
        header.addWidget(close_btn)
        main_layout.addLayout(header)

        # 2. Segmented Pill Control (Chuyển tác vụ)
        seg_frame = QFrame()
        seg_frame.setObjectName("SegmentedBar")
        seg_layout = QHBoxLayout(seg_frame)
        seg_layout.setContentsMargins(2, 2, 2, 2)
        seg_layout.setSpacing(2)

        self.pill_buttons = {}
        tasks = [
            ("translate", "🌐 Dịch AI"),
            ("summarize", "⚡ Tóm Tắt"),
            ("explain", "📊 Infographic"),
            ("chat", "💬 Hỏi Đáp"),
        ]

        for task_id, title_text in tasks:
            btn = QPushButton(title_text)
            btn.setObjectName("PillBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, t=task_id: self.switch_task(t))
            seg_layout.addWidget(btn)
            self.pill_buttons[task_id] = btn

        main_layout.addWidget(seg_frame)

        # 3. Khung nội dung phản hồi AI (dạng Rich Text Card tự co dãn 100%)
        self.txt_display = QTextBrowser()
        self.txt_display.setOpenExternalLinks(False)
        self.txt_display.setCursor(Qt.CursorShape.ArrowCursor)
        self.txt_display.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        self.txt_display.anchorClicked.connect(self.on_anchor_clicked)
        main_layout.addWidget(self.txt_display)

        # 4. Thanh Chat nhập câu hỏi dạng Capsule
        self.chat_container = QWidget()
        self.chat_layout = QHBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setSpacing(6)

        self.input_question = QLineEdit()
        self.input_question.setObjectName("ChatInput")
        self.input_question.setCursor(Qt.CursorShape.IBeamCursor)
        self.input_question.setPlaceholderText("💬 Hỏi bất kỳ điều gì về ảnh... (Enter)")
        self.input_question.returnPressed.connect(self.send_chat_message)
        self.chat_layout.addWidget(self.input_question)

        self.btn_send = QPushButton("Gửi ➤")
        self.btn_send.setObjectName("SendBtn")
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.clicked.connect(self.send_chat_message)
        self.chat_layout.addWidget(self.btn_send)
        main_layout.addWidget(self.chat_container)

        # 5. Thanh hành động phía dưới
        action_bar = QHBoxLayout()
        action_bar.setSpacing(6)

        self.btn_copy = QPushButton("📋 Copy")
        self.btn_copy.setObjectName("ActionBtn")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.clicked.connect(self.copy_result)
        action_bar.addWidget(self.btn_copy)

        self.btn_retry = QPushButton("🔄 Thử lại")
        self.btn_retry.setObjectName("ActionBtn")
        self.btn_retry.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_retry.clicked.connect(self.retry_current_task)
        action_bar.addWidget(self.btn_retry)

        action_bar.addStretch()

        self.btn_overlay = QPushButton("🔤 Dịch đè vị trí (Tab)")
        self.btn_overlay.setObjectName("ActionBtn")
        self.btn_overlay.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_overlay.setToolTip("Đè bản dịch vào đúng vị trí chữ trong ảnh (Bấm Tab để chuyển đổi)")
        self.btn_overlay.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:1 #8B5CF6);
                color: #FFFFFF;
                border: none;
                font-weight: 700;
                padding: 6px 16px;
                border-radius: 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED);
            }
        """)
        self.btn_overlay.clicked.connect(self.on_overlay_clicked)
        action_bar.addWidget(self.btn_overlay)

        main_layout.addLayout(action_bar)
        self.update_active_pill()

    def set_overlay_state(self, is_overlaid: bool, current_mode: str = None):
        self.is_overlaid = is_overlaid

        if is_overlaid:
            self.btn_overlay.setText("↩️ Về ảnh gốc (Tab)")
            self.btn_overlay.setToolTip("Khôi phục lại ảnh chụp ban đầu (Bấm Tab)")
            self.btn_overlay.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #DC2626, stop:1 #EF4444);
                    color: #FFFFFF;
                    border: 1px solid #F87171;
                    font-weight: 700;
                    padding: 6px 16px;
                    border-radius: 8px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: #B91C1C;
                }
            """)
        else:
            self.btn_overlay.setText("🔤 Dịch đè vị trí (Tab)")
            self.btn_overlay.setToolTip("Đè bản dịch vào đúng vị trí chữ trong ảnh (Bấm Tab)")
            self.btn_overlay.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:1 #8B5CF6);
                    color: #FFFFFF;
                    border: none;
                    font-weight: 700;
                    padding: 6px 16px;
                    border-radius: 8px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED);
                }
            """)

    def set_image(self, pil_image: Image.Image, default_task: str = "translate"):
        self.current_image = pil_image
        self.chat_history.clear()
        self.last_ai_result = ""
        self.original_image_text = ""
        self.original_image_paras = []
        self.set_overlay_state(False)
        cfg = app_config.load_config()
        model_name = cfg.get("gemini_model", "gemini-flash-lite-latest")
        self.model_badge.setText(model_name)

        # Trích xuất văn bản gốc siêu tốc qua Windows OCR (nếu ngôn ngữ được hỗ trợ)
        try:
            from ocr_translate import perform_ocr, is_ocr_reliable
            from ai_engine import extract_ocr_paragraphs
            ocr_lang = cfg.get("ocr_lang", "auto")
            ocr_res = perform_ocr(pil_image, lang=ocr_lang)
            if is_ocr_reliable(ocr_res):
                paras, _ = extract_ocr_paragraphs(pil_image, lang=ocr_lang)
                if paras:
                    self.original_image_paras = paras
                    self.original_image_text = "\n\n".join(paras)
        except Exception:
            pass

        self.switch_task(default_task)

    def switch_task(self, task_id: str):
        self.current_task = task_id
        self.update_active_pill()
        self.update_copy_btn_text()

        if task_id == "chat":
            self.input_question.setFocus()
            if self.original_image_text:
                self.render_chat_stream()
            else:
                cfg = app_config.load_config()
                api_key = app_config.get_effective_gemini_api_key(cfg)
                model = cfg.get("gemini_model", "gemini-flash-lite-latest")
                self.set_loading("Đang đọc văn bản gốc từ ảnh...")
                if self.worker:
                    self.worker.cancel()
                self.worker = AIWorker("extract_original", self.current_image, api_key, model)
                self.worker.finished_signal.connect(self.on_original_text_extracted)
                self.worker.start()
        else:
            self.execute_task(task_id)

    def on_original_text_extracted(self, text: str):
        if text and not text.startswith("❌") and not text.startswith("⚠️"):
            self.original_image_text = text.strip()
        else:
            self.original_image_text = text or "Không tìm thấy nội dung văn bản trong ảnh."
        self.update_copy_btn_text()
        self.render_chat_stream()

    def update_active_pill(self):
        for tid, btn in self.pill_buttons.items():
            btn.setProperty("active", "true" if tid == self.current_task else "false")
            btn.style().polish(btn)

        is_trans = (self.current_task == "translate")
        is_chat = (self.current_task == "chat")

        self.chat_container.setVisible(is_chat)
        self.txt_display.show()

        if is_trans:
            self.btn_overlay.setVisible(True)
            self.btn_overlay.setText("🔤 Đè lên ảnh (Tab)" if not self.is_overlaid else "↩️ Hủy ghi đè (Esc)")
        else:
            self.btn_overlay.setVisible(False)

    def execute_task(self, task_id: str):
        if not self.current_image:
            self.set_content("⚠️ Không có ảnh để tạo Infographic.")
            return

        cfg = app_config.load_config()
        api_key = app_config.get_effective_gemini_api_key(cfg)
        model = cfg.get("gemini_model", "gemini-flash-lite-latest")

        # Đối với các tính năng Tóm tắt / Phân tích / Chat, bắt buộc cần Gemini API Key
        if not api_key and task_id != "translate":
            self.set_content(
                "<div style='color: #FCD34D; font-size: 12px; line-height: 1.6;'>"
                "<b>⚠️ Bạn chưa cài đặt Gemini API Key:</b><br><br>"
                "1. Nhấp vào <b>⚙️ Cài đặt</b> trên thanh điều khiển.<br>"
                "2. Vào tab <b>'🤖 Gemini AI'</b> và dán API Key.<br>"
                "3. API Key hoàn toàn <b>MIỄN PHÍ</b> tại <a href='https://aistudio.google.com/app/apikey' style='color:#38BDF8;'>Google AI Studio</a>."
                "</div>"
            )
            return

        # Dừng luồng worker trước đó nếu còn đang chạy an toàn không crash
        if self.worker:
            self.worker.cancel()

        # Dừng watchdog timer cũ nếu có
        if hasattr(self, '_watchdog_timer') and self._watchdog_timer.isActive():
            self._watchdog_timer.stop()

        task_names = {
            "translate": f"Đang dịch sang {get_target_lang_display_name(self.target_lang)}...",
            "summarize": f"Đang tóm tắt bằng {get_target_lang_display_name(self.target_lang)}...",
            "explain": f"Đang thiết kế Infographic ({get_target_lang_display_name(self.target_lang)})...",
        }
        self.set_loading(task_names.get(task_id, "Gemini đang xử lý..."))
        if task_id == "translate":
            self.last_ai_result = ""
            self.btn_overlay.setEnabled(False)
            self.btn_overlay.setText("⏳ Đang dịch...")

        self.worker = AIWorker(
            task_id,
            self.current_image,
            api_key,
            model,
            ocr_paras=getattr(self, 'original_image_paras', []),
            target_lang=getattr(self, 'target_lang', 'vi')
        )
        self.worker.finished_signal.connect(self.on_task_finished)
        self.worker.start()

        # Watchdog: Nếu sau 16 giây không có phản hồi, tự động ngắt và fallback
        self._watchdog_timer = QTimer(self)
        self._watchdog_timer.setSingleShot(True)
        self._watchdog_timer.timeout.connect(lambda: self.on_task_timeout(task_id))
        self._watchdog_timer.start(16000)

    def on_lang_combo_changed(self, idx):
        new_lang = self.lang_combo.currentData()
        if not new_lang or new_lang == self.target_lang:
            return
        self.target_lang = new_lang
        cfg = app_config.load_config()
        cfg["target_lang"] = new_lang
        app_config.save_config(cfg)
        self.target_lang_changed.emit(new_lang)

        # Tự động dịch lại ngay theo ngôn ngữ đích vừa chọn
        if self.current_image and self.current_task in ("translate", "summarize", "explain"):
            self.execute_task(self.current_task)

    def set_target_lang(self, lang_code: str):
        if not lang_code:
            return
        self.target_lang = lang_code
        self.lang_combo.blockSignals(True)
        idx = self.lang_combo.findData(lang_code)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.blockSignals(False)

    def on_task_timeout(self, task_id: str):
        if self.worker:
            self.worker.cancel()

        self.btn_overlay.setEnabled(True)
        self.btn_overlay.setText("🔤 Đè lên ảnh")

        if task_id == "translate" and self.current_image:
            # Thử ngay Google Translate trực tiếp tốc độ cao nếu Gemini gặp sự cố mạng
            try:
                from ai_engine import extract_ocr_paragraphs
                from ocr_translate import translate_text
                paras, _ = extract_ocr_paragraphs(self.current_image)
                if paras:
                    batch = "\n".join(paras)
                    trans = translate_text(batch, target_lang=self.target_lang)
                    lines = [l.strip() for l in trans.split("\n") if l.strip()]
                    if len(lines) == len(paras):
                        res = "\n".join(f"[{i+1}] {t}" for i, t in enumerate(lines))
                    else:
                        res = "\n".join(f"[{i+1}] {translate_text(p, target_lang=self.target_lang)}" for i, p in enumerate(paras[:25]))
                    self.on_task_finished(res)
                    return
            except Exception:
                pass

        self.set_content(
            "<div style='color: #F87171; font-size: 13px; line-height: 1.6; text-align: center; padding-top: 30px;'>"
            "<b>⚠️ Quá thời gian phản hồi (Timeout)</b><br><br>"
            "<span style='color: #94A3B8;'>Mạng Internet hoặc máy chủ AI phản hồi chậm.<br>Vui lòng bấm '🔄 Thử lại' bên dưới.</span>"
            "</div>"
        )

    def send_chat_message(self):
        q = self.input_question.text().strip()
        if not q or not self.current_image:
            return

        cfg = app_config.load_config()
        api_key = app_config.get_effective_gemini_api_key(cfg)
        model = cfg.get("gemini_model", "gemini-flash-lite-latest")

        if not api_key:
            self.set_content("⚠️ Vui lòng cấu hình Gemini API Key trong phần Cài đặt trước.")
            return

        if self.worker:
            self.worker.cancel()

        self.input_question.clear()
        self.current_task = "chat"
        self.update_active_pill()

        self.chat_history.append({"role": "user", "text": q})
        self.render_chat_stream()

        self.worker = AIWorker(
            "chat",
            self.current_image,
            api_key,
            model,
            prompt=q,
            chat_history=self.chat_history[:-1],
            target_lang=getattr(self, 'target_lang', 'vi')
        )
        self.worker.finished_signal.connect(self.on_chat_response)
        self.worker.start()

    def on_task_finished(self, result: str):
        if hasattr(self, '_watchdog_timer') and self._watchdog_timer.isActive():
            self._watchdog_timer.stop()

        self.last_ai_result = result
        self.btn_overlay.setEnabled(True)

        if self.current_task == "explain":
            self.render_infographic(result)
            return

        self.btn_overlay.setText("🔤 Đè lên ảnh (Tab)")

        import re
        lines = [l.strip() for l in result.split('\n') if l.strip()]
        formatted_lines = []

        for idx, line in enumerate(lines):
            st = re.sub(r'^\s*\[?(?:Đoạn\s*)?\d+\]?[\.:\-\s]*', '', line).strip()
            if not st:
                continue

            # Tiêu đề chính dòng đầu tiên
            if idx == 0 and not st.startswith('•') and not st.startswith('-') and len(st) < 180:
                clean_title = re.sub(r'[*_#]', '', st).strip()
                formatted_lines.append(
                    f'<div style="font-size: 14.5px; font-weight: 700; color: #FFFFFF; line-height: 1.45; '
                    f'border-left: 3.5px solid #8B5CF6; padding: 3px 0 3px 10px; margin-bottom: 12px; '
                    f'background: rgba(139, 92, 246, 0.10); border-radius: 0 6px 6px 0;">{clean_title}</div>'
                )
                continue

            if st in ['---', '***', '___']:
                formatted_lines.append('<div style="height: 1px; background-color: rgba(255,255,255,0.12); margin: 12px 0;"></div>')
            elif st.lower().startswith('xem thêm') or st.lower().startswith('tin liên quan') or st.lower().startswith('đọc thêm'):
                clean_sec = re.sub(r'[*_#:]', '', st).strip()
                formatted_lines.append(
                    f'<div style="margin-top: 14px; margin-bottom: 8px; padding-top: 8px; '
                    f'border-top: 1px dashed rgba(255,255,255,0.18); color: #93C5FD; font-weight: 700; font-size: 12px; '
                    f'text-transform: uppercase; letter-spacing: 0.5px;">📰 {clean_sec}</div>'
                )
            elif st.startswith('### ') or st.startswith('## ') or st.startswith('# '):
                head = re.sub(r'^#{1,3}\s*', '', st).strip()
                formatted_lines.append(f'<div style="color: #A5B4FC; font-size: 13.5px; font-weight: bold; margin-top: 10px; margin-bottom: 6px;">{head}</div>')
            elif st.startswith('•') or st.startswith('* ') or st.startswith('- '):
                item = re.sub(r'^[•\-\*]\s*', '', st).strip()
                item_bold = re.sub(r'\*\*(.*?)\*\*', r'<b style="color: #FFFFFF;">\1</b>', item)
                formatted_lines.append(f'<div style="margin-left: 6px; margin-bottom: 6px; line-height: 1.55; color: #E2E8F0;"><span style="color: #60A5FA; font-weight: bold; margin-right: 6px;">•</span>{item_bold}</div>')
            elif re.match(r'^\d+\.\s', st):
                dot_pos = st.find('.')
                num = st[:dot_pos+1]
                content = st[dot_pos+1:].strip()
                content_bold = re.sub(r'\*\*(.*?)\*\*', r'<b style="color: #FFFFFF;">\1</b>', content)
                formatted_lines.append(f'<div style="margin-left: 6px; margin-bottom: 6px; line-height: 1.55; color: #E2E8F0;"><span style="color: #38BDF8; font-weight: bold; margin-right: 6px;">{num}</span>{content_bold}</div>')
            else:
                line_bold = re.sub(r'\*\*(.*?)\*\*', r'<b style="color: #FFFFFF;">\1</b>', st)
                formatted_lines.append(f'<div style="margin-bottom: 8px; line-height: 1.65; color: #F1F5F9;">{line_bold}</div>')

        html = f"""
        <div style="font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif; font-size: 13px; line-height: 1.65; color: #F8FAFC; padding: 4px;">
            {"".join(formatted_lines)}
        </div>
        """
        self.txt_display.setHtml(html)

    def on_chat_response(self, response: str):
        self.chat_history.append({"role": "assistant", "text": response})
        self.last_ai_result = response
        self.update_copy_btn_text()
        self.render_chat_stream()

    def update_copy_btn_text(self):
        if self.current_task == "chat":
            if self.chat_history and self.chat_history[-1].get("role") == "assistant":
                self.btn_copy.setText("📋 Copy Trả Lời")
            else:
                self.btn_copy.setText("📋 Copy Bản Gốc")
        else:
            self.btn_copy.setText("📋 Copy")

    def render_infographic(self, raw_text: str):
        """
        Biến văn bản phân tích từ AI thành giao diện Infographic dạng chữ trực quan,
        sinh động với các khối thẻ Visual Cards, điểm cốt lõi và số liệu nổi bật.
        Dạng văn bản tự co dãn 100%, cuộn mượt mà và dễ dàng chọn/sao chép chữ.
        """
        import html
        import re

        raw_clean = (raw_text or "").strip()
        lines = [line.strip() for line in raw_clean.split('\n') if line.strip()]
        if not lines:
            self.set_content("<div style='color: #94A3B8; text-align: center; padding: 25px;'>Không có dữ liệu phân tích.</div>")
            return

        title = ""
        tldr = ""
        sections = []  # list of (title, items)
        conclusion = None  # (title, items)

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
                    sec_data = (current_sec_title, list(current_sec_items))
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
            sec_data = (current_sec_title, list(current_sec_items))
            if any(k in current_sec_title.lower() for k in ['kết luận', 'lưu ý', 'khuyến nghị', 'bài học', 'takeaway']):
                conclusion = sec_data
            else:
                sections.append(sec_data)

        if not sections and not conclusion and current_sec_items:
            sections.append(("💡 Tổng Quan Phân Tích", current_sec_items))

        if not title:
            title = "📊 Báo Cáo Phân Tích Infographic"

        CARD_PALETTES = [
            {"border": "rgba(99, 102, 241, 0.45)", "bg": "#181F38", "title_color": "#A78BFA", "bullet_color": "#818CF8"},
            {"border": "rgba(14, 165, 233, 0.45)", "bg": "#132338", "title_color": "#38BDF8", "bullet_color": "#0284C7"},
            {"border": "rgba(16, 185, 129, 0.45)", "bg": "#132D28", "title_color": "#34D399", "bullet_color": "#10B981"},
            {"border": "rgba(245, 158, 11, 0.45)", "bg": "#282317", "title_color": "#FBBF24", "bullet_color": "#F59E0B"},
            {"border": "rgba(236, 72, 153, 0.45)", "bg": "#2A1828", "title_color": "#F472B6", "bullet_color": "#EC4899"},
        ]

        def format_inline_markdown(text):
            text = re.sub(r'\*\*(.*?)\*\*', r'<b style="color: #FFFFFF;">\1</b>', text)
            text = re.sub(r'(?<!\*)\*(?!\*)(.*?)\*', r'<i>\1</i>', text)
            text = re.sub(r'`(.*?)`', r'<code style="background-color: rgba(255,255,255,0.1); padding: 1px 4px; border-radius: 4px; color: #38BDF8;">\1</code>', text)
            return text

        html_blocks = []
        html_blocks.append("""
        <div style="font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, sans-serif; color: #F8FAFC; padding: 2px 4px;">
        """)

        # 1. HEADER BANNER
        clean_title = format_inline_markdown(html.escape(title))
        html_blocks.append(f"""
        <div style="background-color: #1E1B4B; border: 1px solid #6366F1; border-radius: 12px; padding: 11px 14px; margin-bottom: 11px;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                    <td align="left" valign="middle">
                        <span style="background-color: #4F46E5; color: #FFFFFF; font-size: 10px; font-weight: 800; padding: 3px 8px; border-radius: 6px; letter-spacing: 0.5px;">📊 INFOGRAPHIC INSIGHT</span>
                    </td>
                    <td align="right" valign="middle">
                        <span style="color: #A5B4FC; font-size: 11px; font-weight: 600;">✦ Gemini Vision</span>
                    </td>
                </tr>
            </table>
            <div style="color: #FFFFFF; font-size: 15px; font-weight: 800; margin-top: 8px; line-height: 1.4;">
                {clean_title}
            </div>
        </div>
        """)

        # 2. CORE TAKEAWAY (TL;DR)
        if tldr:
            clean_tldr = format_inline_markdown(html.escape(tldr))
            html_blocks.append(f"""
            <div style="background-color: #1E293B; border-left: 4px solid #38BDF8; border-radius: 8px; padding: 9px 13px; margin-bottom: 11px;">
                <div style="color: #38BDF8; font-weight: 800; font-size: 11px; letter-spacing: 0.5px; margin-bottom: 3px;">🎯 THÔNG ĐIỆP CỐT LÕI:</div>
                <div style="color: #F1F5F9; font-size: 13px; font-weight: 500; line-height: 1.55;">
                    {clean_tldr}
                </div>
            </div>
            """)

        # 3. VISUAL CARDS
        for i, (sec_title, items) in enumerate(sections):
            pal = CARD_PALETTES[i % len(CARD_PALETTES)]
            clean_sec_title = format_inline_markdown(html.escape(sec_title))

            items_html = []
            for item in items:
                clean_item = format_inline_markdown(html.escape(item))
                items_html.append(f"""
                <div style="margin-bottom: 6px; padding-left: 2px;">
                    <span style="color: {pal['bullet_color']}; font-weight: bold; font-size: 13px;">➜</span>
                    <span style="color: #E2E8F0; font-size: 12.5px; line-height: 1.55; margin-left: 4px;">{clean_item}</span>
                </div>
                """)

            html_blocks.append(f"""
            <div style="background-color: {pal['bg']}; border: 1px solid {pal['border']}; border-radius: 11px; padding: 11px 13px; margin-bottom: 10px;">
                <div style="color: {pal['title_color']}; font-size: 13px; font-weight: 800; margin-bottom: 8px; letter-spacing: 0.3px;">
                    {clean_sec_title}
                </div>
                <div>
                    {"".join(items_html)}
                </div>
            </div>
            """)

        # 4. KẾT LUẬN & LƯU Ý
        if conclusion:
            con_title, con_items = conclusion
            clean_con_title = format_inline_markdown(html.escape(con_title))
            con_items_html = []
            for item in con_items:
                clean_item = format_inline_markdown(html.escape(item))
                con_items_html.append(f"""
                <div style="margin-bottom: 5px;">
                    <span style="color: #10B981; font-weight: bold;">✦</span>
                    <span style="color: #ECFDF5; font-size: 12.5px; line-height: 1.55; margin-left: 4px;">{clean_item}</span>
                </div>
                """)

            html_blocks.append(f"""
            <div style="background-color: #064E3B; border: 1px solid rgba(16, 185, 129, 0.6); border-radius: 11px; padding: 11px 13px; margin-bottom: 10px;">
                <div style="color: #6EE7B7; font-size: 13px; font-weight: 800; margin-bottom: 8px;">
                    {clean_con_title}
                </div>
                <div>
                    {"".join(con_items_html)}
                </div>
            </div>
            """)

        html_blocks.append("</div>")

        final_html = "".join(html_blocks)
        self.txt_display.setHtml(final_html)
        self.txt_display.verticalScrollBar().setValue(0)

    def render_chat_stream(self):
        import html
        import re
        html_parts = []

        # 1. Khung hiển thị Văn bản gốc trích xuất từ ảnh cho người dùng xem và copy
        if self.original_image_text:
            escaped_orig = html.escape(self.original_image_text).replace("\n", "<br>")
            html_parts.append(f"""
            <div style="background-color: #1E293B; border: 1px solid rgba(56, 189, 248, 0.4); border-radius: 12px; padding: 10px 14px; margin-bottom: 12px;">
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 6px;">
                    <tr>
                        <td align="left" valign="middle">
                            <span style="color: #38BDF8; font-weight: bold; font-size: 11px; letter-spacing: 0.5px;">📄 NỘI DUNG GỐC TRONG ẢNH:</span>
                        </td>
                        <td align="right" valign="middle">
                            <a href="#copy_original" style="background-color: #3B82F6; color: #FFFFFF; text-decoration: none; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;">📋 Sao Chép Bản Gốc</a>
                        </td>
                    </tr>
                </table>
                <div style="color: #F8FAFC; font-size: 13px; line-height: 1.6; font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif;">
                    {escaped_orig}
                </div>
            </div>
            """)

        # 2. Các tin nhắn hội thoại
        for msg in self.chat_history:
            role = msg["role"]
            raw_text = msg["text"]
            if role == "user":
                clean_user = html.escape(raw_text).replace("\n", "<br>")
                html_parts.append(f"""
                <div style="margin-bottom: 12px; text-align: right;">
                    <div style="display: inline-block; background-color: #6366F1; color: #FFFFFF; padding: 8px 14px; border-radius: 16px 16px 3px 16px; font-size: 13px; font-weight: 500; max-width: 82%; text-align: left; line-height: 1.5;">
                        {clean_user}
                    </div>
                </div>
                """)
            else:
                s = re.sub(r'\*\*(.*?)\*\*', r'<b style="color: #FFFFFF;">\1</b>', raw_text)
                lines = s.split('\n')
                formatted_lines = []
                for line in lines:
                    st = line.strip()
                    if st.startswith('* ') or st.startswith('- '):
                        item = st[2:].strip()
                        formatted_lines.append(f'<div style="margin-left: 8px; margin-bottom: 5px;"><span style="color: #A78BFA; font-weight: bold;">•</span> {item}</div>')
                    elif re.match(r'^\d+\.\s', st):
                        dot_pos = st.find('.')
                        num = st[:dot_pos+1]
                        content = st[dot_pos+1:].strip()
                        formatted_lines.append(f'<div style="margin-left: 8px; margin-bottom: 5px;"><span style="color: #38BDF8; font-weight: bold;">{num}</span> {content}</div>')
                    elif not st:
                        formatted_lines.append('<div style="height: 6px;"></div>')
                    else:
                        formatted_lines.append(f'<div style="margin-bottom: 3px;">{line}</div>')

                html_parts.append(f"""
                <div style="margin-bottom: 14px; text-align: left;">
                    <div style="color: #C084FC; font-weight: 700; font-size: 11px; margin-bottom: 4px;">✦ GEMINI AI:</div>
                    <div style="background-color: #27354A; color: #F8FAFC; padding: 12px 16px; border-radius: 3px 16px 16px 16px; border: 1px solid rgba(255, 255, 255, 0.12); font-size: 13px; line-height: 1.65;">
                        {"".join(formatted_lines)}
                    </div>
                </div>
                """)

        # 3. Gợi ý câu hỏi nếu chưa chat
        if not self.chat_history:
            html_parts.append("""
            <div style="color: #94A3B8; font-size: 12px; line-height: 1.6; margin-top: 6px; padding: 2px 4px;">
                <span style="color: #A78BFA; font-weight: bold;">✦ Gợi ý câu hỏi nhanh:</span><br>
                <div style="margin-top: 4px;">• <i>'Giải thích chi tiết đoạn văn bản trên'</i></div>
                <div>• <i>'Tóm tắt nội dung này trong 2 câu ngắn'</i></div>
                <div>• <i>'Chỉ ra các điểm quan trọng cần lưu ý'</i></div>
            </div>
            """)

        self.txt_display.setHtml("".join(html_parts))
        if self.chat_history:
            self.txt_display.verticalScrollBar().setValue(self.txt_display.verticalScrollBar().maximum())
        else:
            self.txt_display.verticalScrollBar().setValue(0)

    def set_loading(self, text: str):
        self.txt_display.setHtml(f"""
        <div style="color: #A855F7; font-family: 'Segoe UI Variable Text'; font-size: 13px; padding-top: 28px; text-align: center;">
            <p style="font-size: 20px;">✦</p>
            <p><b>{text}</b></p>
        </div>
        """)

    def set_content(self, html_or_text: str):
        self.txt_display.setHtml(html_or_text)

    def on_anchor_clicked(self, url):
        url_str = url.toString()
        if url_str == "#copy_original":
            if self.original_image_text:
                QApplication.clipboard().setText(self.original_image_text)
                prev_text = self.btn_copy.text()
                self.btn_copy.setText("✓ Đã copy bản gốc")
                QTimer.singleShot(1500, lambda: self.btn_copy.setText(prev_text))
        elif url_str.startswith("http"):
            from PyQt6.QtGui import QDesktopServices
            QDesktopServices.openUrl(url)

    def retry_current_task(self):
        if self.current_task == "chat":
            self.original_image_text = ""
            self.chat_history.clear()
        self.switch_task(self.current_task)

    def copy_result(self):
        if self.current_task == "chat":
            if self.chat_history and self.chat_history[-1].get("role") == "assistant":
                text = self.chat_history[-1]["text"]
            else:
                text = self.original_image_text or self.txt_display.toPlainText()
        else:
            text = self.last_ai_result or self.txt_display.toPlainText()

        if text:
            QApplication.clipboard().setText(text)
            prev_label = self.btn_copy.text()
            self.btn_copy.setText("✓ Đã copy")
            QTimer.singleShot(1500, lambda: self.btn_copy.setText(prev_label))

    def on_overlay_clicked(self):
        if self.is_overlaid:
            self.cancel_overlay_requested.emit()
            return

        text = (self.last_ai_result or "").strip()
        if text and not text.startswith("❌") and not text.startswith("⚠️"):
            self.overlay_requested.emit(text)

    def close_card(self):
        if hasattr(self, '_watchdog_timer') and self._watchdog_timer.isActive():
            self._watchdog_timer.stop()
        if self.worker:
            self.worker.cancel()
        self.hide()
        self.closed.emit()

    def focusNextPrevChild(self, next: bool) -> bool:
        if hasattr(self, 'input_question') and self.input_question.hasFocus():
            return super().focusNextPrevChild(next)
        return False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close_card()
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Tab:
            if not (hasattr(self, 'input_question') and self.input_question.hasFocus()):
                self.switch_mode_requested.emit()
                event.accept()
                return
        super().keyPressEvent(event)
