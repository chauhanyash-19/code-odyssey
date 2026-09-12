package com.voxshield.model

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

/**
 * WsMessages.kt — Kotlin data class equivalents of the browser-side protocol.ts
 * WebSocket message types used by the PhaseGuard/VoxShield backend pipeline.
 *
 * These mirror the binary-frame + JSON-envelope protocol already built for the
 * browser-based AudioWorklet frontend. The only difference on Android is that
 * audio SOURCE changes from AudioWorklet → AudioRecord; all message shapes are
 * identical so the backend requires zero changes.
 *
 * Message flow:
 *   Android → Backend : raw binary ByteString frames (PCM16LE, 16kHz mono, 640-byte chunks = 20ms)
 *   Backend → Android : JSON text frames matching the sealed class hierarchy below
 *
 * Moshi @JsonClass(generateAdapter = true) is used for zero-reflection codegen.
 * Add kapt/ksp for moshi-kotlin-codegen if reflection-free mode is preferred;
 * currently uses moshi-kotlin (reflection-based) for simplicity.
 */

// ─── Incoming message type discriminator ───────────────────────────────────────

/**
 * Raw envelope parsed before dispatching to typed sub-classes.
 */
@JsonClass(generateAdapter = true)
data class WsEnvelope(
    @Json(name = "type") val type: String,
    // Raw JSON object; re-parsed based on `type`
    @Json(name = "payload") val payload: Map<String, Any?>? = null
)

// ─── Typed backend → Android messages ─────────────────────────────────────────

sealed class BackendMessage {

    /**
     * PDI (Phone Deception Index) update — primary fraud probability signal.
     * Backend emits this ~every 2–5 seconds as more audio is analyzed.
     *
     * [pdiScore]  0.0 = definitely safe, 1.0 = definitely fraud
     * [verdict]   Human-readable category: "safe" | "suspicious" | "scam"
     * [confidence] Model confidence in this verdict (0.0–1.0)
     */
    @JsonClass(generateAdapter = true)
    data class PdiUpdate(
        @Json(name = "call_id")    val callId: String,
        @Json(name = "pdi_score")  val pdiScore: Float,
        @Json(name = "verdict")    val verdict: String,        // "safe" | "suspicious" | "scam"
        @Json(name = "confidence") val confidence: Float,
        @Json(name = "timestamp")  val timestamp: Long
    ) : BackendMessage()

    /**
     * Real-time fact-check result for a specific claim detected in speech.
     * Backend emits this when the STT pipeline detects a verifiable claim
     * (e.g., "your account has been locked", "IRS is calling").
     *
     * [status]         Action-level verdict: "SAFE" | "CRITICAL" | "UNCERTAIN"
     * [claim]          The detected claim text
     * [result]         Legacy field: "true" | "false" | "unverifiable"
     * [verdictMessage] Human-readable description of the verdict reason (nullable)
     * [confidence]     Confidence in the fact-check result
     */
    @JsonClass(generateAdapter = true)
    data class FactCheckUpdate(
        @Json(name = "call_id")         val callId: String,
        @Json(name = "status")          val status: String = "UNCERTAIN",  // SAFE | CRITICAL | UNCERTAIN
        @Json(name = "claim")           val claim: String = "",
        @Json(name = "result")          val result: String = "unverifiable",
        @Json(name = "verdict_message") val verdictMessage: String? = null,
        @Json(name = "confidence")      val confidence: Float = 0f,
        @Json(name = "timestamp")       val timestamp: Long = 0L
    ) : BackendMessage()

    /**
     * Incremental STT transcript chunk.
     * [isFinal] false = interim result, true = committed word sequence.
     */
    @JsonClass(generateAdapter = true)
    data class TranscriptChunk(
        @Json(name = "call_id")   val callId: String,
        @Json(name = "text")      val text: String,
        @Json(name = "is_final")  val isFinal: Boolean,
        @Json(name = "timestamp") val timestamp: Long
    ) : BackendMessage()

    /**
     * Session lifecycle status from backend.
     * [status] "active" | "ended" | "error" | "reconnecting"
     */
    @JsonClass(generateAdapter = true)
    data class SessionStatus(
        @Json(name = "call_id")   val callId: String,
        @Json(name = "status")    val status: String,
        @Json(name = "message")   val message: String? = null,
        @Json(name = "timestamp") val timestamp: Long
    ) : BackendMessage()

    // Removed ScamAlert here as backend does not send 'scam_alert' messages.
    // CRITICAL alerts are exclusively sent via FactCheckUpdate with status="CRITICAL".

    /**
     * Backend pipeline mode update.
     * Emitted when the server switches between full and limited (offline) mode.
     *
     * [mode] "full" = all checks active | "limited" = local-only fallback
     *        (corresponds to the server-side offline_fallback LIMITED MODE)
     */
    @JsonClass(generateAdapter = true)
    data class ModeUpdate(
        @Json(name = "call_id")   val callId: String,
        @Json(name = "mode")      val mode: String,            // "full" | "limited"
        @Json(name = "message")   val message: String? = null,
        @Json(name = "timestamp") val timestamp: Long = 0L
    ) : BackendMessage()

    /** Fallback for unrecognised message types — preserves forward-compatibility. */
    data class Unknown(val rawType: String) : BackendMessage()
}

// ─── Verdict helpers ───────────────────────────────────────────────────────────

enum class PdiVerdict(val label: String, val emoji: String) {
    SAFE("Safe", "\u2705"),
    SUSPICIOUS("Suspicious", "\u26a0\ufe0f"),
    SCAM("Scam Detected", "\uD83D\uDEA8"),
    UNKNOWN("Analyzing\u2026", "\uD83D\uDD0D");

    companion object {
        fun from(raw: String?) = when (raw?.lowercase()) {
            "safe"       -> SAFE
            "suspicious" -> SUSPICIOUS
            "scam", "critical" -> SCAM   // factcheck_update CRITICAL maps to SCAM
            else         -> UNKNOWN
        }
    }
}
