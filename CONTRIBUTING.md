# Contributing to AirTouch

Thanks for helping make AirTouch better! Bug reports, gesture ideas and pull requests are all welcome.

## Getting started

```bash
git clone https://github.com/younespuri/AirTouch.git
cd AirTouch
python -m venv .venv
# Windows: .venv\Scripts\activate   macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
python download_model.py   # fetches the MediaPipe hand model
python main.py
```

## Running the tests

```bash
pytest
```

The tests cover the gesture logic, smoothing and toolbar without needing a webcam, so they run anywhere (including CI).

## Making a change

1. Open an issue first for anything bigger than a small fix, so we can agree on the approach.
2. Create a branch from `main`.
3. Keep gesture thresholds and tunable values in `config.py` rather than hard-coding them.
4. Add or update tests in `tests/` when you change gesture or smoothing logic.
5. Make sure `pytest` passes, then open a pull request and describe how you tested it with a webcam.

## Good first contributions

The [roadmap](README.md#roadmap) lists features that are ready to pick up, such as shape snapping on the whiteboard or exporting drawings as PNG. Testing on macOS or Linux and reporting what works is also very helpful.
