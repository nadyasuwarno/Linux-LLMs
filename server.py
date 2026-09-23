"""Stage 3: the brain as a server. The N80 (or fake_phone.py) sends photos here.

    python server.py                 # listens on port 8000
    python server.py --mac-say       # the Mac also speaks (handy while testing)
    python server.py --llm           # narration rephrased by your node's model

It prints the addresses it can be reached at. Open http://localhost:8000 in a
browser to watch what the phone is seeing.

What the phone talks to (kept deliberately simple for a 2006 phone):

  GET  /ping           -> "ok"
  POST /frame          body = one JPEG photo
                       -> plain text, one "key=value" per line:
                            speak=1
                            text=I see a person and a cup.
                            objects=person:0.91,cup:0.78
                            faces=smiling
                            ms=41
  GET  /annotated.jpg  -> the last photo with boxes drawn on, sized for the N80 screen
  GET  /last.json      -> everything about the last photo, for debugging
"""
import argparse
import json
import socket
import threading
import time

from flask import Flask, Response, request

from vision import config
from vision.detector import Vision
from vision.media import MacVoice, from_jpeg, phone_size, to_jpeg
from vision.narrator import Narrator

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=config.SERVER_PORT)
ap.add_argument("--mac-say", action="store_true")
ap.add_argument("--llm", action="store_true")
ap.add_argument("--no-mediapipe", action="store_true")
a = ap.parse_args()

vision = Vision(use_mediapipe=not a.no_mediapipe)
narrator = Narrator(use_llm=a.llm)
voice = MacVoice(enabled=a.mac_say)
lock = threading.Lock()        # one photo at a time through the models
last = {"jpeg": b"", "result": None, "text": "", "time": 0.0, "client": ""}

app = Flask(__name__)


@app.get("/ping")
def ping():
    return Response("ok\n", mimetype="text/plain")


@app.post("/frame")
def frame():
    data = request.get_data()
    if not data and "image" in request.files:          # also accept a form upload
        data = request.files["image"].read()
    try:
        img = from_jpeg(data)
    except ValueError:
        return Response("error=not a JPEG\n", status=400, mimetype="text/plain")

    with lock:
        result = vision.analyze(img)
        text, speak = narrator.update(result)
        annotated = phone_size(vision.annotate(img, result), config.PHONE_SCREEN)
        last.update(jpeg=to_jpeg(annotated, 75), result=result, text=text,
                    time=time.time(), client=request.args.get("client", request.remote_addr))

    if speak:
        print(f"[{last['client']}] {result['ms']} ms: {text}")
        voice.say(text)

    lines = [
        f"speak={1 if speak else 0}",
        f"text={text}",
        "objects=" + ",".join(f'{o["label"]}:{o["conf"]}' for o in result["objects"]),
        "faces=" + ",".join(f["expression"] or "face" for f in result["faces"]),
        f"ms={result['ms']}",
    ]
    return Response("\n".join(lines) + "\n", mimetype="text/plain")


@app.get("/annotated.jpg")
def annotated():
    if not last["jpeg"]:
        return Response("no photo yet\n", status=404, mimetype="text/plain")
    return Response(last["jpeg"], mimetype="image/jpeg")


@app.get("/last.json")
def last_json():
    return Response(json.dumps({k: v for k, v in last.items() if k != "jpeg"}, indent=2),
                    mimetype="application/json")


@app.get("/")
def home():
    return """<!doctype html><title>N80 vision</title>
<body style="background:#111;color:#eee;font:16px system-ui;text-align:center">
<h2>What the N80 sees</h2>
<img id=i style="width:640px;max-width:95vw;image-rendering:pixelated;border:1px solid #444">
<p id=t style="font-size:22px">waiting for the first photo...</p>
<script>
setInterval(async () => {
  const r = await fetch('/last.json'); const j = await r.json();
  if (j.result) { document.getElementById('t').textContent = j.text;
                  document.getElementById('i').src = '/annotated.jpg?' + j.time; }
}, 700);
</script>"""


def my_addresses():
    ips = set()
    try:  # the address other devices on your WiFi use to reach this Mac
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.168.0.1", 1))
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    return sorted(ips - {"0.0.0.0"})


if __name__ == "__main__":
    print("\nServer ready. Reach it at:")
    print(f"  this Mac:        http://localhost:{a.port}")
    for ip in my_addresses():
        print(f"  phone on WiFi:   http://{ip}:{a.port}   <- put this IP in n80_client.py")
    print()
    app.run(host="0.0.0.0", port=a.port, threaded=True)
