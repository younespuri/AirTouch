"""On-screen whiteboard toolbar.

Buttons are selected by dwelling the pointer over them (keyboard shortcuts
still work). The toolbar draws itself and hit-tests points; the mode owns
the actual actions.
"""
import cv2

_FONT = cv2.FONT_HERSHEY_SIMPLEX


class Toolbar:
    def __init__(self, colors, top: int = 104, height: int = 48, left: int = 16, gap: int = 8):
        self.colors = colors
        self._buttons = []
        x, y0, y1 = left, top, top + height

        for i in range(len(colors)):
            self._add(f"color{i}", "color", i, x, y0, x + 48, y1)
            x += 48 + gap
        x += gap
        self._add("size-", "size", -2, x, y0, x + 40, y1); x += 40 + gap
        self._size_box = (x, y0, x + 66, y1); x += 66 + gap
        self._add("size+", "size", +2, x, y0, x + 40, y1); x += 40 + gap
        self._add("undo", "undo", None, x, y0, x + 78, y1); x += 78 + gap
        self._add("clear", "clear", None, x, y0, x + 78, y1); x += 78 + gap
        self._add("save", "save", None, x, y0, x + 78, y1); x += 78 + gap

        self.region = (left - 6, top - 6, x, y1 + 6)

    def _add(self, bid, kind, payload, x0, y0, x1, y1):
        self._buttons.append({"id": bid, "kind": kind, "payload": payload,
                              "rect": (x0, y0, x1, y1)})

    def in_region(self, pt) -> bool:
        x0, y0, x1, y1 = self.region
        return x0 <= pt[0] <= x1 and y0 <= pt[1] <= y1

    def hit_test(self, pt):
        px, py = pt
        for b in self._buttons:
            x0, y0, x1, y1 = b["rect"]
            if x0 <= px <= x1 and y0 <= py <= y1:
                return b
        return None

    def draw(self, frame, color_idx, thickness, hovered_id=None, dwell=0.0) -> None:
        for b in self._buttons:
            x0, y0, x1, y1 = b["rect"]
            kind = b["kind"]
            if kind == "color":
                cv2.rectangle(frame, (x0, y0), (x1, y1), self.colors[b["payload"]], -1)
                border = (255, 255, 255) if b["payload"] == color_idx else (40, 40, 40)
                cv2.rectangle(frame, (x0, y0), (x1, y1), border,
                              3 if b["payload"] == color_idx else 1)
            else:
                cv2.rectangle(frame, (x0, y0), (x1, y1), (45, 45, 45), -1)
                cv2.rectangle(frame, (x0, y0), (x1, y1), (0, 200, 255), 1)
                if kind == "size":
                    label = "-" if b["payload"] < 0 else "+"
                else:
                    label = {"undo": "UNDO", "clear": "CLR", "save": "SAVE"}[kind]
                self._centered_text(frame, label, b["rect"],
                                    0.9 if kind == "size" else 0.5)
            if hovered_id == b["id"]:
                cv2.rectangle(frame, (x0, y0), (x1, y1), (0, 255, 0), 2)
                w = int((x1 - x0) * min(max(dwell, 0.0), 1.0))
                cv2.rectangle(frame, (x0, y1 - 4), (x0 + w, y1), (0, 255, 0), -1)

        # size read-out between the -/+ buttons
        x0, y0, x1, y1 = self._size_box
        cv2.rectangle(frame, (x0, y0), (x1, y1), (25, 25, 25), -1)
        cv2.rectangle(frame, (x0, y0), (x1, y1), (0, 200, 255), 1)
        self._centered_text(frame, str(thickness), self._size_box, 0.6)

    @staticmethod
    def _centered_text(frame, text, rect, scale):
        x0, y0, x1, y1 = rect
        (tw, th), _ = cv2.getTextSize(text, _FONT, scale, 2)
        tx = x0 + (x1 - x0 - tw) // 2
        ty = y0 + (y1 - y0 + th) // 2
        cv2.putText(frame, text, (tx, ty), _FONT, scale, (230, 230, 230), 2, cv2.LINE_AA)
