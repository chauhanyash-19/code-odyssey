package com.voxshield.audio

import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlin.math.abs
import kotlin.math.sqrt

private const val TAG = "VoxShield.AudioCapture"

/**
 * AudioCaptureManager — Captures microphone audio and emits raw PCM16LE frames
 * for streaming to the backend scam-detection WebSocket endpoint.
 *
 * ══════════════════════════════════════════════════════════════════════════════
 * ⚠️ SPEAKERPHONE CONSTRAINT — READ THIS FIRST ⚠️
 * ══════════════════════════════════════════════════════════════════════════════
 * This class uses AudioSource.VOICE_RECOGNITION — a standard, fully-permitted
 * microphone capture path requiring only RECORD_AUDIO permission.
 *
 * This captures whatever the phone's microphone physically hears.
 *
 * During a phone call:
 *   - YOUR voice: always captured (mic is always on your side)
 *   - CALLER's voice: captured ONLY if the call is on SPEAKERPHONE, because
 *     that routes the earpiece audio through the physical speaker which the
 *     microphone can then pick up acoustically.
 *
 * Why NOT AudioSource.VOICE_CALL?
 *   VOICE_CALL, VOICE_UPLINK, and VOICE_DOWNLINK are non-functional for
 *   third-party apps on non-rooted Android since API 23 (Android 6). These
 *   sources are silently suppressed or return silence by the OS audio policy.
 *   They are not used here — not even as a fallback.
 *
 * Why NOT a system-level captureAudioOutput?
 *   CAPTURE_AUDIO_OUTPUT is a system-signature-only permission. It cannot be
 *   declared by Play Store apps. Not used here.
 *
 * The speakerphone requirement is NOT a bug. It is a hard Android OS constraint
 * and is disclosed to users prominently throughout the onboarding and in-call UI.
 * ══════════════════════════════════════════════════════════════════════════════
 *
 * Audio config:
 *   Source : VOICE_RECOGNITION (disables AGC + noise suppression → cleaner
 *            signal for ML inference vs. plain MIC)
 *   Rate   : 16 000 Hz (standard for speech; matches backend STT pipeline)
 *   Channel: Mono (CHANNEL_IN_MONO)
 *   Format : PCM 16-bit signed little-endian (ENCODING_PCM_16BIT)
 *   Chunk  : 640 bytes = 320 samples = exactly 20 ms @ 16kHz
 *            (matches 20ms AudioWorklet quantum on browser side — same backend)
 *
 * Outputs:
 *   [audioFrames]  SharedFlow<ByteArray> — each emission is one 640-byte PCM chunk
 *   [amplitude]    StateFlow<Float>      — RMS amplitude 0.0–1.0 for waveform UI
 *   [isRecording]  StateFlow<Boolean>    — true while AudioRecord is running
 */
class AudioCaptureManager {

    companion object {
        const val SAMPLE_RATE = 16_000          // Hz
        const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        const val BYTES_PER_SAMPLE = 2          // 16-bit = 2 bytes
        const val CHUNK_MS = 20                 // ms per frame
        const val SAMPLES_PER_CHUNK = SAMPLE_RATE * CHUNK_MS / 1000  // = 320
        const val BYTES_PER_CHUNK = SAMPLES_PER_CHUNK * BYTES_PER_SAMPLE  // = 640

        // Audio source: VOICE_RECOGNITION disables AGC and noise suppression.
        // This gives the backend a cleaner raw signal for ML/STT inference.
        // Do NOT change to VOICE_CALL — it is non-functional on non-rooted devices.
        @Suppress("DEPRECATION")
        val AUDIO_SOURCE = MediaRecorder.AudioSource.VOICE_RECOGNITION
    }

    // ─── Exposed flows ────────────────────────────────────────────────────────

    private val _audioFrames = MutableSharedFlow<ByteArray>(extraBufferCapacity = 200)
    /** Each emission is exactly [BYTES_PER_CHUNK] bytes of PCM16LE audio. */
    val audioFrames: SharedFlow<ByteArray> = _audioFrames.asSharedFlow()

    private val _amplitude = MutableStateFlow(0f)
    /** Normalised RMS amplitude in range [0, 1]. Drives the waveform UI indicator. */
    val amplitude: StateFlow<Float> = _amplitude.asStateFlow()

    private val _isRecording = MutableStateFlow(false)
    val isRecording: StateFlow<Boolean> = _isRecording.asStateFlow()

    // ─── Internals ────────────────────────────────────────────────────────────

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var captureJob: Job? = null
    private var audioRecord: AudioRecord? = null

    // ─── Public API ───────────────────────────────────────────────────────────

    /**
     * Start continuous microphone capture. Emits PCM frames to [audioFrames].
     * Requires RECORD_AUDIO permission to have been granted before calling.
     * Safe to call multiple times — subsequent calls are no-ops if already recording.
     */
    @Suppress("MissingPermission")  // Permission checked by caller (ForegroundService)
    fun start() {
        if (_isRecording.value) return

        val minBufferBytes = AudioRecord.getMinBufferSize(
            SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT
        )
        if (minBufferBytes == AudioRecord.ERROR || minBufferBytes == AudioRecord.ERROR_BAD_VALUE) {
            Log.e(TAG, "AudioRecord.getMinBufferSize returned error — device may not support config")
            return
        }

        // Double-buffer: ensures the OS never starves while we're copying data
        val bufferBytes = maxOf(minBufferBytes * 2, BYTES_PER_CHUNK * 4)

        try {
            audioRecord = AudioRecord(
                AUDIO_SOURCE,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferBytes
            )
        } catch (e: SecurityException) {
            Log.e(TAG, "RECORD_AUDIO permission not granted — cannot start capture", e)
            return
        }

        if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
            Log.e(TAG, "AudioRecord failed to initialize — releasing")
            audioRecord?.release()
            audioRecord = null
            return
        }

        audioRecord!!.startRecording()
        _isRecording.value = true
        Log.i(TAG, "AudioCapture started — source=VOICE_RECOGNITION, rate=$SAMPLE_RATE, chunk=$BYTES_PER_CHUNK bytes")

        captureJob = scope.launch {
            val buffer = ByteArray(BYTES_PER_CHUNK)
            val recorder = audioRecord ?: return@launch

            while (isActive && _isRecording.value) {
                val bytesRead = recorder.read(buffer, 0, BYTES_PER_CHUNK)
                when {
                    bytesRead > 0 -> {
                        // Emit PCM frame for WebSocket streaming
                        _audioFrames.tryEmit(buffer.copyOf(bytesRead))
                        // Update amplitude for waveform UI (computed on IO thread)
                        _amplitude.value = computeRmsAmplitude(buffer, bytesRead)
                    }
                    bytesRead == AudioRecord.ERROR_INVALID_OPERATION ->
                        Log.e(TAG, "AudioRecord.read: ERROR_INVALID_OPERATION")
                    bytesRead == AudioRecord.ERROR_BAD_VALUE ->
                        Log.e(TAG, "AudioRecord.read: ERROR_BAD_VALUE")
                }
            }
        }
    }

    /** Stop audio capture and release AudioRecord resources. */
    fun stop() {
        _isRecording.value = false
        captureJob?.cancel()
        captureJob = null
        try {
            audioRecord?.stop()
            audioRecord?.release()
        } catch (e: Exception) {
            Log.w(TAG, "Error stopping AudioRecord: ${e.message}")
        }
        audioRecord = null
        _amplitude.value = 0f
        Log.i(TAG, "AudioCapture stopped")
    }

    fun destroy() {
        stop()
        scope.cancel()
    }

    // ─── Signal processing ────────────────────────────────────────────────────

    /**
     * Compute normalised RMS amplitude from PCM16LE byte array.
     * Returns value in [0, 1] clamped. Used only for the waveform UI —
     * not sent to backend.
     */
    private fun computeRmsAmplitude(pcmBytes: ByteArray, validBytes: Int): Float {
        if (validBytes < 2) return 0f
        var sumSq = 0.0
        val sampleCount = validBytes / BYTES_PER_SAMPLE
        for (i in 0 until sampleCount) {
            // PCM16LE: low byte first, then high byte (little-endian)
            val sample = (pcmBytes[i * 2].toInt() and 0xFF) or
                         (pcmBytes[i * 2 + 1].toInt() shl 8)
            val signed = if (sample > 32767) sample - 65536 else sample
            sumSq += signed.toLong() * signed.toLong()
        }
        val rms = sqrt(sumSq / sampleCount)
        // Normalise by max PCM16 value (32768)
        return (rms / 32768.0).toFloat().coerceIn(0f, 1f)
    }
}
