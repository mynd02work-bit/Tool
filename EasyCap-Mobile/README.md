# 📱 EasyCap Mobile (Android)
### Trợ Lý Dịch Màn Hình 1:1 & AI Vision Copilot Dạng Bóng Nổi

Ứng dụng di động Native dành riêng cho **Android (Kotlin + Jetpack Compose)**, kế thừa trọn vẹn sức mạnh của EasyCap phiên bản máy tính:
- 🫧 **Bóng nổi thông minh (Floating Bubble):** Chạy ngầm mượt mà trên mọi ứng dụng khác (Manga, Game, X, Facebook, PDF).
- 🔤 **Dịch đè 1:1 trực tiếp:** Chạm 1-chạm vào bóng nổi để chụp màn hình, OCR offline qua Google ML Kit và vẽ đè bản dịch tại đúng vị trí khung chữ.
- 🤖 **AI Copilot đa phương thức:** Tích hợp Google Gemini 2.0 Flash Vision để giải thích lỗi code, giải bài tập và tóm tắt văn bản.

---

## 🛠️ Hướng Dẫn Mở Dự Án & Build APK

### 1. Yêu cầu môi trường
* **Android Studio** (Koala / Ladybug / Meerkat hoặc mới hơn).
* **JDK 17** hoặc **JDK 21**.
* Điện thoại Android từ **Android 8.0 (API 26)** đến **Android 15 (API 35)**.

### 2. Các bước mở dự án
1. Khởi động **Android Studio**.
2. Chọn **Open** và duyệt tới thư mục `d:\Code\tool\dịch màn hình\EasyCap-Mobile`.
3. Chờ Gradle đồng bộ (Sync Project with Gradle Files).
4. Bật **USB Debugging (Gỡ lỗi USB)** trên điện thoại và cắm cáp kết nối vào máy tính.
5. Nhấn nút **Run 'app' ▶️** trên thanh công cụ của Android Studio để cài ứng dụng trực tiếp lên điện thoại!

### 3. Xuất file cài đặt `.APK` độc lập
Trong Android Studio:
1. Vào menu **Build ➔ Build Bundle(s) / APK(s) ➔ Build APK(s)**.
2. File APK sẽ được tạo tại: `app/build/outputs/apk/debug/app-debug.apk`.
3. Copy file APK này sang điện thoại và cài đặt trực tiếp.

---

## 🔄 Cơ Chế Đồng Bộ & Cập Nhật Tự Động Từ Máy Tính Sang Điện Thoại

Ứng dụng hỗ trợ 2 cơ chế cập nhật đồng bộ để khi bạn sửa đổi trên máy tính, điện thoại sẽ có bản mới ngay:

### Cách 1: Tự động cập nhật không dây (OTA - Over-The-Air qua GitHub)
1. Khi cập nhật mã nguồn trên máy tính, bạn chỉ cần sửa số phiên bản trong `version.json` ở thư mục gốc và push lên GitHub.
2. Khi mở app **EasyCap Mobile** trên điện thoại (hoặc bấm biểu tượng làm mới 🔄 trên màn hình chính), app sẽ tự động phát hiện bản mới, tải về và mở màn hình cập nhật ngay lập tức mà không cần cắm cáp!

### Cách 2: Cập nhật siêu tốc 1-Click qua Wi-Fi / Cáp USB (`cap_nhat_len_dien_thoai.bat`)
1. Kết nối điện thoại với máy tính (cắm cáp USB hoặc chung mạng Wi-Fi).
2. Nhấp đúp vào file script **`cap_nhat_len_dien_thoai.bat`** tại thư mục gốc dự án.
3. Script sẽ tự động biên dịch APK mới và cài đè lên điện thoại trong vòng 5 giây!

---

## 📂 Cấu Trúc Mã Nguồn

```text
app/src/main/
├── AndroidManifest.xml                  # Khai báo quyền vẽ lên app khác & Screen Capture
├── java/com/easycap/mobile/
│   ├── MainActivity.kt                  # Giao diện chính (Cấp quyền, bật bóng nổi & API key)
│   ├── service/
│   │   ├── FloatingBubbleService.kt     # Quản lý bóng nổi, cử chỉ vuốt kéo & menu hành động
│   │   └── ScreenCaptureService.kt      # Quản lý MediaProjection chụp ảnh màn hình GPU
│   ├── ocr/
│   │   └── MlKitOcrEngine.kt            # Nhận diện chữ Offline < 80ms bằng Google ML Kit v2
│   ├── ai/
│   │   └── GeminiVisionClient.kt        # Kết nối Gemini 2.0 Flash Vision API
│   ├── ui/
│   │   ├── overlay/
│   │   │   └── ScreenOverlayManager.kt  # Vẽ đè bản dịch và co giãn font tự động
│   │   └── copilot/
│   │       └── CopilotCardView.kt       # Giao diện thẻ trượt AI Copilot (Compose)
│   └── data/
│       └── AppPreferences.kt            # Quản lý lưu trữ SharedPreferences
└── res/                                 # Tài nguyên giao diện, icon vector & màu sắc
```
