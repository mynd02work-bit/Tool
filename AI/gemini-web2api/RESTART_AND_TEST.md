# ✅ Cookie đã sẵn sàng - Restart và Test

## Trạng thái hiện tại

✅ **cookie.txt đã được tạo** với đầy đủ 16 cookies  
✅ **Bao gồm tất cả cookies cần thiết**: SID, HSID, SSID, APISID, SAPISID, __Secure-1PSID  
✅ **config.json đã đúng** với `"cookie_file": "cookie.txt"`

## Bước tiếp theo (BẮT BUỘC)

### 1. Restart Server

**Tìm terminal đang chạy gemini-web2api server và:**

```bash
# Nhấn Ctrl+C để dừng server
# Sau đó khởi động lại:
python -m gemini_web2api.server
```

**Hoặc nếu chạy dưới dạng service:**
```bash
# Restart service
```

### 2. Test Vision

**Trong terminal MỚI (không phải terminal đang chạy server):**

```bash
cd m:/ERP/AI/gemini-web2api

# Test với ảnh đơn giản
python test_vision_simple.py
```

### 3. Kết quả mong đợi

#### ✅ Thành công:
```
======================================================================
  Testing Vision Capability
======================================================================

📤 Sending request to: http://localhost:8081/v1/chat/completions
🖼️  Image: 1x1 red pixel (base64)
📝 Prompt: What color is this image?

📊 Status Code: 200

✅ SUCCESS! Vision is working!

──────────────────────────────────────────────────────────────────────
Response:
──────────────────────────────────────────────────────────────────────
Red (hoặc mô tả về màu đỏ)
──────────────────────────────────────────────────────────────────────
```

#### ❌ Nếu vẫn lỗi:
```
Response: It looks like you forgot to attach or include the image!
```

→ Server chưa được restart, cookies cũ vẫn đang được dùng

## Sau khi thành công

### Test với ảnh thật:

```bash
# Test với ảnh bất kỳ
python test_vision.py path/to/your/image.jpg

# Test với prompt tùy chỉnh
python test_vision.py meter.jpg "Đọc số trên đồng hồ này"
```

### Sử dụng trong code:

```python
import requests
import base64

# Đọc ảnh
with open("image.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode()

# Gọi API
response = requests.post(
    "http://localhost:8081/v1/chat/completions",
    headers={
        "Authorization": "Bearer sk-gemini",
        "Content-Type": "application/json"
    },
    json={
        "model": "gemini-3.5-flash",
        "messages": [{
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
        }],
        "temperature": 0.0,
        "max_tokens": 200
    }
)

result = response.json()
print(result["choices"][0]["message"]["content"])
```

## Troubleshooting

### Vẫn không nhận được ảnh sau khi restart?

1. **Kiểm tra server đã load cookie chưa:**
   - Xem logs khi server khởi động
   - Tìm dòng: "Cookie loaded" hoặc tương tự

2. **Kiểm tra cookie.txt:**
   ```bash
   python check_cookie_status.py
   ```
   
   Phải thấy:
   ```
   ✅ All required cookies present!
   ```

3. **Thử test basic API trước:**
   ```bash
   python test_basic.py
   ```
   
   Nếu basic API không hoạt động → Vấn đề ở server/config
   Nếu basic API OK nhưng vision không → Vấn đề ở cookies

4. **Cookies có thể đã hết hạn:**
   - Lấy cookies mới từ gemini.google.com
   - Chạy lại `create_cookie_from_screenshot.py`
   - Restart server

## Tóm tắt

1. ✅ Cookie đã có đầy đủ (16 cookies)
2. 🔄 **RESTART SERVER** (quan trọng!)
3. ✅ Test với `python test_vision_simple.py`
4. 🎉 Nếu thành công → Vision đã hoạt động!

---

**Lưu ý**: Server PHẢI được restart để load cookies mới. Nếu không restart, server vẫn dùng cookies cũ (hoặc không có cookies).
