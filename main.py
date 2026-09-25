"""AirTouch: gesture-controlled virtual mouse and air whiteboard.

Run:
    python main.py                    # start in virtual-mouse mode
    python main.py --mode whiteboard  # start in whiteboard mode
    python main.py --camera 1         # use a different webcam

Keys:
    TAB    switch mode
    SPACE  pause / resume control
    Q/ESC  quit
    Whiteboard: C clear | S save | [ ] thickness | N color
"""
import argparse
import time

import cv2

from airtouch.hand_tracking import HandTracker
from airtouch.hud import render as render_hud
from airtouch.modes import MouseMode, WhiteboardMode
from config import Config


def parse_args():
    p = argparse.ArgumentParser(description="AirTouch gesture control")
    p.add_argument("--camera", type=int, default=None, help="camera index")
    p.add_argument("--width", type=int, default=None, help="capture width")
    p.add_argument("--height", type=int, default=None, help="capture height")
    p.add_argument("--mode", choices=["mouse", "whiteboard"], default="whiteboard",
                   help="mode to start in")
    return p.parse_args()


def main():
    args = parse_args()
    cfg = Config()
    if args.camera is not None:
        cfg.camera_index = args.camera
    if args.width:
        cfg.frame_width = args.width
    if args.height:
        cfg.frame_height = args.height

    cam = cv2.VideoCapture(cfg.camera_index)
    if not cam.isOpened():
        raise SystemExit("[ERROR] Could not open camera. Try a different index: --camera 1")
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.frame_width)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.frame_height)

    tracker = HandTracker(cfg)
    modes = [MouseMode(cfg), WhiteboardMode(cfg)]
    idx = 0 if args.mode == "mouse" else 1

    window = "AirTouch"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window, cfg.frame_width, cfg.frame_height)

    paused = False
    prev_t = time.monotonic()
    fps = 0.0

    print("AirTouch running.  TAB=switch  SPACE=pause  Q=quit")
    try:
        while True:
            ok, frame = cam.read()
            if not ok:
                print("[ERROR] camera read failed")
                break
            if cfg.flip_horizontal:
                frame = cv2.flip(frame, 1)

            hand = tracker.process(frame)
            if hand is not None:
                tracker.draw(frame, hand)

            mode = modes[idx]
            output = mode.process(frame, hand, paused)

            now = time.monotonic()
            dt = now - prev_t
            prev_t = now
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt)  # smoothed FPS

            other_name = modes[(idx + 1) % len(modes)].name
            render_hud(output, mode, fps, paused, other_name, hand)
            cv2.imshow(window, output)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):  # Q or ESC
                break
            if key == 9:  # TAB
                mode.reset()
                idx = (idx + 1) % len(modes)
            elif key == 32:  # SPACE
                paused = not paused
                if paused:
                    mode.reset()
            elif key != 255:
                mode.handle_key(key)
    finally:
        for m in modes:
            m.reset()
        cam.release()
        tracker.close()
        cv2.destroyAllWindows()
        print("AirTouch stopped")


if __name__ == "__main__":
    main()
