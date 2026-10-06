package com.easycap.mobile.data

import android.content.Context
import android.content.SharedPreferences

class AppPreferences(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("easycap_prefs", Context.MODE_PRIVATE)

    var geminiApiKey: String
        get() = prefs.getString("gemini_api_key", "") ?: ""
        set(value) = prefs.edit().putString("gemini_api_key", value).apply()

    var targetLanguage: String
        get() = prefs.getString("target_language", "vi") ?: "vi"
        set(value) = prefs.edit().putString("target_language", value).apply()

    var isFloatingBubbleEnabled: Boolean
        get() = prefs.getBoolean("floating_bubble_enabled", false)
        set(value) = prefs.edit().putBoolean("floating_bubble_enabled", value).apply()

    var autoInpaint: Boolean
        get() = prefs.getBoolean("auto_inpaint", true)
        set(value) = prefs.edit().putBoolean("auto_inpaint", value).apply()
}
