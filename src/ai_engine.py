import io
import base64
import json
import urllib.request
import urllib.error
import socket
from PIL import Image

# Đặt timeout toàn cục cho tất cả socket mạng để tuyệt đối không bao giờ bị treo vô tận
socket.setdefaulttimeout(30.0)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

def pil_to_base64(pil_img: Image.Image, format="JPEG", quality=85, max_dim=2048) -> str:
    if pil_img.mode in ("RGBA", "P"):
        pil_img = pil_img.convert("RGB")
    w, h = pil_img.size
    if max_dim and max(w, h) > max_dim:
        ratio = max_dim / max(w, h)
        pil_img = pil_img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    pil_img.save(buffer, format=format, quality=quality)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def _send_gemini_request(api_key: str, model: str, payload: dict, timeout: int = 15):
    # Loại bỏ tiền tố 'models/' nếu người dùng hoặc config có vô tình thêm vào
    clean_model = model.replace("models/", "").strip()
    clean_key = api_key.strip()

    url = GEMINI_API_URL.format(model=clean_model, api_key=clean_key)
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

def extract_ocr_paragraphs(pil_img: Image.Image, lang: str = "auto") -> tuple[list[str], list[dict]]:
    """
    Trích xuất văn bản từ ảnh qua Windows OCR và gom cụm đoạn văn thông minh (Smart Reading Flow):
    - Tự động phát hiện các dòng thuộc cùng một đoạn văn (Paragraph) dựa trên lề trái, độ rộng và khoảng cách dòng chuẩn.
    - Giữ các nút bấm, menu, nhãn giao diện hoặc tiêu đề thành từng dòng độc lập (1:1).
    - Hỗ trợ đa ngôn ngữ (tiếng Anh, tiếng Trung, tiếng Nhật, tiếng Việt...).
    Trả về:
    - paras: danh sách chuỗi văn bản của từng khối đoạn [para_1, para_2, ...]
    - blocks: danh sách bounding box (x, y, w, h, avg_line_h, original) của từng khối
    """
    try:
        from ocr_translate import perform_ocr
        ocr_res = perform_ocr(pil_img, lang=lang)
        if not ocr_res.get("success"):
            return [], []

        raw_lines = ocr_res.get("lines", [])
        valid_lines = [l for l in raw_lines if len(l.get("text", "").strip()) >= 1 and l.get("w", 0) >= 4 and l.get("h", 0) >= 4]
        if not valid_lines:
            raw_txt = ocr_res.get("text", "").strip()
            return ([raw_txt] if raw_txt else []), []

        # Sắp xếp các dòng theo cột trước (x theo cụm), sau đó theo thứ tự y từ trên xuống
        sorted_lines = sorted(valid_lines, key=lambda l: (round(l.get('x', 0) / 70.0), l.get('y', 0)))

        # Gom các dòng thuộc cùng một đoạn văn bản hoặc tiêu đề
        groups = []
        curr_g = [sorted_lines[0]]

        for l in sorted_lines[1:]:
            prev = curr_g[-1]
            prev_h = prev.get('h', 16)
            curr_h = l.get('h', 16)
            gap_y = l.get('y', 0) - (prev.get('y', 0) + prev_h)

            # Cùng cột: lề trái gần nhau hoặc có độ giao nhau ngang lớn
            prev_r = prev.get('x', 0) + prev.get('w', 0)
            l_r = l.get('x', 0) + l.get('w', 0)
            overlap = min(prev_r, l_r) - max(prev.get('x', 0), l.get('x', 0))
            is_same_col = abs(l.get('x', 0) - prev.get('x', 0)) <= max(35.0, prev.get('w', 40) * 0.35) or (overlap >= min(prev.get('w', 40), l.get('w', 40)) * 0.40)
            
            # Cỡ font tương đồng: Tiêu đề (25-35px) và thân bài (12-16px) tuyệt đối không gom chung một khối
            h_ratio = min(prev_h, curr_h) / max(1, max(prev_h, curr_h))
            is_similar_font = (h_ratio >= 0.70)

            # Khoảng cách dòng chuẩn trong cùng một đoạn văn bản:
            # Nếu khoảng cách lớn (> 0.85 chiều cao dòng) -> Là khoảng cách giữa tiêu đề và bài viết, cần tách khối
            is_tight_gap = (-prev_h * 0.35 <= gap_y <= prev_h * 0.85)

            if is_same_col and is_similar_font and is_tight_gap:
                curr_g.append(l)
            else:
                groups.append(curr_g)
                curr_g = [l]

        if curr_g:
            groups.append(curr_g)

        all_blocks = []
        paras = []
        for g in groups:
            min_x = min(item['x'] for item in g)
            min_y = min(item['y'] for item in g)
            max_x = max(item['x'] + item['w'] for item in g)
            max_y = max(item['y'] + item['h'] for item in g)
            combined_text = " ".join(item['text'].strip() for item in g).strip()
            if not combined_text:
                continue
            paras.append(combined_text)
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
        return paras, all_blocks
    except Exception:
        return [], []

def extract_ocr_text(pil_img: Image.Image, lang: str = "en-US") -> str:
    paras, _ = extract_ocr_paragraphs(pil_img, lang)
    return "\n\n".join(paras)

def test_gemini_connection(api_key: str, model: str = "gemini-flash-lite-latest") -> tuple[bool, str]:
    """
    Kiểm tra tính hợp lệ của API Key với cơ chế tự động chuyển model dự phòng thông minh.
    Hỗ trợ cả khóa AIzaSy truyền thống và khóa định dạng mới AQ. từ Google AI Studio.
    """
    if not api_key or not api_key.strip():
        return False, "Vui lòng nhập API Key trước khi kiểm tra."

    clean_key = api_key.strip()
    
    if len(clean_key) < 15:
        return False, "API Key quá ngắn hoặc không đúng định dạng. Vui lòng kiểm tra lại mã đã sao chép từ Google AI Studio."

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": "Hello, respond with OK."}
                ]
            }
        ]
    }

    # Danh sách model thử nghiệm theo thứ tự ưu tiên: model được chọn -> các model hoạt động ổn định nhất
    candidate_pool = [
        model,
        "gemini-flash-lite-latest",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite"
    ]
    models_to_try = []
    for m in candidate_pool:
        if m and m not in models_to_try:
            models_to_try.append(m)

    last_error = ""
    for m in models_to_try:
        try:
            res_json = _send_gemini_request(clean_key, m, payload, timeout=5)
            if "candidates" in res_json and len(res_json["candidates"]) > 0:
                if m == model:
                    return True, f"Kết nối thành công tới mô hình {m}!"
                else:
                    return True, f"Kết nối thành công! Đã tự động kết nối mô hình khả dụng ({m})."
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            try:
                err_json = json.loads(err_body)
                last_error = err_json.get("error", {}).get("message", str(e))
            except Exception:
                last_error = f"Lỗi HTTP {e.code}: {e.reason}"
        except Exception as e:
            last_error = str(e)

    return False, f"Không thể kết nối: {last_error}"

def query_gemini_vision(
    api_key: str,
    pil_img: Image.Image,
    prompt: str,
    model: str = "gemini-flash-lite-latest",
    chat_history: list = None
) -> str:
    """
    Gửi ảnh và prompt trực tiếp tới Gemini Multimodal Vision API
    """
    if not api_key or not api_key.strip():
        try:
            import config as app_config
            api_key = app_config.get_effective_gemini_api_key()
        except Exception:
            pass

    if not api_key or not api_key.strip():
        return "⚠️ Bạn chưa nhập Gemini API Key. Hãy mở Cài đặt (⚙️) ➔ Tab 'Gemini AI' để dán key hoàn toàn miễn phí."

    clean_key = api_key.strip()
    b64_image = pil_to_base64(pil_img)

    contents = []
    if chat_history:
        for msg in chat_history:
            role = msg.get("role", "user")
            text = msg.get("text", "")
            contents.append({
                "role": "model" if role == "assistant" else "user",
                "parts": [{"text": text}]
            })

    current_parts = [
        {"text": prompt},
        {
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": b64_image
            }
        }
    ]
    contents.append({
        "role": "user",
        "parts": current_parts
    })

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 8192,
        }
    }

    # Thử model chính, nếu gặp lỗi tự động fallback sang các model dự phòng khả dụng
    candidate_pool = [
        model,
        "gemini-flash-lite-latest",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite"
    ]
    models_to_try = []
    for m in candidate_pool:
        if m and m not in models_to_try:
            models_to_try.append(m)

    last_err_msg = ""
    for m in models_to_try:
        try:
            res_json = _send_gemini_request(clean_key, m, payload, timeout=25)
            candidates = res_json.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            try:
                err_json = json.loads(err_body)
                last_err_msg = err_json.get("error", {}).get("message", str(e))
            except Exception:
                last_err_msg = f"HTTP {e.code}"
        except Exception as e:
            last_err_msg = str(e)

    return f"❌ Lỗi Gemini AI: {last_err_msg}"

SUPPORTED_TARGET_LANGUAGES = [
    ("vi", "Tiếng Việt"),
    ("en", "English"),
    ("zh-CN", "中文 (简体)"),
    ("zh-TW", "中文 (繁體)"),
    ("ja", "日本語 (Tiếng Nhật)"),
    ("ko", "한국어 (Tiếng Hàn)"),
    ("fr", "Français (Tiếng Pháp)"),
    ("de", "Deutsch (Tiếng Đức)"),
    ("ru", "Русский (Tiếng Nga)"),
    ("es", "Español (Tây Ban Nha)"),
    ("th", "ภาษาไทย (Tiếng Thái)"),
    ("hi", "हिन्दी (Tiếng Hindi)"),
    ("id", "Indonesia"),
    ("pt", "Português"),
    ("it", "Italiano"),
    ("ar", "العربية (Tiếng Ả Rập)")
]

LANG_NAME_MAP = {
    "vi": "Tiếng Việt",
    "en": "Tiếng Anh (English)",
    "zh": "Tiếng Trung Giản Thể (Simplified Chinese)",
    "zh-cn": "Tiếng Trung Giản Thể (Simplified Chinese)",
    "zh-tw": "Tiếng Trung Phồn Thể (Traditional Chinese)",
    "ja": "Tiếng Nhật (Japanese)",
    "ko": "Tiếng Hàn (Korean)",
    "fr": "Tiếng Pháp (French)",
    "de": "Tiếng Đức (German)",
    "ru": "Tiếng Nga (Russian)",
    "es": "Tiếng Tây Ban Nha (Spanish)",
    "th": "Tiếng Thái (Thai)",
    "hi": "Tiếng Hindi (Hindi)",
    "id": "Tiếng Indonesia (Indonesian)",
    "pt": "Tiếng Bồ Đào Nha (Portuguese)",
    "it": "Tiếng Ý (Italian)",
    "ar": "Tiếng Ả Rập (Arabic)"
}

def get_target_lang_display_name(code: str) -> str:
    clean = (code or "vi").strip().lower().replace("_", "-")
    return LANG_NAME_MAP.get(clean, LANG_NAME_MAP.get(clean.split("-")[0], code or "Tiếng Việt"))

def ai_translate_image(
    pil_img: Image.Image,
    target_lang: str = "vi",
    api_key: str = "",
    model: str = "gemini-flash-lite-latest",
    ocr_paras: list = None
) -> str:
    if not api_key or not api_key.strip():
        try:
            import config as app_config
            api_key = app_config.get_effective_gemini_api_key()
        except Exception:
            pass

    if ocr_paras is not None:
        paras = ocr_paras
    else:
        from ocr_translate import perform_ocr, is_ocr_reliable
        ocr_res = perform_ocr(pil_img)
        reliable = is_ocr_reliable(ocr_res)
        paras, _ = extract_ocr_paragraphs(pil_img) if reliable else ([], [])

    target_name = get_target_lang_display_name(target_lang)

    ocr_hint = ""
    if paras and len("\n".join(paras).strip()) >= 20:
        sample_text = "\n".join(paras[:15])
        ocr_hint = (
            f"\n\nTHAM KHẢO VĂN BẢN TỪ MÁY (NẾU CÓ):\n{sample_text}\n"
            "LƯU Ý ĐẶC BIỆT: Bạn BẮT BUỘC QUAN SÁT HÌNH ẢNH TRỰC TIẾP để đọc và dịch đầy đủ và chuẩn xác tất cả nội dung (tiêu đề, bài viết, số liệu). "
            "Nếu văn bản tham khảo trên bị thiếu hoặc không đúng ngôn ngữ trong ảnh, HÃY HOÀN TOÀN DỊCH TRỰC TIẾP TỪ HÌNH ẢNH.\n"
        )

    prompt = (
        f"Bạn là chuyên gia dịch thuật đa ngôn ngữ và tài liệu hình ảnh chuyên nghiệp.\n\n"
        f"NHIỆM VỤ:\n"
        f"1. Tự động nhận diện chính xác ngôn ngữ gốc trong hình ảnh (bất kể là tiếng Hindi, tiếng Anh, tiếng Trung, tiếng Nhật, tiếng Hàn, tiếng Pháp, tiếng Nga, tiếng Ả Rập, tiếng Việt hay bất kỳ ngôn ngữ nào trên thế giới).\n"
        f"2. Dịch ĐẦY ĐỦ, TOÀN DIỆN VÀ CHUẨN XÁC 100% tất cả các nội dung trong ảnh sang {target_name}.\n\n"
        f"YÊU CẦU CHẤT LƯỢNG BẮT BUỘC:\n"
        f"1. TÍNH CHÍNH XÁC & LOGIC:\n"
        f"   - Giữ nguyên 100% các con số, tỷ số (2:1), ngày giờ, mã số, tên riêng nhân vật / vận động viên.\n"
        f"   - Tên quốc gia, địa danh được dịch chuẩn xác theo ngôn ngữ đích {target_name}.\n"
        f"   - Tiêu đề và nội dung bài viết phải ăn khớp logic tuyệt đối theo ngữ pháp tự nhiên của {target_name}.\n"
        f"2. CẤU TRÚC VĂN BẢN RÕ RÀNG:\n"
        f"   - Tiêu đề chính in đậm trên dòng đầu tiên: **Tiêu đề**\n"
        f"   - Đoạn thân bài viết liền mạch, đầy đủ câu từ, hành văn tự nhiên.\n"
        f"   - Phần tin liên quan / danh sách: Sử dụng các gạch đầu dòng bắt đầu bằng dấu '• '.\n"
        f"3. Tuyệt đối KHÔNG tự tiện đánh số [1], [2] nếu bản gốc không có số.\n"
        f"4. CHỈ trả về đúng bản dịch hoàn chỉnh sang {target_name}, không kèm giải thích thừa hay lời chào."
        + ocr_hint
    )

    res = ""
    if api_key and api_key.strip():
        res = query_gemini_vision(api_key, pil_img, prompt, model=model)

    # Nếu Gemini gặp sự cố (mất mạng, lỗi key, rate limit, timeout) -> Tự động fallback sang Google Translate siêu tốc (<0.5s)
    if not res or res.startswith("❌") or res.startswith("⚠️"):
        if paras:
            try:
                from ocr_translate import translate_text
                # Thử dịch theo lô toàn bộ văn bản trong 1 request HTTP duy nhất
                batch_text = "\n".join(paras)
                trans_all = translate_text(batch_text, target_lang=target_lang)
                if trans_all and not trans_all.startswith("[Lỗi"):
                    trans_lines = [l.strip() for l in trans_all.split("\n") if l.strip()]
                    if len(trans_lines) == len(paras):
                        return "\n".join(f"[{i+1}] {t}" for i, t in enumerate(trans_lines))
                
                # Nếu số dòng tách không khớp hoặc có sự cố, dịch từng dòng nhanh
                fallback_items = []
                for i, p in enumerate(paras[:25]):
                    trans = translate_text(p, target_lang=target_lang)
                    if trans.startswith("[Lỗi"):
                        trans = p
                    fallback_items.append(f"[{i+1}] {trans}")
                return "\n".join(fallback_items)
            except Exception:
                pass

    return res

def ai_summarize_image(pil_img: Image.Image, target_lang: str = "vi", api_key: str = "", model: str = "gemini-flash-lite-latest") -> str:
    target_name = get_target_lang_display_name(target_lang)
    ocr_text = extract_ocr_text(pil_img)
    if ocr_text:
        prompt = (
            f"Dưới đây là nội dung trong ảnh chụp:\n\"\"\"\n{ocr_text}\n\"\"\"\n\n"
            f"Hãy đọc và tóm tắt nội dung trên thành 3 đến 5 gạch đầu dòng cô đọng nhất bằng {target_name}. "
            f"Nêu bật các số liệu, luận điểm hoặc thông tin quan trọng nhất."
        )
    else:
        prompt = (
            f"Hãy đọc toàn bộ thông tin trong bức ảnh này và tóm tắt thành 3 đến 5 gạch đầu dòng cô đọng nhất bằng {target_name}. "
            f"Nêu bật các số liệu, luận điểm hoặc hành động quan trọng nhất."
        )
    return query_gemini_vision(api_key, pil_img, prompt, model=model)

def ai_explain_image(pil_img: Image.Image, target_lang: str = "vi", api_key: str = "", model: str = "gemini-flash-lite-latest") -> str:
    """
    Phân tích toàn diện ảnh và trích xuất thành bản INFOGRAPHIC trực quan, sinh động và cô đọng theo ngôn ngữ đích.
    """
    target_name = get_target_lang_display_name(target_lang)
    ocr_text = extract_ocr_text(pil_img)
    text_ctx = f"\n\nVăn bản nhận dạng từ ảnh:\n\"\"\"\n{ocr_text}\n\"\"\"" if ocr_text else ""
    prompt = (
        f"Bạn là một chuyên gia thiết kế Infographic và truyền thông thị giác. "
        f"Hãy phân tích toàn diện nội dung trong bức ảnh này và biến nó thành một bản INFOGRAPHIC CÔ ĐỌNG, TRỰC QUAN BẰNG {target_name.upper()}.{text_ctx}\n\n"
        f"BẮT BUỘC TUÂN THỦ CẤU TRÚC SAU ĐÂY:\n"
        f"1. Dòng đầu tiên là TIÊU ĐỀ: Bắt đầu bằng '# ' kèm emoji đại diện phù hợp nhất.\n"
        f"2. Dòng thứ hai là ĐIỂM CỐT LÕI (TL;DR): Bắt đầu bằng '> ' nêu thông điệp đắt giá nhất trong 1 câu ngắn gọn.\n"
        f"3. CÁC KHỐI PHÂN TÍCH (Visual Cards): Chia thành 2 đến 4 khối nội dung chính, mỗi khối bắt đầu bằng '### [Emoji] [Tên khối]'.\n"
        f"   Bên trong mỗi khối, dùng các gạch đầu dòng ngắn gọn theo mẫu: '- **[Từ khóa/Số liệu]**: [Mô tả súc tích]'.\n"
        f"4. KHỐI KẾT LUẬN: Bắt đầu bằng '### 💡 [Tên phần kết luận]' nêu 1-2 khuyến cáo, bài học hoặc điểm mấu chốt thực tế.\n\n"
        f"Yêu cầu: Viết ngắn gọn, cô đọng, sinh động bằng {target_name}, dùng nhiều emoji trực quan, tuyệt đối không viết văn bản dài dòng nhàm chán."
    )
    return query_gemini_vision(api_key, pil_img, prompt, model=model)

def ai_chat_with_image(pil_img: Image.Image, question: str, chat_history: list = None, target_lang: str = "vi", api_key: str = "", model: str = "gemini-flash-lite-latest") -> str:
    target_name = get_target_lang_display_name(target_lang)
    ocr_text = extract_ocr_text(pil_img)
    text_ctx = f"\n(Văn bản trích xuất từ ảnh: {ocr_text})" if ocr_text else ""
    prompt = f"Trả lời câu hỏi sau đây dựa trên nội dung bức ảnh{text_ctx}: {question}\nTrả lời bằng {target_name} rõ ràng, súc tích và chính xác."
    return query_gemini_vision(api_key, pil_img, prompt, model=model, chat_history=chat_history)

def get_image_original_text(pil_img: Image.Image, api_key: str = "", model: str = "gemini-flash-lite-latest") -> str:
    """
    Trích xuất nguyên văn chính xác 100% nội dung chữ gốc trong ảnh:
    - Nếu Windows OCR hỗ trợ tin cậy: Trích xuất nhanh tại máy (<50ms).
    - Nếu Windows OCR không tối ưu (tiếng Ả Rập, Nga, Albania, CJK đặc thù...): Sử dụng Gemini Vision để trích xuất chuẩn 100% nguyên văn không dịch.
    """
    from ocr_translate import perform_ocr, is_ocr_reliable
    ocr_res = None
    try:
        ocr_res = perform_ocr(pil_img)
        if is_ocr_reliable(ocr_res):
            paras, _ = extract_ocr_paragraphs(pil_img)
            if paras:
                return "\n\n".join(paras)
    except Exception:
        pass

    if not api_key or not api_key.strip():
        try:
            import config as app_config
            api_key = app_config.get_effective_gemini_api_key()
        except Exception:
            pass

    if api_key and api_key.strip():
        prompt = (
            "Hãy đọc và trích xuất NGUYÊN VĂN CHÍNH XÁC 100% tất cả các đoạn văn bản xuất hiện trong hình ảnh này.\n"
            "YÊU CẦU BẮT BUỘC:\n"
            "1. Giữ nguyên 100% ngôn ngữ gốc của ảnh (tuyệt đối KHÔNG dịch sang tiếng khác).\n"
            "2. Giữ nguyên bố cục, tiêu đề, dấu gạch đầu dòng và ngắt dòng (\\n\\n).\n"
            "3. CHỈ trả về đúng toàn bộ nội dung văn bản gốc, KHÔNG thêm lời chào, nhận xét hay giải thích nào."
        )
        res = query_gemini_vision(api_key, pil_img, prompt, model=model)
        if res and not res.startswith("❌") and not res.startswith("⚠️"):
            return res.strip()

    try:
        if ocr_res:
            raw_t = ocr_res.get("text", "").strip()
            if raw_t:
                return raw_t
    except Exception:
        pass

    return "Không tìm thấy nội dung văn bản trong ảnh."

def ai_translate_image_blocks(
    pil_img: Image.Image,
    target_lang: str = "vi",
    api_key: str = "",
    model: str = "gemini-flash-lite-latest"
) -> list[dict]:
    """
    Nhận diện các khối văn bản trên ảnh và dịch từng khối sang target_lang cùng với tọa độ bounding box [x, y, w, h].
    Tạo hiệu ứng đè chữ trực tiếp (In-place Text Replacement) chuẩn xác 100% trên MỌI NGÔN NGỮ
    (Hindi, Nhật, Trung, Hàn, Thái, Ả Rập, Nga, v.v.) mà không che đè lên hình ảnh hay người trong ảnh.
    """
    if not api_key or not api_key.strip():
        try:
            import config as app_config
            api_key = app_config.get_effective_gemini_api_key()
        except Exception:
            pass

    if not api_key:
        return []

    target_name = get_target_lang_display_name(target_lang)
    img_w, img_h = pil_img.size

    prompt = (
        f"Detect all text paragraphs, titles, headlines, and captions in this image and translate them into {target_name}.\n"
        "Return a valid JSON array of objects with the exact schema:\n"
        "[\n"
        "  {\n"
        '    "box_2d": [ymin, xmin, ymax, xmax],\n'
        '    "original": "exact original text",\n'
        f'    "translated": "natural accurate translation in {target_name}"\n'
        "  }\n"
        "]\n"
        "Coordinates ymin, xmin, ymax, xmax must be integers normalized between 0 and 1000.\n"
        "Do NOT include bounding boxes over photos or empty areas without text.\n"
        "Return ONLY the raw JSON array without markdown formatting or code block wrappers."
    )

    try:
        raw_res = query_gemini_vision(api_key, pil_img, prompt, model=model)
        if not raw_res or raw_res.startswith("❌") or raw_res.startswith("⚠️"):
            return []

        clean = raw_res.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*", "", clean)
            clean = re.sub(r"\s*```$", "", clean)

        data = None
        try:
            data = json.loads(clean.strip(), strict=False)
        except Exception:
            trimmed = clean.strip()
            last_brace = trimmed.rfind("}")
            if last_brace != -1:
                try:
                    data = json.loads(trimmed[:last_brace+1] + "\n]", strict=False)
                except Exception:
                    pass
        if not isinstance(data, list):
            return []

        blocks = []
        for item in data:
            box = item.get("box_2d", [])
            trans = (item.get("translated") or "").strip()
            orig = (item.get("original") or "").strip()
            if len(box) == 4 and trans:
                ymin, xmin, ymax, xmax = [float(v) for v in box]
                if ymax <= ymin or xmax <= xmin:
                    continue
                bx = (xmin / 1000.0) * img_w
                by = (ymin / 1000.0) * img_h
                bw = ((xmax - xmin) / 1000.0) * img_w
                bh = ((ymax - ymin) / 1000.0) * img_h
                if bw < 8 or bh < 6:
                    continue
                orig_lines = max(1, orig.count('\n') + 1)
                if orig_lines == 1 and len(orig) > 35 and bh >= 48:
                    orig_lines = max(2, int(round(bh / 32.0)))
                blocks.append({
                    "x": float(bx),
                    "y": float(by),
                    "w": float(bw),
                    "h": float(bh),
                    "original": orig,
                    "translated": trans,
                    "avg_line_h": float(bh / orig_lines),
                    "num_lines": orig_lines
                })
        return blocks
    except Exception as e:
        print("Error in ai_translate_image_blocks:", e)
        return []

