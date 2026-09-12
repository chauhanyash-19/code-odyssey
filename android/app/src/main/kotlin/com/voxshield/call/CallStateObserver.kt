package com.voxshield.call

import android.content.Context
import android.media.AudioManager
import android.os.Build
import android.telephony.PhoneStateListener
import android.telephony.TelephonyCallback
import android.telephony.TelephonyManager
import android.util.Log
import androidx.annotation.RequiresApi
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
import java.util.concurrent.Executors

private const val TAG = "VoxShield.CallState"
private const val SPEAKER_POLL_INTERVAL_MS = 1_000L

/**
 * CallStateObserver — monitors phone call state and speakerphone status.
 *
 * ──────────────────────────────────────────────────────────────────────────────
 * IMPORTANT: What this class does and does NOT do
 * ──────────────────────────────────────────────────────────────────────────────
 * ✅ Reads call STATE (idle / ringing / off-hook) via TelephonyManager.
 *    This is explicitly permitted by Android for all apps.
 *
 * ✅ Reads speakerphone status via AudioManager.isSpeakerphoneOn().
 *    This is a non-privileged, non-dangerous API requiring no permission.
 *
 * ❌ Does NOT read caller ID, phone numbers, or any call content.
 * ❌ Does NOT capture or access in-call audio — that is AudioCaptureManager's
 *    job via the microphone, subject to the speakerphone constraint.
 *
 * ──────────────────────────────────────────────────────────────────────────────
 * API compatibility:
 *   API < 31  : PhoneStateListener (deprecated but functional)
 *   API >= 31 : TelephonyCallback (new preferred API)
 *
 * Permission requirement:
 *   READ_PHONE_STATE     : API 26–32 (runtime dangerous permission)
 *   READ_BASIC_PHONE_STATE : API 33+ (runtime permission — no carrier info)
 *
 * If the permission is denied, call state always reads IDLE and the observer
 * degrades gracefully — protection still works via manual start, but the
 * automatic "call detected → service activates" trigger won't function.
 * ──────────────────────────────────────────────────────────────────────────────
 */
class CallStateObserver(private val context: Context) {

    // ─── Exposed state flows ──────────────────────────────────────────────────

    private val _callState = MutableStateFlow(VoxCallState.IDLE)
    /** Current phone call state. Updated by TelephonyManager. */
    val callState: StateFlow<VoxCallState> = _callState.asStateFlow()

    private val _isSpeakerOn = MutableStateFlow(false)
    /** True if the phone speaker is currently active. Polled every 1s during calls. */
    val isSpeakerOn: StateFlow<Boolean> = _isSpeakerOn.asStateFlow()

    private val _incomingNumber = MutableStateFlow<String?>(null)
    /**
     * The phone number of the current incoming/active call, if available.
     *
     * ⚠️ On API 31+ this is always null — TelephonyCallback.CallStateListener does NOT
     * provide the caller number without READ_CALL_LOG (a restricted permission we don't use).
     * In that case we treat the caller as unknown (fail-open: protection prompt is always shown).
     *
     * On API 26–30 the legacy PhoneStateListener.onCallStateChanged() receives the number
     * when the phone rings, and we capture it here.
     *
     * Set to null when the call ends (IDLE).
     */
    val incomingNumber: StateFlow<String?> = _incomingNumber.asStateFlow()

    // ─── Internals ────────────────────────────────────────────────────────────

    private val scope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    private val telephonyManager = context.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager

    private var speakerPollJob: Job? = null
    private var legacyListener: LegacyPhoneStateListener? = null
    private var modernCallback: ModernTelephonyCallback? = null

    // ─── Registration ─────────────────────────────────────────────────────────

    /**
     * Start observing. Requires READ_PHONE_STATE or READ_BASIC_PHONE_STATE
     * to have been granted. Call from within the foreground service.
     */
    @Suppress("MissingPermission")
    fun register() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            // API 31+: TelephonyCallback (non-deprecated path)
            registerModernCallback()
        } else {
            // API 26–30: PhoneStateListener (deprecated but still functional)
            @Suppress("DEPRECATION")
            registerLegacyListener()
        }
        startSpeakerPolling()
        Log.i(TAG, "CallStateObserver registered (API ${Build.VERSION.SDK_INT})")
    }

    fun unregister() {
        stopSpeakerPolling()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            modernCallback?.let { telephonyManager.unregisterTelephonyCallback(it) }
            modernCallback = null
        } else {
            @Suppress("DEPRECATION")
            legacyListener?.let { telephonyManager.listen(it, PhoneStateListener.LISTEN_NONE) }
            legacyListener = null
        }
        Log.i(TAG, "CallStateObserver unregistered")
    }

    fun destroy() {
        unregister()
        scope.cancel()
    }

    // ─── Modern API (31+) ─────────────────────────────────────────────────────

    @RequiresApi(Build.VERSION_CODES.S)
    @Suppress("MissingPermission")
    private fun registerModernCallback() {
        val callback = ModernTelephonyCallback { state -> onCallStateChanged(state) }
        modernCallback = callback
        telephonyManager.registerTelephonyCallback(
            Executors.newSingleThreadExecutor(),
            callback
        )
    }

    @RequiresApi(Build.VERSION_CODES.S)
    private inner class ModernTelephonyCallback(
        private val onState: (Int) -> Unit
    ) : TelephonyCallback(), TelephonyCallback.CallStateListener {
        override fun onCallStateChanged(state: Int) = onState(state)
    }

    // ─── Legacy API (< 31) ────────────────────────────────────────────────────

    @Suppress("DEPRECATION", "MissingPermission")
    private fun registerLegacyListener() {
        val listener = LegacyPhoneStateListener { state, number -> onCallStateChanged(state, number) }
        legacyListener = listener
        telephonyManager.listen(listener, PhoneStateListener.LISTEN_CALL_STATE)
    }

    @Suppress("DEPRECATION")
    private inner class LegacyPhoneStateListener(
        private val onState: (Int, String?) -> Unit
    ) : PhoneStateListener() {
        override fun onCallStateChanged(state: Int, phoneNumber: String?) = onState(state, phoneNumber)
    }

    // ─── Shared state update ──────────────────────────────────────────────────

    /**
     * Called by both legacy and modern telephony listeners.
     *
     * @param state  Raw TelephonyManager call state constant.
     * @param number Caller's phone number, available ONLY from the legacy API (<31) on RINGING.
     *               Always null on API 31+ (modern callback doesn't provide it without restricted perms).
     */
    private fun onCallStateChanged(state: Int, number: String? = null) {
        val newState = when (state) {
            TelephonyManager.CALL_STATE_IDLE    -> VoxCallState.IDLE
            TelephonyManager.CALL_STATE_RINGING -> VoxCallState.RINGING
            TelephonyManager.CALL_STATE_OFFHOOK -> VoxCallState.OFFHOOK
            else -> VoxCallState.IDLE
        }
        // Capture number on RINGING; clear on IDLE
        when (newState) {
            VoxCallState.RINGING -> {
                if (!number.isNullOrBlank()) {
                    _incomingNumber.value = number
                    Log.d(TAG, "Incoming number captured (legacy API)")
                } else {
                    // Modern API (31+) or number unavailable — leave as null
                    // ContactLookupHelper treats null as unknown (fail-open)
                    Log.d(TAG, "Incoming number not available — will treat as unknown (fail-open)")
                }
            }
            VoxCallState.IDLE -> {
                _incomingNumber.value = null
            }
            else -> { /* OFFHOOK — keep existing number */ }
        }
        if (_callState.value != newState) {
            Log.d(TAG, "Call state: ${_callState.value} -> $newState")
            _callState.value = newState
        }
    }

    // ─── Speaker polling ──────────────────────────────────────────────────────

    private fun startSpeakerPolling() {
        speakerPollJob?.cancel()
        speakerPollJob = scope.launch {
            while (isActive) {
                @Suppress("DEPRECATION")
                val speakerOn = audioManager.isSpeakerphoneOn
                if (_isSpeakerOn.value != speakerOn) {
                    _isSpeakerOn.value = speakerOn
                    Log.d(TAG, "Speakerphone: $speakerOn")
                }
                delay(SPEAKER_POLL_INTERVAL_MS)
            }
        }
    }

    private fun stopSpeakerPolling() {
        speakerPollJob?.cancel()
        speakerPollJob = null
        _isSpeakerOn.value = false
    }
}

// ─── Call state enum ─────────────────────────────────────────────────────────

enum class VoxCallState {
    IDLE,       // No call
    RINGING,    // Incoming call — not yet answered
    OFFHOOK     // Call in progress (or outgoing dialing)
}
