package com.voxshield.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

// ─── Color palette ─────────────────────────────────────────────────────────
// Premium dark-mode palette — deep navy/slate backgrounds, electric teal accent

object VoxColors {
    // Backgrounds
    val Background       = Color(0xFF0A0F1E)   // Very deep navy
    val SurfaceCard      = Color(0xFF111827)   // Slightly lighter card
    val SurfaceElevated  = Color(0xFF1E2A3A)   // Elevated content areas

    // Brand accent — electric teal/cyan
    val Accent           = Color(0xFF00D4FF)
    val AccentDim        = Color(0xFF0090B0)
    val AccentGlow       = Color(0x3300D4FF)   // 20% opacity glow

    // Semantic states
    val Safe             = Color(0xFF22C55E)   // Green
    val SafeDim          = Color(0xFF166534)
    val Suspicious       = Color(0xFFF59E0B)   // Amber
    val SuspiciousDim    = Color(0xFF92400E)
    val Scam             = Color(0xFFEF4444)   // Red
    val ScamDim          = Color(0xFF991B1B)
    val ScamGlow         = Color(0x40EF4444)

    // Text
    val TextPrimary      = Color(0xFFF1F5F9)
    val TextSecondary    = Color(0xFF94A3B8)
    val TextMuted        = Color(0xFF475569)

    // Waveform bars
    val WaveformActive   = Color(0xFF00D4FF)
    val WaveformInactive = Color(0xFF1E3A4A)

    // Borders
    val Border           = Color(0xFF1E2D45)
    val BorderAccent     = Color(0xFF0A4D68)
}

val VoxColorScheme = darkColorScheme(
    primary          = VoxColors.Accent,
    onPrimary        = Color(0xFF001524),
    primaryContainer = VoxColors.AccentDim,
    secondary        = VoxColors.Safe,
    background       = VoxColors.Background,
    surface          = VoxColors.SurfaceCard,
    onBackground     = VoxColors.TextPrimary,
    onSurface        = VoxColors.TextPrimary,
    error            = VoxColors.Scam
)

// ─── Typography ────────────────────────────────────────────────────────────

object VoxType {
    val DisplayLarge = TextStyle(
        fontSize = 32.sp,
        fontWeight = FontWeight.Bold,
        letterSpacing = (-0.5).sp,
        color = VoxColors.TextPrimary
    )
    val Headline = TextStyle(
        fontSize = 22.sp,
        fontWeight = FontWeight.SemiBold,
        color = VoxColors.TextPrimary
    )
    val Body = TextStyle(
        fontSize = 15.sp,
        fontWeight = FontWeight.Normal,
        color = VoxColors.TextSecondary,
        lineHeight = 22.sp
    )
    val Caption = TextStyle(
        fontSize = 12.sp,
        fontWeight = FontWeight.Medium,
        color = VoxColors.TextMuted,
        letterSpacing = 0.4.sp
    )
    val Label = TextStyle(
        fontSize = 13.sp,
        fontWeight = FontWeight.SemiBold,
        letterSpacing = 0.2.sp,
        color = VoxColors.TextPrimary
    )
}

// ─── Theme wrapper ──────────────────────────────────────────────────────────

@Composable
fun VoxShieldTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = VoxColorScheme,
        content = content
    )
}
