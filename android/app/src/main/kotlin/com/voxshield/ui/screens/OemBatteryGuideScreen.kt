package com.voxshield.ui.screens

import android.app.Activity
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.voxshield.oem.OemBatteryOptimizationHelper
import com.voxshield.ui.theme.VoxColors

/**
 * OemBatteryGuideScreen — shown after permissions when a restrictive OEM is detected.
 *
 * Explains, in device-specific language, how to allowlist VoxShield in the OEM's
 * battery manager / autostart settings so the foreground service is not killed
 * during long calls.
 *
 * Why this matters:
 *   OEM battery managers (Xiaomi MIUI, Oppo ColorOS, Vivo FuntouchOS, Huawei EMUI,
 *   Samsung OneUI) can kill even foreground services with persistent notifications
 *   if the app is not explicitly allowlisted. This is a well-documented issue
 *   (see dontkillmyapp.com) that affects all background-critical apps.
 *
 * The "Go to Settings" button attempts to deep-link to the exact OEM settings page;
 * falls back to AOSP battery optimization dialog or App Info if unavailable.
 *
 * @param onContinue Called after settings have been opened or user taps Skip
 */
@Composable
fun OemBatteryGuideScreen(onContinue: () -> Unit) {
    val context = LocalContext.current
    val activity = context as? Activity
    val profile = remember { OemBatteryOptimizationHelper.detectOemProfile() }
    val instructions = remember { OemBatteryOptimizationHelper.getInstructions(context) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(VoxColors.Background)
            .padding(horizontal = 24.dp)
            .verticalScroll(rememberScrollState()),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Spacer(modifier = Modifier.height(64.dp))

        Text("⚙️", fontSize = 56.sp)
        Spacer(modifier = Modifier.height(20.dp))

        Text(
            text = "One More Step",
            fontSize = 26.sp,
            fontWeight = FontWeight.Bold,
            color = VoxColors.TextPrimary,
            textAlign = TextAlign.Center
        )
        Spacer(modifier = Modifier.height(8.dp))

        profile?.let {
            Text(
                text = "${it.manufacturerName} device detected",
                fontSize = 13.sp,
                color = VoxColors.Accent,
                fontWeight = FontWeight.SemiBold
            )
        }

        Spacer(modifier = Modifier.height(20.dp))

        Text(
            text = "${profile?.manufacturerName ?: "Your device"}'s battery manager " +
                    "can stop background apps — including VoxShield — even when a foreground " +
                    "service is running. To ensure protection stays active during calls, " +
                    "you need to allowlist VoxShield in your battery settings.",
            fontSize = 14.sp,
            color = VoxColors.TextSecondary,
            textAlign = TextAlign.Center,
            lineHeight = 22.sp
        )

        Spacer(modifier = Modifier.height(24.dp))

        // Instruction card
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(VoxColors.SurfaceElevated)
                .border(1.dp, VoxColors.Border, RoundedCornerShape(16.dp))
                .padding(20.dp)
        ) {
            Column {
                Text(
                    text = "📋 Instructions",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = VoxColors.Accent
                )
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = instructions,
                    fontSize = 13.sp,
                    color = VoxColors.TextSecondary,
                    lineHeight = 20.sp
                )
            }
        }

        Spacer(modifier = Modifier.height(32.dp))

        // Primary CTA: deep-link to OEM settings
        Button(
            onClick = {
                activity?.let { OemBatteryOptimizationHelper.launchBatterySettings(it) }
                onContinue()
            },
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp),
            shape = RoundedCornerShape(16.dp),
            colors = ButtonDefaults.buttonColors(containerColor = VoxColors.Accent)
        ) {
            Text(
                text = "Go to Battery Settings",
                color = Color(0xFF001524),
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        // Secondary: skip
        TextButton(onClick = onContinue) {
            Text(
                text = "Skip — I'll do this later",
                color = VoxColors.TextMuted,
                fontSize = 14.sp
            )
        }

        Spacer(modifier = Modifier.height(48.dp))
    }
}
