# Hướng dẫn Tích hợp Google OAuth 2.0 toàn diện (MyLearn Project)

Chào bạn, với tư cách là một Senior Fullstack Developer, tôi đã phân tích dự án `MyLearn` của bạn và đã xây dựng sẵn hệ thống này. Dưới đây là tài liệu kiến trúc, luồng hoạt động và hướng dẫn chi tiết từng bước để bạn hoàn thiện quy trình Đăng nhập bằng Google.

## 1. TECH STACK (Công nghệ sử dụng hiện tại)
Hệ thống của chúng ta được thiết kế theo đúng yêu cầu Gen Z, tối ưu hóa tốc độ và bảo mật:
- **Frontend**: HTML/CSS/JS thuần (Vanilla JS) kết hợp thiết kế UI Glassmorphism hiện đại.
- **Backend**: Python (FastAPI) - Tối ưu cho kiến trúc MVC và xử lý bất đồng bộ tốc độ cao.
- **Database**: Firebase Firestore (NoSQL) - Lý tưởng cho lưu trữ và đồng bộ hóa thời gian thực.
- **Công cụ OAuth**: **Google Identity Services (GSI)** kết hợp với luồng xác thực **OAuth2 Implicit Flow** tùy chỉnh trên FastAPI.

---

## 2. HƯỚNG DẪN LẤY CLIENT ID TRÊN GOOGLE CLOUD CONSOLE
Đây là bước bắt buộc đầu tiên. Bạn cần tạo "chứng minh thư" (Client ID) để Google cho phép ứng dụng MyLearn kết nối với hệ thống của họ.

### Bước 1: Khởi tạo dự án
1. Truy cập [Google Cloud Console](https://console.cloud.google.com/).
2. Đăng nhập bằng Gmail Admin của bạn (VD: `Mynd02.work@gmail.com`).
3. Nhấp vào mũi tên chỉ xuống ở góc trên bên trái (cạnh logo Google Cloud) ➔ **New Project** (Dự án mới).
4. Đặt tên dự án: `MyLearn Workspace` ➔ Nhấn **Create** (Tạo).

### Bước 2: Cấu hình Màn hình xin phép OAuth (OAuth Consent Screen)
1. Trong menu bên trái, điều hướng tới **APIs & Services** ➔ **OAuth consent screen**.
2. Chọn **External** (Bên ngoài) để bất kỳ ai có tài khoản Google đều đăng nhập được ➔ Nhấn **Create**.
3. Điền các thông tin bắt buộc:
   - **App name**: `MyLearn Gen Z` (Tên sẽ hiển thị cho người dùng khi họ đăng nhập).
   - **User support email**: Chọn email của bạn.
   - **Developer contact information**: Nhập email của bạn.
4. Kéo xuống dưới cùng và nhấn **Save and Continue** liên tục qua các bước (Scopes, Test users) cho đến khi hoàn tất.
5. (Quan trọng) Nhấn nút **PUBLISH APP** để chuyển trạng thái từ Testing sang In Production.

### Bước 3: Tạo thông tin xác thực (Credentials)
1. Chuyển sang tab **Credentials** (Thông tin xác thực) ở menu bên trái.
2. Nhấn nút **+ CREATE CREDENTIALS** (Tạo thông tin xác thực) ở thanh trên cùng ➔ Chọn **OAuth client ID**.
3. Cấu hình chi tiết:
   - **Application type**: Chọn **Web application** (Ứng dụng web).
   - **Name**: `MyLearn Local Client`
   - **Authorized JavaScript origins** (Nguồn cấp phép JS): Nhấn Add URI và nhập: 
     `http://127.0.0.1:1122`
   - **Authorized redirect URIs** (URI chuyển hướng): Nhấn Add URI và nhập: 
     `http://127.0.0.1:1122/auth/callback`
4. Nhấn **CREATE**.
5. Màn hình sẽ hiện ra **Client ID** (Ví dụ: `123456789-abcxyz.apps.googleusercontent.com`). Hãy sao chép chuỗi này!

> [!IMPORTANT]
> Sau khi có Client ID, bạn hãy mở file `app/static/js/auth.js` và `app/views/login.html` trong mã nguồn, tìm dòng chữ `1098472918471-mylearnapp.apps.googleusercontent.com` và thay thế bằng Client ID thực tế của bạn.

---

## 3. LUỒNG HOẠT ĐỘNG VÀ MÃ NGUỒN (Đã tích hợp trong dự án)

Luồng (User Flow) được thiết kế bảo mật cao, tách biệt rõ ràng giữa Client và Server.

### Bước 1: Frontend gọi trang Google Login
Thay vì dùng thư viện nặng, chúng ta tạo một URL chuyển hướng chuẩn OAuth2. 
**File**: `app/static/js/auth.js`

```javascript
function triggerRealGoogleLogin() {
    const clientId = "MÃ_CLIENT_ID_CỦA_BẠN";
    const redirectUri = window.location.origin + "/auth/callback";
    
    // Gọi thẳng sang cổng xác thực an toàn của Google
    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=token&scope=email%20profile&prompt=select_account`;
    
    window.location.href = authUrl;
}
```

### Bước 2: Frontend nhận Token từ Google & Gọi Backend
Sau khi user đồng ý, Google chuyển hướng về `http://127.0.0.1:1122/auth/callback#access_token=...`.
Mã nguồn tại file `app/views/auth_callback.html` sẽ tách Token này ra, và an toàn gửi lên Backend.

```javascript
// Xử lý lỗi nếu user từ chối cấp quyền
const error = params.get('error');
if (error) {
    alert("Lỗi từ Google: " + error);
    window.location.href = '/login';
}

// Lấy thông tin user an toàn qua Google API
fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
    headers: { Authorization: `Bearer ${accessToken}` }
})
.then(res => res.json())
.then(userInfo => {
    // Gửi data sang FastAPI Backend của chúng ta
    return fetch('/api/auth/google-login', { ... })
})
```

### Bước 3: Backend xử lý & Cấp Session Cookie (Bảo mật)
Tại Backend FastAPI, chúng ta thực hiện việc tạo/kiểm tra người dùng trong Firestore và **cấp phát Cookie HttpOnly**.
**File**: `app/login/controller.py`

```python
@router.post("/api/auth/google-login")
async def google_login(req: GoogleLoginRequest, response: Response, db = Depends(get_firebase_db)):
    # 1. Tạo hoặc lấy thông tin User từ Firestore Database
    user_data = create_or_get_user(...)
    
    # 2. BẢO MẬT: Không trả Token thẳng về JS để tránh lỗi XSS!
    # Thay vào đó, set vào HTTP-Only Cookie.
    response.set_cookie(
        key="mylearn_user_uid",
        value=user_data["uid"],
        httponly=True,  # Ngăn chặn mã độc XSS đọc được Cookie
        samesite="lax", # Ngăn chặn tấn công CSRF
        secure=False    # Cài thành True khi deploy lên server HTTPS (SSL)
    )
    
    return {"status": "success", "message": "Đăng nhập thành công!"}
```

## 4. CẤU TRÚC THƯ MỤC CỦA TÍNH NĂNG NÀY
```text
d:\Code\MyLearn\app\
├── controllers\
│   └── main_controller.py      # Định tuyến các trang HTML (bao gồm /auth/callback)
├── login\
│   ├── controller.py           # API Endpoints (Nơi chứa /api/auth/google-login)
│   ├── service.py              # Logic xử lý User, Tier (Vĩnh viễn, Tháng)
│   └── models.py               # Schema Validate dữ liệu đầu vào (Pydantic)
├── static\
│   └── js\
│       └── auth.js             # Logic xử lý nút đăng nhập ở thanh Sidebar
└── views\
    ├── index.html              # Trang chủ ứng dụng
    ├── login.html              # Màn hình đăng nhập chính
    └── auth_callback.html      # Trang trung gian xử lý kết quả trả về từ Google
```

> [!TIP]
> Việc sử dụng **HttpOnly Cookie** trong bước 3 là kỹ thuật bảo mật tiêu chuẩn ngành (Industry Standard) của các Senior Developer để tránh triệt để tấn công XSS (Cross-site Scripting). Hacker dù có chèn mã độc vào web cũng không thể lấy được session của người dùng!
