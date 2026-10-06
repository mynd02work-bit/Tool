package com.easycap.mobile.ai

import android.graphics.Bitmap
import android.util.Base64
import com.google.gson.Gson
import com.google.gson.JsonObject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.ByteArrayOutputStream
import java.util.concurrent.TimeUnit

class GeminiVisionClient(private val apiKey: String) {

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    private val gson = Gson()

    private fun bitmapToBase64(bitmap: Bitmap): String {
        val outputStream = ByteArrayOutputStream()
        // Resize nếu ảnh quá lớn để tối ưu đường truyền
        val maxDim = 1600
        val w = bitmap.width
        val h = bitmap.height
        val scaled = if (maxOf(w, h) > maxDim) {
            val ratio = maxDim.toFloat() / maxOf(w, h).toFloat()
            Bitmap.createScaledBitmap(bitmap, (w * ratio).toInt(), (h * ratio).toInt(), true)
        } else {
            bitmap
        }
        scaled.compress(Bitmap.CompressFormat.JPEG, 85, outputStream)
        return Base64.encodeToString(outputStream.toByteArray(), Base64.NO_WRAP)
    }

    suspend fun analyzeImage(
        bitmap: Bitmap,
        prompt: String,
        model: String = "gemini-2.0-flash"
    ): Result<String> = withContext(Dispatchers.IO) {
        try {
            if (apiKey.isBlank()) {
                return@withContext Result.failure(Exception("Vui lòng cấu hình Gemini API Key trong phần Cài đặt!"))
            }

            val base64Img = bitmapToBase64(bitmap)
            val url = "https://generativelanguage.googleapis.com/v1beta/models/$model:generateContent?key=$apiKey"

            val jsonBody = """
            {
              "contents": [
                {
                  "parts": [
                    { "text": ${gson.toJson(prompt)} },
                    {
                      "inlineData": {
                        "mimeType": "image/jpeg",
                        "data": "$base64Img"
                      }
                    }
                  ]
                }
              ]
            }
            """.trimIndent()

            val request = Request.Builder()
                .url(url)
                .post(jsonBody.toRequestBody("application/json".toMediaType()))
                .build()

            val response = client.newCall(request).execute()
            val respBody = response.body?.string() ?: ""

            if (!response.isSuccessful) {
                return@withContext Result.failure(Exception("Lỗi API (${response.code}): $respBody"))
            }

            val jsonObject = gson.fromJson(respBody, JsonObject::class.java)
            val candidates = jsonObject.getAsJsonArray("candidates")
            if (candidates != null && candidates.size() > 0) {
                val first = candidates[0].asJsonObject
                val content = first.getAsJsonObject("content")
                val parts = content.getAsJsonArray("parts")
                val text = parts[0].asJsonObject.get("text").asString
                Result.success(text)
            } else {
                Result.failure(Exception("Không nhận được phản hồi phân tích từ Gemini!"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
