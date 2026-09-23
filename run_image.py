"""Stage 1: test the vision on ONE picture. No camera, no phone, no network.

    python run_image.py samples/my_photo.jpg
    python run_image.py samples/my_photo.jpg --phone     # shrink it to N80 size first

Prints what it found, the sentence it would say, and saves <name>_annotated.jpg.
"""
import argparse
import json
from pathlib import Path

import cv2

from vision.detector import Vision
from vision.media import phone_size
from vision.narrator import describe

ap = argparse.ArgumentParser()
ap.add_argument("image")
ap.add_argument("--phone", action="store_true", help="shrink to 320x240 like the N80 would")
ap.add_argument("--no-mediapipe", action="store_true", help="use OpenCV YuNet for faces instead")
a = ap.parse_args()

img = cv2.imread(a.image)
if img is None:
    raise SystemExit(f"Could not open {a.image}")
if a.phone:
    img = phone_size(img)

vision = Vision(use_mediapipe=not a.no_mediapipe)
result = vision.analyze(img)

print(json.dumps(result, indent=2))
print("\nSays:", describe(result))

out = Path(a.image).with_name(Path(a.image).stem + "_annotated.jpg")
cv2.imwrite(str(out), vision.annotate(img, result))
print("Saved:", out)
