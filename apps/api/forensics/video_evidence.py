"""
forensics/video_evidence.py — Automated video-frame evidence capture.

PRIVACY & SCOPE NOTICE:
This module performs presence detection and evidence capture ONLY.
It does NOT perform facial recognition, identity matching, or any lookup
against external databases. Automated identification of individuals from
captured frames is strictly out of scope and should not be added.
This capability requires law-enforcement legal authority, not a third-party
app, and carries serious misidentification/misuse risk.

Frames originate from user-consented screen capture, not any call-tapping
mechanism.
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Path to the pre-trained Haar Cascade for frontal face detection
# OpenCV bundles this XML file. We locate it via cv2.data.haarcascades
CASCADE_PATH = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
_face_cascade = cv2.CascadeClassifier(CASCADE_PATH)


def process_test_frame(image_path: str, call_id: str) -> Optional[Dict[str, Any]]:
    """
    Process a video frame (stubbed via a test image path).
    
    1. Reads the image.
    2. Runs Haar Cascade to detect if at least one face is present.
    3. Computes SHA-256 hash of the image bytes for chain-of-custody.
    4. Returns metadata.

    Returns None if the image cannot be read.
    """
    if not os.path.exists(image_path):
        logger.warning(f"Video evidence stub: test image not found at {image_path}")
        return None

    try:
        # Read the raw bytes for hashing
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        return process_frame_bytes(image_bytes, call_id, local_path=image_path)

    except Exception as e:
        logger.error(f"Error processing video evidence frame from path: {e}", exc_info=True)
        return None

def process_frame_bytes(image_bytes: bytes, call_id: str, local_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Process a video frame from raw bytes.
    
    1. Runs Haar Cascade to detect if at least one face is present.
    2. Computes SHA-256 hash of the image bytes for chain-of-custody.
    3. Returns metadata.

    Returns None if the image cannot be read.
    """
    try:
        # Compute SHA-256
        sha256_hash = hashlib.sha256(image_bytes).hexdigest()

        # Load image for OpenCV presence detection from bytes
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if img is None:
            logger.warning("Video evidence: cv2 failed to decode image bytes")
            return None

        # Convert to grayscale for Haar Cascade
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect faces (presence only)
        faces = _face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        face_detected = len(faces) > 0
        
        logger.info(f"Video evidence processed: call_id={call_id} hash={sha256_hash[:8]}... face_detected={face_detected}")

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "call_id": call_id,
            "sha256_hash": sha256_hash,
            "face_detected": face_detected,
            "local_path": local_path,
        }

    except Exception as e:
        logger.error(f"Error processing video evidence frame: {e}", exc_info=True)
        return None
