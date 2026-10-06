package com.easycap.mobile.ui.copilot

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

enum class CopilotTab(val label: String, val icon: String) {
    TRANSLATE("Dịch", "🌐"),
    SUMMARIZE("Tóm tắt", "📋"),
    EXPLAIN("Giải thích", "💡"),
    CHAT("Hỏi AI", "💬")
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CopilotCardView(
    resultText: String,
    isLoading: Boolean,
    selectedTab: CopilotTab,
    onTabSelected: (CopilotTab) -> Unit,
    onSendPrompt: (String) -> Unit,
    onClose: () -> Unit
) {
    var customPrompt by remember { mutableStateOf("") }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E202F)),
        elevation = CardDefaults.cardElevation(defaultElevation = 16.dp)
    ) {
        Column(
            modifier = Modifier
                .padding(20.dp)
                .fillMaxWidth()
        ) {
            // Header Bar
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("✦", color = Color(0xFFA29BFE), fontSize = 20.sp, fontWeight = FontWeight.Bold)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        "EasyCap AI Copilot",
                        color = Color.White,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
                IconButton(onClick = onClose) {
                    Icon(Icons.Default.Close, contentDescription = "Close", tint = Color.LightGray)
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Action Tabs
            ScrollableTabRow(
                selectedTabIndex = selectedTab.ordinal,
                containerColor = Color.Transparent,
                contentColor = Color(0xFFA29BFE),
                edgePadding = 0.dp
            ) {
                CopilotTab.entries.forEach { tab ->
                    Tab(
                        selected = selectedTab == tab,
                        onClick = { onTabSelected(tab) },
                        text = {
                            Text(
                                "${tab.icon} ${tab.label}",
                                fontSize = 13.sp,
                                fontWeight = if (selectedTab == tab) FontWeight.Bold else FontWeight.Normal
                            )
                        }
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // Response Box
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 100.dp, max = 260.dp)
                    .background(Color(0xFF151622), RoundedCornerShape(16.dp))
                    .padding(14.dp)
                    .verticalScroll(rememberScrollState())
            ) {
                if (isLoading) {
                    Row(
                        modifier = Modifier.align(Alignment.Center),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        CircularProgressIndicator(
                            color = Color(0xFFA29BFE),
                            strokeWidth = 3.dp,
                            modifier = Modifier.size(24.dp)
                        )
                        Spacer(modifier = Modifier.width(12.dp))
                        Text("Gemini đang phân tích...", color = Color.Gray, fontSize = 14.sp)
                    }
                } else {
                    Text(
                        text = if (resultText.isBlank()) "Đang chờ nội dung phân tích..." else resultText,
                        color = Color(0xFFE2E8F0),
                        fontSize = 14.sp,
                        lineHeight = 22.sp
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // Question Input Bar
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                OutlinedTextField(
                    value = customPrompt,
                    onValueChange = { customPrompt = it },
                    placeholder = { Text("Hỏi thêm về màn hình...", color = Color.Gray, fontSize = 13.sp) },
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(16.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White,
                        focusedBorderColor = Color(0xFFA29BFE),
                        unfocusedBorderColor = Color(0xFF2D3045),
                        focusedContainerColor = Color(0xFF151622),
                        unfocusedContainerColor = Color(0xFF151622)
                    ),
                    singleLine = true
                )
                Spacer(modifier = Modifier.width(8.dp))
                IconButton(
                    onClick = {
                        if (customPrompt.isNotBlank()) {
                            onSendPrompt(customPrompt)
                            customPrompt = ""
                        }
                    },
                    modifier = Modifier
                        .background(Color(0xFF6C5CE7), RoundedCornerShape(14.dp))
                        .size(48.dp)
                ) {
                    Icon(Icons.Default.Send, contentDescription = "Send", tint = Color.White)
                }
            }
        }
    }
}
