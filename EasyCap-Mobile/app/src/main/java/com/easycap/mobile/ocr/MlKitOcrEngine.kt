package com.easycap.mobile.ocr

import android.graphics.Bitmap
import android.graphics.Rect
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

data class TextBlockItem(
    val text: String,
    val boundingBox: Rect,
    val lines: List<String>
)

class MlKitOcrEngine {
    private val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)

    suspend fun recognizeText(bitmap: Bitmap): Result<List<TextBlockItem>> =
        suspendCancellableCoroutine { continuation ->
            val image = InputImage.fromBitmap(bitmap, 0)
            recognizer.process(image)
                .addOnSuccessListener { visionText ->
                    val blocks = mutableListOf<TextBlockItem>()
                    for (block in visionText.textBlocks) {
                        val box = block.boundingBox ?: continue
                        val lines = block.lines.map { it.text }
                        blocks.add(
                            TextBlockItem(
                                text = block.text,
                                boundingBox = box,
                                lines = lines
                            )
                        )
                    }
                    continuation.resume(Result.success(blocks))
                }
                .addOnFailureListener { exception ->
                    continuation.resume(Result.failure(exception))
                }
        }
}
