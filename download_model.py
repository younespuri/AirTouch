"""Download the MediaPipe hand-landmarker model used by AI-Mouse.

The model file (~7.5 MB) is not stored in the repository. Run this once
before the first launch:

    python download_model.py
"""
import os
import urllib.request

URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
DEST = "hand_landmarker.task"


def main():
    if os.path.exists(DEST):
        print(f"'{DEST}' already present -- nothing to do.")
        return
    print(f"Downloading model to '{DEST}' ...")
    urllib.request.urlretrieve(URL, DEST)
    print(f"Done ({os.path.getsize(DEST) / 1e6:.1f} MB).")


if __name__ == "__main__":
    main()
