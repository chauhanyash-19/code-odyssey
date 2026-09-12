package com.voxshield.service

import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.SystemClock
import android.util.Log
import androidx.core.app.NotificationCompat
import com.voxshield.MainActivity
import com.voxshield.VoxShieldApplication.Companion.CHANNEL_ALERTS

private const val TAG = "VoxShield.Receiver"
private const val HEARTBEAT_TIMEOUT_MS = 90_000L  // 3 missed heartbeats @ 30s = service dead
private const val NOTIFICATION_ID_STOPPED = 1003

/**
 * ServiceHeartbeatReceiver — dual-purpose BroadcastReceiver:
 *
 * 1. BOOT_COMPLETED: If protection was enabled before reboot, restart the service.
 *    This ensures VoxShield comes back automatically after device restart without
 *    requiring the user to manually reopen the app.
 *
 * 2. HEARTBEAT action: Tracks timestamps of heartbeat broadcasts sent by
 *    [VoxShieldForegroundService] every 30 seconds. If a heartbeat is missed for
 *    more than [HEARTBEAT_TIMEOUT_MS], the service has been killed (OEM battery
 *    manager or system resource pressure). In that case, fire a "protection stopped"
 *    heads-up notification so the failure is visible rather than silent.
 *
 * 3. PROTECTION_STOPPED: Explicit stop signal sent by the service on clean shutdown.
 *    Resets the watchdog timer and clears the "stopped" notification.
 */
class ServiceHeartbeatReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            Intent.ACTION_BOOT_COMPLETED    -> handleBoot(context)
            VoxShieldForegroundService.ACTION_HEARTBEAT -> handleHeartbeat(context)
            "com.voxshield.action.PROTECTION_STOPPED"   -> handleProtectionStopped(context)
        }
    }

    // ─── Boot handling ────────────────────────────────────────────────────────

    private fun handleBoot(context: Context) {
        val prefs = context.getSharedPreferences(
            VoxShieldForegroundService.PREFS_NAME, Context.MODE_PRIVATE
        )
        val wasEnabled = prefs.getBoolean(VoxShieldForegroundService.PREF_PROTECTION_ENABLED, false)
        val backendUrl = prefs.getString(
            VoxShieldForegroundService.PREF_BACKEND_URL,
            DEFAULT_BACKEND_WS_URL
        ) ?: DEFAULT_BACKEND_WS_URL

        if (wasEnabled) {
            Log.i(TAG, "Boot received — protection was active, restarting service")
            val serviceIntent = Intent(context, VoxShieldForegroundService::class.java).apply {
                action = VoxShieldForegroundService.ACTION_START
                putExtra(VoxShieldForegroundService.EXTRA_BACKEND_URL, backendUrl)
            }
            context.startForegroundService(serviceIntent)
        } else {
            Log.d(TAG, "Boot received — protection was not active, no action needed")
        }
    }

    // ─── Heartbeat watchdog ───────────────────────────────────────────────────

    private fun handleHeartbeat(context: Context) {
        lastHeartbeatMs = SystemClock.elapsedRealtime()
        Log.v(TAG, "Heartbeat received at $lastHeartbeatMs")

        // Cancel any "stopped" notification that may have been shown
        context.getSystemService(NotificationManager::class.java)
            .cancel(NOTIFICATION_ID_STOPPED)
    }

    private fun handleProtectionStopped(context: Context) {
        Log.i(TAG, "Protection cleanly stopped — resetting watchdog")
        lastHeartbeatMs = 0L
        context.getSystemService(NotificationManager::class.java)
            .cancel(NOTIFICATION_ID_STOPPED)
    }

    companion object {
        @Volatile private var lastHeartbeatMs = 0L

        /**
         * Called by a periodic alarm or WorkManager task (if added later) to check
         * whether the service is still alive. Alternatively, this can be called from
         * [handleHeartbeat] with a delayed check using a Handler — but a simpler and
         * battery-friendlier approach is to check from an alarm that fires every 60s.
         *
         * For the MVP, the "protection stopped" notification is shown from here when
         * a heartbeat timestamp check detects the service has gone silent.
         */
        fun checkAndNotifyIfDead(context: Context) {
            if (lastHeartbeatMs == 0L) return  // Protection not yet started
            val elapsed = SystemClock.elapsedRealtime() - lastHeartbeatMs
            if (elapsed > HEARTBEAT_TIMEOUT_MS) {
                Log.w(TAG, "Heartbeat timeout (${elapsed}ms) — service appears dead")
                showStoppedNotification(context)
            }
        }

        private fun showStoppedNotification(context: Context) {
            val restartIntent = PendingIntent.getActivity(
                context, 0,
                Intent(context, MainActivity::class.java),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
            )
            val notification = NotificationCompat.Builder(context, CHANNEL_ALERTS)
                .setSmallIcon(android.R.drawable.ic_dialog_alert)
                .setContentTitle("⚠️ VoxShield protection stopped")
                .setContentText("Tap to restart and check your battery settings.")
                .setContentIntent(restartIntent)
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .build()

            context.getSystemService(NotificationManager::class.java)
                .notify(NOTIFICATION_ID_STOPPED, notification)
        }
    }
}
