"""The eyes of the system: looks at one picture and reports what is in it.

    vision = Vision()
    result = vision.analyze(picture)          # picture = an OpenCV image (BGR)
    drawn  = vision.annotate(picture, result) # same picture with boxes and labels

`result` is a plain dict, so it is easy to print, send as JSON, or turn into speech:

    {"objects": [{"label": "cup", "conf": 0.78, "box": [x1, y1, x2, y2]}, ...],
     "faces":   [{"expression": "smiling", "box": [...], "scores": {...}}, ...],
     "face_engine": "mediapipe" | "yunet" | "none",
     "ms": 42}
"""
import time

import cv2
import numpy as np

from . import config


class Vision:
    def __init__(self, use_mediapipe=True):
        # 1. Objects: YOLO. Downloads the weights the first time (a few MB).
        from ultralytics import YOLO, settings

        settings.update({"sync": False})   # don't send usage analytics to Ultralytics
        config.MODELS_DIR.mkdir(exist_ok=True)
        self.yolo = YOLO(str(config.YOLO_MODEL))

        # 2. Faces + expressions: MediaPipe, if its model file is present.
        self.landmarker = None
        if use_mediapipe and config.FACE_LANDMARKER.exists():
            try:
                import mediapipe as mp
                from mediapipe.tasks.python import BaseOptions, vision as mp_vision

                opts = mp_vision.FaceLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=str(config.FACE_LANDMARKER)),
                    num_faces=config.MAX_FACES,
                    output_face_blendshapes=True,
                )
                self.landmarker = mp_vision.FaceLandmarker.create_from_options(opts)
                self._mp = mp
            except Exception as e:  # keep going without it
                print(f"[vision] MediaPipe not available ({e}); using OpenCV YuNet for faces.")

        # 3. Faces (boxes only): OpenCV's YuNet, as a fallback.
        self.yunet = None
        if self.landmarker is None and config.YUNET.exists():
            self.yunet = cv2.FaceDetectorYN.create(str(config.YUNET), "", (320, 320), 0.7)

        self.face_engine = "mediapipe" if self.landmarker else ("yunet" if self.yunet else "none")
        print(f"[vision] objects: {config.YOLO_MODEL.name} | faces: {self.face_engine}")

    # ------------------------------------------------------------------ analyze
    def analyze(self, bgr):
        t0 = time.time()
        result = {
            "objects": self._objects(bgr),
            "faces": self._faces(bgr),
            "face_engine": self.face_engine,
        }
        result["ms"] = int((time.time() - t0) * 1000)
        return result

    def _objects(self, bgr):
        r = self.yolo.predict(bgr, imgsz=config.YOLO_IMGSZ, conf=config.YOLO_CONF, verbose=False)[0]
        out = []
        for box, cls, conf in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist(), r.boxes.conf.tolist()):
            out.append({
                "label": r.names[int(cls)],
                "conf": round(float(conf), 2),
                "box": [int(v) for v in box],
            })
        out.sort(key=lambda o: -o["conf"])
        return out

    def _faces(self, bgr):
        h, w = bgr.shape[:2]
        faces = []

        if self.landmarker is not None:
            rgb = np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
            res = self.landmarker.detect(image)
            for i, points in enumerate(res.face_landmarks):
                xs = [p.x * w for p in points]
                ys = [p.y * h for p in points]
                box = [int(max(0, min(xs))), int(max(0, min(ys))), int(min(w, max(xs))), int(min(h, max(ys)))]
                scores = {}
                if res.face_blendshapes and i < len(res.face_blendshapes):
                    scores = {c.category_name: round(float(c.score), 2) for c in res.face_blendshapes[i]}
                faces.append({"expression": expression_from_blendshapes(scores), "box": box,
                              "scores": pick_scores(scores)})

        elif self.yunet is not None:
            self.yunet.setInputSize((w, h))
            _, found = self.yunet.detect(bgr)
            for f in (found if found is not None else [])[: config.MAX_FACES]:
                x, y, fw, fh = [int(v) for v in f[:4]]
                faces.append({"expression": None, "box": [x, y, x + fw, y + fh], "scores": {}})

        return faces

    # ----------------------------------------------------------------- annotate
    def annotate(self, bgr, result):
        """Draw boxes and labels onto a copy of the picture."""
        img = bgr.copy()
        scale = max(img.shape[1] / 640.0, 0.5)   # keep text readable on small and big images
        thick = max(1, int(round(2 * scale)))

        for o in result["objects"]:
            x1, y1, x2, y2 = o["box"]
            color = (60, 200, 60) if o["label"] != "person" else (255, 170, 40)
            cv2.rectangle(img, (x1, y1), (x2, y2), color, thick)
            _label(img, f'{o["label"]} {int(o["conf"] * 100)}%', (x1, y1), color, scale)

        for f in result["faces"]:
            x1, y1, x2, y2 = f["box"]
            cv2.rectangle(img, (x1, y1), (x2, y2), (60, 60, 240), thick)
            if f["expression"]:
                _label(img, f["expression"], (x1, y2 + int(18 * scale)), (60, 60, 240), scale)
        return img


# -------------------------------------------------------------------- helpers
def expression_from_blendshapes(s):
    """Turn MediaPipe's 52 face scores (0..1) into one word. Simple rules you can tune."""
    if not s:
        return None
    g = lambda k: s.get(k, 0.0)
    smile = (g("mouthSmileLeft") + g("mouthSmileRight")) / 2
    frown = (g("mouthFrownLeft") + g("mouthFrownRight")) / 2
    brow_down = (g("browDownLeft") + g("browDownRight")) / 2
    blink = (g("eyeBlinkLeft") + g("eyeBlinkRight")) / 2
    jaw, brow_up = g("jawOpen"), g("browInnerUp")

    if jaw > 0.45 and brow_up > 0.35:
        return "surprised"
    if smile > 0.45:
        return "smiling"
    if brow_down > 0.45:
        return "frowning"
    if frown > 0.35:
        return "sad"
    if jaw > 0.45:
        return "mouth open"
    if blink > 0.6:
        return "eyes closed"
    return "neutral"


def pick_scores(s):
    keys = ["mouthSmileLeft", "mouthSmileRight", "jawOpen", "browInnerUp",
            "browDownLeft", "mouthFrownLeft", "eyeBlinkLeft"]
    return {k: s[k] for k in keys if k in s}


def _label(img, text, org, color, scale):
    font, fs = cv2.FONT_HERSHEY_SIMPLEX, 0.5 * scale
    (tw, th), _ = cv2.getTextSize(text, font, fs, 1)
    x, y = org[0], max(org[1], th + 4)
    cv2.rectangle(img, (x, y - th - 4), (x + tw + 4, y), color, -1)
    cv2.putText(img, text, (x + 2, y - 3), font, fs, (255, 255, 255), 1, cv2.LINE_AA)
