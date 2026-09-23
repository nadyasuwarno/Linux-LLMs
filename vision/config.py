"""All the settings in one place. Change things here, not inside the other files."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"

# --- Objects: YOLO ---------------------------------------------------------
# "n" = nano, the smallest and fastest. Knows 80 everyday things (person, cup,
# laptop, dog, chair...). For more accuracy but slower, try "yolo26s.pt".
YOLO_MODEL = MODELS_DIR / "yolo26n.pt"
YOLO_CONF = 0.40        # ignore guesses below 40% confidence
YOLO_IMGSZ = 320        # the N80 sends tiny photos, so a small input size is enough

# --- Faces -----------------------------------------------------------------
# MediaPipe Face Landmarker: 478 face points + 52 "blendshape" scores
# (smile, jaw open, brows up...). We turn those into an expression word.
FACE_LANDMARKER = MODELS_DIR / "face_landmarker.task"
# OpenCV YuNet: a tiny, fast face *finder*. Used when MediaPipe isn't available.
YUNET = MODELS_DIR / "face_detection_yunet_2023mar.onnx"
MAX_FACES = 3

# --- The phone -------------------------------------------------------------
PHONE_FRAME = (320, 240)     # size the N80 sends (and we simulate on the Mac)
PHONE_SCREEN = (320, 240)    # size of the annotated picture we send back
JPEG_QUALITY = 60            # lower = smaller file = faster over old WiFi

# --- Server ----------------------------------------------------------------
SERVER_PORT = 8000

# --- Narration -------------------------------------------------------------
REPEAT_AFTER_S = 8.0   # say the same thing again only after this many seconds

# Optional: let a language model rephrase the narration. Off unless you pass --llm.
# The default points at Ollama through an SSH tunnel to your Oracle node
# (ssh -L 11434:127.0.0.1:11434 <your-node>), the same setup as the class Week 11 kit.
LLM_URL = "http://127.0.0.1:11434/v1/chat/completions"
LLM_MODEL = "qwen3.5:4b"
LLM_TIMEOUT_S = 6.0
