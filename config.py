"""Central configuration for the AI-Mouse gesture-control suite.

Every tunable number lives here so behavior can be adjusted without
touching the logic. All gesture thresholds are ratios relative to the
detected hand size, which keeps them stable at different distances
from the camera.
"""
from dataclasses import dataclass


@dataclass
class Config:
    # --- Camera ---
    camera_index: int = 0
    frame_width: int = 1280
    frame_height: int = 720
    flip_horizontal: bool = True

    # --- Hand tracking (MediaPipe Tasks) ---
    model_path: str = "hand_landmarker.task"   # run download_model.py to fetch it
    max_num_hands: int = 1
    detection_confidence: float = 0.7
    tracking_confidence: float = 0.7
    # Run detection on a frame downscaled to this width (0 = full resolution).
    # The display stays full-res; smaller = faster and lighter on the CPU.
    detection_width: int = 640

    # --- Cursor smoothing (One Euro Filter) ---
    min_cutoff: float = 1.0
    beta: float = 0.007

    # --- Virtual mouse ---
    frame_reduction: int = 120        # margin (px) of the active region
    click_enter_ratio: float = 0.40   # thumb-index pinch tight enough to press
    click_exit_ratio: float = 0.60    # release threshold (hysteresis)
    scroll_speed: int = 40            # scroll step size
    scroll_dead_zone: int = 12        # ignore vertical motion smaller than this (px)

    # --- Air whiteboard ---
    pen_thickness: int = 6
    pen_smoothing: int = 7            # moving-average window for the pen (higher = smoother)
    eraser_radius: int = 45           # size of the open-hand eraser
    stable_frames: int = 3            # frames a gesture must hold before it counts
    toolbar_dwell_frames: int = 12    # frames to hover a toolbar button before it fires
    undo_limit: int = 20              # how many strokes can be undone
    bg_dim: float = 0.25             # brightness of the camera behind the canvas when dimmed (B)
