"""On-screen heads-up display: current mode, status, gesture hints, FPS."""
import cv2

_FONT = cv2.FONT_HERSHEY_SIMPLEX
_FINGERS = [("I", "index"), ("M", "middle"), ("R", "ring"), ("P", "pinky")]


def render(frame, mode, fps: float, paused: bool, other_name: str = "", hand=None) -> None:
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 96), (0, 0, 0), -1)
    cv2.rectangle(frame, (0, 0), (w, 96), (0, 200, 255), 1)

    state = "PAUSED" if paused else mode.status
    color = (0, 0, 255) if paused else (0, 255, 0)
    cv2.putText(frame, f"MODE: {mode.name}   [{state}]", (16, 34),
                _FONT, 0.8, color, 2, cv2.LINE_AA)
    cv2.putText(frame, mode.hint, (16, 62),
                _FONT, 0.5, (230, 230, 230), 1, cv2.LINE_AA)

    tab = f"TAB -> {other_name}" if other_name else "TAB: switch mode"
    cv2.putText(frame, f"{tab}    SPACE: pause    Q: quit", (16, 86),
                _FONT, 0.5, (0, 200, 255), 1, cv2.LINE_AA)

    cv2.putText(frame, f"{fps:4.1f} FPS", (w - 130, 34),
                _FONT, 0.7, (0, 255, 255), 2, cv2.LINE_AA)

    # Live "which fingers are up" indicator -- helps you see what the app detects.
    if hand is not None:
        fingers = hand.fingers_up()
        cv2.putText(frame, "detected:", (w - 300, 70), _FONT, 0.45, (180, 180, 180), 1, cv2.LINE_AA)
        for i, (lab, key) in enumerate(_FINGERS):
            cx = w - 200 + i * 48
            up = fingers[key]
            col = (0, 255, 0) if up else (80, 80, 80)
            cv2.circle(frame, (cx, 66), 12, col, -1, cv2.LINE_AA)
            cv2.putText(frame, lab, (cx - 6, 71), _FONT, 0.5, (0, 0, 0), 2, cv2.LINE_AA)
