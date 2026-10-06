# Hướng dẫn Nhanh: Khắc phục AI Local không đọc được ảnh

## Vấn đề
AI local (gemini-web2api) của bạn không thể đọc được ảnh vì **thiếu cookie authentication** để upload ảnh lên Google Gemini.

## Giải pháp (3 bước đơn giản)

### Bước 1: Lấy Cookie từ Google Gemini

#### Cách 1: Tự động (Khuyến nghị)
```bash
cd m:/ERP/AI/gemini-web2api
python extract_cookie.py
```

Script sẽ tự động tìm và extract cookie từ Chrome/Edge.

#### Cách 2: Thủ công (Nếu cách 1 không hoạt động)

1. Mở Chrome/Edge
2. Truy cập: https://gemini.google.com
3. Đăng nhập tài khoản Google
4. Nhấn **F12** → Tab **Application** → **Cookies** → `https://gemini.google.com`
5. Copy các cookie sau:
   - `__Secure-1PSID`
   - `__Secure-1PSIDTS`
   - `SAPISID`
   - `HSID`, `SSID`, `APISID`, `SID`

6. Tạo file `cookie.txt` trong `m:/ERP/AI/gemini-web2api/`:
```
__Secure-1PSID=xxx; __Secure-1PSIDTS=xxx; SAPISID=xxx; HSID=xxx; SSID=xxx; APISID=xxx; SID=xxx
```

### Bước 2: Cấu hình config.json

Mở file `m:/ERP/AI/gemini-web2api/config.json` và thêm dòng:

```json
{
  "cookie_file": "cookie.txt",
  "log_requests": true
}
```

**Lưu ý**: File `config.json` có thể đã tồn tại, chỉ cần thêm/sửa dòng `"cookie_file"`.

### Bước 3: Khởi động lại Server

```bash
# Dừng server hiện tại (Ctrl+C)

# Khởi động lại
cd m:/ERP/AI/gemini-web2api
python -m gemini_web2api.server
```

Hoặc nếu đang chạy dưới dạng service, restart service.

## Test Vision

```bash
# Test với ảnh bất kỳ
python test_vision.py test.jpg

# Test với prompt tùy chỉnh
python test_vision.py meter.jpg "Đọc số trên đồng hồ này"
```

## Kết quả mong đợi

✅ **Trước khi cấu hình cookie:**
```
❌ Error: Image upload failed
```

✅ **Sau khi cấu hình cookie:**
```
✅ Success!
📋 Response:
Trong ảnh này có...
```

## Troubleshooting

### Lỗi: "Image upload failed"
- Cookie đã hết hạn → Lấy lại cookie mới
- File `cookie.txt` sai format → Kiểm tra lại format
- Chưa cấu hình `config.json` → Thêm `"cookie_file": "cookie.txt"`

### Lỗi: "Cannot connect to server"
- Server chưa chạy → Khởi động server: `python -m gemini_web2api.server`
- Port bị chiếm → Đổi port trong `config.json`

### Lỗi: "401 Unauthorized"
- Cookie đã hết hạn (thường 30-90 ngày)
- Cần lấy cookie mới từ gemini.google.com

## Lưu ý Bảo mật

⚠️ **QUAN TRỌNG:**
- File `cookie.txt` chứa thông tin đăng nhập Google
- **KHÔNG** commit lên Git (đã có trong `.gitignore`)
- **KHÔNG** chia sẻ cookie với người khác
- Định kỳ refresh cookie (30-90 ngày)

## Alternative: Dùng Ollama (Không cần cookie)

Nếu không muốn dùng cookie, có thể chuyển sang Ollama:

```bash
# 1. Cài Ollama
# Download: https://ollama.ai

# 2. Pull vision model
ollama pull llava

# 3. Cập nhật .env
LOCAL_GEMINI_URL=http://localhost:11434/v1/chat/completions
LOCAL_GEMINI_MODEL=llava
```

## Tài liệu chi tiết

- [SETUP_VISION.md](SETUP_VISION.md) - Hướng dẫn chi tiết đầy đủ
- [README.md](README.md) - Tài liệu chính của gemini-web2api

## Hỗ trợ

Nếu vẫn gặp vấn đề, kiểm tra:
1. Server logs: Xem terminal đang chạy server
2. Cookie format: Đảm bảo đúng format `name=value; name2=value2`
3. Config path: Đảm bảo `cookie_file` trỏ đúng đường dẫn

---

**Tóm tắt**: Lấy cookie từ gemini.google.com → Lưu vào `cookie.txt` → Cấu hình `config.json` → Restart server → Test với `test_vision.py`
