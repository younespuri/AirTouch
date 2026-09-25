# AI-Mouse

Control your computer with hand gestures through your webcam — a **virtual mouse**
and an **air whiteboard**, both driven by a shared real-time hand-tracking engine.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![OpenCV](https://img.shields.io/badge/OpenCV-green)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Hands-orange)
![CI](https://github.com/younespuri/AI-Mouse/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/License-MIT-yellow)

<!-- Demo: record ~10s of writing, erasing and cursor control, save it as
     docs/demo.gif, then replace this comment with:  ![demo](docs/demo.gif) -->

## Highlights

- **Virtual mouse** — move, left click, right click, click-and-drag, and scroll with one hand.
- **Air whiteboard** — write with one finger, erase with an open hand, and use an on-screen toolbar (colors, brush size, undo, clear, save) driven by hovering. Full undo history.
- **Jitter-free pointing** — cursor coordinates run through a [One Euro Filter](https://gery.casiez.net/1euro/), the same technique used in professional motion tracking, for smoothing without lag.
- **Scale-invariant gestures** — every threshold is normalized to the detected hand size, so gestures work at different distances from the camera.
- **Modular architecture** — a shared tracking engine plus swappable interaction modes; adding a new mode is one small class. Pure logic is split from the camera/ML layer and covered by a unit-test suite that runs in CI.

## Gestures

### Virtual Mouse
| Gesture | Action |
| --- | --- |
| Index finger up | Move cursor |
| Index + middle up (a "V"), move hand up/down | Scroll |
| Thumb + index pinch | Left click (tap) / drag (hold and move) |
| Thumb + middle pinch | Right click |
| Relaxed hand | Idle (no action) |

### Air Whiteboard
| Gesture / Key | Action |
| --- | --- |
| Index finger up | Write |
| Open hand (all fingers up) | Erase |
| Two fingers up | Move without drawing |
| Hover a toolbar button (top bar) | Pick color / brush size / undo / clear / save |
| `C` | Clear the whole canvas |
| `Z` | Undo the last stroke |
| `B` | Dim the camera background so strokes stand out |
| `S` | Save the drawing to `outputs/` |
| `[` / `]` | Decrease / increase pen thickness |
| `N` | Cycle pen color |

### Global keys
| Key | Action |
| --- | --- |
| `TAB` | Switch mode |
| `SPACE` | Pause / resume control |
| `Q` or `ESC` | Quit |

## Installation

```bash
git clone https://github.com/younespuri/AI-Mouse.git
cd AI-Mouse

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

# fetch the hand-tracking model (~7.5 MB, not stored in the repo)
python download_model.py
```

## Usage

```bash
python main.py                 # air whiteboard (default)
python main.py --mode mouse    # virtual-mouse mode
python main.py --camera 1      # pick another webcam
```

Press `SPACE` to pause any time the cursor gets away from you, and `Q` to quit.

## How it works

1. **MediaPipe HandLandmarker** (Tasks API, video mode) detects 21 landmarks per frame from the webcam.
2. `ai_mouse/hand_tracking.py` wraps those landmarks with geometry helpers — finger states and pinch ratios — all normalized by palm size, so gestures stay robust as you move closer or farther.
3. Each mode in `ai_mouse/modes.py` maps gestures to actions. The virtual mouse maps an *active region* of the frame onto the full screen and drives the OS cursor through **PyAutoGUI**.
4. Cursor coordinates pass through a **One Euro Filter** (`ai_mouse/smoothing.py`) that removes hand tremor while keeping fast motion responsive.

## Project structure

```
AI-Mouse/
├── main.py                 # entry point: capture loop + mode switching
├── download_model.py       # fetches the hand-landmarker model
├── config.py               # every tunable parameter in one place
├── ai_mouse/
│   ├── hand.py             # pure hand geometry (no camera/ML deps)
│   ├── hand_tracking.py    # MediaPipe HandLandmarker wrapper
│   ├── smoothing.py        # One Euro Filter
│   ├── modes.py            # MouseMode, WhiteboardMode
│   ├── toolbar.py          # on-screen whiteboard toolbar
│   └── hud.py              # on-screen overlay
├── tests/                  # unit tests (pytest)
├── .github/workflows/      # continuous integration
├── requirements.txt
└── README.md
```

## Tuning

All thresholds live in [`config.py`](config.py). If a gesture triggers too easily
or not enough, adjust the matching `*_ratio` (lower = harder to trigger). Cursor
feel is controlled by `min_cutoff` and `beta` of the One Euro Filter.

**Performance:** detection runs on a downscaled copy of each frame (`detection_width`,
default 640 px) while the display stays full resolution. Lower it for more speed on
weak hardware, or set it to `0` to detect at full resolution.

**Writing feel:** `pen_smoothing` sets how many recent points are averaged for the pen
(higher = smoother but slightly laggier). `bg_dim` sets how dark the camera goes when you
press `B`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The suite covers the smoothing filter, hand geometry, the toolbar, and the
whiteboard's write / erase / undo logic — no webcam or model download needed.
It runs automatically on every push via GitHub Actions.

## Roadmap

- [ ] Two-hand support
- [ ] User-recorded custom gestures
- [ ] Shape/stroke recognition in the whiteboard

## License

Released under the [MIT License](LICENSE).
