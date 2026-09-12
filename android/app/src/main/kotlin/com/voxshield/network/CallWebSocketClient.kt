package com.voxshield.network

import android.util.Log
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import com.voxshield.model.BackendMessage
import com.voxshield.model.WsEnvelope
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import java.util.concurrent.TimeUnit
import kotlin.math.min
import kotlin.math.pow

private const val TAG = "VoxShield.WsClient"

/** Maximum time to wait between reconnect attempts (30 seconds). */
private const val MAX_BACKOFF_MS = 30_000L

/**
 * CallWebSocketClient — manages the OkHttp WebSocket connection to the backend
 * scam-detection pipeline at `wss://{host}/ws/call/{callId}`.
 *
 * ──────────────────────────────────────────────────────────────────────────────
 * PROTOCOL (identical to browser AudioWorklet frontend — no backend changes needed)
 * ──────────────────────────────────────────────────────────────────────────────
 * Android → Backend : Raw binary frames (ByteString)
 *   Each frame = 640 bytes = 320 PCM16LE samples = exactly 20ms at 16kHz mono.
 *   Frames are sent at the rate they are produced by AudioCaptureManager.
 *   No JSON envelope, no header — raw PCM bytes only.
 *
 * Backend → Android : JSON text frames
 *   Deserialized into BackendMessage sealed class via Moshi.
 *   Types: pdi_update, factcheck_update, transcript_chunk, session_status, scam_alert.
 *
 * ──────────────────────────────────────────────────────────────────────────────
 * Connection lifecycle
 * ──────────────────────────────────────────────────────────────────────────────
 * connect()          — opens WS, starts reconnect loop on failure
 * sendAudioFrame()   — sends a binary PCM chunk; no-ops if not connected
 * disconnect()       — clean close; stops reconnect loop
 *
 * Exponential backoff: 1s → 2s → 4s → 8s → 16s → 30s (cap), then stays at 30s.
 */
class CallWebSocketClient(
    private val backendWsBaseUrl: String,   // e.g. "wss://your-tunnel.trycloudflare.com"
    private val callId: String              // UUID per protection session
) {
    // ─── State flows consumed by UI layer ────────────────────────────────────

    private val _connectionState = MutableStateFlow<WsConnectionState>(WsConnectionState.Disconnected)
    val connectionState: StateFlow<WsConnectionState> = _connectionState.asStateFlow()

    private val _messages = MutableSharedFlow<BackendMessage>(extraBufferCapacity = 64)
    val messages: SharedFlow<BackendMessage> = _messages.asSharedFlow()

    // ─── Internals ────────────────────────────────────────────────────────────

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var webSocket: WebSocket? = null
    private var reconnectAttempts = 0
    private var shouldReconnect = true

    private val moshi = Moshi.Builder()
        .addLast(KotlinJsonAdapterFactory())
        .build()
    private val envelopeAdapter = moshi.adapter(WsEnvelope::class.java)

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.SECONDS)   // No read timeout — streaming connection
        .writeTimeout(15, TimeUnit.SECONDS)
        .pingInterval(20, TimeUnit.SECONDS) // Keeps the WS alive through NAT/proxies
        .build()

    // ─── Public API ───────────────────────────────────────────────────────────

    fun connect() {
        shouldReconnect = true
        openWebSocket()
    }

    /**
     * Sends one 640-byte PCM16LE audio frame to the backend.
     * This is the hot path — called ~50 times per second. Must be non-blocking.
     * No-ops silently if the socket is not currently open.
     */
    fun sendAudioFrame(pcmBytes: ByteArray) {
        val ws = webSocket ?: return
        if (_connectionState.value != WsConnectionState.Connected) return
        ws.send(ByteString.of(*pcmBytes))
    }

    /** Clean disconnect — stops reconnect loop. */
    fun disconnect() {
        shouldReconnect = false
        webSocket?.close(1000, "VoxShield session ended")
        webSocket = null
        _connectionState.value = WsConnectionState.Disconnected
    }

    fun destroy() {
        disconnect()
        scope.cancel()
        httpClient.dispatcher.executorService.shutdown()
    }

    // ─── Private: connection management ──────────────────────────────────────

    private fun openWebSocket() {
        val url = "$backendWsBaseUrl/ws/call/$callId"
        Log.d(TAG, "Connecting to $url (attempt ${reconnectAttempts + 1})")

        val request = Request.Builder()
            .url(url)
            .header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            .build()
        webSocket = httpClient.newWebSocket(request, object : WebSocketListener() {

            override fun onOpen(ws: WebSocket, response: Response) {
                Log.i(TAG, "WebSocket connected: $url")
                reconnectAttempts = 0
                _connectionState.value = WsConnectionState.Connected
            }

            override fun onMessage(ws: WebSocket, text: String) {
                parseAndEmitMessage(text)
            }

            override fun onClosing(ws: WebSocket, code: Int, reason: String) {
                Log.i(TAG, "WebSocket closing: $code $reason")
                ws.close(1000, null)
            }

            override fun onClosed(ws: WebSocket, code: Int, reason: String) {
                Log.i(TAG, "WebSocket closed: $code $reason")
                _connectionState.value = WsConnectionState.Disconnected
                scheduleReconnect()
            }

            override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "WebSocket failure: ${t.message}", t)
                _connectionState.value = WsConnectionState.Error(t.message ?: "Unknown error")
                scheduleReconnect()
            }
        })
        _connectionState.value = WsConnectionState.Connecting
    }

    private fun scheduleReconnect() {
        if (!shouldReconnect) return
        scope.launch {
            val backoffMs = min(
                (1_000L * 2.0.pow(reconnectAttempts.toDouble())).toLong(),
                MAX_BACKOFF_MS
            )
            reconnectAttempts++
            Log.d(TAG, "Reconnecting in ${backoffMs}ms (attempt $reconnectAttempts)")
            _connectionState.value = WsConnectionState.Reconnecting(reconnectAttempts, backoffMs)
            delay(backoffMs)
            if (shouldReconnect) openWebSocket()
        }
    }

    // ─── Private: message parsing ─────────────────────────────────────────────

    private fun parseAndEmitMessage(json: String) {
        try {
            val envelope = envelopeAdapter.fromJson(json) ?: return
            val message: BackendMessage = when (envelope.type) {
                "pdi_update"       -> parsePdiUpdate(json)
                "factcheck_update" -> parseFactCheck(json)
                "transcript_chunk" -> parseTranscript(json)
                "session_status"   -> parseSessionStatus(json)
                "mode_update"      -> parseModeUpdate(json)
                else               -> BackendMessage.Unknown(envelope.type)
            }
            scope.launch { _messages.emit(message) }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse WS message: $json", e)
        }
    }

    private fun parsePdiUpdate(json: String) =
        moshi.adapter(BackendMessage.PdiUpdate::class.java).fromJson(json)
            ?: BackendMessage.Unknown("pdi_update_parse_fail")

    private fun parseFactCheck(json: String) =
        moshi.adapter(BackendMessage.FactCheckUpdate::class.java).fromJson(json)
            ?: BackendMessage.Unknown("factcheck_update_parse_fail")

    private fun parseTranscript(json: String) =
        moshi.adapter(BackendMessage.TranscriptChunk::class.java).fromJson(json)
            ?: BackendMessage.Unknown("transcript_chunk_parse_fail")

    private fun parseSessionStatus(json: String) =
        moshi.adapter(BackendMessage.SessionStatus::class.java).fromJson(json)
            ?: BackendMessage.Unknown("session_status_parse_fail")

    private fun parseModeUpdate(json: String) =
        moshi.adapter(BackendMessage.ModeUpdate::class.java).fromJson(json)
            ?: BackendMessage.Unknown("mode_update_parse_fail")
}

// ─── Connection state ADT ────────────────────────────────────────────────────

sealed class WsConnectionState {
    object Disconnected : WsConnectionState()
    object Connecting : WsConnectionState()
    object Connected : WsConnectionState()
    data class Reconnecting(val attempt: Int, val delayMs: Long) : WsConnectionState()
    data class Error(val message: String) : WsConnectionState()
}
