"""Small shared helpers: resizing like the phone does, JPEG in/out, speaking on the Mac."""
import shutil
import subprocess

import cv2
import numpy as np

from . import config


def phone_size(bgr, size=config.PHONE_FRAME):
    """Shrink a picture to what the N80 would send (fits inside 320x240, keeps shape)."""
    h, w = bgr.shape[:2]
    s = min(size[0] / w, size[1] / h, 1.0)
    return cv2.resize(bgr, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA) if s < 1 else bgr


def to_jpeg(bgr, quality=config.JPEG_QUALITY):
    ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes() if ok else b""


def from_jpeg(data):
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("not a readable image")
    return img


class MacVoice:
    """Speaks with macOS's built-in `say`. Skips a sentence if still talking."""

    def __init__(self, enabled=True):
        self.enabled = enabled and shutil.which("say") is not None
        self.proc = None

    def say(self, text):
        if not self.enabled or not text:
            return
        if self.proc is not None and self.proc.poll() is None:
            return  # still speaking the last sentence
        self.proc = subprocess.Popen(["say", text])
