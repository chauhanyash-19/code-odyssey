'use client';
import React, { useState, useCallback } from 'react';

interface VideoFrameSummary {
  timestamp: string | null;
  sha256_hash: string | null;
  face_detected: boolean | null;
  local_path: string | null;
}

interface DraftResponse {
  draft_id: string;
  payload_summary: string;
  destination: string;
  verdict: string;
  drafted_at: string;
  video_frame_count: number;
  video_frames_summary: VideoFrameSummary[];
  warning: string;
}

interface DispatchResult {
  success: boolean;
  delivery_status: string;
  dispatched_at?: string;
  error?: string;
}

interface Props {
  callId: string;
  authToken: string;
  onClose: () => void;
}

type ModalStep = 'idle' | 'loading_draft' | 'review' | 'confirming' | 'done' | 'error';

export default function EscalationModal({ callId, authToken, onClose }: Props) {
  const [step, setStep] = useState<ModalStep>('idle');
  const [draft, setDraft] = useState<DraftResponse | null>(null);
  const [dispatchResult, setDispatchResult] = useState<DispatchResult | null>(null);
  const [errorMessage, setErrorMessage] = useState('');

  const API = 'http://localhost:8000';

  const fetchDraft = useCallback(async () => {
    setStep('loading_draft');
    setErrorMessage('');
    try {
      const res = await fetch(`${API}/call/${callId}/escalate/draft`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({ format: 'webhook' }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || res.statusText);
      }
      const data: DraftResponse = await res.json();
      setDraft(data);
      setStep('review');
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to fetch escalation draft';
      setErrorMessage(msg);
      setStep('error');
    }
  }, [callId, authToken]);

  const confirmDispatch = useCallback(async () => {
    if (!draft) return;
    setStep('confirming');
    try {
      const res = await fetch(`${API}/call/${callId}/escalate/confirm`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({ draft_id: draft.draft_id }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || res.statusText);
      }
      const result: DispatchResult = await res.json();
      setDispatchResult(result);
      setStep('done');
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Dispatch failed';
      setErrorMessage(msg);
      setStep('error');
    }
  }, [draft, callId, authToken]);

  // Auto-fetch draft when modal first mounts
  React.useEffect(() => {
    fetchDraft();
  }, [fetchDraft]);

  return (
    <div
      id="escalation-modal-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: 'rgba(0,0,0,0.85)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        id="escalation-modal"
        className="relative w-full max-w-2xl mx-4 rounded-2xl overflow-hidden shadow-2xl"
        style={{
          background: 'linear-gradient(135deg, #0d0d1a 0%, #1a0a0a 100%)',
          border: '1px solid rgba(192,57,43,0.4)',
          boxShadow: '0 0 60px rgba(192,57,43,0.2), 0 0 120px rgba(0,0,0,0.8)',
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-6 py-4 border-b"
          style={{ borderColor: 'rgba(192,57,43,0.3)', background: 'rgba(192,57,43,0.08)' }}
        >
          <div className="flex items-center gap-3">
            <span className="text-2xl">🚨</span>
            <div>
              <h2 className="text-lg font-bold text-red-300 tracking-wide uppercase">
                Escalate to Cybercrime Cell
              </h2>
              <p className="text-xs text-gray-500 font-mono mt-0.5">
                Call ID: {callId}
              </p>
            </div>
          </div>
          <button
            id="btn-close-escalation-modal"
            onClick={onClose}
            className="text-gray-500 hover:text-white transition-colors text-xl leading-none"
            title="Close"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5 max-h-[70vh] overflow-y-auto">

          {/* Loading draft */}
          {step === 'loading_draft' && (
            <div className="flex flex-col items-center gap-4 py-10">
              <div
                className="w-12 h-12 rounded-full border-4 border-red-700 border-t-transparent animate-spin"
              />
              <p className="text-gray-400 font-mono text-sm">Preparing escalation draft…</p>
            </div>
          )}

          {/* Review step */}
          {step === 'review' && draft && (
            <>
              {/* Warning banner */}
              <div
                className="flex items-start gap-3 p-4 rounded-xl border"
                style={{ background: 'rgba(243,156,18,0.08)', borderColor: 'rgba(243,156,18,0.3)' }}
              >
                <span className="text-yellow-400 text-xl mt-0.5">⚠️</span>
                <p className="text-yellow-300 text-sm leading-relaxed font-mono">
                  {draft.warning}
                </p>
              </div>

              {/* Verdict + destination */}
              <div className="grid grid-cols-2 gap-3">
                <InfoCard label="Verdict" value={draft.verdict} highlight={draft.verdict === 'CRITICAL'} />
                <InfoCard label="Destination" value={draft.destination || '(not configured)'} />
                <InfoCard label="Drafted At" value={draft.drafted_at.slice(0, 19).replace('T', ' ')} />
                <InfoCard label="Video Frames" value={`${draft.video_frame_count} captured`} />
              </div>

              {/* Payload summary */}
              <div
                className="rounded-xl p-4 border font-mono text-xs text-gray-300 leading-relaxed"
                style={{ background: 'rgba(255,255,255,0.03)', borderColor: 'rgba(255,255,255,0.08)' }}
              >
                <p className="text-gray-500 uppercase text-xs tracking-widest mb-2 font-semibold">
                  Payload Summary
                </p>
                {draft.payload_summary}
              </div>

              {/* Video frames table */}
              {draft.video_frame_count > 0 && (
                <div>
                  <p className="text-gray-400 uppercase text-xs tracking-widest font-semibold mb-3">
                    📹 Captured Video Evidence Frames
                  </p>
                  <div className="space-y-2">
                    {draft.video_frames_summary.map((frame, i) => (
                      <FrameCard key={i} index={i + 1} frame={frame} />
                    ))}
                  </div>
                  <p className="text-xs text-gray-600 mt-2 font-mono">
                    Privacy: Presence detection ONLY (Haar Cascade). No facial recognition performed.
                  </p>
                </div>
              )}

              {draft.video_frame_count === 0 && (
                <div
                  className="flex items-center gap-3 p-3 rounded-lg border text-gray-500 text-sm font-mono"
                  style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.02)' }}
                >
                  <span>📷</span>
                  No video frames captured yet. Frame capture triggers automatically on CRITICAL verdict.
                </div>
              )}
            </>
          )}

          {/* Confirming */}
          {step === 'confirming' && (
            <div className="flex flex-col items-center gap-4 py-10">
              <div className="w-12 h-12 rounded-full border-4 border-red-600 border-t-transparent animate-spin" />
              <p className="text-gray-400 font-mono text-sm">Dispatching escalation report…</p>
            </div>
          )}

          {/* Done */}
          {step === 'done' && dispatchResult && (
            <div className="space-y-4">
              <div
                className={`flex items-center gap-3 p-4 rounded-xl border ${
                  dispatchResult.success
                    ? 'border-green-700 bg-green-900/20 text-green-300'
                    : 'border-yellow-700 bg-yellow-900/20 text-yellow-300'
                }`}
              >
                <span className="text-2xl">{dispatchResult.success ? '✅' : '⚠️'}</span>
                <div>
                  <p className="font-bold text-sm uppercase tracking-wider">
                    {dispatchResult.success ? 'Escalation Dispatched' : 'Logged (Not Sent)'}
                  </p>
                  <p className="text-xs opacity-80 font-mono mt-1">
                    Status: {dispatchResult.delivery_status}
                    {dispatchResult.dispatched_at && ` — ${dispatchResult.dispatched_at.slice(0, 19).replace('T', ' ')} UTC`}
                  </p>
                  {dispatchResult.error && (
                    <p className="text-xs text-yellow-400 font-mono mt-1">
                      Note: {dispatchResult.error}
                    </p>
                  )}
                </div>
              </div>
              <p className="text-gray-500 text-sm font-mono text-center">
                Chain-of-custody record has been saved to the forensic dossier.
              </p>
            </div>
          )}

          {/* Error */}
          {step === 'error' && (
            <div
              className="flex items-start gap-3 p-4 rounded-xl border border-red-700 bg-red-900/20"
            >
              <span className="text-red-400 text-xl">❌</span>
              <div>
                <p className="text-red-300 font-bold text-sm">Error</p>
                <p className="text-red-400 text-xs font-mono mt-1">{errorMessage}</p>
              </div>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div
          className="flex items-center justify-between px-6 py-4 border-t gap-4"
          style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(0,0,0,0.3)' }}
        >
          <button
            id="btn-cancel-escalation"
            onClick={onClose}
            className="px-5 py-2.5 rounded-lg text-sm font-semibold text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 transition-all"
          >
            {step === 'done' ? 'Close' : 'Cancel'}
          </button>

          <div className="flex gap-3">
            {step === 'error' && (
              <button
                id="btn-retry-draft"
                onClick={fetchDraft}
                className="px-5 py-2.5 rounded-lg text-sm font-semibold bg-gray-700 hover:bg-gray-600 text-white transition-all"
              >
                ↺ Retry
              </button>
            )}
            {step === 'review' && (
              <button
                id="btn-confirm-dispatch"
                onClick={confirmDispatch}
                className="px-6 py-2.5 rounded-lg text-sm font-bold text-white transition-all transform hover:scale-105 active:scale-95"
                style={{
                  background: 'linear-gradient(135deg, #c0392b, #922b21)',
                  boxShadow: '0 0 20px rgba(192,57,43,0.4)',
                }}
              >
                🚨 Confirm Dispatch
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* Sub-components */

function InfoCard({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div
      className="rounded-xl p-3 border"
      style={{ background: 'rgba(255,255,255,0.03)', borderColor: 'rgba(255,255,255,0.08)' }}
    >
      <p className="text-gray-500 uppercase text-xs tracking-widest font-semibold mb-1">{label}</p>
      <p
        className={`font-mono text-sm font-bold ${
          highlight ? 'text-red-400' : 'text-gray-200'
        }`}
      >
        {value}
      </p>
    </div>
  );
}

function FrameCard({ index, frame }: { index: number; frame: VideoFrameSummary }) {
  const faceColor =
    frame.face_detected === true
      ? 'text-green-400'
      : frame.face_detected === false
      ? 'text-gray-400'
      : 'text-gray-600';

  return (
    <div
      className="flex items-start gap-4 rounded-xl p-4 border"
      style={{ background: 'rgba(255,255,255,0.03)', borderColor: 'rgba(59,130,246,0.2)' }}
    >
      <div
        className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center font-bold text-blue-300 text-sm"
        style={{ background: 'rgba(59,130,246,0.15)', border: '1px solid rgba(59,130,246,0.3)' }}
      >
        #{index}
      </div>
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-xs font-bold uppercase ${faceColor}`}>
            {frame.face_detected === true
              ? '👤 Presence Detected'
              : frame.face_detected === false
              ? '🚫 No Face Detected'
              : '❓ Unknown'}
          </span>
        </div>
        <p className="text-gray-500 font-mono text-xs truncate">
          SHA-256: {frame.sha256_hash ? `${frame.sha256_hash.slice(0, 24)}…` : 'N/A'}
        </p>
        {frame.timestamp && (
          <p className="text-gray-600 font-mono text-xs">
            {frame.timestamp.slice(0, 19).replace('T', ' ')} UTC
          </p>
        )}
      </div>
    </div>
  );
}
