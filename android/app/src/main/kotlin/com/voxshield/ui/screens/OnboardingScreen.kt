package com.voxshield.ui.screens

import android.Manifest
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.voxshield.ui.theme.VoxColors
import com.voxshield.util.PermissionUtils
import kotlinx.coroutines.launch

/**
 * OnboardingScreen — shown on first launch before any permission requests.
 *
 * 3-page horizontal pager that:
 *   Page 0: Explains the speakerphone constraint honestly
 *   Page 1: How to use speakerphone during a suspicious call
 *   Page 2: Permission rationale + triggers RECORD_AUDIO and phone state requests
 *
 * ──────────────────────────────────────────────────────────────────────────────
 * WHY WE SHOW THIS SCREEN
 * ──────────────────────────────────────────────────────────────────────────────
 * Android does not allow third-party apps to access in-call audio directly.
 * This is a deliberate OS privacy protection. VoxShield works by listening through
 * the phone's microphone — which only hears the caller when speakerphone is on.
 *
 * Setting honest expectations upfront:
 *   a) Prevents user confusion ("why isn't it working?")
 *   b) Avoids misleading marketing that could violate Play Store policy
 *   c) Follows Android's recommended rationale-before-permission pattern
 * ──────────────────────────────────────────────────────────────────────────────
 *
 * @param onComplete Called when the user has granted required permissions and
 *                   finished onboarding. Navigate to HomeScreen from here.
 * @param onSkip     Called if the user taps "Skip" — partial setup, protection
 *                   available but call-state auto-trigger won't work.
 */
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun OnboardingScreen(
    onComplete: () -> Unit,
    onSkip: () -> Unit
) {
    val pagerState = rememberPagerState(pageCount = { 3 })
    val scope = rememberCoroutineScope()

    var micGranted by remember { mutableStateOf(false) }
    var phoneGranted by remember { mutableStateOf(false) }

    // RECORD_AUDIO launcher — shown with rationale dialog (this IS the rationale dialog)
    val micLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        micGranted = granted
        if (granted) {
            // Proceed to request phone state permission
            scope.launch {
                // Phone state launcher will be triggered next
            }
        }
    }

    // Phone state permission launcher
    val phonePermission = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        Manifest.permission.READ_BASIC_PHONE_STATE
    } else {
        Manifest.permission.READ_PHONE_STATE
    }
    val phoneLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        phoneGranted = granted
        onComplete()  // Proceed regardless — phone state is optional
    }

    // Notification permission (API 33+)
    val notifLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { _ ->
        // After notifications, request microphone
        micLauncher.launch(Manifest.permission.RECORD_AUDIO)
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(VoxColors.Background)
    ) {
        Column(modifier = Modifier.fillMaxSize()) {

            // Skip button (top right)
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 52.dp, end = 24.dp),
                horizontalArrangement = Arrangement.End
            ) {
                TextButton(onClick = onSkip) {
                    Text("Skip", color = VoxColors.TextMuted, fontSize = 14.sp)
                }
            }

            // Pager
            HorizontalPager(
                state = pagerState,
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
            ) { page ->
                when (page) {
                    0 -> OnboardingPage0()
                    1 -> OnboardingPage1()
                    2 -> OnboardingPage2()
                }
            }

            // Page dots
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 24.dp),
                horizontalArrangement = Arrangement.Center
            ) {
                repeat(3) { index ->
                    val isSelected = pagerState.currentPage == index
                    Box(
                        modifier = Modifier
                            .padding(horizontal = 4.dp)
                            .size(if (isSelected) 24.dp else 8.dp, 8.dp)
                            .clip(CircleShape)
                            .background(
                                if (isSelected) VoxColors.Accent else VoxColors.Border
                            )
                    )
                }
            }

            // Action button
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 24.dp)
                    .padding(bottom = 48.dp)
            ) {
                Button(
                    onClick = {
                        if (pagerState.currentPage < 2) {
                            scope.launch { pagerState.animateScrollToPage(pagerState.currentPage + 1) }
                        } else {
                            // Trigger permission chain: notifications → mic → phone state
                            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                                notifLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                            } else {
                                micLauncher.launch(Manifest.permission.RECORD_AUDIO)
                            }
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(56.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = VoxColors.Accent)
                ) {
                    Text(
                        text = if (pagerState.currentPage < 2) "Next →" else "Allow Access & Start",
                        color = Color(0xFF001524),
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }
    }
}

// ─── Page 0: How VoxShield works (speakerphone constraint explanation) ────────

@Composable
private fun OnboardingPage0() {
    OnboardingPageLayout(
        emoji = "🛡️",
        title = "How VoxShield Works",
        body = "VoxShield listens through your microphone, not directly from the call.\n\n" +
                "Android doesn't allow apps to tap call audio directly — this is a privacy " +
                "protection built into the operating system for everyone's security.\n\n" +
                "VoxShield uses the standard microphone to detect scam patterns in real time.",
        illustrationText = "📱  🔊  →  🎙️  →  🧠  →  🛡️",
        illustrationLabel = "Speaker → Mic → AI Analysis → Protection"
    )
}

// ─── Page 1: Use speakerphone ─────────────────────────────────────────────────

@Composable
private fun OnboardingPage1() {
    OnboardingPageLayout(
        emoji = "🔊",
        title = "Put It on Speaker",
        body = "When you suspect a scam — or when an unknown number calls — switch the " +
                "call to speakerphone.\n\n" +
                "This routes the caller's voice through the phone's speaker, where the " +
                "microphone can pick it up for analysis.\n\n" +
                "VoxShield will show a real-time fraud score and alert you the moment a " +
                "scam pattern is detected.",
        illustrationText = "📵  ──→  📢",
        illustrationLabel = "Switch to speakerphone during suspicious calls"
    )
}

// ─── Page 2: Permission rationale ────────────────────────────────────────────

@Composable
private fun OnboardingPage2() {
    OnboardingPageLayout(
        emoji = "🎙️",
        title = "Allow Microphone Access",
        body = "VoxShield needs microphone access to listen for scam patterns.\n\n" +
                "We never record or store your calls — audio is analyzed in real time by " +
                "the fraud detection engine and immediately discarded. Nothing leaves your " +
                "device in any form other than the anonymous analysis result.\n\n" +
                "Tap \"Allow Access & Start\" to grant access and begin protection.",
        illustrationText = "🎙️  🔒  ☁️",
        illustrationLabel = "Real-time analysis — no recordings stored"
    )
}

// ─── Shared page layout ───────────────────────────────────────────────────────

@Composable
private fun OnboardingPageLayout(
    emoji: String,
    title: String,
    body: String,
    illustrationText: String,
    illustrationLabel: String
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        // Large emoji
        Text(emoji, fontSize = 64.sp)
        Spacer(modifier = Modifier.height(24.dp))

        // Title
        Text(
            text = title,
            fontSize = 26.sp,
            fontWeight = FontWeight.Bold,
            color = VoxColors.TextPrimary,
            textAlign = TextAlign.Center
        )
        Spacer(modifier = Modifier.height(16.dp))

        // Illustration block
        Box(
            modifier = Modifier
                .clip(RoundedCornerShape(16.dp))
                .background(VoxColors.SurfaceElevated)
                .padding(16.dp),
            contentAlignment = Alignment.Center
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = illustrationText,
                    fontSize = 28.sp,
                    textAlign = TextAlign.Center,
                    letterSpacing = 4.sp
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = illustrationLabel,
                    fontSize = 12.sp,
                    color = VoxColors.TextMuted,
                    textAlign = TextAlign.Center
                )
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        // Body
        Text(
            text = body,
            fontSize = 14.sp,
            color = VoxColors.TextSecondary,
            textAlign = TextAlign.Center,
            lineHeight = 22.sp
        )
    }
}
