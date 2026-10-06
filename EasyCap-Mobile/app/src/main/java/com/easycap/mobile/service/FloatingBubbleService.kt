package com.easycap.mobile.service

import android.annotation.SuppressLint
import android.app.*
import android.content.Context
import android.content.Intent
import android.graphics.PixelFormat
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.IBinder
import android.view.*
import android.widget.ImageView
import androidx.compose.ui.platform.ComposeView
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.core.app.NotificationCompat
import com.easycap.mobile.MainActivity
import com.easycap.mobile.R
import com.easycap.mobile.ai.GeminiVisionClient
import com.easycap.mobile.data.AppPreferences
import com.easycap.mobile.ocr.MlKitOcrEngine
import com.easycap.mobile.ui.copilot.CopilotCardView
import com.easycap.mobile.ui.copilot.CopilotTab
import com.easycap.mobile.ui.overlay.ScreenOverlayManager
import com.easycap.mobile.ui.overlay.TranslatedItem
import kotlinx.coroutines.*
import kotlin.math.abs

class FloatingBubbleService : Service() {

    private val serviceScope = CoroutineScope(Dispatchers.Main + Job())
    private lateinit var windowManager: WindowManager
    private lateinit var preferences: AppPreferences
    private lateinit var overlayManager: ScreenOverlayManager

    private var bubbleView: View? = null
    private var copilotOverlayView: View? = null
    private var screenCaptureService: ScreenCaptureService? = null

    private val ocrEngine = MlKitOcrEngine()
    private var geminiClient: GeminiVisionClient? = null

    companion object {
        const val CHANNEL_ID = "easycap_foreground_service"
        const val NOTIFICATION_ID = 1001
        const val EXTRA_RESULT_CODE = "extra_result_code"
        const val EXTRA_RESULT_DATA = "extra_result_data"

        var isRunning = false
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        isRunning = true
        windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        preferences = AppPreferences(this)
        overlayManager = ScreenOverlayManager(this)

        if (preferences.geminiApiKey.isNotBlank()) {
            geminiClient = GeminiVisionClient(preferences.geminiApiKey)
        }

        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification())
        createFloatingBubble()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val resultCode = intent?.getIntExtra(EXTRA_RESULT_CODE, Activity.RESULT_CANCELED) ?: Activity.RESULT_CANCELED
        val resultData = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            intent?.getParcelableExtra(EXTRA_RESULT_DATA, Intent::class.java)
        } else {
            @Suppress("DEPRECATION")
            intent?.getParcelableExtra<Intent>(EXTRA_RESULT_DATA)
        }

        if (resultCode == Activity.RESULT_OK && resultData != null) {
            val projectionManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            val projection = projectionManager.getMediaProjection(resultCode, resultData)
            screenCaptureService = ScreenCaptureService(this, projection)
        }

        return START_STICKY
    }

    @SuppressLint("ClickableViewAccessibility")
    private fun createFloatingBubble() {
        val bubbleSize = (56 * resources.displayMetrics.density).toInt()

        val layoutParams = WindowManager.LayoutParams(
            bubbleSize,
            bubbleSize,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            else
                WindowManager.LayoutParams.TYPE_PHONE,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = 20
            y = resources.displayMetrics.heightPixels / 3
        }

        val imageView = ImageView(this).apply {
            setImageResource(R.drawable.ic_bubble_logo)
            elevation = 16f
        }

        var initialX = 0
        var initialY = 0
        var initialTouchX = 0f
        var initialTouchY = 0f
        var isClick = false

        imageView.setOnTouchListener { _, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    initialX = layoutParams.x
                    initialY = layoutParams.y
                    initialTouchX = event.rawX
                    initialTouchY = event.rawY
                    isClick = true
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = (event.rawX - initialTouchX).toInt()
                    val dy = (event.rawY - initialTouchY).toInt()
                    if (abs(dx) > 10 || abs(dy) > 10) {
                        isClick = false
                    }
                    layoutParams.x = initialX + dx
                    layoutParams.y = initialY + dy
                    windowManager.updateViewLayout(imageView, layoutParams)
                    true
                }
                MotionEvent.ACTION_UP -> {
                    if (isClick) {
                        onBubbleClicked()
                    } else {
                        // Snap vào mép viền gần nhất (Trái hoặc Phải)
                        val screenWidth = resources.displayMetrics.widthPixels
                        layoutParams.x = if (layoutParams.x < screenWidth / 2) 10 else screenWidth - bubbleSize - 10
                        windowManager.updateViewLayout(imageView, layoutParams)
                    }
                    true
                }
                else -> false
            }
        }

        windowManager.addView(imageView, layoutParams)
        bubbleView = imageView
    }

    private fun onBubbleClicked() {
        serviceScope.launch {
            // Ẩn bóng nổi tạm thời để không bị dính vào ảnh chụp màn hình
            bubbleView?.visibility = View.GONE
            delay(100)

            val screenshot = screenCaptureService?.captureScreen()
            bubbleView?.visibility = View.VISIBLE

            if (screenshot == null) {
                return@launch
            }

            // Mặc định: Chạy OCR & Dịch đè 1:1 trực tiếp
            val ocrResult = ocrEngine.recognizeText(screenshot)
            ocrResult.onSuccess { blocks ->
                if (blocks.isNotEmpty()) {
                    // Tạo bản dịch mô phỏng hoặc gọi Gemini dịch ngữ cảnh
                    val translatedItems = blocks.map { block ->
                        TranslatedItem(
                            originalBlock = block,
                            translatedText = "[Dịch] ${block.text}"
                        )
                    }
                    overlayManager.showTranslations(translatedItems) {
                        // Dismiss callback
                    }
                } else {
                    // Nếu không có nhiều text, hiển thị thẻ Copilot AI
                    showCopilotCard(screenshot)
                }
            }.onFailure {
                showCopilotCard(screenshot)
            }
        }
    }

    private fun showCopilotCard(bitmap: android.graphics.Bitmap) {
        hideCopilotCard()

        val layoutParams = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            else
                WindowManager.LayoutParams.TYPE_PHONE,
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or WindowManager.LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.BOTTOM
        }

        var resultText by androidx.compose.runtime.mutableStateOf("✦ Đang phân tích màn hình...")
        var isLoading by androidx.compose.runtime.mutableStateOf(true)
        var currentTab by androidx.compose.runtime.mutableStateOf(CopilotTab.EXPLAIN)

        val composeView = ComposeView(this).apply {
            setContent {
                CopilotCardView(
                    resultText = resultText,
                    isLoading = isLoading,
                    selectedTab = currentTab,
                    onTabSelected = { tab ->
                        currentTab = tab
                        requestAiAnalysis(bitmap, tab) { res, loading ->
                            resultText = res
                            isLoading = loading
                        }
                    },
                    onSendPrompt = { prompt ->
                        requestCustomPrompt(bitmap, prompt) { res, loading ->
                            resultText = res
                            isLoading = loading
                        }
                    },
                    onClose = { hideCopilotCard() }
                )
            }
        }

        windowManager.addView(composeView, layoutParams)
        copilotOverlayView = composeView

        // Bắt đầu phân tích tab mặc định
        requestAiAnalysis(bitmap, currentTab) { res, loading ->
            resultText = res
            isLoading = loading
        }
    }

    private fun requestAiAnalysis(
        bitmap: android.graphics.Bitmap,
        tab: CopilotTab,
        callback: (String, Boolean) -> Unit
    ) {
        callback("Đang gửi yêu cầu tới Gemini...", true)
        val prompt = when (tab) {
            CopilotTab.TRANSLATE -> "Hãy dịch toàn bộ nội dung trong bức ảnh này sang tiếng Việt chuẩn xác và tự nhiên."
            CopilotTab.SUMMARIZE -> "Hãy tóm tắt các ý chính quan trọng nhất trong ảnh thành các gạch đầu dòng ngắn gọn."
            CopilotTab.EXPLAIN -> "Hãy giải thích chi tiết nội dung bức ảnh này (nếu là code thì giải thích lỗi và cách fix, nếu là bài toán hãy giải chi tiết)."
            CopilotTab.CHAT -> "Bức ảnh này đang hiển thị nội dung gì? Hãy mô tả tổng quan."
        }

        serviceScope.launch {
            val client = geminiClient ?: GeminiVisionClient(preferences.geminiApiKey)
            val result = client.analyzeImage(bitmap, prompt)
            result.onSuccess { text ->
                callback(text, false)
            }.onFailure { err ->
                callback("Lỗi: ${err.message}", false)
            }
        }
    }

    private fun requestCustomPrompt(
        bitmap: android.graphics.Bitmap,
        prompt: String,
        callback: (String, Boolean) -> Unit
    ) {
        callback("Gemini đang suy nghĩ...", true)
        serviceScope.launch {
            val client = geminiClient ?: GeminiVisionClient(preferences.geminiApiKey)
            val result = client.analyzeImage(bitmap, prompt)
            result.onSuccess { text ->
                callback(text, false)
            }.onFailure { err ->
                callback("Lỗi: ${err.message}", false)
            }
        }
    }

    private fun hideCopilotCard() {
        copilotOverlayView?.let {
            try {
                windowManager.removeView(it)
            } catch (_: Exception) {}
            copilotOverlayView = null
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                getString(R.string.channel_name),
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = getString(R.string.channel_desc)
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(): Notification {
        val intent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.notification_title))
            .setContentText(getString(R.string.notification_text))
            .setSmallIcon(R.drawable.ic_bubble_logo)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    override fun onDestroy() {
        super.onDestroy()
        isRunning = false
        serviceScope.cancel()
        overlayManager.hide()
        hideCopilotCard()
        bubbleView?.let {
            try { windowManager.removeView(it) } catch (_: Exception) {}
        }
        screenCaptureService?.release()
    }
}
