"""
forensics/pdf_report.py — Forensic PDF dossier generator for the 1930 portal.

PDF contents (formatted for India's National Cyber Crime Portal submission):
  1. Cover page: call metadata, case summary
  2. Chain of custody: SHA-256 hash, recording timestamp, ingestion source
  3. DSP analysis: peak PDI, tremor findings, ensemble verdict
  4. Extracted identifiers: UPI IDs, phone numbers, impersonated entities
  5. Fact-check verdict history: all verdicts with timestamps
  6. Spectrogram: embedded matplotlib PNG of the recorded audio
  7. Scambaiter log: exchange history (if scambaiter was deployed)
  8. Escalation records: timestamps, destinations, delivery statuses

Uses ReportLab for PDF generation and matplotlib for spectrogram generation.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server-side rendering
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

logger = logging.getLogger(__name__)

# ── Styles ─────────────────────────────────────────────────────────────────────
_styles = getSampleStyleSheet()

_TITLE_STYLE = ParagraphStyle(
    "PhaseGuardTitle",
    parent=_styles["Title"],
    fontSize=18,
    textColor=colors.HexColor("#1a1a2e"),
    spaceAfter=12,
)
_HEADING_STYLE = ParagraphStyle(
    "PhaseGuardHeading",
    parent=_styles["Heading1"],
    fontSize=13,
    textColor=colors.HexColor("#16213e"),
    spaceBefore=16,
    spaceAfter=8,
    borderPad=4,
)
_BODY_STYLE = ParagraphStyle(
    "PhaseGuardBody",
    parent=_styles["Normal"],
    fontSize=9,
    leading=13,
    spaceAfter=4,
)
_CRITICAL_STYLE = ParagraphStyle(
    "PhaseGuardCritical",
    parent=_styles["Normal"],
    fontSize=10,
    textColor=colors.red,
    fontName="Helvetica-Bold",
)
_MONO_STYLE = ParagraphStyle(
    "PhaseGuardMono",
    parent=_styles["Code"],
    fontSize=8,
    fontName="Courier",
    backColor=colors.HexColor("#f5f5f5"),
    spaceAfter=6,
)


def _make_table(data: List[List[str]], col_widths=None) -> Table:
    """Create a styled two-column info table."""
    t = Table(data, colWidths=col_widths or [5 * cm, 11 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4ff")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return t


def _generate_spectrogram(
    pcm16_bytes: bytes,
    fs: int = 16_000,
    max_duration_seconds: float = 30.0,
) -> Optional[bytes]:
    """
    Generate a spectrogram PNG from PCM16LE audio bytes.
    Returns PNG bytes, or None if audio is empty.
    """
    if not pcm16_bytes:
        return None

    try:
        audio = np.frombuffer(pcm16_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        # Limit to first 30 seconds for a reasonable image size
        max_samples = int(max_duration_seconds * fs)
        audio = audio[:max_samples]

        fig, ax = plt.subplots(figsize=(10, 3))
        ax.specgram(audio, Fs=fs, cmap="viridis", scale="dB")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Frequency (Hz)")
        ax.set_title("Call Audio Spectrogram (first 30s)")
        ax.set_ylim(0, 4000)
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception as exc:
        logger.warning("Spectrogram generation failed: %s", exc)
        return None


def generate_forensic_pdf(
    call_id: str,
    call_start_time: str,
    call_duration_seconds: float,
    ingestion_mode: str,
    hash_result: Dict[str, Any],
    peak_pdi: float,
    tremor_findings: Dict[str, Any],
    ensemble_label: str,
    identifiers: Dict[str, Any],
    factcheck_history: List[Dict[str, Any]],
    transcript_summary: str,
    scambaiter_log: List[Dict[str, Any]],
    escalation_records: List[Dict[str, Any]],
    pcm16_bytes: bytes,
    fs: int = 16_000,
) -> bytes:
    """
    Build the complete forensic PDF dossier.

    Parameters match the fields of CallSession from connection_manager.py.

    Returns
    -------
    bytes
        PDF file bytes ready for HTTP response or file write.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"PhaseGuard Forensic Dossier — {call_id}",
        author="PhaseGuard Anti-Scam System",
        subject="Cyber Crime Evidence Dossier",
    )

    story = []

    # ── Cover page ─────────────────────────────────────────────────────────────
    story.append(Paragraph("🛡 PhaseGuard Forensic Evidence Dossier", _TITLE_STYLE))
    story.append(Paragraph("Prepared for: National Cyber Crime Portal (cybercrime.gov.in) | Helpline: 1930", _BODY_STYLE))
    story.append(Spacer(1, 0.5 * cm))

    final_verdict = (
        factcheck_history[-1].get("status", "UNKNOWN") if factcheck_history else "UNKNOWN"
    )
    verdict_color = {"CRITICAL": colors.red, "SAFE": colors.green, "UNCERTAIN": colors.orange}.get(
        final_verdict, colors.gray
    )
    story.append(
        Paragraph(
            f"<b>FINAL VERDICT: <font color='{verdict_color.hexval()}'>{final_verdict}</font></b>",
            ParagraphStyle(
                "verdict",
                parent=_styles["Normal"],
                fontSize=14,
                alignment=TA_CENTER,
                spaceAfter=12,
            ),
        )
    )

    meta_data = [
        ["Field", "Value"],
        ["Call ID", call_id],
        ["Call Start", call_start_time],
        ["Duration", f"{call_duration_seconds:.1f} seconds"],
        ["Ingestion Source", ingestion_mode.upper()],
        ["Generated At", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")],
    ]
    story.append(_make_table(meta_data))
    story.append(PageBreak())

    # ── Chain of custody ───────────────────────────────────────────────────────
    story.append(Paragraph("1. Chain of Custody / Audio Integrity", _HEADING_STYLE))
    story.append(Paragraph(
        "The SHA-256 hash below was computed over the raw PCM16LE audio bytes at the time of "
        "recording. Any modification to the audio file will change this hash, making tampering "
        "detectable.",
        _BODY_STYLE,
    ))
    custody_data = [
        ["Field", "Value"],
        ["SHA-256 Hash", hash_result.get("sha256_hex", "N/A")],
        ["Audio Size", f"{hash_result.get('size_bytes', 0):,} bytes"],
        ["Audio Duration", f"{hash_result.get('duration_seconds', 0):.1f} seconds"],
        ["Sample Rate", f"{fs} Hz PCM16LE Mono"],
    ]
    story.append(_make_table(custody_data))
    story.append(Spacer(1, 0.3 * cm))

    # ── DSP Analysis ───────────────────────────────────────────────────────────
    story.append(Paragraph("2. DSP / Voice Analysis", _HEADING_STYLE))
    dsp_data = [
        ["Metric", "Result"],
        ["Peak PDI Score", f"{peak_pdi:.4f} (1.0 = fully synthetic, 0.0 = human)"],
        ["Voice Classification", ensemble_label],
        ["Tremor Energy", f"{tremor_findings.get('tremor_energy', 0):.4f}"],
        ["Physiological Tremor", "DETECTED" if tremor_findings.get("has_tremor") else "NOT DETECTED"],
        ["Peak Tremor Frequency", f"{tremor_findings.get('peak_tremor_hz', 0):.1f} Hz"],
    ]
    story.append(_make_table(dsp_data))

    # Spectrogram
    story.append(Spacer(1, 0.3 * cm))
    spectrogram_png = _generate_spectrogram(pcm16_bytes, fs)
    if spectrogram_png:
        img_buf = io.BytesIO(spectrogram_png)
        story.append(Image(img_buf, width=16 * cm, height=5 * cm))
        story.append(Paragraph("Figure 1: Call Audio Spectrogram (first 30 seconds)", _BODY_STYLE))
    story.append(Spacer(1, 0.3 * cm))

    # ── Extracted Identifiers ─────────────────────────────────────────────────
    story.append(Paragraph("3. Extracted Scam Identifiers", _HEADING_STYLE))
    story.append(Paragraph(
        "These identifiers were extracted from the call transcript and are suitable for "
        "inclusion in an FIR or complaint on the National Cyber Crime Portal.",
        _BODY_STYLE,
    ))

    def _list_or_none(items):
        return ", ".join(items) if items else "None detected"

    id_data = [
        ["Identifier Type", "Values"],
        ["UPI IDs", _list_or_none(identifiers.get("upi_ids", []))],
        ["Phone Numbers", _list_or_none(identifiers.get("phone_numbers", []))],
        ["Bank Accounts", _list_or_none(identifiers.get("bank_accounts", []))],
        ["IFSC Codes", _list_or_none(identifiers.get("ifsc_codes", []))],
        ["URLs / Apps", _list_or_none(identifiers.get("urls", []))],
        ["Impersonated Entities", _list_or_none(identifiers.get("impersonated_entities", []))],
        ["Caller Claimed Names", _list_or_none(identifiers.get("caller_claimed_names", []))],
    ]
    story.append(_make_table(id_data))
    story.append(Spacer(1, 0.3 * cm))

    # ── Fact-Check History ────────────────────────────────────────────────────
    story.append(Paragraph("4. Real-Time Fact-Check Verdict History", _HEADING_STYLE))
    if factcheck_history:
        fc_data = [["Timestamp", "Status", "Message"]]
        for entry in factcheck_history:
            fc_data.append([
                entry.get("ts", ""),
                entry.get("status", ""),
                entry.get("message", "")[:120],
            ])
        t = Table(fc_data, colWidths=[4 * cm, 3 * cm, 9 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff0f0")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No fact-check verdicts recorded during this call.", _BODY_STYLE))

    story.append(Spacer(1, 0.3 * cm))

    # ── Transcript Summary ────────────────────────────────────────────────────
    story.append(Paragraph("5. Transcript Summary", _HEADING_STYLE))
    story.append(Paragraph(transcript_summary or "No transcript available.", _BODY_STYLE))

    # ── Scambaiter Log ────────────────────────────────────────────────────────
    if scambaiter_log:
        story.append(PageBreak())
        story.append(Paragraph("6. AI Scambaiter Exchange Log", _HEADING_STYLE))
        story.append(Paragraph(
            "The following exchanges were conducted by the PhaseGuard AI scambaiter persona "
            "('Ramesh Ji') to delay the scammer and gather additional evidence.",
            _BODY_STYLE,
        ))
        for i, exchange in enumerate(scambaiter_log):
            story.append(Paragraph(
                f"<b>Exchange {i+1}</b> [{exchange.get('ts', '')}]", _BODY_STYLE
            ))
            story.append(Paragraph(
                f"<b>Scammer:</b> {exchange.get('caller', '')}", _BODY_STYLE
            ))
            story.append(Paragraph(
                f"<b>Scambaiter:</b> {exchange.get('response', '')}", _BODY_STYLE
            ))
            story.append(Spacer(1, 0.2 * cm))

    # ── Escalation Records ────────────────────────────────────────────────────
    if escalation_records:
        story.append(Paragraph("7. Escalation Chain of Custody", _HEADING_STYLE))
        story.append(Paragraph(
            "All escalation attempts are logged here for chain-of-custody purposes. "
            "No escalation was sent without explicit human confirmation.",
            _BODY_STYLE,
        ))
        esc_data = [["Drafted At", "Confirmed At", "Destination", "Status"]]
        for rec in escalation_records:
            esc_data.append([
                rec.get("drafted_at", ""),
                rec.get("confirmed_at", "") or "NOT YET CONFIRMED",
                rec.get("destination", ""),
                rec.get("delivery_status", ""),
            ])
        t = Table(esc_data, colWidths=[4 * cm, 4 * cm, 5 * cm, 3 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t)

    # ── Footer note ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "This document was generated by PhaseGuard Anti-Scam OS. "
        "To report a cybercrime in India, visit: cybercrime.gov.in or call helpline 1930.",
        ParagraphStyle("footer", parent=_styles["Normal"], fontSize=8, textColor=colors.grey),
    ))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()
