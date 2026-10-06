package com.easycap.mobile

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.media.projection.MediaProjectionManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.easycap.mobile.data.AppPreferences
import com.easycap.mobile.service.FloatingBubbleService
import com.easycap.mobile.updater.AppUpdater
import com.easycap.mobile.updater.UpdateInfo
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    private lateinit var preferences: AppPreferences
    private lateinit var appUpdater: AppUpdater
    private val currentVersionCode = 1
    private val currentVersionName = "1.0.0"

    private val projectionManager by lazy {
        getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
    }

    private var isServiceRunningState = mutableStateOf(false)

    private val overlayPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) {
        checkAndStartService()
    }

    private val screenCaptureLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            val serviceIntent = Intent(this, FloatingBubbleService::class.java).apply {
                putExtra(FloatingBubbleService.EXTRA_RESULT_CODE, result.resultCode)
                putExtra(FloatingBubbleService.EXTRA_RESULT_DATA, result.data)
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(serviceIntent)
            } else {
                startService(serviceIntent)
            }
            isServiceRunningState.value = true
            Toast.makeText(this, "Bóng nổi EasyCap đã xuất hiện!", Toast.LENGTH_SHORT).show()
        } else {
            Toast.makeText(this, "Cần cấp quyền chụp màn hình để dịch!", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        preferences = AppPreferences(this)
        appUpdater = AppUpdater(this)
        isServiceRunningState.value = FloatingBubbleService.isRunning

        setContent {
            EasyCapTheme {
                MainScreen(
                    isRunning = isServiceRunningState.value,
                    apiKey = preferences.geminiApiKey,
                    currentVersionName = currentVersionName,
                    currentVersionCode = currentVersionCode,
                    appUpdater = appUpdater,
                    onToggleService = { enable ->
                        if (enable) {
                            requestPermissionsAndStart()
                        } else {
                            stopService(Intent(this, FloatingBubbleService::class.java))
                            isServiceRunningState.value = false
                        }
                    },
                    onSaveApiKey = { newKey ->
                        preferences.geminiApiKey = newKey
                        Toast.makeText(this, "Đã lưu API Key thành công!", Toast.LENGTH_SHORT).show()
                    }
                )
            }
        }
    }

    private fun requestPermissionsAndStart() {
        if (!Settings.canDrawOverlays(this)) {
            val intent = Intent(
                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:$packageName")
            )
            overlayPermissionLauncher.launch(intent)
            return
        }
        checkAndStartService()
    }

    private fun checkAndStartService() {
        if (Settings.canDrawOverlays(this)) {
            screenCaptureLauncher.launch(projectionManager.createScreenCaptureIntent())
        }
    }
}

@Composable
fun EasyCapTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            background = Color(0xFF12131C),
            surface = Color(0xFF1E202F),
            primary = Color(0xFF6C5CE7)
        ),
        content = content
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    isRunning: Boolean,
    apiKey: String,
    currentVersionName: String,
    currentVersionCode: Int,
    appUpdater: AppUpdater,
    onToggleService: (Boolean) -> Unit,
    onSaveApiKey: (String) -> Unit
) {
    var apiKeyInput by remember { mutableStateOf(apiKey) }
    val coroutineScope = rememberCoroutineScope()

    var isCheckingUpdate by remember { mutableStateOf(false) }
    var availableUpdate by remember { mutableStateOf<UpdateInfo?>(null) }
    var downloadProgress by remember { mutableStateOf(-1) }
    var updateStatusMessage by remember { mutableStateOf("") }

    // Tự động kiểm tra bản cập nhật mới trên GitHub khi khởi chạy app
    LaunchedEffect(Unit) {
        val result = appUpdater.checkForUpdates(currentVersionCode)
        result.onSuccess { update ->
            if (update != null) {
                availableUpdate = update
            }
        }
    }

    Scaffold(
        containerColor = Color(0xFF12131C)
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 20.dp)
                .verticalScroll(rememberScrollState())
        ) {
            Spacer(modifier = Modifier.height(24.dp))

            // Hero Header
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(
                        Brush.horizontalGradient(listOf(Color(0xFF6C5CE7), Color(0xFFA29BFE))),
                        RoundedCornerShape(24.dp)
                    )
                    .padding(24.dp)
            ) {
                Column {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            "🚀 EasyCap Mobile",
                            color = Color.White,
                            fontSize = 22.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = Color.White.copy(alpha = 0.2f)
                        ) {
                            Text(
                                "v$currentVersionName",
                                color = Color.White,
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                            )
                        }
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        "Trợ lý dịch màn hình 1:1 & AI Copilot bóng nổi thông minh",
                        color = Color(0xFFE2E8F0),
                        fontSize = 13.sp
                    )
                }
            }

            Spacer(modifier = Modifier.height(18.dp))

            // Service Toggle Card
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1E202F)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier
                        .padding(20.dp)
                        .fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            "Bóng Nổi EasyCap",
                            color = Color.White,
                            fontSize = 17.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            if (isRunning) "Đang hoạt động trên màn hình" else "Đang tắt",
                            color = if (isRunning) Color(0xFF00CEC9) else Color.Gray,
                            fontSize = 13.sp
                        )
                    }

                    Switch(
                        checked = isRunning,
                        onCheckedChange = { onToggleService(it) },
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = Color.White,
                            checkedTrackColor = Color(0xFF6C5CE7)
                        )
                    )
                }
            }

            Spacer(modifier = Modifier.height(18.dp))

            // OTA Auto Update Card
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1E202F)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Refresh, contentDescription = null, tint = Color(0xFF00CEC9))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                "Đồng Bộ & Cập Nhật OTA",
                                color = Color.White,
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }

                        IconButton(
                            onClick = {
                                isCheckingUpdate = true
                                updateStatusMessage = "Đang kiểm tra máy chủ GitHub..."
                                coroutineScope.launch {
                                    val result = appUpdater.checkForUpdates(currentVersionCode)
                                    isCheckingUpdate = false
                                    result.onSuccess { update ->
                                        if (update != null) {
                                            availableUpdate = update
                                            updateStatusMessage = "Đã có bản cập nhật v${update.versionName}!"
                                        } else {
                                            updateStatusMessage = "Ứng dụng đang ở bản mới nhất (v$currentVersionName)."
                                        }
                                    }.onFailure { err ->
                                        updateStatusMessage = "Kiểm tra thất bại: ${err.message}"
                                    }
                                }
                            }
                        ) {
                            if (isCheckingUpdate) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(20.dp),
                                    color = Color(0xFF00CEC9),
                                    strokeWidth = 2.dp
                                )
                            } else {
                                Icon(Icons.Default.Refresh, contentDescription = "Check update", tint = Color.LightGray)
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        if (updateStatusMessage.isNotBlank()) updateStatusMessage
                        else "Khi bạn cập nhật phiên bản mới trên máy tính, điện thoại sẽ tự động phát hiện và cập nhật ngay lập tức.",
                        color = Color(0xFF94A3B8),
                        fontSize = 12.sp,
                        lineHeight = 18.sp
                    )

                    if (availableUpdate != null) {
                        Spacer(modifier = Modifier.height(12.dp))
                        Surface(
                            shape = RoundedCornerShape(14.dp),
                            color = Color(0xFF151622),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Text(
                                    "✨ Bản Mới: v${availableUpdate?.versionName}",
                                    color = Color(0xFF00CEC9),
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 14.sp
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    availableUpdate?.releaseNotes ?: "",
                                    color = Color(0xFFCBD5E1),
                                    fontSize = 12.sp,
                                    lineHeight = 18.sp
                                )

                                Spacer(modifier = Modifier.height(10.dp))

                                if (downloadProgress >= 0) {
                                    LinearProgressIndicator(
                                        progress = { downloadProgress / 100f },
                                        modifier = Modifier.fillMaxWidth(),
                                        color = Color(0xFF00CEC9),
                                        trackColor = Color(0xFF2D3045)
                                    )
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(
                                        "Đang tải bản cập nhật: $downloadProgress%",
                                        color = Color.LightGray,
                                        fontSize = 11.sp
                                    )
                                } else {
                                    Button(
                                        onClick = {
                                            availableUpdate?.let { update ->
                                                downloadProgress = 0
                                                coroutineScope.launch {
                                                    val res = appUpdater.downloadAndInstall(update) { p ->
                                                        downloadProgress = p
                                                    }
                                                    res.onFailure {
                                                        downloadProgress = -1
                                                        updateStatusMessage = "Lỗi tải về: ${it.message}"
                                                    }
                                                }
                                            }
                                        },
                                        shape = RoundedCornerShape(10.dp),
                                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF00CEC9)),
                                        modifier = Modifier.fillMaxWidth()
                                    ) {
                                        Text("Cập Nhật Ngay Lập Tức", color = Color(0xFF12131C), fontWeight = FontWeight.Bold)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(18.dp))

            // Gemini API Setup Card
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1E202F)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Lock, contentDescription = null, tint = Color(0xFFA29BFE))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            "Google Gemini API Key",
                            color = Color.White,
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }

                    Spacer(modifier = Modifier.height(10.dp))
                    Text(
                        "Dán API Key từ Google AI Studio để sử dụng Trợ lý AI Copilot giải bài, tóm tắt và phân tích code.",
                        color = Color(0xFF94A3B8),
                        fontSize = 12.sp,
                        lineHeight = 18.sp
                    )

                    Spacer(modifier = Modifier.height(14.dp))

                    OutlinedTextField(
                        value = apiKeyInput,
                        onValueChange = { apiKeyInput = it },
                        placeholder = { Text("Dán Gemini API Key...", color = Color.Gray, fontSize = 13.sp) },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(14.dp),
                        singleLine = true,
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedTextColor = Color.White,
                            unfocusedTextColor = Color.White,
                            focusedBorderColor = Color(0xFFA29BFE),
                            unfocusedBorderColor = Color(0xFF2D3045),
                            focusedContainerColor = Color(0xFF151622),
                            unfocusedContainerColor = Color(0xFF151622)
                        )
                    )

                    Spacer(modifier = Modifier.height(14.dp))

                    Button(
                        onClick = { onSaveApiKey(apiKeyInput.trim()) },
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF6C5CE7)),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Lưu Cài Đặt", color = Color.White, fontWeight = FontWeight.Bold)
                    }
                }
            }

            Spacer(modifier = Modifier.height(18.dp))

            // Quick Usage Guide
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1E202F)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Text("💡 Hướng Dẫn Nhanh", color = Color.White, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                    Spacer(modifier = Modifier.height(12.dp))
                    GuideItem("1. Chạm bóng nổi", "Tự động chụp và dịch đè 1:1 văn bản tiếng nước ngoài.")
                    GuideItem("2. Chạm vào màn hình", "Ẩn bản dịch, quay lại màn hình ứng dụng gốc.")
                    GuideItem("3. Gọi AI Copilot", "Tóm tắt bài báo, giải code bug và giải toán tức thì.")
                }
            }

            Spacer(modifier = Modifier.height(30.dp))
        }
    }
}

@Composable
fun GuideItem(title: String, desc: String) {
    Row(modifier = Modifier.padding(vertical = 6.dp)) {
        Icon(Icons.Default.Check, contentDescription = null, tint = Color(0xFF00CEC9), modifier = Modifier.size(18.dp))
        Spacer(modifier = Modifier.width(10.dp))
        Column {
            Text(title, color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
            Text(desc, color = Color(0xFF94A3B8), fontSize = 12.sp)
        }
    }
}
