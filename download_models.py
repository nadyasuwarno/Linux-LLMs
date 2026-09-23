"""Step 1: download the three model files into models/. Run once:  python download_models.py"""
import urllib.request

from vision import config

FILES = {
    config.FACE_LANDMARKER:
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task",
    config.YUNET:
        "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
}

config.MODELS_DIR.mkdir(exist_ok=True)
for path, url in FILES.items():
    if path.exists():
        print(f"already have {path.name}")
        continue
    print(f"downloading {path.name} ...")
    urllib.request.urlretrieve(url, path)
    print(f"  saved {path.stat().st_size // 1024} KB")

# YOLO downloads itself the first time it is loaded:
from ultralytics import YOLO  # noqa: E402

YOLO(str(config.YOLO_MODEL))
print(f"have {config.YOLO_MODEL.name}")
print("All models ready.")
