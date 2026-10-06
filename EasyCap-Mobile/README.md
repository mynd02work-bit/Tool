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
