# Khắc phục: Thiếu Cookies SID, HSID, APISID

## Vấn đề hiện tại

✅ **API hoạt động** - Server đang chạy tốt  
✅ **Text-only requests hoạt động** - Anonymous mode OK  
❌ **Vision KHÔNG hoạt động** - Thiếu cookies để upload ảnh

## Nguyên nhân

Cookies bạn export **thiếu 3 cookies quan trọng**:
- `SID` - Session ID
- `HSID` - Host Session ID  
- `APISID` - API Session ID

Những cookies này cần thiết để:
1. Authenticate với Google Gemini
2. Upload ảnh lên Google servers
3. Sử dụng multimodal/vision features

## Giải pháp: Export lại cookies đầy đủ

### Cách 1: Sử dụng Extension "EditThisCookie" (Khuyến nghị)

1. **Cài extension**:
   - Chrome: https://chrome.google.com/webstore/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg
   - Edge: Tìm "EditThisCookie" trong Edge Add-ons

2. **Export cookies**:
   - Mở https://gemini.google.com và đăng nhập
   - Click icon EditThisCookie
   - Click biểu tượng "Export" (mũi tên xuống)
   - Copy toàn bộ JSON

3. **Tạo file mới**:
   ```bash
   # Paste JSON vào file: cookies_full.json
   # Sau đó chạy:
   python generate_cookie_from_json.py
   ```

### Cách 2: Export thủ công từ DevTools

1. **Mở DevTools**:
   - Truy cập: https://gemini.google.com
   - Nhấn F12 → Tab **Application** → **Cookies** → `https://gemini.google.com`

2. **Copy các cookies sau** (QUAN TRỌNG - phải có đủ):

   | Cookie Name | Domain | Bắt buộc |
   |-------------|--------|----------|
   | `SID` | .google.com | ✅ **CẦN** |
   | `HSID` | .google.com | ✅ **CẦN** |
   | `SSID` | .google.com | ✅ **CẦN** |
   | `APISID` | .google.com | ✅ **CẦN** |
   | `SAPISID` | .google.com | ✅ **CẦN** |
   | `__Secure-1PSID` | .google.com | ✅ **CẦN** |
   | `__Secure-1PSIDTS` | .google.com | Nên có |
   | `__Secure-3PSID` | .google.com | Nên có |

3. **Tạo cookie.txt** với format:
   ```
   SID=xxx; HSID=xxx; SSID=xxx; APISID=xxx; SAPISID=xxx; __Secure-1PSID=xxx; __Secure-1PSIDTS=xxx
   ```

### Cách 3: Sử dụng Console để extract

1. Mở https://gemini.google.com
2. Nhấn F12 → Tab **Console**
3. Paste và chạy script sau:

```javascript
// Extract all cookies
const cookies = document.cookie.split('; ');
const cookieObj = {};
cookies.forEach(c => {
    const [name, value] = c.split('=');
    cookieObj[name] = value;
});

// Check for required cookies
const required = ['SID', 'HSID', 'SSID', 'APISID', 'SAPISID', '__Secure-1PSID'];
const found = [];
const missing = [];

required.forEach(name => {
    if (cookieObj[name]) {
        found.push(name);
    } else {
        missing.push(name);
    }
});

console.log('✅ Found cookies:', found);
console.log('❌ Missing cookies:', missing);

// Generate cookie string
const cookieString = Object.entries(cookieObj)
    .map(([k, v]) => `${k}=${v}`)
    .join('; ');

console.log('\n📋 Cookie string (copy this):');
console.log(cookieString);
```

4. Copy cookie string từ console
5. Lưu vào `cookie.txt`

## Kiểm tra cookies hiện tại

```bash
# Kiểm tra cookies đã export
python check_cookie_status.py
```

Nếu thấy:
```
❌ Missing cookies:
   ✗ SID
   ✗ HSID
   ✗ APISID
```

→ Cần export lại theo hướng dẫn trên

## Sau khi có đủ cookies

```bash
# 1. Đảm bảo cookie.txt có đủ cookies
python check_cookie_status.py

# 2. Restart server
# Ctrl+C để dừng server hiện tại
python -m gemini_web2api.server

# 3. Test vision
python test_vision_simple.py
```

## Kết quả mong đợi

### ❌ Trước (thiếu cookies):
```
Response: It looks like you forgot to attach or include the image!
```

### ✅ Sau (đủ cookies):
```
Response: Red (hoặc mô tả màu đỏ)
```

## Troubleshooting

### Vẫn không tìm thấy SID, HSID, APISID?

**Nguyên nhân**: Trình duyệt có thể đang ở chế độ incognito hoặc cookies bị block.

**Giải pháp**:
1. Đảm bảo KHÔNG dùng incognito mode
2. Kiểm tra cookie settings: chrome://settings/cookies
3. Cho phép cookies cho google.com
4. Đăng xuất và đăng nhập lại gemini.google.com
5. Export lại cookies

### Cookies vẫn không hoạt động?

**Alternative**: Sử dụng Ollama với vision model (không cần cookies)

```bash
# 1. Cài Ollama
# Download: https://ollama.ai

# 2. Pull vision model
ollama pull llava

# 3. Cập nhật .env
LOCAL_GEMINI_URL=http://localhost:11434/v1/chat/completions
LOCAL_GEMINI_MODEL=llava

# 4. Test
python test_vision_simple.py
```

## Tóm tắt

1. ✅ Server hoạt động tốt
2. ✅ Text-only API hoạt động
3. ❌ Vision cần cookies đầy đủ (thiếu SID, HSID, APISID)
4. 🔧 Export lại cookies theo hướng dẫn trên
5. 🔄 Restart server
6. ✅ Test lại vision

---

**Lưu ý**: Nếu không muốn phức tạp với cookies, hãy dùng Ollama + llava model (miễn phí, local, không cần authentication).
