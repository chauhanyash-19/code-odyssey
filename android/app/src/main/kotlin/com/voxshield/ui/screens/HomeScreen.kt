package com.voxshield.ui.screens

import android.content.Context
import android.content.Intent
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.voxshield.model.PdiVerdict
import com.voxshield.network.WsConnectionState
import com.voxshield.service.ProtectionState
import com.voxshield.service.VoxShieldForegroundService
import com.voxshield.call.VoxCallState
import com.voxshield.ui.components.ProtectionBanner
import com.voxshield.ui.components.SpeakerBanner
import com.voxshield.ui.components.ScamAlertBanner
import com.voxshield.ui.components.LimitedModeBanner
import com.voxshield.ui.components.UncertainBanner
import com.voxshield.ui.components.WaveformIndicator
import com.voxshield.ui.theme.VoxColors

/**
 * HomeScreen — main VoxShield dashboard.
 *
 * Displays:
 *  - Large shield toggle (start / stop protection)
 *  - Real-time call state: OFFHOOK + speaker off → SpeakerBanner
 *                          OFFHOOK + speaker on  → ProtectionBanner + waveform + PDI score
 *  - WebSocket connection status
 *  - Latest transcript snippet
 *  - Settings shortcut (backend URL config)
 *
 * @param protectionState  Live state from VoxShieldForegroundService via Binder
 * @param amplitude        Live RMS from AudioCaptureManager (0.0–1.0)
 * @param backendUrl       Current backend WS URL (from SharedPreferences)
 * @param onBackendUrlChange  Called when user changes the backend URL in settings
 */
@Composable
fun HomeScreen(
    protectionState: ProtectionState,
    amplitude: Float,
    backendUrl: String,
    onBackendUrlChange: (String) -> Unit,
    onDismissAlert: () -> Unit,
    onSetPromptUnknownOnly: (Boolean) -> Unit = {}
) {
    val context = LocalContext.current
    var showSettings by remember { mutableStateOf(false) }
    var editableUrl by remember { mutableStateOf(backendUrl) }

    // Pulsing ring animation for the shield button when active
    val infiniteTransition = rememberInfiniteTransition(label = "shield_pulse")
    val ringScale by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 1.12f,
        animationSpec = infiniteRepeatable(
            animation = tween(1200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "ring_scale"
    )

    val isActive = protectionState.isProtectionActive
    val callActive = protectionState.callState == VoxCallState.OFFHOOK

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(VoxColors.Background)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(52.dp))

            // ── Header ────────────────────────────────────────────────────────
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "VoxShield",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    color = VoxColors.TextPrimary
                )
                IconButton(onClick = { showSettings = true }) {
                    Text("⚙️", fontSize = 22.sp)
                }
            }

            Spacer(modifier = Modifier.height(40.dp))

            // ── Shield toggle button ──────────────────────────────────────────
            Box(contentAlignment = Alignment.Center) {
                // Outer pulsing ring (only when active)
                if (isActive) {
                    Box(
                        modifier = Modifier
                            .size(180.dp)
                            .scale(ringScale)
                            .clip(CircleShape)
                            .background(VoxColors.AccentGlow)
                    )
                }

                // Main shield button
                Box(
                    modifier = Modifier
                        .size(160.dp)
                        .clip(CircleShape)
                        .background(
                            Brush.radialGradient(
                                colors = if (isActive) {
                                    listOf(VoxColors.AccentDim, Color(0xFF003D55))
                                } else {
                                    listOf(VoxColors.SurfaceElevated, VoxColors.SurfaceCard)
                                }
                            )
                        )
                        .border(
                            width = 2.dp,
                            color = if (isActive) VoxColors.Accent else VoxColors.Border,
                            shape = CircleShape
                        )
                        .clickable { toggleProtection(context, isActive, backendUrl) },
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = if (isActive) "🛡️" else "🔓",
                            fontSize = 48.sp
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = if (isActive) "ACTIVE" else "TAP TO START",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (isActive) VoxColors.Accent else VoxColors.TextMuted,
                            letterSpacing = 1.5.sp
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(32.dp))

            // ── Status label ──────────────────────────────────────────────────
            Text(
                text = when {
                    !isActive -> "Protection is off"
                    callActive && !protectionState.isSpeakerOn -> "Call active — enable speakerphone"
                    callActive && protectionState.isSpeakerOn  -> "Analyzing call in real time"
                    else -> "Protection active — waiting for a call"
                },
                fontSize = 15.sp,
                color = VoxColors.TextSecondary,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(24.dp))

            // ── Unknown caller prompt banner ───────────────────────────────────
            // Show prominently when: call is ringing/active AND protection is off
            // AND caller is unknown (or promptOnUnknownOnly is false = show always)
            val callIsActive = protectionState.callState in listOf(VoxCallState.RINGING, VoxCallState.OFFHOOK)
            val showUnknownPrompt = !isActive &&
                callIsActive &&
                (!protectionState.promptOnUnknownOnly || !protectionState.isKnownContact)

            UnknownCallerBanner(
                visible = showUnknownPrompt,
                isKnownContact = protectionState.isKnownContact,
                onStartProtection = { toggleProtection(context, isActive = false, backendUrl = backendUrl) },
                modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp)
            )

            // ── Call state banners ────────────────────────────────────────────

            ScamAlertBanner(
                visible = isActive && protectionState.factcheckStatus == "CRITICAL",
                message = protectionState.latestVerdictMessage.ifEmpty { "Possible scam detected" },
                onDismiss = onDismissAlert,
                modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp)
            )

            LimitedModeBanner(
                visible = isActive && protectionState.isLimitedMode,
                modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp)
            )

            UncertainBanner(
                visible = isActive && protectionState.factcheckStatus == "UNCERTAIN",
                modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp)
            )

            SpeakerBanner(
                visible = isActive && callActive && !protectionState.isSpeakerOn,
                modifier = Modifier.fillMaxWidth()
            )

            ProtectionBanner(
                pdiScore = protectionState.pdiScore,
                verdictLabel = protectionState.verdict.label,
                verdictEmoji = protectionState.verdict.emoji,
                amplitude = amplitude,
                visible = isActive && callActive && protectionState.isSpeakerOn,
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(20.dp))

            // ── Idle waveform (when active but no call) ───────────────────────
            if (isActive && !callActive) {
                WaveformIndicator(
                    amplitude = 0f,
                    isActive = false,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(20.dp))
            }

            // ── WebSocket connection status ────────────────────────────────────
            if (isActive) {
                ConnectionStatusChip(protectionState.wsConnectionState)
                Spacer(modifier = Modifier.height(12.dp))
            }

            // ── Transcript snippet ─────────────────────────────────────────────
            if (isActive && protectionState.latestTranscript.isNotBlank()) {
                TranscriptCard(text = protectionState.latestTranscript)
                Spacer(modifier = Modifier.height(12.dp))
            }

            // ── Info card (how it works reminder) ─────────────────────────────
            if (!isActive) {
                InfoCard()
            }

            Spacer(modifier = Modifier.height(48.dp))
        }

        // ── Settings sheet ────────────────────────────────────────────────────
        if (showSettings) {
            SettingsBottomSheet(
                currentUrl = editableUrl,
                promptOnUnknownOnly = protectionState.promptOnUnknownOnly,
                onUrlChange = { editableUrl = it },
                onSave = {
                    onBackendUrlChange(editableUrl)
                    showSettings = false
                },
                onDismiss = { showSettings = false },
                onSetPromptUnknownOnly = onSetPromptUnknownOnly
            )
        }
    }
}

// ─── UnknownCallerBanner ────────────────────────────────────────────────────

/**
 * Prominent amber banner shown when an unknown caller is on the line and protection is off.
 *
 * Show conditions:
 *   - Call is active (RINGING or OFFHOOK)
 *   - Protection is NOT already running
 *   - Caller is NOT a known contact (or 'prompt for unknown only' is disabled)
 *
 * @param visible           Whether to show this banner.
 * @param isKnownContact    True if the caller was identified in contacts. Used for subtitle text.
 * @param onStartProtection Called when the user taps "Start Protection".
 */
@Composable
fun UnknownCallerBanner(
    visible: Boolean,
    isKnownContact: Boolean,
    onStartProtection: () -> Unit,
    modifier: Modifier = Modifier
) {
    if (!visible) return

    val warningColor = Color(0xFFFF8C00)  // Amber — distinct from the red CRITICAL banner

    // Gentle pulsing border to draw attention
    val infiniteTransition = rememberInfiniteTransition(label = "unknown_pulse")
    val borderAlpha by infiniteTransition.animateFloat(
        initialValue = 0.5f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(900, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "border_alpha"
    )

    Column(
        modifier = modifier
            .clip(RoundedCornerShape(14.dp))
            .background(warningColor.copy(alpha = 0.10f))
            .border(1.5.dp, warningColor.copy(alpha = borderAlpha), RoundedCornerShape(14.dp))
            .padding(horizontal = 16.dp, vertical = 14.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("⚠️", fontSize = 20.sp)
            Spacer(modifier = Modifier.width(8.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = if (isKnownContact) "Incoming call" else "Unknown number calling",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = warningColor
                )
                Text(
                    text = if (isKnownContact)
                        "Tap to start protection manually"
                    else
                        "Not in your contacts \u2014 potential scam risk",
                    fontSize = 11.sp,
                    color = warningColor.copy(alpha = 0.8f),
                    lineHeight = 16.sp
                )
            }
        }
        Spacer(modifier = Modifier.height(10.dp))
        Button(
            onClick = onStartProtection,
            modifier = Modifier.fillMaxWidth().height(40.dp),
            shape = RoundedCornerShape(10.dp),
            colors = ButtonDefaults.buttonColors(containerColor = warningColor)
        ) {
            Text(
                text = "🛡️  Start Protection",
                color = Color.Black,
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

// ─── Sub-composables ─────────────────────────────────────────────────────────

@Composable
private fun ConnectionStatusChip(state: WsConnectionState) {
    val (text, color) = when (state) {
        is WsConnectionState.Connected    -> "● Connected to backend" to VoxColors.Safe
        is WsConnectionState.Connecting   -> "○ Connecting…" to VoxColors.Suspicious
        is WsConnectionState.Reconnecting -> "↺ Reconnecting (attempt ${state.attempt})…" to VoxColors.Suspicious
        is WsConnectionState.Error        -> "✕ ${state.message}" to VoxColors.Scam
        else                              -> "○ Disconnected" to VoxColors.TextMuted
    }
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(20.dp))
            .background(color.copy(alpha = 0.12f))
            .border(1.dp, color.copy(alpha = 0.3f), RoundedCornerShape(20.dp))
            .padding(horizontal = 12.dp, vertical = 5.dp)
    ) {
        Text(text, color = color, fontSize = 12.sp, fontWeight = FontWeight.Medium)
    }
}

@Composable
private fun TranscriptCard(text: String) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(VoxColors.SurfaceCard)
            .border(1.dp, VoxColors.Border, RoundedCornerShape(12.dp))
            .padding(14.dp)
    ) {
        Text("🗣 Latest transcript", color = VoxColors.TextMuted, fontSize = 11.sp)
        Spacer(modifier = Modifier.height(6.dp))
        Text(
            text = "\"$text\"",
            color = VoxColors.TextPrimary,
            fontSize = 13.sp,
            fontStyle = androidx.compose.ui.text.font.FontStyle.Italic,
            lineHeight = 20.sp
        )
    }
}

@Composable
private fun InfoCard() {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(VoxColors.SurfaceElevated)
            .border(1.dp, VoxColors.Border, RoundedCornerShape(16.dp))
            .padding(20.dp)
    ) {
        Text(
            text = "ℹ️ How to use VoxShield",
            fontSize = 15.sp,
            fontWeight = FontWeight.SemiBold,
            color = VoxColors.TextPrimary
        )
        Spacer(modifier = Modifier.height(12.dp))
        listOf(
            "1. Tap the shield to start protection",
            "2. When a suspicious call comes in, tap the speakerphone button on your phone",
            "3. VoxShield will begin analyzing the call audio in real time",
            "4. Watch for the fraud score — we'll alert you if it looks like a scam"
        ).forEach { step ->
            Row(modifier = Modifier.padding(vertical = 3.dp)) {
                Text(step, color = VoxColors.TextSecondary, fontSize = 13.sp, lineHeight = 20.sp)
            }
        }
        Spacer(modifier = Modifier.height(12.dp))
        Text(
            text = "⚠️ Protection requires speakerphone — Android doesn't allow apps to tap call audio directly.",
            fontSize = 12.sp,
            color = VoxColors.TextMuted,
            lineHeight = 18.sp
        )
    }
}

@Composable
private fun SettingsBottomSheet(
    currentUrl: String,
    promptOnUnknownOnly: Boolean,
    onUrlChange: (String) -> Unit,
    onSave: () -> Unit,
    onDismiss: () -> Unit,
    onSetPromptUnknownOnly: (Boolean) -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.6f))
            .clickable(onClick = onDismiss),
        contentAlignment = Alignment.BottomCenter
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp))
                .background(VoxColors.SurfaceCard)
                .padding(24.dp)
                .clickable(enabled = false) {}
        ) {
            Text("Settings", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = VoxColors.TextPrimary)
            Spacer(modifier = Modifier.height(20.dp))
            Text("Backend WebSocket URL", fontSize = 13.sp, color = VoxColors.TextMuted)
            Spacer(modifier = Modifier.height(8.dp))
            OutlinedTextField(
                value = currentUrl,
                onValueChange = onUrlChange,
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = VoxColors.Accent,
                    focusedTextColor = VoxColors.TextPrimary,
                    unfocusedTextColor = VoxColors.TextSecondary
                )
            )
            Spacer(modifier = Modifier.height(20.dp))

            // ── Unknown-caller prompting toggle ────────────────────────────
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Only prompt for unknown callers",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Medium,
                        color = VoxColors.TextPrimary
                    )
                    Text(
                        text = "Show Start Protection only when the caller isn't in your contacts",
                        fontSize = 11.sp,
                        color = VoxColors.TextMuted,
                        lineHeight = 16.sp
                    )
                }
                Switch(
                    checked = promptOnUnknownOnly,
                    onCheckedChange = onSetPromptUnknownOnly,
                    colors = SwitchDefaults.colors(checkedThumbColor = VoxColors.Accent)
                )
            }

            Spacer(modifier = Modifier.height(20.dp))
            Button(
                onClick = onSave,
                modifier = Modifier.fillMaxWidth().height(48.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = VoxColors.Accent)
            ) {
                Text("Save", color = Color(0xFF001524), fontWeight = FontWeight.Bold)
            }
            Spacer(modifier = Modifier.height(16.dp))
        }
    }
}

// ─── Helper: start/stop service ──────────────────────────────────────────────

private fun toggleProtection(context: Context, isActive: Boolean, backendUrl: String) {
    val serviceIntent = Intent(context, VoxShieldForegroundService::class.java).apply {
        action = if (isActive) VoxShieldForegroundService.ACTION_STOP
                 else          VoxShieldForegroundService.ACTION_START
        putExtra(VoxShieldForegroundService.EXTRA_BACKEND_URL, backendUrl)
    }
    if (isActive) {
        context.stopService(serviceIntent)
    } else {
        context.startForegroundService(serviceIntent)
    }
}
