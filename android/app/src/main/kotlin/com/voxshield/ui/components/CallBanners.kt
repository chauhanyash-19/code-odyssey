package com.voxshield.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.foundation.clickable
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.voxshield.ui.theme.VoxColors

/**
 * SpeakerBanner — persistent high-visibility banner shown when:
 *   - A call is active (OFFHOOK state)
 *   - Speakerphone is OFF
 *
 * Prompts the user to switch to speakerphone so VoxShield can hear the caller.
 *
 * Design: amber/orange gradient with pulsing opacity — draws attention without
 * being intrusive. Slides in/out with animation as conditions change.
 *
 * @param visible  True when the banner should be shown
 */
@Composable
fun SpeakerBanner(
    visible: Boolean,
    modifier: Modifier = Modifier
) {
    // Pulsing opacity animation — draws attention
    val infiniteTransition = rememberInfiniteTransition(label = "speaker_pulse")
    val pulse by infiniteTransition.animateFloat(
        initialValue = 0.85f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 800),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse_alpha"
    )

    AnimatedVisibility(
        visible = visible,
        enter = slideInVertically { -it },
        exit = slideOutVertically { -it },
        modifier = modifier
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(
                    brush = Brush.horizontalGradient(
                        colors = listOf(
                            Color(0xFF92400E),   // Deep amber
                            Color(0xFF78350F)
                        )
                    )
                )
                .border(
                    width = 1.dp,
                    color = Color(0xFFF59E0B),
                    shape = RoundedCornerShape(12.dp)
                )
                .padding(horizontal = 16.dp, vertical = 12.dp)
                .alpha(pulse),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Start
        ) {
            Text(
                text = "🔊",
                fontSize = 20.sp
            )
            Spacer(modifier = Modifier.width(10.dp))
            Text(
                text = "Turn on speaker for VoxShield to protect this call",
                color = Color(0xFFFDE68A),
                fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold,
                lineHeight = 18.sp
            )
        }
    }
}

/**
 * ProtectionBanner — shown when call is active AND speakerphone is ON.
 * Displays shield icon, "VoxShield is listening" label, live waveform,
 * and the current PDI verdict chip.
 *
 * @param pdiScore   Current fraud probability (0.0–1.0)
 * @param verdictLabel  Human-readable verdict string ("Safe", "Suspicious", "Scam Detected")
 * @param amplitude  Live RMS amplitude for the embedded waveform
 * @param visible    True when the banner should be shown
 */
@Composable
fun ProtectionBanner(
    pdiScore: Float,
    verdictLabel: String,
    verdictEmoji: String,
    amplitude: Float,
    visible: Boolean,
    modifier: Modifier = Modifier
) {
    val verdictColor = when (verdictLabel.lowercase()) {
        "safe"           -> VoxColors.Safe
        "suspicious"     -> VoxColors.Suspicious
        "scam detected"  -> VoxColors.Scam
        else             -> VoxColors.Accent
    }

    AnimatedVisibility(
        visible = visible,
        enter = slideInVertically { -it },
        exit = slideOutVertically { -it },
        modifier = modifier
    ) {
        androidx.compose.foundation.layout.Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(
                    brush = Brush.verticalGradient(
                        colors = listOf(VoxColors.SurfaceElevated, VoxColors.SurfaceCard)
                    )
                )
                .border(
                    width = 1.dp,
                    color = VoxColors.AccentDim,
                    shape = RoundedCornerShape(12.dp)
                )
                .padding(16.dp)
        ) {
            // Header row
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(text = "🛡️", fontSize = 18.sp)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "VoxShield is listening",
                        color = VoxColors.Accent,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }
                // PDI verdict chip
                Row(
                    modifier = Modifier
                        .clip(RoundedCornerShape(20.dp))
                        .background(verdictColor.copy(alpha = 0.18f))
                        .border(1.dp, verdictColor.copy(alpha = 0.4f), RoundedCornerShape(20.dp))
                        .padding(horizontal = 10.dp, vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(text = verdictEmoji, fontSize = 13.sp)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = verdictLabel,
                        color = verdictColor,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }

            // PDI score bar
            androidx.compose.foundation.layout.Spacer(modifier = Modifier.size(10.dp))
            PDIScoreBar(score = pdiScore, color = verdictColor)

            // Live waveform
            androidx.compose.foundation.layout.Spacer(modifier = Modifier.size(8.dp))
            WaveformIndicator(
                amplitude = amplitude,
                isActive = true,
                modifier = Modifier.fillMaxWidth()
            )
        }
    }
}

/** Thin horizontal progress bar showing PDI fraud probability. */
@Composable
private fun PDIScoreBar(score: Float, color: Color) {
    androidx.compose.foundation.layout.Column {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text("Fraud Probability", color = VoxColors.TextMuted, fontSize = 11.sp)
            Text(
                "${(score * 100).toInt()}%",
                color = color,
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold
            )
        }
        androidx.compose.foundation.layout.Spacer(modifier = Modifier.size(4.dp))
        androidx.compose.foundation.layout.Box(
            modifier = Modifier
                .fillMaxWidth()
                .size(height = 4.dp, width = 0.dp)
                .clip(RoundedCornerShape(2.dp))
                .background(VoxColors.Border)
        ) {
            androidx.compose.foundation.layout.Box(
                modifier = Modifier
                    .fillMaxWidth(score.coerceIn(0f, 1f))
                    .size(height = 4.dp, width = 0.dp)
                    .clip(RoundedCornerShape(2.dp))
                    .background(
                        Brush.horizontalGradient(
                            colors = listOf(VoxColors.Safe, color)
                        )
                    )
            )
        }
    }
}

/**
 * ScamAlertBanner — high-priority red pulsing banner for CRITICAL factcheck results.
 * Includes a Dismiss action that allows the user to stop the vibration/alert locally.
 */
@Composable
fun ScamAlertBanner(
    visible: Boolean,
    message: String,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    val infiniteTransition = rememberInfiniteTransition(label = "scam_pulse")
    val pulse by infiniteTransition.animateFloat(
        initialValue = 0.85f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 600),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse_alpha_scam"
    )

    AnimatedVisibility(
        visible = visible,
        enter = slideInVertically { -it },
        exit = slideOutVertically { -it },
        modifier = modifier
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(
                    brush = Brush.horizontalGradient(
                        colors = listOf(
                            Color(0xFF7F1D1D),   // Deep red
                            Color(0xFF450A0A)
                        )
                    )
                )
                .border(
                    width = 1.dp,
                    color = Color(0xFFEF4444),
                    shape = RoundedCornerShape(12.dp)
                )
                .padding(16.dp)
                .alpha(pulse),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(
                modifier = Modifier.weight(1f),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(text = "⚠️", fontSize = 24.sp)
                Spacer(modifier = Modifier.width(12.dp))
                androidx.compose.foundation.layout.Column {
                    Text(
                        text = "Scam Detected",
                        color = Color(0xFFFCA5A5),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.size(2.dp))
                    Text(
                        text = message,
                        color = Color.White,
                        fontSize = 13.sp,
                        lineHeight = 18.sp
                    )
                }
            }
            TextButton(onClick = onDismiss) {
                Text("Dismiss", color = Color(0xFFFCA5A5), fontWeight = FontWeight.Bold)
            }
        }
    }
}

/**
 * LimitedModeBanner — shown when the backend enters LIMITED MODE (offline/fallback checks only).
 */
@Composable
fun LimitedModeBanner(
    visible: Boolean,
    modifier: Modifier = Modifier
) {
    AnimatedVisibility(
        visible = visible,
        enter = slideInVertically { -it },
        exit = slideOutVertically { -it },
        modifier = modifier
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(Color(0xFF1E293B))
                .border(
                    width = 1.dp,
                    color = Color(0xFF475569),
                    shape = RoundedCornerShape(12.dp)
                )
                .padding(horizontal = 16.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(text = "⚡", fontSize = 16.sp)
            Spacer(modifier = Modifier.width(10.dp))
            Text(
                text = "LIMITED MODE — Local protection checks only",
                color = Color(0xFFCBD5E1),
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium
            )
        }
    }
}

/**
 * UncertainBanner — gentler banner for UNCERTAIN factcheck results.
 */
@Composable
fun UncertainBanner(
    visible: Boolean,
    modifier: Modifier = Modifier
) {
    AnimatedVisibility(
        visible = visible,
        enter = slideInVertically { -it },
        exit = slideOutVertically { -it },
        modifier = modifier
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(Color(0xFF172554)) // Deep blue
                .border(
                    width = 1.dp,
                    color = Color(0xFF3B82F6),
                    shape = RoundedCornerShape(12.dp)
                )
                .padding(horizontal = 16.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(text = "🔍", fontSize = 16.sp)
            Spacer(modifier = Modifier.width(10.dp))
            Text(
                text = "Verifying claims…",
                color = Color(0xFFBFDBFE),
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium
            )
        }
    }
}
