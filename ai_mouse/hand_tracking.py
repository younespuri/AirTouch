"""MediaPipe HandLandmarker (Tasks API) wrapper that yields `Hand` objects."""
import os
import time

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from .hand import Hand

_CONNECTIONS = vision.HandLandmarksConnections.HAND_CONNECTIONS


class HandTracker:
    """Runs the MediaPipe HandLandmarker over a video stream."""

    def __init__(self, config):
        if not os.path.exists(config.model_path):
            raise FileNotFoundError(
                f"Hand model '{config.model_path}' not found. "
                "Fetch it once with:  python download_model.py"
            )
        options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=config.model_path),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=config.max_num_hands,
            min_hand_detection_confidence=config.detection_confidence,
            min_tracking_confidence=config.tracking_confidence,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._det_w = config.detection_width
        self._t0 = None
        self._last_ts = -1

    def _timestamp_ms(self) -> int:
        # VIDEO mode requires strictly increasing timestamps.
        now = time.monotonic()
        if self._t0 is None:
            self._t0 = now
        ts = int((now - self._t0) * 1000)
        if ts <= self._last_ts:
            ts = self._last_ts + 1
        self._last_ts = ts
        return ts

    def process(self, frame_bgr):
        h, w = frame_bgr.shape[:2]
        # Detect on a smaller copy for speed; landmarks are normalized (0-1),
        # so they map back onto the full-resolution frame unchanged.
        if self._det_w and w > self._det_w:
            det_h = int(round(h * self._det_w / w))
            small = cv2.resize(frame_bgr, (self._det_w, det_h), interpolation=cv2.INTER_AREA)
        else:
            small = frame_bgr
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB,
                            data=np.ascontiguousarray(rgb))
        result = self._landmarker.detect_for_video(mp_image, self._timestamp_ms())
        if not result.hand_landmarks:
            return None
        return Hand(result.hand_landmarks[0], w, h)

    def draw(self, frame_bgr, hand: Hand) -> None:
        for c in _CONNECTIONS:
            cv2.line(frame_bgr, hand.point(c.start), hand.point(c.end),
                     (0, 200, 0), 2, cv2.LINE_AA)
        for i in range(len(hand)):
            cv2.circle(frame_bgr, hand.point(i), 3, (0, 0, 255), -1, cv2.LINE_AA)

    def close(self) -> None:
        self._landmarker.close()
