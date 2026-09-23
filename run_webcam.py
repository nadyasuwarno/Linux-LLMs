"""Stage 2: live on your Mac's webcam, pretending to be the N80.

    python run_webcam.py            # shrinks each frame to 320x240, like the phone
    python run_webcam.py --full     # full webcam resolution (to compare)
    python run_webcam.py --quiet    # don't speak
    python run_webcam.py --llm      # narration rephrased by your node's model (see README)

A window shows what the model sees. Press  q  to quit.
The first run, macOS asks to let Terminal use the camera: allow it, then run again.
"""
import argparse
import time

import cv2

from vision.detector import Vision
from vision.media import MacVoice, phone_size
from vision.narrator import Narrator

ap = argparse.ArgumentParser()
ap.add_argument("--camera", type=int, default=0, help="0 = built-in webcam")
ap.add_argument("--full", action="store_true")
ap.add_argument("--quiet", action="store_true")
ap.add_argument("--llm", action="store_true")
ap.add_argument("--no-mediapipe", action="store_true")
a = ap.parse_args()

vision = Vision(use_mediapipe=not a.no_mediapipe)
narrator = Narrator(use_llm=a.llm)
voice = MacVoice(enabled=not a.quiet)

cam = cv2.VideoCapture(a.camera)
if not cam.isOpened():
    raise SystemExit("Can't open the camera. System Settings > Privacy & Security > Camera: allow Terminal.")

print("Running. Press q in the video window to quit.")
fps = 0.0
while True:
    ok, frame = cam.read()
    if not ok:
        print("Camera stopped sending frames.")
        break
    if not a.full:
        frame = phone_size(frame)

    t0 = time.time()
    result = vision.analyze(frame)
    text, speak = narrator.update(result)
    if speak:
        print(f"[{result['ms']} ms] {text}")
        voice.say(text)

    shown = vision.annotate(frame, result)
    fps = 0.9 * fps + 0.1 * (1.0 / max(time.time() - t0, 1e-3))
    cv2.putText(shown, f"{fps:4.1f} fps", (8, shown.shape[0] - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imshow("N80 vision (Mac preview) - press q to quit",
               cv2.resize(shown, None, fx=2, fy=2) if not a.full else shown)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cam.release()
cv2.destroyAllWindows()
