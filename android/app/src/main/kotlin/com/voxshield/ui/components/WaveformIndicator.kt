package com.voxshield.ui.components

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.voxshield.ui.theme.VoxColors
import kotlin.math.sin

private const val BAR_COUNT = 20

/**
 * WaveformIndicator — live animated audio waveform composable.
 *
 * Renders [BAR_COUNT] vertical rounded bars whose heights are modulated by:
 *   a) [amplitude] — the live RMS amplitude from [AudioCaptureManager] (0.0–1.0)
 *   b) A sine-wave phase animation that makes bars "breathe" even at low amplitude
 *
 * When [isActive] is false (no call / speaker off), bars render at minimal height
 * with a dimmed color to indicate the capture is paused.
 *
 * @param amplitude  Normalised RMS amplitude from AudioCaptureManager.amplitude flow
 * @param isActive   True when AudioRecord is running and streaming
 * @param activeColor Bar fill color when active (defaults to teal accent)
 */
@Composable
fun WaveformIndicator(
    amplitude: Float,
    isActive: Boolean,
    modifier: Modifier = Modifier,
    activeColor: Color = VoxColors.WaveformActive,
    inactiveColor: Color = VoxColors.WaveformInactive
) {
    // Phase animation — creates the organic "wave" motion between bars
    val infiniteTransition = rememberInfiniteTransition(label = "waveform")
    val phase by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = (2 * Math.PI).toFloat(),
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "phase"
    )

    // Breathing pulse when idle (low amplitude)
    val idlePulse by infiniteTransition.animateFloat(
        initialValue = 0.05f,
        targetValue = 0.15f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1800, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "idle_pulse"
    )

    Canvas(
        modifier = modifier
            .fillMaxWidth()
            .height(48.dp)
    ) {
        val totalWidth = size.width
        val totalHeight = size.height
        val barWidth = (totalWidth / BAR_COUNT) * 0.6f
        val spacing = totalWidth / BAR_COUNT
        val cornerRadius = CornerRadius(barWidth / 2f)
        val minBarHeight = totalHeight * 0.08f
        val maxBarHeight = totalHeight * 0.9f

        for (i in 0 until BAR_COUNT) {
            val sineOffset = sin((i.toFloat() / BAR_COUNT) * 2 * Math.PI + phase).toFloat()
            val barAmplitude = if (isActive) {
                // Mix live amplitude with sine wave for organic look
                (amplitude * 0.7f + (sineOffset * 0.3f + 0.3f) * amplitude).coerceIn(0f, 1f)
            } else {
                // Gentle idle pulse when not active
                idlePulse * (0.5f + 0.5f * sin((i.toFloat() / BAR_COUNT) * Math.PI + phase).toFloat())
                    .coerceIn(0f, 1f)
            }

            val barHeight = (minBarHeight + barAmplitude * (maxBarHeight - minBarHeight))
                .coerceAtLeast(minBarHeight)
            val x = i * spacing + spacing / 2f - barWidth / 2f
            val y = (totalHeight - barHeight) / 2f

            drawRoundRect(
                color = if (isActive) activeColor else inactiveColor,
                topLeft = Offset(x, y),
                size = Size(barWidth, barHeight),
                cornerRadius = cornerRadius,
                alpha = if (isActive) 0.9f else 0.35f
            )
        }
    }
}
