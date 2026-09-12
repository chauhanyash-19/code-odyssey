package com.voxshield.service

import android.app.Notification
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Binder
import android.os.Build
import android.os.IBinder
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.content.Context
import android.util.Log
import androidx.core.app.NotificationCompat
import com.voxshield.MainActivity
import com.voxshield.VoxShieldApplication.Companion.CHANNEL_ALERTS
import com.voxshield.VoxShieldApplication.Companion.CHANNEL_PROTECTION
import com.voxshield.audio.AudioCaptureManager
import com.voxshield.call.CallStateObserver
import com.voxshield.call.ContactLookupHelper
import com.voxshield.call.VoxCallState
import com.voxshield.model.BackendMessage
import com.voxshield.model.PdiVerdict
import com.voxshield.network.CallWebSocketClient
import com.voxshield.network.WsConnectionState
import com.voxshield.util.PermissionUtils
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.util.UUID

private const val TAG = "VoxShield.Service"
private const val NOTIFICATION_ID_PROTECTION = 1001
private const val NOTIFICATION_ID_ALERT = 1002
private const val HEARTBEAT_INTERVAL_MS = 30_000L

// Default backend URL — user can override in Settings
const val DEFAULT_BACKEND_WS_URL = "wss://deviant-park-emacs-bars.trycloudflare.com"

/**
 * VoxShieldForegroundService — the persistent foreground service that:
 *
 *  1. Shows a permanent notification: "🛡️ VoxShield protection active — tap to stop"
 *  2. Owns [AudioCaptureManager] (AudioRecord lifecycle)
 *  3. Owns [CallWebSocketClient] (streaming to backend)
 *  4. Owns [CallStateObserver] (call state + speaker detection)
 *  5. Wires audio frames → WebSocket in a coroutine
 *  6. Sends a 30-second heartbeat broadcast; [ServiceHeartbeatReceiver] watches
 *     for missed heartbeats and fires a "protection stopped" alert notification
 *
 * ──────────────────────────────────────────────────────────────────────────────
 * Foreground service type: "microphone" (mandatory on API 34+)
 * ──────────────────────────────────────────────────────────────────────────────
 * Declared in AndroidManifest.xml as:
 *   android:foregroundServiceType="microphone"
 *
 * And at runtime (API 29+) startForeground() is called with
 *   ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
 * so the OS knows this service uses the mic and keeps it alive accordingly.
 *
 * This does NOT grant any special access to call audio. It simply:
 *   a) Prevents Android from killing the process while protection is active
 *   b) Satisfies API 34+ enforcement of foreground service types
 * ──────────────────────────────────────────────────────────────────────────────
 *
 * Binding:
 *   Activities bind to this service via [LocalBinder] to receive live state
 *   (connection status, PDI score, call state) without polling.
 */
class VoxShieldForegroundService : Service() {

    // ─── Binder (for MainActivity to receive live state) ──────────────────────

    inner class LocalBinder : Binder() {
        val service get() = this@VoxShieldForegroundService
    }

    private val binder = LocalBinder()

    // ─── Live state exposed to bound activities ───────────────────────────────

    private val _protectionState = MutableStateFlow(ProtectionState())
    val protectionState: StateFlow<ProtectionState> = _protectionState.asStateFlow()

    // ─── Core components ──────────────────────────────────────────────────────

    private lateinit var audioCapture: AudioCaptureManager
    private lateinit var callObserver: CallStateObserver
    private var wsClient: CallWebSocketClient? = null
    private var callId: String = UUID.randomUUID().toString()

    // ─── Coroutine scope ──────────────────────────────────────────────────────

    private val serviceScope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    private var audioStreamJob: Job? = null
    private var messageListenerJob: Job? = null
    private var callStateListenerJob: Job? = null
    private var heartbeatJob: Job? = null
    private var vibrationJob: Job? = null

    // ─── Service lifecycle ────────────────────────────────────────────────────

    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "VoxShieldForegroundService onCreate")
        audioCapture = AudioCaptureManager()
        callObserver = CallStateObserver(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> startProtection(intent)
            ACTION_STOP  -> stopProtection()
            else         -> startProtection(intent)
        }
        return START_STICKY  // System will restart this service if killed
    }

    override fun onBind(intent: Intent): IBinder = binder

    override fun onDestroy() {
        super.onDestroy()
        Log.i(TAG, "VoxShieldForegroundService onDestroy")
        stopProtectionInternal()
        serviceScope.cancel()
    }

    // ─── Protection start/stop ────────────────────────────────────────────────

    private fun startProtection(intent: Intent?) {
        val backendUrl = intent?.getStringExtra(EXTRA_BACKEND_URL) ?: DEFAULT_BACKEND_WS_URL
        callId = UUID.randomUUID().toString()

        Log.i(TAG, "Starting protection | callId=$callId | backend=$backendUrl")

        // 1. Promote to foreground (required BEFORE starting AudioRecord on API 34+)
        val notification = buildProtectionNotification()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NOTIFICATION_ID_PROTECTION,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
            )
        } else {
            startForeground(NOTIFICATION_ID_PROTECTION, notification)
        }

        // 2. Register call state observer (needs phone state permission)
        if (PermissionUtils.hasPhoneState(this)) {
            @Suppress("MissingPermission")
            callObserver.register()
        }

        // 3. Connect WebSocket
        wsClient = CallWebSocketClient(backendUrl, callId).also { it.connect() }

        // 4. Start audio capture (needs RECORD_AUDIO permission)
        if (PermissionUtils.hasRecordAudio(this)) {
            @Suppress("MissingPermission")
            audioCapture.start()
        }

        // 5. Wire: audio frames → WebSocket
        wireAudioToWebSocket()

        // 6. Wire: backend messages → state
        listenToBackendMessages()

        // 7. Wire: call state → service state
        listenToCallState()

        // 8. Start heartbeat
        startHeartbeat()

        _protectionState.value = _protectionState.value.copy(isProtectionActive = true, callId = callId)
        saveProtectionEnabled(true)
        Log.i(TAG, "Protection started successfully")
    }

    private fun stopProtection() {
        Log.i(TAG, "Stopping protection (user request)")
        stopProtectionInternal()
        stopSelf()
    }

    private fun stopProtectionInternal() {
        heartbeatJob?.cancel()
        audioStreamJob?.cancel()
        messageListenerJob?.cancel()
        callStateListenerJob?.cancel()
        audioCapture.stop()
        wsClient?.disconnect()
        callObserver.unregister()
        _protectionState.value = ProtectionState() // Reset to defaults
        saveProtectionEnabled(false)
        stopForeground(STOP_FOREGROUND_REMOVE)
    }

    // ─── Coroutine wiring ─────────────────────────────────────────────────────

    /** Forwards each 640-byte PCM chunk from AudioRecord → WebSocket binary frame. */
    private fun wireAudioToWebSocket() {
        audioStreamJob?.cancel()
        audioStreamJob = serviceScope.launch {
            audioCapture.audioFrames.collect { pcmChunk ->
                wsClient?.sendAudioFrame(pcmChunk)
            }
        }
    }

    /** Deserializes incoming backend JSON messages and updates protectionState. */
    private fun listenToBackendMessages() {
        messageListenerJob?.cancel()
        val client = wsClient ?: return
        messageListenerJob = serviceScope.launch {
            launch {
                client.connectionState.collect { connState ->
                    _protectionState.value = _protectionState.value.copy(
                        wsConnectionState = connState
                    )
                    updateNotification()
                }
            }
            launch {
                client.messages.collect { message ->
                    when (message) {
                        is BackendMessage.PdiUpdate -> {
                            val verdict = PdiVerdict.from(message.verdict)
                            _protectionState.value = _protectionState.value.copy(
                                pdiScore = message.pdiScore,
                                verdict = verdict
                            )
                            updateNotification()
                        }
                        is BackendMessage.FactCheckUpdate -> {
                            val msg = message.verdictMessage ?: ""
                            _protectionState.value = _protectionState.value.copy(
                                factcheckStatus = message.status,
                                latestVerdictMessage = msg
                            )
                            if (message.status == "CRITICAL") {
                                triggerCriticalVibration()
                                showScamAlertNotification(message.confidence, msg.ifEmpty { "Scam Detected" })
                            } else if (message.status == "SAFE") {
                                cancelVibration()
                            }
                            updateNotification()
                        }
                        is BackendMessage.ModeUpdate -> {
                            _protectionState.value = _protectionState.value.copy(
                                isLimitedMode = message.mode == "limited"
                            )
                            updateNotification()
                        }
                        is BackendMessage.TranscriptChunk -> {
                            _protectionState.value = _protectionState.value.copy(
                                latestTranscript = message.text
                            )
                        }
                        else -> { /* Other message types handled by UI layer */ }
                    }
                }
            }
        }
    }

    /** Observes call state and speakerphone to update the protection state. */
    private fun listenToCallState() {
        // Load the "prompt for unknown only" preference (default true)
        val promptOnUnknownOnly = getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
            .getBoolean(PREF_PROMPT_UNKNOWN_ONLY, true)
        _protectionState.value = _protectionState.value.copy(promptOnUnknownOnly = promptOnUnknownOnly)

        callStateListenerJob?.cancel()
        callStateListenerJob = serviceScope.launch {
            launch {
                callObserver.callState.collect { state ->
                    _protectionState.value = _protectionState.value.copy(callState = state)
                }
            }
            launch {
                callObserver.isSpeakerOn.collect { speakerOn ->
                    _protectionState.value = _protectionState.value.copy(isSpeakerOn = speakerOn)
                    updateNotification()
                }
            }
            // Contact lookup: when ringing, check if caller is a known contact
            launch {
                callObserver.incomingNumber.collect { number ->
                    val isKnown = ContactLookupHelper.isKnownContact(this@VoxShieldForegroundService, number)
                    _protectionState.value = _protectionState.value.copy(isKnownContact = isKnown)
                    Log.d(TAG, "Contact lookup result for ${number ?: "<null>"}: isKnown=$isKnown")
                }
            }
        }
    }

    /** Persist the "prompt for unknown callers only" user preference. */
    fun setPromptOnUnknownOnly(enabled: Boolean) {
        getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
            .edit().putBoolean(PREF_PROMPT_UNKNOWN_ONLY, enabled).apply()
        _protectionState.value = _protectionState.value.copy(promptOnUnknownOnly = enabled)
    }


    // ─── Alert Management ─────────────────────────────────────────────────────

    fun dismissAlert() {
        _protectionState.value = _protectionState.value.copy(
            factcheckStatus = "SAFE",
            latestVerdictMessage = ""
        )
        cancelVibration()
        updateNotification()
    }

    // ─── Vibration ────────────────────────────────────────────────────────────

    private fun triggerCriticalVibration() {
        // Prevent overlapping jobs
        if (vibrationJob?.isActive == true) return
        
        val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val vibratorManager = getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
            vibratorManager.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        }

        if (!vibrator.hasVibrator()) return

        val timings = longArrayOf(0, 200, 100, 400, 100, 800)
        val amplitudes = intArrayOf(0, 255, 0, 255, 0, 255)
        val effect = VibrationEffect.createWaveform(timings, amplitudes, 0) // 0 = repeat indefinitely

        vibrator.vibrate(effect)

        // Safety cap: Automatically stop vibration after 15 seconds to save battery/annoyance
        vibrationJob = serviceScope.launch {
            delay(15_000L)
            cancelVibration()
        }
    }

    private fun cancelVibration() {
        vibrationJob?.cancel()
        vibrationJob = null
        val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val vibratorManager = getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
            vibratorManager.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        }
        vibrator.cancel()
    }

    // ─── Heartbeat (watchdog) ─────────────────────────────────────────────────

    /**
     * Sends a heartbeat broadcast every 30 seconds.
     * [ServiceHeartbeatReceiver] tracks these and fires an alert notification
     * if a heartbeat is missed (indicating the service was killed by the OS/OEM).
     */
    private fun startHeartbeat() {
        heartbeatJob?.cancel()
        heartbeatJob = serviceScope.launch {
            while (isActive) {
                delay(HEARTBEAT_INTERVAL_MS)
                sendBroadcast(Intent(ACTION_HEARTBEAT).apply {
                    setPackage(packageName)
                })
            }
        }
    }

    // ─── Notifications ────────────────────────────────────────────────────────

    private fun buildProtectionNotification(): Notification {
        val state = _protectionState.value
        val speakerText = when {
            state.callState == VoxCallState.OFFHOOK && !state.isSpeakerOn ->
                "🔊 Turn on speaker to protect this call"
            state.callState == VoxCallState.OFFHOOK && state.isSpeakerOn ->
                "🎙️ Listening — PDI ${(state.pdiScore * 100).toInt()}%"
            else -> "Protection active — waiting for a call"
        }

        val stopIntent = PendingIntent.getService(
            this, 0,
            Intent(this, VoxShieldForegroundService::class.java).apply { action = ACTION_STOP },
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val openAppIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        return NotificationCompat.Builder(this, CHANNEL_PROTECTION)
            .setSmallIcon(android.R.drawable.ic_lock_idle_lock)
            .setContentTitle("🛡️ VoxShield protection active")
            .setContentText(speakerText)
            .setContentIntent(openAppIntent)
            .addAction(android.R.drawable.ic_delete, "Stop", stopIntent)
            .setOngoing(true)       // Cannot be dismissed by user swipe
            .setSilent(true)        // No sound/vibration on update
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
            .build()
    }

    private fun updateNotification() {
        val nm = getSystemService(NotificationManager::class.java)
        nm.notify(NOTIFICATION_ID_PROTECTION, buildProtectionNotification())
    }

    private fun showScamAlertNotification(score: Float, reason: String) {
        val openIntent = PendingIntent.getActivity(
            this, 1,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        val notification = NotificationCompat.Builder(this, CHANNEL_ALERTS)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("🚨 Scam Alert — ${(score * 100).toInt()}% fraud probability")
            .setContentText(reason)
            .setContentIntent(openIntent)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .build()
        getSystemService(NotificationManager::class.java)
            .notify(NOTIFICATION_ID_ALERT, notification)
    }

    // ─── SharedPreferences persistence ───────────────────────────────────────

    private fun saveProtectionEnabled(enabled: Boolean) {
        getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
            .edit().putBoolean(PREF_PROTECTION_ENABLED, enabled).apply()
    }

    companion object {
        const val ACTION_START = "com.voxshield.action.START"
        const val ACTION_STOP  = "com.voxshield.action.STOP"
        const val ACTION_HEARTBEAT = "com.voxshield.action.HEARTBEAT"
        const val EXTRA_BACKEND_URL = "backend_ws_url"
        const val PREFS_NAME = "voxshield_prefs"
        const val PREF_PROTECTION_ENABLED = "protection_enabled"
        const val PREF_BACKEND_URL = "backend_ws_url"
        const val PREF_ONBOARDING_DONE = "onboarding_complete"
        const val PREF_PROMPT_UNKNOWN_ONLY = "prompt_unknown_only"  // default true
    }
}

// ─── Protection state data class ──────────────────────────────────────────────

data class ProtectionState(
    val isProtectionActive: Boolean = false,
    val callId: String = "",
    val callState: VoxCallState = VoxCallState.IDLE,
    val isSpeakerOn: Boolean = false,
    val pdiScore: Float = 0f,
    val verdict: PdiVerdict = PdiVerdict.UNKNOWN,
    val wsConnectionState: WsConnectionState = WsConnectionState.Disconnected,
    val latestTranscript: String = "",
    val factcheckStatus: String = "SAFE",
    val latestVerdictMessage: String = "",
    val isLimitedMode: Boolean = false,
    /** True if the current caller's number is found in the user's saved contacts. */
    val isKnownContact: Boolean = false,
    /**
     * User setting: only show the prominent 'Start Protection' prompt for unknown callers.
     * Default true. When false, prompt shows for every incoming call.
     * Loaded from SharedPreferences; can be toggled in the Settings sheet.
     */
    val promptOnUnknownOnly: Boolean = true,
)
