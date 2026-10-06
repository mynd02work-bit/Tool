# Hướng dẫn cấu hình Vision/Multimodal cho Gemini Web2API

## Vấn đề
AI local không thể đọc được ảnh vì thiếu cookie authentication để upload ảnh lên Google Gemini.

## Giải pháp: Cấu hình Cookie

### Bước 1: Lấy Cookie từ Google Gemini

#### Cách 1: Sử dụng Chrome DevTools (Khuyến nghị)

1. Mở trình duyệt Chrome/Edge
2. Truy cập: https://gemini.google.com
3. Đăng nhập vào tài khoản Google của bạn
4. Nhấn `F12` để mở DevTools
5. Chuyển sang tab **Application** (hoặc **Storage**)
6. Trong sidebar bên trái, mở **Cookies** → `https://gemini.google.com`
7. Tìm và copy các cookie quan trọng:
   - `__Secure-1PSID`
   - `__Secure-1PSIDTS`
   - `SAPISID`
   - `HSID`
   - `SSID`
   - `APISID`
   - `SID`

#### Cách 2: Sử dụng Extension "Cookie Editor"

1. Cài extension: [Cookie Editor](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
2. Truy cập https://gemini.google.com và đăng nhập
3. Click vào icon Cookie Editor
4. Click **Export** → **Netscape format**
5. Copy toàn bộ nội dung

### Bước 2: Tạo file cookie.txt

Tạo file `cookie.txt` trong thư mục `m:/ERP/AI/gemini-web2api/` với format:

```
__Secure-1PSID=<giá_trị>; __Secure-1PSIDTS=<giá_trị>; SAPISID=<giá_trị>; HSID=<giá_trị>; SSID=<giá_trị>; APISID=<giá_trị>; SID=<giá_trị>
```

**Ví dụ:**
```
__Secure-1PSID=g.a000xxx; __Secure-1PSIDTS=sidts-xxx; SAPISID=abc123/def456; HSID=xyz789; SSID=abc123; APISID=def456; SID=ghi789
```

**Hoặc format JSON:**
```json
{
  "cookie": "__Secure-1PSID=g.a000xxx; __Secure-1PSIDTS=sidts-xxx; SAPISID=abc123/def456; HSID=xyz789; SSID=abc123; APISID=def456; SID=ghi789",
  "sapisid": "abc123/def456"
}
```

### Bước 3: Cập nhật config.json

Mở file `config.json` và thêm/sửa:

```json
{
  "cookie_file": "cookie.txt",
  "log_requests": true
}
```

**Hoặc dùng đường dẫn tuyệt đối:**
```json
{
  "cookie_file": "m:/ERP/AI/gemini-web2api/cookie.txt",
  "log_requests": true
}
```

### Bước 4: Khởi động lại server

```bash
cd m:/ERP/AI/gemini-web2api
python -m gemini_web2api.server
```

Hoặc nếu đang chạy service, restart service.

## Test Vision Capability

### Test với curl:

```bash
curl -X POST http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-gemini" \
  -d '{
    "model": "gemini-3.5-flash",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "What is in this image?"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
            }
          }
        ]
      }
    ]
  }'
```

### Test với Python:

```python
import requests
import base64

# Đọc ảnh
with open("test_image.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode()

# Gửi request
response = requests.post(
    "http://localhost:8081/v1/chat/completions",
    headers={
        "Authorization": "Bearer sk-gemini",
        "Content-Type": "application/json"
    },
    json={
        "model": "gemini-3.5-flash",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Mô tả ảnh này"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    }
                ]
            }
        ]
    }
)

print(response.json())
```

## Lưu ý quan trọng

### Bảo mật Cookie
- **KHÔNG** commit file `cookie.txt` lên Git (đã có trong `.gitignore`)
- Cookie chứa thông tin đăng nhập, cần bảo mật tuyệt đối
- Định kỳ refresh cookie (thường 30-90 ngày)

### Khi nào cần refresh cookie?
- Khi thấy lỗi: `401 Unauthorized` hoặc `403 Forbidden`
- Khi upload ảnh thất bại với lỗi authentication
- Khi đăng xuất/đăng nhập lại Google account

### Troubleshooting

#### Lỗi: "Image upload failed"
- Kiểm tra cookie còn hợp lệ không
- Kiểm tra file `cookie.txt` có đúng format không
- Kiểm tra `config.json` đã trỏ đúng `cookie_file` chưa

#### Lỗi: "No upload URL in response headers"
- Cookie đã hết hạn, cần lấy lại
- Hoặc thiếu cookie `SAPISID`

#### Lỗi: "Invalid file reference"
- Upload thành công nhưng response không đúng format
- Thử lại với cookie mới

## Alternative: Sử dụng Ollama (Không cần cookie)

Nếu không muốn dùng cookie, có thể chuyển sang Ollama với vision model:

```bash
# Cài Ollama
# Download từ: https://ollama.ai

# Pull vision model
ollama pull llava

# Chạy server
ollama serve

# Cập nhật .env
LOCAL_GEMINI_URL=http://localhost:11434/v1/chat/completions
LOCAL_GEMINI_MODEL=llava
```

## Tài liệu tham khảo
- [Gemini Web2API GitHub](https://github.com/your-repo/gemini-web2api)
- [Google Gemini](https://gemini.google.com)
- [Ollama Vision Models](https://ollama.ai/library)
