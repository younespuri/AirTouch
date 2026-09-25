"""Pure-geometry hand model (no camera or ML dependencies).

Kept separate from `hand_tracking` so the geometry can be unit-tested and
reused without importing MediaPipe or OpenCV.
"""
import math

# MediaPipe hand-landmark indices we rely on.
WRIST = 0
THUMB_TIP = 4
INDEX_TIP = 8
MIDDLE_TIP = 12
RING_TIP = 16
PINKY_TIP = 20
MIDDLE_MCP = 9

# tip -> pip pairs used to decide whether a finger is extended.
_FINGERS = {
    "index": (8, 6),
    "middle": (12, 10),
    "ring": (16, 14),
    "pinky": (20, 18),
}

# A finger counts as extended when its tip is this much farther from the wrist
# than its PIP joint. Higher = stricter (finger must be more clearly straight).
FINGER_EXTEND_MARGIN = 1.1


class Hand:
    """A single detected hand for one frame, with geometry helpers.

    `landmarks` is any sequence of 21 objects exposing normalized .x/.y
    (0..1) attributes -- e.g. MediaPipe's NormalizedLandmark list.
    """

    def __init__(self, landmarks, width: int, height: int):
        self._lm = landmarks
        self.width = width
        self.height = height

    def __len__(self):
        return len(self._lm)

    def point(self, idx: int):
        """Landmark position in pixel coordinates."""
        p = self._lm[idx]
        return int(p.x * self.width), int(p.y * self.height)

    def distance(self, a: int, b: int) -> float:
        """Pixel distance between two landmarks."""
        pa, pb = self._lm[a], self._lm[b]
        return math.hypot((pa.x - pb.x) * self.width, (pa.y - pb.y) * self.height)

    @property
    def size(self) -> float:
        """Palm reference length; makes thresholds scale-invariant."""
        return self.distance(WRIST, MIDDLE_MCP) + 1e-6

    def fingers_up(self, margin: float = FINGER_EXTEND_MARGIN) -> dict:
        """Whether each of the four fingers is extended (thumb excluded)."""
        up = {}
        for name, (tip, pip) in _FINGERS.items():
            up[name] = self.distance(tip, WRIST) > self.distance(pip, WRIST) * margin
        return up

    def pinch_ratio(self, tip_a: int = THUMB_TIP, tip_b: int = INDEX_TIP) -> float:
        """Distance between two fingertips, normalized by hand size."""
        return self.distance(tip_a, tip_b) / self.size
