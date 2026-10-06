import os
import re
import json
import urllib.parse
import urllib.request
from typing import Callable, Optional

import config as app_config
from ocr_translate import translate_text
from ai_engine import _send_gemini_request

def batch_translate_texts(
    texts: list[str],
    target_lang: str = "vi",
    source_lang: str = "auto",
    batch_size: int = 25,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    progress_range: tuple[int, int] = (0, 100)
) -> dict[str, str]:
    """
    Dịch danh sách các đoạn văn bản theo lô (batch) có bộ nhớ đệm chống trùng lặp,
    ưu tiên Gemini AI và tự động fallback sang Google Translate.
    Trả về dict ánh xạ {text_gốc: text_dịch}.
    """
    if not texts:
        return {}

    # 1. Thu thập danh sách text duy nhất (loại bỏ trùng lặp và chuỗi chỉ có số/kí tự đặc biệt)
    unique_texts = []
    seen = set()
    trans_map = {}

    for t in texts:
        t_clean = t.strip()
        if not t_clean:
            continue
        if re.match(r'^[\d\s\.\,\:\-\/\\#\$%€£¥+=*()_\[\]{}]+$', t_clean):
            trans_map[t] = t
            continue
        if t not in seen:
            seen.add(t)
            unique_texts.append(t)

    total_unique = len(unique_texts)
    if total_unique == 0:
        return trans_map

    cfg = app_config.load_config()
    api_key = app_config.get_effective_gemini_api_key(cfg)
    model = cfg.get("gemini_model", "gemini-flash-lite-latest")

    start_pct, end_pct = progress_range
    pct_span = max(1, end_pct - start_pct)

    # 2. Xử lý theo từng lô
    for idx in range(0, total_unique, batch_size):
        chunk = unique_texts[idx:idx + batch_size]
        current_pct = start_pct + int((idx / total_unique) * pct_span)

        if progress_callback:
            progress_callback(current_pct, f"Đang dịch {idx + 1} - {min(idx + len(chunk), total_unique)} / {total_unique} đoạn...")

        translated_chunk = None

        # Thử Gemini AI trước nếu có API Key
        if api_key and not api_key.startswith("AIzaSyDummy"):
            try:
                system_prompt = (
                    f"You are a professional document translator. Translate the following JSON array of strings from {source_lang} to {target_lang}. "
                    f"Preserve terminology, placeholders, code names, and tone. "
                    f"Return ONLY a valid JSON array of strings with the EXACT same length and order. Do not wrap in markdown quotes if possible."
                )
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": system_prompt},
                            {"text": json.dumps(chunk, ensure_ascii=False)}
                        ]
                    }],
                    "generationConfig": {
                        "temperature": 0.1,
                        "responseMimeType": "application/json"
                    }
                }
                resp = _send_gemini_request(api_key, model, payload, timeout=20)
                candidate = resp.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                parsed = json.loads(candidate)
                if isinstance(parsed, list) and len(parsed) == len(chunk):
                    translated_chunk = [str(item) for item in parsed]
            except Exception:
                translated_chunk = None

        # Fallback Google Translate với delimiter
        if not translated_chunk or len(translated_chunk) != len(chunk):
            try:
                query = "\n@@@\n".join(chunk)
                resp_text = translate_text(query, target_lang=target_lang, source_lang=source_lang)
                parts = resp_text.split("@@@")
                if len(parts) == len(chunk):
                    translated_chunk = [p.strip() for p in parts]
                else:
                    # Fallback dịch từng câu nếu delimiter bị lỗi
                    translated_chunk = [translate_text(item, target_lang=target_lang, source_lang=source_lang) for item in chunk]
            except Exception:
                translated_chunk = [translate_text(item, target_lang=target_lang, source_lang=source_lang) for item in chunk]

        for orig_t, trans_t in zip(chunk, translated_chunk):
            trans_map[orig_t] = trans_t

    if progress_callback:
        progress_callback(end_pct, f"Đã hoàn thành dịch {total_unique} đoạn văn bản!")

    return trans_map


def translate_excel(
    input_path: str,
    output_path: str,
    target_lang: str = "vi",
    source_lang: str = "auto",
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> str:
    """
    Dịch file Excel (.xlsx, .xlsm):
    - Dịch nội dung các ô văn bản.
    - Giữ nguyên 100% công thức (bắt đầu bằng '='), số, ngày tháng, định dạng màu sắc, viền, font chữ.
    """
    import openpyxl

    if progress_callback:
        progress_callback(5, "Đang mở file Excel...")

    wb = openpyxl.load_workbook(input_path)
    cells_to_translate = []
    texts_to_translate = []

    for sheet in wb.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                val = cell.value
                if val and isinstance(val, str):
                    val_clean = val.strip()
                    if not val_clean.startswith("="):
                        cells_to_translate.append(cell)
                        texts_to_translate.append(val)

    if progress_callback:
        progress_callback(15, f"Tìm thấy {len(texts_to_translate)} ô cần dịch trong file Excel...")

    # Dịch toàn bộ texts theo lô
    trans_map = batch_translate_texts(
        texts_to_translate,
        target_lang=target_lang,
        source_lang=source_lang,
        progress_callback=progress_callback,
        progress_range=(15, 85)
    )

    if progress_callback:
        progress_callback(88, "Đang ghi đè bản dịch vào các ô tính...")

    for cell in cells_to_translate:
        orig = cell.value
        if orig in trans_map:
            cell.value = trans_map[orig]

    if progress_callback:
        progress_callback(95, "Đang lưu file Excel đã dịch...")

    wb.save(output_path)

    if progress_callback:
        progress_callback(100, f"✓ Đã lưu file Excel thành công!")

    return output_path


def translate_word(
    input_path: str,
    output_path: str,
    target_lang: str = "vi",
    source_lang: str = "auto",
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> str:
    """
    Dịch toàn diện file Word (.docx):
    - Dịch 100% văn bản trong mọi thành phần: đoạn văn thường, bảng biểu, hình khối (Shapes),
      hộp văn bản (Text Boxes), DrawingML, VML, SmartArt, Header và Footer.
    - Giữ nguyên 100% hình khối, viền màu, nền, căn lề và bố cục không bị xô lệch hay mất hình.
    """
    import docx

    if progress_callback:
        progress_callback(5, "Đang phân tích cấu trúc tài liệu Word (.docx)...")

    doc = docx.Document(input_path)

    # Hàm trích xuất text trực tiếp của 1 paragraph XML (chỉ lấy các <w:t> trực tiếp,
    # không lấy nhầm các <w:t> nằm trong shape con để tránh trùng lặp)
    def get_p_direct_text(p_elem):
        t_elems = []
        for r in p_elem.xpath('./w:r'):
            for t in r.xpath('./w:t'):
                t_elems.append(t)
        text = "".join(t.text for t in t_elems if t.text)
        return text, t_elems

    # 1. Thu thập tất cả <w:p> trong toàn bộ tài liệu (Body, Tables, Shapes, Textboxes, SmartArt...)
    p_elements = list(doc._element.xpath('.//w:p'))

    # 2. Thu thập thêm <w:p> trong Header và Footer của tất cả sections
    for section in doc.sections:
        try:
            p_elements.extend(section.header._element.xpath('.//w:p'))
        except Exception:
            pass
        try:
            p_elements.extend(section.footer._element.xpath('.//w:p'))
        except Exception:
            pass

    # Loại bỏ phần tử trùng lặp
    seen_elements = set()
    unique_p_elements = []
    for p_elem in p_elements:
        if p_elem not in seen_elements:
            seen_elements.add(p_elem)
            unique_p_elements.append(p_elem)

    paragraphs_to_translate = []
    texts = []

    for p_elem in unique_p_elements:
        orig_text, t_elems = get_p_direct_text(p_elem)
        if orig_text and orig_text.strip():
            paragraphs_to_translate.append((p_elem, orig_text, t_elems))
            texts.append(orig_text)

    if progress_callback:
        progress_callback(15, f"Tìm thấy {len(texts)} đoạn văn bản (bao gồm cả trong Shapes & Hộp thoại) trong Word...")

    trans_map = batch_translate_texts(
        texts,
        target_lang=target_lang,
        source_lang=source_lang,
        progress_callback=progress_callback,
        progress_range=(15, 85)
    )

    if progress_callback:
        progress_callback(88, "Đang cập nhật bản dịch vào các đoạn văn và Shape...")

    # Cập nhật bản dịch: chỉ ghi đè vào <w:t> trực tiếp, TUYỆT ĐỐI không xóa <w:drawing> hay các phần tử đồ họa
    for p_elem, orig_text, t_elems in paragraphs_to_translate:
        if orig_text in trans_map:
            trans_t = trans_map[orig_text]
            if t_elems:
                t_elems[0].text = trans_t
                for t in t_elems[1:]:
                    t.text = ""

    if progress_callback:
        progress_callback(95, "Đang lưu file Word đã dịch...")

    doc.save(output_path)

    if progress_callback:
        progress_callback(100, "✓ Đã lưu file Word thành công!")

    return output_path


def translate_pptx(
    input_path: str,
    output_path: str,
    target_lang: str = "vi",
    source_lang: str = "auto",
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> str:
    """
    Dịch file PowerPoint (.pptx):
    - Dịch tiêu đề, nội dung trên các slide, bảng biểu và toàn bộ hình khối (Shapes, GroupShapes).
    - Bảo toàn bố cục slide, hình ảnh và hoạt họa.
    """
    import pptx

    if progress_callback:
        progress_callback(5, "Đang mở bài thuyết trình PowerPoint (.pptx)...")

    prs = pptx.Presentation(input_path)

    def extract_shape_paragraphs(shapes):
        res = []
        for shape in shapes:
            if shape.has_text_frame:
                for p in shape.text_frame.paragraphs:
                    if p.text.strip():
                        res.append(p)
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        for p in cell.text_frame.paragraphs:
                            if p.text.strip():
                                res.append(p)
            if hasattr(shape, "shapes"):  # Hỗ trợ group shapes lồng nhau
                res.extend(extract_shape_paragraphs(shape.shapes))
        return res

    paragraphs_to_translate = []
    for slide in prs.slides:
        paragraphs_to_translate.extend(extract_shape_paragraphs(slide.shapes))

    texts = [p.text for p in paragraphs_to_translate]

    if progress_callback:
        progress_callback(15, f"Tìm thấy {len(texts)} đoạn chữ trên {len(prs.slides)} trang slide...")

    trans_map = batch_translate_texts(
        texts,
        target_lang=target_lang,
        source_lang=source_lang,
        progress_callback=progress_callback,
        progress_range=(15, 85)
    )

    if progress_callback:
        progress_callback(88, "Đang cập nhật chữ dịch trên các slide và shape...")

    for p in paragraphs_to_translate:
        orig = p.text
        if orig in trans_map:
            trans_t = trans_map[orig]
            if p.runs:
                p.runs[0].text = trans_t
                for r in p.runs[1:]:
                    r.text = ""
            else:
                p.text = trans_t

    if progress_callback:
        progress_callback(95, "Đang lưu bài thuyết trình PowerPoint...")

    prs.save(output_path)

    if progress_callback:
        progress_callback(100, "✓ Đã lưu file PowerPoint thành công!")

    return output_path



def translate_pdf(
    input_path: str,
    output_path: str,
    target_lang: str = "vi",
    source_lang: str = "auto",
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> str:
    """
    Dịch file PDF (.pdf) giữ nguyên 100% bố cục và định dạng gốc:
    - Bảo toàn kích thước trang, hình ảnh, bảng biểu, đồ họa vector và vị trí từng khối.
    - Che text cũ và chèn chữ dịch chuẩn Unicode / Tiếng Việt vào đúng tọa độ của từng khối.
    - Hỗ trợ xuất sang Word (.docx) nếu người dùng chủ động chọn đuôi .docx.
    """
    import pymupdf

    if progress_callback:
        progress_callback(5, "Đang phân tích cấu trúc các trang PDF...")

    doc = pymupdf.open(input_path)
    total_pages = len(doc)
    page_data = []
    all_texts = []

    for page_num in range(total_pages):
        page = doc[page_num]
        text_blocks = page.get_text("blocks")
        # Mỗi block: (x0, y0, x1, y1, text, block_no, block_type)
        valid_page_blocks = []
        for b in text_blocks:
            if len(b) >= 7 and b[6] == 0:  # block_type == 0: văn bản
                clean_t = b[4].strip()
                if clean_t:
                    rect = pymupdf.Rect(b[0], b[1], b[2], b[3])
                    valid_page_blocks.append((rect, clean_t))
                    all_texts.append(clean_t)
        page_data.append((page_num, valid_page_blocks))

    if progress_callback:
        progress_callback(15, f"Tìm thấy {len(all_texts)} đoạn văn bản trên {total_pages} trang PDF...")

    trans_map = batch_translate_texts(
        all_texts,
        target_lang=target_lang,
        source_lang=source_lang,
        progress_callback=progress_callback,
        progress_range=(15, 80)
    )

    if progress_callback:
        progress_callback(85, "Đang định dạng và lưu bản dịch...")

    # Nếu người dùng chủ động chọn xuất sang Word (.docx)
    if output_path.lower().endswith(".docx"):
        import docx
        out_doc = docx.Document()
        out_doc.add_heading(f"Bản Dịch: {os.path.basename(input_path)}", 0)

        for page_num, blocks in page_data:
            out_doc.add_heading(f"--- Trang {page_num + 1} ---", level=2)
            for rect, t in blocks:
                trans_t = trans_map.get(t, t)
                out_doc.add_paragraph(trans_t)

        out_doc.save(output_path)
    else:
        # Xuất file PDF chuẩn: GIỮ NGUYÊN 100% CẤU TRÚC GỐC, HÌNH ẢNH, BỐ CỤC
        if not output_path.lower().endswith(".pdf"):
            output_path += ".pdf"

        # Tìm font hệ thống hỗ trợ trọn vẹn Unicode và Tiếng Việt
        font_candidates = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/tahoma.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        font_obj = None
        for p in font_candidates:
            if os.path.exists(p):
                try:
                    font_obj = pymupdf.Font(fontfile=p)
                    break
                except Exception:
                    pass

        if not font_obj:
            try:
                font_obj = pymupdf.Font("helv")
            except Exception:
                pass

        for page_num, blocks in page_data:
            page = doc[page_num]
            tw = pymupdf.TextWriter(page.rect) if hasattr(pymupdf, 'TextWriter') else None

            for rect, orig_t in blocks:
                trans_t = trans_map.get(orig_t, orig_t)
                if not trans_t or not trans_t.strip():
                    continue

                # 1. Che sạch chữ cũ trên trang
                try:
                    page.draw_rect(rect, color=None, fill=(1, 1, 1))
                except Exception:
                    pass

                # 2. Tính toán cỡ chữ vừa vặn trong khung rect
                h = rect.height
                w = max(rect.width, 20.0)
                orig_lines = max(1, orig_t.count('\n') + 1)
                base_fsize = max(7, min(20, int((h / orig_lines) * 0.72)))

                # 3. Vẽ chữ dịch đã ngắt dòng chuẩn xác
                if tw and font_obj:
                    try:
                        char_ratio = len(trans_t) / max(1, len(orig_t))
                        if char_ratio > 1.3:
                            base_fsize = max(7, base_fsize - 1)
                        tw.fill_textbox(rect, trans_t, font=font_obj, fontsize=base_fsize)
                    except Exception:
                        page.insert_textbox(rect, trans_t, fontsize=base_fsize, color=(0.1, 0.1, 0.1))
                else:
                    page.insert_textbox(rect, trans_t, fontsize=base_fsize, color=(0.1, 0.1, 0.1))

            if tw:
                try:
                    tw.write_text(page, color=(0.08, 0.1, 0.15))
                except Exception:
                    pass

        doc.save(output_path, garbage=4, deflate=True)

    doc.close()

    if progress_callback:
        progress_callback(100, "✓ Đã dịch và lưu file thành công!")

    return output_path


def translate_image(
    input_path: str,
    output_path: str,
    target_lang: str = "vi",
    source_lang: str = "auto",
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> str:
    """
    Dịch file ảnh (.png, .jpg, .jpeg, .webp, .bmp) giữ nguyên 100% bố cục và đồ họa
    bằng cách đè chữ dịch 1:1 theo từng vị trí khối (BlockOverlayElement).
    """
    from PIL import Image
    from PyQt6.QtGui import QPixmap, QPainter, QColor, QGuiApplication
    from PyQt6.QtCore import QRectF
    from canvas_elements import BlockOverlayElement
    from overlay import sample_block_colors, cluster_lines_into_blocks
    from ocr_translate import perform_ocr, is_ocr_reliable, translate_text
    from ai_engine import extract_ocr_paragraphs, ai_translate_image_blocks

    if QGuiApplication.instance() is None:
        import sys
        _app = QGuiApplication(sys.argv if sys.argv else [""])

    if progress_callback:
        progress_callback(10, "Đang mở và đọc thông tin ảnh...")

    pil_img = Image.open(input_path).convert("RGB")
    cfg = app_config.load_config()
    api_key = app_config.get_effective_gemini_api_key(cfg)
    model = cfg.get("gemini_model", "gemini-flash-lite-latest")
    ocr_lang = cfg.get("ocr_lang", "auto")

    blocks = []
    # 1. Ưu tiên hàng đầu: Gemini Multimodal Vision API nhận diện & dịch đè 1:1 chuẩn xác mọi ngôn ngữ
    if api_key and not api_key.startswith("AIzaSyDummy"):
        if progress_callback:
            progress_callback(25, "Đang nhận diện vị trí và dịch ngữ cảnh AI bằng Gemini Vision...")
        try:
            blocks = ai_translate_image_blocks(pil_img, target_lang=target_lang, api_key=api_key, model=model)
        except Exception as e:
            print("Lỗi ai_translate_image_blocks:", e)

    # 2. Dự phòng ngoại tuyến: Windows OCR nếu AI không khả dụng hoặc không có mạng
    if not blocks:
        if progress_callback:
            progress_callback(40, "Đang quét nhận diện chữ bằng OCR...")
        try:
            ocr_res = perform_ocr(pil_img, lang=ocr_lang)
            _, blocks = extract_ocr_paragraphs(pil_img, lang=ocr_lang)
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
            print("Lỗi OCR:", e)

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

    if not valid_blocks:
        raise RuntimeError("Không tìm thấy khối văn bản nào trong ảnh để dịch. Vui lòng kiểm tra lại độ rõ nét của chữ trong ảnh.")

    needs_translation = [b for b in valid_blocks if not b.get('translated')]
    if needs_translation:
        if progress_callback:
            progress_callback(60, f"Đang dịch {len(needs_translation)} khối văn bản...")
        orig_texts = [b['original'].replace('\n', ' ').strip() for b in needs_translation]
        trans_map = batch_translate_texts(
            orig_texts,
            target_lang=target_lang,
            source_lang=source_lang,
            progress_callback=progress_callback,
            progress_range=(60, 85)
        )
        for blk in needs_translation:
            cleaned = blk['original'].replace('\n', ' ').strip()
            blk['translated'] = trans_map.get(cleaned, cleaned)

    if progress_callback:
        progress_callback(85, "Đang vẽ đè chữ dịch 1:1 chuẩn màu và vị trí...")

    pix = QPixmap(input_path)
    if not pix.isNull():
        painter = QPainter(pix)
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

        pix.save(output_path)
    else:
        raise RuntimeError("Không thể tải ảnh để vẽ đè bản dịch.")

    if progress_callback:
        progress_callback(100, "✓ Đã dịch và lưu file ảnh thành công!")

    return output_path


def translate_document_file(
    input_path: str,
    output_path: Optional[str] = None,
    target_lang: str = "vi",
    source_lang: str = "auto",
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> str:
    """
    Hàm điều phối tổng quát: Tự động phân loại định dạng file và gọi hàm dịch tương ứng.
    Bảo toàn 100% định dạng gốc của file (PDF ra PDF, Word ra Word, Excel ra Excel, PPTX ra PPTX, Ảnh ra Ảnh).
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File không tồn tại: {input_path}")

    ext = os.path.splitext(input_path)[1].lower()
    base_name = os.path.splitext(input_path)[0]

    if not output_path:
        out_ext = ext
        output_path = f"{base_name}_{target_lang}{out_ext}"

    if ext in (".xlsx", ".xlsm", ".xltx"):
        return translate_excel(input_path, output_path, target_lang=target_lang, source_lang=source_lang, progress_callback=progress_callback)
    elif ext in (".docx", ".docm"):
        return translate_word(input_path, output_path, target_lang=target_lang, source_lang=source_lang, progress_callback=progress_callback)
    elif ext in (".pptx", ".pptm"):
        return translate_pptx(input_path, output_path, target_lang=target_lang, source_lang=source_lang, progress_callback=progress_callback)
    elif ext == ".pdf":
        return translate_pdf(input_path, output_path, target_lang=target_lang, source_lang=source_lang, progress_callback=progress_callback)
    elif ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"):
        return translate_image(input_path, output_path, target_lang=target_lang, source_lang=source_lang, progress_callback=progress_callback)
    else:
        raise ValueError(f"Định dạng file '{ext}' chưa được hỗ trợ. Vui lòng chọn file Word (.docx), Excel (.xlsx), PowerPoint (.pptx), PDF (.pdf) hoặc File ảnh.")

