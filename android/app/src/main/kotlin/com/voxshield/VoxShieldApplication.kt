package com.voxshield

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build

/**
 * VoxShieldApplication — Application subclass.
 *
 * Creates notification channels at startup so they are always available
 * before any Service or Activity tries to post a notification. Channel
 * creation is idempotent — safe to call on every app launch.
 */
class VoxShieldApplication : Application() {

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return

        val notificationManager = getSystemService(NotificationManager::class.java)

        // --- Primary protection channel (silent, persistent) ---
        val protectionChannel = NotificationChannel(
            CHANNEL_PROTECTION,
            "VoxShield Protection",
            NotificationManager.IMPORTANCE_LOW          // Silent — no sound/vibration
        ).apply {
            description = "Persistent notification shown while VoxShield protection is active"
            setShowBadge(false)
            enableVibration(false)
            enableLights(false)
        }

        // --- Alert channel (for "protection stopped" and warnings) ---
        val alertChannel = NotificationChannel(
            CHANNEL_ALERTS,
            "VoxShield Alerts",
            NotificationManager.IMPORTANCE_HIGH         // Heads-up notification
        ).apply {
            description = "Alerts when VoxShield protection stops unexpectedly"
            enableVibration(true)
        }

        notificationManager.createNotificationChannels(listOf(protectionChannel, alertChannel))
    }

    companion object {
        const val CHANNEL_PROTECTION = "voxshield_protection"
        const val CHANNEL_ALERTS = "voxshield_alerts"
    }
}
