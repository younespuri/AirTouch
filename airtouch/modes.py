"""Interaction modes. Each mode maps hand gestures to a different behavior.

Adding a new capability is as simple as writing another Mode subclass
and registering it in main.py.
"""
import os
import time

import cv2
import numpy as np

from .hand import INDEX_TIP, MIDDLE_TIP, THUMB_TIP
from .smoothing import Point2DFilter
from .toolbar import Toolbar


class Mode:
    """Base class. Subclasses map gestures to actions in process()."""

    name = "Mode"
    hint = ""

    def __init__(self, config):
        self.cfg = config
        self.status = "IDLE"

    def process(self, frame, hand, paused):
        """Handle one frame; return the image to display."""
        raise NotImplementedError

    def handle_key(self, key: int) -> bool:
        """Handle a mode-specific key press. Return True if consumed."""
        return False

    def reset(self) -> None:
        """Release any held state (called on pause / mode switch / exit)."""
        self.status = "IDLE"


class MouseMode(Mode):
    name = "Virtual Mouse"
    hint = "1 finger=move   pinch=click/drag   thumb+middle=right   2 fingers=scroll"

    def __init__(self, config, pg=None):
        super().__init__(config)
        # pyautogui is imported lazily (and can be injected for tests) so the
        # rest of the app does not need a display server just to load modes.
        if pg is None:
            import pyautogui as pg
        pg.FAILSAFE = False
        pg.PAUSE = 0
        self._pg = pg
        self.screen_w, self.screen_h = pg.size()
        # Velocity-adaptive smoothing keeps the cursor calm when still and
        # responsive when moving fast.
        self._filter = Point2DFilter(config.min_cutoff, config.beta)
        self._dragging = False
        self._right_armed = True
        self._scroll_anchor = None

    def reset(self):
        super().reset()
        if self._dragging:
            self._pg.mouseUp()
        self._dragging = False
        self._right_armed = True
        self._scroll_anchor = None
        self._filter.reset()

    def _move_cursor(self, hand, frame):
        fr = self.cfg.frame_reduction
        h, w = frame.shape[:2]
        x_px, y_px = hand.point(INDEX_TIP)
        sx = np.interp(x_px, (fr, w - fr), (0, self.screen_w))
        sy = np.interp(y_px, (fr, h - fr), (0, self.screen_h))
        sx, sy = self._filter(sx, sy)
        sx = float(np.clip(sx, 0, self.screen_w - 1))
        sy = float(np.clip(sy, 0, self.screen_h - 1))
        self._pg.moveTo(sx, sy)

    def process(self, frame, hand, paused):
        h, w = frame.shape[:2]
        fr = self.cfg.frame_reduction
        cv2.rectangle(frame, (fr, fr), (w - fr, h - fr), (255, 120, 0), 1)

        if paused or hand is None:
            if self._dragging:
                self._pg.mouseUp()
                self._dragging = False
            self.status = "PAUSED" if paused else "NO HAND"
            return frame

        fingers = hand.fingers_up()
        ti = hand.pinch_ratio(THUMB_TIP, INDEX_TIP)
        tm = hand.pinch_ratio(THUMB_TIP, MIDDLE_TIP)
        cursor = hand.point(INDEX_TIP)

        # 1) thumb-index pinch -> press and hold (tap = click, hold+move = drag)
        if ti < self.cfg.click_enter_ratio and not self._dragging:
            self._pg.mouseDown()
            self._dragging = True
        elif ti > self.cfg.click_exit_ratio and self._dragging:
            self._pg.mouseUp()
            self._dragging = False

        if self._dragging:
            self._move_cursor(hand, frame)
            self.status = "DRAG / CLICK"
            self._draw_cursor(frame, cursor, (0, 255, 0), filled=True)
            return frame

        # 2) thumb-middle pinch -> right click (fires once per pinch)
        if tm < self.cfg.click_enter_ratio:
            if self._right_armed:
                self._pg.rightClick()
                self._right_armed = False
            self.status = "RIGHT CLICK"
            self._draw_cursor(frame, cursor, (0, 165, 255), filled=True)
            return frame
        if tm > self.cfg.click_exit_ratio:
            self._right_armed = True

        # 3) index + middle up (V) -> scroll by vertical motion
        if fingers["index"] and fingers["middle"] and not fingers["ring"]:
            _, y_px = hand.point(INDEX_TIP)
            if self._scroll_anchor is None:
                self._scroll_anchor = y_px
            dy = self._scroll_anchor - y_px
            if abs(dy) > self.cfg.scroll_dead_zone:
                self._pg.scroll(int(np.sign(dy) * self.cfg.scroll_speed))
            self.status = "SCROLL"
            self._draw_cursor(frame, cursor, (255, 255, 0), filled=False)
            return frame
        self._scroll_anchor = None

        # 4) index up only -> move cursor
        if fingers["index"]:
            self._move_cursor(hand, frame)
            self.status = "MOVE"
            self._draw_cursor(frame, cursor, (0, 0, 255), filled=False)
            return frame

        self.status = "IDLE"
        return frame

    @staticmethod
    def _draw_cursor(frame, pt, color, filled):
        cv2.circle(frame, pt, 10, color, -1 if filled else 2, cv2.LINE_AA)


class WhiteboardMode(Mode):
    name = "Air Whiteboard"
    hint = "1 finger=write   open hand=erase   2 fingers=move   B=dim bg   hover bar=tools"

    COLORS = [
        (0, 255, 255),    # yellow
        (0, 255, 0),      # green
        (255, 128, 0),    # blue
        (0, 0, 255),      # red
        (255, 255, 255),  # white
    ]

    def __init__(self, config):
        super().__init__(config)
        self.canvas = None
        self.prev = None
        self.thickness = config.pen_thickness
        self.color_idx = 0
        self._dim_bg = False
        self._on = 0
        self._off = 0
        self._writing = False
        self._prev_action = None      # "write" | "erase" | None -> drives undo snapshots
        self._smooth = []
        self.toolbar = Toolbar(self.COLORS)
        self._undo = []
        self._hover_id = None
        self._dwell = 0

    def reset(self):
        super().reset()
        self.prev = None
        self._writing = False
        self._prev_action = None
        self._on = self._off = 0
        self._smooth = []
        self._hover_id = None
        self._dwell = 0

    def _ensure_canvas(self, frame):
        if self.canvas is None or self.canvas.shape != frame.shape:
            self.canvas = np.zeros_like(frame)

    def _compose(self, frame):
        """Blend the strokes over the camera, optionally dimming the camera."""
        bg = cv2.convertScaleAbs(frame, alpha=self.cfg.bg_dim) if self._dim_bg else frame
        return cv2.add(bg, self.canvas)

    def _snapshot(self):
        if self.canvas is None:
            return
        self._undo.append(self.canvas.copy())
        if len(self._undo) > self.cfg.undo_limit:
            self._undo.pop(0)

    def _undo_last(self):
        if self._undo:
            self.canvas = self._undo.pop()
            self.prev = None

    def _begin(self, action):
        """Take an undo snapshot the first frame an action (write/erase) starts."""
        if self._prev_action != action:
            self._snapshot()
        self._prev_action = action

    def _smoothed_point(self, hand):
        # A short moving average is enough for a pen tip; the cursor uses a
        # velocity-adaptive filter instead because it needs sub-pixel calm.
        x, y = hand.point(INDEX_TIP)
        self._smooth.append((x, y))
        if len(self._smooth) > self.cfg.pen_smoothing:
            self._smooth.pop(0)
        return (int(np.mean([p[0] for p in self._smooth])),
                int(np.mean([p[1] for p in self._smooth])))

    def process(self, frame, hand, paused):
        self._ensure_canvas(frame)

        if paused or hand is None:
            self.status = "PAUSED" if paused else "NO HAND"
            self.prev = None
            self._prev_action = None
            self._hover_id, self._dwell = None, 0
            out = self._compose(frame)
            self.toolbar.draw(out, self.color_idx, self.thickness)
            return out

        fingers = hand.fingers_up()
        open_hand = all(fingers.values())
        index_only = (fingers["index"] and not fingers["middle"]
                      and not fingers["ring"] and not fingers["pinky"])
        point = self._smoothed_point(hand)

        # --- Toolbar: dwell a raised finger over a button to select it ---
        if index_only and self.toolbar.in_region(point):
            b = self.toolbar.hit_test(point)
            bid = b["id"] if b else None
            if bid is not None and bid == self._hover_id:
                self._dwell += 1
            else:
                self._hover_id, self._dwell = bid, 0
            if b and self._dwell >= self.cfg.toolbar_dwell_frames:
                self._activate(b)
                self._dwell = 0
            self._writing = False
            self._prev_action = None
            self.prev = None
            self.status = "MENU"
            out = self._compose(frame)
            self.toolbar.draw(out, self.color_idx, self.thickness, self._hover_id,
                              self._dwell / max(1, self.cfg.toolbar_dwell_frames))
            self._draw_cursor(out, point, (0, 255, 0))
            return out
        self._hover_id, self._dwell = None, 0

        # --- Open hand -> erase ---
        if open_hand:
            self._begin("erase")
            cv2.circle(self.canvas, point, self.cfg.eraser_radius, (0, 0, 0), -1)
            self._writing = False
            self.prev = None
            self._on = self._off = 0
            self.status = "ERASING"
            out = self._compose(frame)
            cv2.circle(out, point, self.cfg.eraser_radius, (255, 255, 255), 2, cv2.LINE_AA)
            self.toolbar.draw(out, self.color_idx, self.thickness)
            return out

        # --- One finger up -> write (short stability filter avoids flicker) ---
        if index_only:
            self._on += 1
            self._off = 0
        else:
            self._off += 1
            self._on = 0
        if self._on >= self.cfg.stable_frames:
            self._writing = True
        if self._off >= self.cfg.stable_frames:
            self._writing = False
            self.prev = None

        color = self.COLORS[self.color_idx]
        if self._writing:
            self._begin("write")
            if self.prev is not None:
                cv2.line(self.canvas, self.prev, point, color, self.thickness, cv2.LINE_AA)
            self.prev = point
            self.status = "WRITING"
        else:
            self._prev_action = None
            self.prev = None
            self.status = "HOVER"

        out = self._compose(frame)
        ring = (0, 255, 0) if self._writing else (0, 0, 255)
        cv2.circle(out, point, 8, color, -1, cv2.LINE_AA)
        cv2.circle(out, point, 14, ring, 2, cv2.LINE_AA)
        self.toolbar.draw(out, self.color_idx, self.thickness)
        return out

    def _activate(self, b):
        kind = b["kind"]
        if kind == "color":
            self.color_idx = b["payload"]
        elif kind == "size":
            self.thickness = int(min(40, max(1, self.thickness + b["payload"])))
        elif kind == "undo":
            self._undo_last()
        elif kind == "clear":
            self._snapshot()
            self.canvas = np.zeros_like(self.canvas)
            self.prev = None
        elif kind == "save":
            self._save()

    @staticmethod
    def _draw_cursor(frame, pt, color):
        cv2.circle(frame, pt, 8, color, -1, cv2.LINE_AA)
        cv2.circle(frame, pt, 16, color, 2, cv2.LINE_AA)

    def handle_key(self, key):
        if key == ord("c"):
            self._snapshot()
            self.canvas = np.zeros_like(self.canvas)
            self.prev = None
            return True
        if key == ord("s"):
            self._save()
            return True
        if key == ord("n"):
            self.color_idx = (self.color_idx + 1) % len(self.COLORS)
            return True
        if key == ord("z"):
            self._undo_last()
            return True
        if key == ord("b"):
            self._dim_bg = not self._dim_bg
            return True
        if key == ord("["):
            self.thickness = max(1, self.thickness - 1)
            return True
        if key == ord("]"):
            self.thickness = min(40, self.thickness + 1)
            return True
        return False

    def _save(self):
        if self.canvas is None:
            return
        os.makedirs("outputs", exist_ok=True)
        path = os.path.join("outputs", f"whiteboard_{int(time.time())}.png")
        cv2.imwrite(path, self.canvas)
        print(f"[saved] {path}")
