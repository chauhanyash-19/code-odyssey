"""
govt_export/chakshu_export.py — Generates a downloadable export format matching DoT's Chakshu/Sanchar Saathi.
"""
from __future__ import annotations
import io
import csv
import logging
from datetime import datetime, timezone
from core.connection_manager import manager

logger = logging.getLogger(__name__)

def generate_chakshu_csv(call_id: str) -> bytes:
    """Generate a CSV matching Chakshu portal reporting fields."""
    session = manager.require_session(call_id)
    
    # Extract fields based on session history
    caller_number = "UNKNOWN"
    if session.extracted_identifiers and session.extracted_identifiers.get('phone_numbers_mentioned'):
        caller_number = session.extracted_identifiers['phone_numbers_mentioned'][0]
    
    fraud_category = session.latest_ensemble_label if session.latest_ensemble_label else "UNKNOWN"
    date_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    transcript_summary = " ".join(session.transcript_history)[:500]
    description = f"Automated PhaseGuard Detection. Peak PDI: {session.peak_pdi:.2f}. Transcript: {transcript_summary}"
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Caller Number", "Fraud Category", "Date/Time", "Description"])
    writer.writerow([caller_number, fraud_category, date_time, description])
    
    return output.getvalue().encode('utf-8')
