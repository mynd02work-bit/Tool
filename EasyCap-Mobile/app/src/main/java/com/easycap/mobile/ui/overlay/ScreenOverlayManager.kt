package com.easycap.mobile.ui.overlay

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.*
import android.os.Build
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import com.easycap.mobile.ocr.TextBlockItem

data class TranslatedItem(
    val originalBlock: TextBlockItem,
    val translatedText: String
)

class ScreenOverlayManager(private val context: Context) {
    private val windowManager = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
    private var overlayView: InpaintCanvasView? = null

    @SuppressLint("ClickableViewAccessibility")
    fun showTranslations(items: List<TranslatedItem>, onDismiss: () -> Unit) {
        hide()

        val layoutParams = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            else
                WindowManager.LayoutParams.TYPE_PHONE,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                    WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
        }

        val canvasView = InpaintCanvasView(context, items)
        canvasView.setOnTouchListener { _, event ->
            if (event.action == MotionEvent.ACTION_UP) {
                hide()
                onDismiss()
            }
            true
        }

        windowManager.addView(canvasView, layoutParams)
        overlayView = canvasView
    }

    fun hide() {
        overlayView?.let {
            try {
                windowManager.removeView(it)
            } catch (_: Exception) {}
            overlayView = null
        }
    }

    private class InpaintCanvasView(
        context: Context,
        private val items: List<TranslatedItem>
    ) : View(context) {

        private val bgPaint = Paint().apply {
            color = Color.parseColor("#EE1E202F") // Modern dark glassmorphic card
            style = Paint.Style.FILL
            isAntiAlias = true
        }

        private val strokePaint = Paint().apply {
            color = Color.parseColor("#446C5CE7") // Subtle purple glowing border
            style = Paint.Style.STROKE
            strokeWidth = 2f
            isAntiAlias = true
        }

        private val textPaint = Paint().apply {
            color = Color.WHITE
            isAntiAlias = true
            typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        }

        private val hintPaint = Paint().apply {
            color = Color.parseColor("#88FFFFFF")
            textSize = 36f
            textAlign = Paint.Align.CENTER
            isAntiAlias = true
        }

        override fun onDraw(canvas: Canvas) {
            super.onDraw(canvas)

            // Dim screen nhẹ để làm nổi bật văn bản dịch
            canvas.drawColor(Color.parseColor("#44000000"))

            for (item in items) {
                val box = item.originalBlock.boundingBox
                val rectF = RectF(box)

                // Bo góc cho từng khối dịch
                val radius = 12f
                canvas.drawRoundRect(rectF, radius, radius, bgPaint)
                canvas.drawRoundRect(rectF, radius, radius, strokePaint)

                // Tính toán font size tự co giãn vừa khít bounding box
                val availableW = rectF.width() - 16f
                val availableH = rectF.height() - 8f
                if (availableW > 10 && availableH > 10) {
                    val optimalSize = computeOptimalTextSize(item.translatedText, availableW, availableH)
                    textPaint.textSize = optimalSize

                    val fontMetrics = textPaint.fontMetrics
                    val textBaseline = rectF.centerY() - (fontMetrics.descent + fontMetrics.ascent) / 2
                    canvas.drawText(item.translatedText, rectF.left + 8f, textBaseline, textPaint)
                }
            }

            // Dòng hướng dẫn người dùng
            canvas.drawText("Chạm vào bất kỳ đâu trên màn hình để đóng", width / 2f, height - 80f, hintPaint)
        }

        private fun computeOptimalTextSize(text: String, maxW: Float, maxH: Float): Float {
            var low = 12f
            var high = 56f
            var best = 16f
            val tempPaint = Paint(textPaint)

            while (low <= high) {
                val mid = (low + high) / 2f
                tempPaint.textSize = mid
                val textW = tempPaint.measureText(text)
                val textH = tempPaint.fontMetrics.descent - tempPaint.fontMetrics.ascent

                if (textW <= maxW && textH <= maxH) {
                    best = mid
                    low = mid + 1f
                } else {
                    high = mid - 1f
                }
            }
            return best
        }
    }
}
