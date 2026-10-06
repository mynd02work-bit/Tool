import urllib.parse
import urllib.request
import json
import winocr
from PIL import Image

def _run_single_ocr(ocr_img, lang, scale, w, h):
    try:
        res = winocr.recognize_pil_sync(ocr_img, lang)
        extracted_lines = []
        for line in res.get("lines", []):
            line_text = line.get("text", "").strip()
            if not line_text:
                continue
            
            words = line.get("words", [])
            if words:
                min_x = min(w_item["bounding_rect"]["x"] for w_item in words) / scale
                min_y = min(w_item["bounding_rect"]["y"] for w_item in words) / scale
                max_x = max(w_item["bounding_rect"]["x"] + w_item["bounding_rect"]["width"] for w_item in words) / scale
                max_y = max(w_item["bounding_rect"]["y"] + w_item["bounding_rect"]["height"] for w_item in words) / scale
                extracted_lines.append({
                    "text": line_text,
                    "x": min_x,
                    "y": min_y,
                    "w": max_x - min_x,
                    "h": max_y - min_y
                })
            else:
                extracted_lines.append({
                    "text": line_text,
                    "x": 0.0,
                    "y": 0.0,
                    "w": float(w),
                    "h": 30.0
                })
                
        full_text = res.get("text", "").strip()
        return {
            "success": True,
            "text": full_text,
            "lines": extracted_lines,
            "lang": lang
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "text": "",
            "lines": [],
            "lang": lang
        }

def perform_ocr(pil_image: Image.Image, lang: str = "auto"):
    """
    Thực hiện OCR thông minh trên ảnh PIL sử dụng Windows Media OCR (winocr).
    Tự động nâng độ phân giải 1.5x với ảnh vừa và nhỏ.
    Tự động dò tìm ngôn ngữ tối ưu từ các gói ngôn ngữ đã cài trên Windows (en-US, zh-Hans-CN, ja-JP, vi-VN, v.v.)
    để nhận diện chuẩn xác cả tiếng Anh, tiếng Trung, tiếng Nhật và nhiều ngôn ngữ khác.
    """
    try:
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")
            
        w, h = pil_image.size
        scale = 1.5 if (w < 1600 and h < 1200) else 1.0
        if scale > 1.0:
            ocr_img = pil_image.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
        else:
            ocr_img = pil_image

        # Lấy danh sách ngôn ngữ OCR khả dụng trên hệ thống Windows
        available = []
        try:
            available = [l.language_tag for l in winocr.OcrEngine.available_recognizer_languages]
        except Exception:
            available = []

        if not available:
            available = ["en-US"]

        # Thứ tự ưu tiên kiểm tra ngôn ngữ:
        if lang and lang != "auto" and lang in available:
            langs_to_try = [lang]
        else:
            langs_to_try = []
            for preferred in ["en-US", "zh-Hans-CN", "zh-Hant-TW", "ja-JP", "ko-KR", "vi-VN"]:
                if preferred in available and preferred not in langs_to_try:
                    langs_to_try.append(preferred)
            for l in available:
                if l not in langs_to_try:
                    langs_to_try.append(l)

        best_result = None
        best_score = -1

        import re
        for cur_lang in langs_to_try:
            res = _run_single_ocr(ocr_img, cur_lang, scale, w, h)
            lines = res.get("lines", [])
            if not lines:
                continue

            full_txt = res.get("text", "")
            # Đếm số lượng ký tự CJK (chữ Hán, Nhật, Hàn)
            cjk_chars = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff\uac00-\ud7af]', full_txt)
            cjk_count = len(cjk_chars)
            unique_cjk = len(set(cjk_chars))
            char_count = sum(len(l.get("text", "").strip()) for l in lines)
            is_cjk_lang = any(k in cur_lang.lower() for k in ("zh", "ja", "ko", "chinese", "japanese", "korean"))
            cjk_ratio = cjk_count / max(1, len(full_txt))
            # Chỉ thưởng điểm CJK khi có đủ từ vựng đa dạng (tránh ký tự lặp '二' hallucinate trên tiếng Hindi/đường kẻ)
            cjk_bonus = (cjk_count * 10) if (is_cjk_lang and unique_cjk >= 4 and cjk_count >= 6 and cjk_ratio >= 0.50) else 0

            # Điểm từ vựng chữ cái Latin chuẩn cho en-US
            latin_words = len(re.findall(r'[a-zA-Z]{2,}', full_txt))
            latin_bonus = (latin_words * 3) if ("en" in cur_lang.lower()) else 0

            # Phạt nặng nếu văn bản chứa các ký tự thuộc hệ chữ không được Windows OCR hỗ trợ
            unsupported = re.findall(r'[\u0900-\u0DFF\u0E00-\u0E7F\u0400-\u04FF\u0590-\u05FF\u0600-\u06FF\u1000-\u109F\u1780-\u17FF]', full_txt)
            penalty = 120 if unsupported else 0

            score = len(lines) * 20 + char_count + cjk_bonus + latin_bonus - penalty

            if score > best_score:
                best_score = score
                best_result = res

        # Tự động chuẩn hóa xóa các dấu cách thừa giữa các chữ Hán/Nhật/Hàn do winocr tự sinh
        if best_result and best_result.get("lines"):
            chosen_lang = best_result.get("lang", "")
            if any(k in chosen_lang.lower() for k in ("zh", "ja", "ko")):
                clean_lines = []
                for l in best_result["lines"]:
                    txt = l.get("text", "")
                    clean_t = re.sub(r'(?<=[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff\uac00-\ud7af])\s+(?=[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff\uac00-\ud7af])', '', txt)
                    l["text"] = clean_t.strip()
                    clean_lines.append(l)
                best_result["lines"] = clean_lines
                raw_full = best_result.get("text", "")
                best_result["text"] = re.sub(r'(?<=[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff\uac00-\ud7af])\s+(?=[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff\uac00-\ud7af])', '', raw_full).strip()

        return best_result or {"success": False, "error": "Không nhận dạng được văn bản", "text": "", "lines": []}
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "text": "",
            "lines": []
        }

def is_ocr_reliable(ocr_res: dict) -> bool:
    """
    Kiểm tra xem kết quả Windows OCR có đáng tin cậy hay không.
    Nếu hình ảnh là ngôn ngữ chưa cài gói OCR trên Windows (như tiếng Hindi, Ả Rập, tiếng Nga, tiếng Nhật...)
    khiến WinOCR đoán mò ra các ký tự Latin lộn xộn hoặc hallucinate tiếng Trung, hàm sẽ trả về False
    để nhường quyền xử lý cho Gemini Multimodal Vision API (đọc trực tiếp từ ảnh chuẩn 100%).
    """
    if not ocr_res or not ocr_res.get("success"):
        return False
    lines = ocr_res.get("lines", [])
    if not lines:
        return False
    full_text = ocr_res.get("text", "")
    if len(full_text.strip()) < 3:
        return False

    # Phải có ít nhất 12 ký tự nếu chỉ tìm thấy 1 dòng lẻ loi
    if len(full_text.strip()) < 12 and len(lines) <= 1:
        return False

    import re
    # 1. Phát hiện các ký tự thuộc hệ chữ không được Windows OCR hỗ trợ
    # (Devanagari/Hindi, Bengali, Tamil, Thai, Ả Rập, Do Thái, Cyrillic, Myanmar, Khmer...)
    unsupported_chars = re.findall(r'[\u0900-\u0DFF\u0E00-\u0E7F\u0400-\u04FF\u0590-\u05FF\u0600-\u06FF\u1000-\u109F\u1780-\u17FF]', full_text)
    if unsupported_chars:
        return False

    # 2. Phát hiện các ký tự radical/nét bộ thủ Kangxi mà WinOCR thường ghép bừa từ ảnh không phải chữ Hán
    radical_chars = re.findall(r'[\u2E80-\u2FDF\u31C0-\u31EF\u4E28\u4E2C\u4E3F\u4E5B\u4E85\u5182\u5315\u5338]', full_text)
    if radical_chars:
        return False

    lang = str(ocr_res.get("lang", ""))

    # 3. Nếu là tiếng Trung, Nhật, Hàn (CJK)
    if any(k in lang.lower() for k in ("zh", "ja", "ko")):
        cjk_chars = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff\uac00-\ud7af]', full_text)
        if len(cjk_chars) < 8:
            return False
        unique_cjk = set(cjk_chars)
        # Phải có ít nhất 5 ký tự khác nhau (tránh lặp '二' hoặc '一' do gạch ngang tiếng Hindi/đường kẻ)
        if len(unique_cjk) < 5:
            return False
        from collections import Counter
        counts = Counter(cjk_chars)
        most_common_ratio = counts.most_common(1)[0][1] / len(cjk_chars)
        if most_common_ratio > 0.35:
            return False
        non_space = [c for c in full_text if not c.isspace()]
        if len(cjk_chars) / max(1, len(non_space)) < 0.50:
            return False
        return len(lines) >= 1

    # 4. Ngôn ngữ dùng chữ cái Latin (English, Tiếng Việt, French, German, Spanish...)
    words = [w for w in re.split(r'\s+', full_text) if len(w) >= 2]
    if not words:
        return len(full_text.strip()) >= 2 and len(lines) >= 1

    # Chấp nhận từ chứa chữ cái (hỗ trợ đầy đủ Unicode tiếng Việt, tiếng Anh và các ngôn ngữ khác)
    clean_words = [w for w in words if any(c.isalpha() for c in w)]
    ratio = len(clean_words) / max(1, len(words))
    if len(clean_words) < 1 or ratio < 0.35:
        return False

    return len(lines) >= 1

def translate_text(text: str, target_lang: str = "vi", source_lang: str = "auto"):
    """
    Dịch văn bản sử dụng Google Translate API miễn phí.
    """
    if not text or not text.strip():
        return ""
    
    try:
        encoded_text = urllib.parse.quote(text.strip())
        url = (
            f"https://translate.googleapis.com/translate_a/single?"
            f"client=gtx&sl={source_lang}&tl={target_lang}&dt=t&q={encoded_text}"
        )
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            translated_segments = []
            if data and isinstance(data[0], list):
                for segment in data[0]:
                    if segment and len(segment) > 0 and segment[0]:
                        translated_segments.append(segment[0])
            return "".join(translated_segments)
    except Exception as e:
        return f"[Lỗi dịch: {e}]"
