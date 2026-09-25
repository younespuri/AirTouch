"""Unit tests for the pure-logic parts (no webcam or model needed)."""
import numpy as np

from airtouch.hand import Hand
from airtouch.smoothing import OneEuroFilter
from airtouch.toolbar import Toolbar
from airtouch.modes import MouseMode, WhiteboardMode
from config import Config


class LM:
    """Minimal stand-in for a MediaPipe normalized landmark."""

    def __init__(self, x, y, z=0.0):
        self.x = x
        self.y = y
        self.z = z


def make_hand(index=False, middle=False, ring=False, pinky=False,
              index_tip=(0.58, 0.35), w=1280, h=720):
    lm = [LM(0.5, 0.7) for _ in range(21)]
    lm[0] = LM(0.5, 0.95)   # wrist
    lm[9] = LM(0.5, 0.60)   # middle MCP (palm reference)

    def finger(tip, pip, up, base_x):
        lm[pip] = LM(base_x, 0.60)
        lm[tip] = LM(base_x, 0.35) if up else LM(base_x, 0.72)

    finger(8, 6, index, 0.57)
    finger(12, 10, middle, 0.50)
    finger(16, 14, ring, 0.45)
    finger(20, 18, pinky, 0.40)
    lm[8] = LM(index_tip[0], index_tip[1])
    return Hand(lm, w, h)


def frame():
    return np.zeros((720, 1280, 3), np.uint8)


# --- One Euro Filter ---

def test_filter_passes_first_value():
    assert OneEuroFilter()(3.0, t=0.0) == 3.0


def test_filter_converges_to_constant():
    f = OneEuroFilter(min_cutoff=1.0, beta=0.0)
    t, out = 0.0, None
    for _ in range(60):
        t += 0.033
        out = f(10.0, t)
    assert abs(out - 10.0) < 0.5


# --- Hand geometry ---

def test_fingers_up_open_hand():
    assert make_hand(True, True, True, True).fingers_up() == {
        "index": True, "middle": True, "ring": True, "pinky": True}


def test_fingers_up_index_only():
    up = make_hand(True, False, False, False).fingers_up()
    assert up["index"] and not (up["middle"] or up["ring"] or up["pinky"])


def test_pinch_ratio_scale_invariant():
    a = make_hand(True, index_tip=(0.55, 0.4), w=1280, h=720).pinch_ratio()
    b = make_hand(True, index_tip=(0.55, 0.4), w=640, h=360).pinch_ratio()
    assert abs(a - b) < 1e-6


# --- Toolbar ---

def test_toolbar_first_button_is_color():
    tb = Toolbar(WhiteboardMode.COLORS)
    x0, y0, x1, y1 = tb._buttons[0]["rect"]
    hit = tb.hit_test(((x0 + x1) // 2, (y0 + y1) // 2))
    assert hit is not None and hit["kind"] == "color"


def test_toolbar_region_is_a_top_band():
    tb = Toolbar(WhiteboardMode.COLORS)
    assert tb.in_region((20, 120))
    assert not tb.in_region((20, 600))


# --- Whiteboard behavior ---

def test_write_paints_pixels():
    wb = WhiteboardMode(Config())
    for i in range(6):
        wb.process(frame(), make_hand(True, index_tip=(0.40 + i * 0.03, 0.35)), False)
    assert wb.status == "WRITING"
    assert (wb.canvas.sum(axis=2) > 0).sum() > 0


def test_dim_background_darkens():
    wb = WhiteboardMode(Config())
    f = np.full((720, 1280, 3), 200, np.uint8)   # bright gray, empty canvas
    wb._ensure_canvas(f)
    normal = wb._compose(f)
    wb._dim_bg = True
    dimmed = wb._compose(f)
    assert dimmed.mean() < normal.mean()


def test_open_hand_erases():
    wb = WhiteboardMode(Config())
    wb.process(frame(), make_hand(True, True, True, True, index_tip=(0.5, 0.35)), False)
    wb.canvas[:] = (0, 255, 255)
    for _ in range(5):
        wb.process(frame(), make_hand(True, True, True, True, index_tip=(0.5, 0.35)), False)
    assert wb.status == "ERASING"
    assert int(wb.canvas[252, 640].sum()) == 0   # y=0.35*720, x=0.5*1280


def test_undo_reverts_a_stroke():
    wb = WhiteboardMode(Config())
    for i in range(6):
        wb.process(frame(), make_hand(True, index_tip=(0.40 + i * 0.03, 0.35)), False)
    painted = (wb.canvas.sum(axis=2) > 0).sum()
    assert painted > 0
    wb.handle_key(ord("z"))
    assert (wb.canvas.sum(axis=2) > 0).sum() < painted


# --- Virtual mouse (pyautogui injected as a fake) ---

class FakeMouse:
    """Records the calls MouseMode makes instead of moving the real cursor."""

    def __init__(self):
        self.events = []
        self.FAILSAFE = True
        self.PAUSE = 0.1

    def size(self):
        return (1920, 1080)

    def moveTo(self, x, y):
        self.events.append(("move", x, y))

    def mouseDown(self):
        self.events.append(("down",))

    def mouseUp(self):
        self.events.append(("up",))

    def rightClick(self):
        self.events.append(("right",))

    def scroll(self, amount):
        self.events.append(("scroll", amount))


def mouse_hand(index=True, middle=False, thumb_index=False, thumb_middle=False,
               index_tip=(0.5, 0.35)):
    """A hand posed for a mouse gesture; optionally pinch thumb to index/middle."""
    h = make_hand(index, middle, False, False, index_tip=index_tip)
    if thumb_index:
        tip = h._lm[8]
        h._lm[4] = LM(tip.x + 0.005, tip.y + 0.005)
    elif thumb_middle:
        tip = h._lm[12]
        h._lm[4] = LM(tip.x + 0.005, tip.y + 0.005)
    else:
        h._lm[4] = LM(0.2, 0.5)   # thumb far from both -> no pinch
    return h


def test_mouse_move_calls_moveto():
    pg = FakeMouse()
    m = MouseMode(Config(), pg=pg)
    m.process(frame(), mouse_hand(index=True), False)
    assert any(e[0] == "move" for e in pg.events)
    assert m.status == "MOVE"


def test_mouse_pinch_presses_then_releases():
    pg = FakeMouse()
    m = MouseMode(Config(), pg=pg)
    m.process(frame(), mouse_hand(index=True, thumb_index=True), False)
    assert ("down",) in pg.events and m._dragging
    m.process(frame(), mouse_hand(index=True, thumb_index=False), False)
    assert ("up",) in pg.events and not m._dragging


def test_mouse_right_click_fires_once_per_pinch():
    pg = FakeMouse()
    m = MouseMode(Config(), pg=pg)
    for _ in range(3):
        m.process(frame(), mouse_hand(index=False, thumb_middle=True), False)
    assert sum(1 for e in pg.events if e == ("right",)) == 1


def test_mouse_scroll_on_vertical_motion():
    pg = FakeMouse()
    m = MouseMode(Config(), pg=pg)
    for i in range(4):
        m.process(frame(), mouse_hand(index=True, middle=True,
                                      index_tip=(0.5, 0.5 - i * 0.05)), False)
    assert any(e[0] == "scroll" for e in pg.events)
    assert m.status == "SCROLL"
