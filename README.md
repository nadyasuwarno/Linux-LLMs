# Untitled_N80: a talking camera from 2006

A Nokia N80 (Symbian S60, 2006) becomes a networked AI camera. It takes small photos
and sends them over WiFi to a Mac, where **YOLO** finds objects, **MediaPipe** reads
facial expressions, and **OpenCV** handles the pictures. The Mac sends back a sentence
and a picture with boxes drawn on it. The phone shows the picture and says out loud
what it thinks it sees.

*PSAM 5600 B: Small Linux Devices, Large Language Models. Parsons, Fall 2026.*

```
 Nokia N80  (n80/n80_client.py)            Mac  (server.py)
 ──────────────────────────────            ────────────────────────────────────────
 take 320x240 photo  ── POST /frame ─────▶  OpenCV decode
                                            YOLO26n: "person 91%, cup 78%"
                                            MediaPipe: face -> "smiling"
                                            narrator: "I see a person and a cup.
                                                       Someone is smiling."
 show + speak (audio.say) ◀── text ───────  (optional: LLM on Oracle node rephrases)
 show boxes  ◀── GET /annotated.jpg ──────  OpenCV draws boxes, shrinks for the N80 screen
```

## Models and why

| Job | Model | Why this one |
|---|---|---|
| What objects are in view | **YOLO26n** (Ultralytics) | "n" = nano: the fastest YOLO, about 30 ms per photo on a laptop CPU. Knows 80 everyday things (person, cup, phone, dog, chair…). Swap in `yolo26s.pt` in `vision/config.py` for more accuracy. |
| Faces and expressions | **MediaPipe Face Landmarker** | Finds 478 points on each face plus 52 "blendshape" scores (smile, jaw open, brows up…). `vision/detector.py` turns those into one word: smiling, surprised, frowning, sad, mouth open, eyes closed, neutral. |
| Faces (backup) | **OpenCV YuNet** | A tiny, fast face finder built into OpenCV. Used automatically if MediaPipe isn't available. It finds faces but doesn't read expressions. |
| Pictures | **OpenCV** | Webcam, resizing to phone size, JPEG in and out, drawing boxes and labels. |
| Voice | macOS `say` / the phone's `audio.say` | Built in. Nothing to install. |
| Personality (optional) | **Your node's LLM** (Ollama, e.g. `qwen3.5:4b`) | Rephrases the plain sentence. Off unless you pass `--llm`. |

This detects *that* a person is there and *how their face looks*. It does not recognize
*who* someone is. That's on purpose.

## Files

```
vision/config.py      all the settings: models, sizes, port
vision/detector.py    YOLO + MediaPipe + OpenCV: picture in, results + drawn picture out
vision/narrator.py    results -> a sentence; decides when to speak; optional LLM
vision/media.py       phone-sized resize, JPEG, Mac speech
download_models.py    Step 1: fetch the model files
run_image.py          Stage 1: one photo, no camera
run_webcam.py         Stage 2: live on the Mac webcam, at N80 resolution
server.py             Stage 3: the server the phone talks to (+ browser view)
fake_phone.py         Stage 3: pretends to be the N80, to test the server
n80/hello_n80.py      Stage 4: on the phone - speech, camera, WiFi checks
n80/n80_client.py     Stage 5: on the phone - the real talking camera
```

---

## Part A: run it on the Mac

Run each block in **Terminal**, inside this folder. Don't move on until you see the
"✅ worked when" result.

### A0. One-time setup

```bash
python3 --version
```
You need **3.10–3.12**. If it's missing or older, install Python 3.12 from
[python.org/downloads](https://www.python.org/downloads/macos/) and open a new Terminal window.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python download_models.py
```
- `venv` makes a private box for this project's packages, so they don't mix with anything else on your Mac.
- `source .venv/bin/activate` steps into that box. **Do this every time you open a new Terminal window.** Your prompt starts with `(.venv)` when you're in it.
- `pip install` downloads YOLO, MediaPipe, OpenCV and Flask. The first time takes a few minutes and about 1 GB.
- `download_models.py` fetches the three model files into `models/`.

✅ **Worked when** the last line says `All models ready.`

### A1. Stage 1: one photo

Put a few of your own photos in `samples/` (people, a mug, a laptop…), then:

```bash
python run_image.py samples/YOURPHOTO.jpg --phone
```
`--phone` shrinks the photo to 320×240 first, like the N80 will.

✅ **Worked when** it prints `faces: mediapipe`, a list of objects, a `Says:` line, and saves
`samples/YOURPHOTO_annotated.jpg` with boxes on it.

### A2. Stage 2: live webcam

```bash
python run_webcam.py
```
A window shows your webcam at N80 resolution with boxes and labels, and the Mac speaks when
the scene changes. Smile at it, open your mouth, hold up a cup. Press **q** to quit.
The first time, macOS asks to let Terminal use the camera: allow it and run again.

✅ **Worked when** it says things like "I see a person. Someone is smiling."

### A3. Stage 3: server + fake phone (two Terminal windows)

Window 1:
```bash
source .venv/bin/activate
python server.py
```
Leave it running. Note the `phone on WiFi: http://192.168.x.x:8000` line: that's your
Mac's address. If macOS asks whether Python may accept incoming connections, click **Allow**.

Window 2:
```bash
source .venv/bin/activate
python fake_phone.py
```
Open **http://localhost:8000** in your browser to watch what the "phone" sees.

✅ **Worked when** window 2 prints `round trip … ms -> I see …` and the browser page updates.

**This is the finish line for the Mac side.** The real N80 sends the same requests
`fake_phone.py` sends, so if this works, the Mac is ready for the phone.

---

## Part B: bring in the Nokia N80

### B1. Get Python running on the phone

1. Charge the phone and insert a memory card (drive `E:`).
2. Phone: **Menu → Tools → App. mgr. → Options → Settings → Software installation → All**.
3. Install, in this order, the **PyS60 for S60 3rd Edition** packages (`.sis` files):
   the Python runtime, then the Python Script Shell. Version **1.4.5** is the classic one
   for the N80. Archived copies are online; check where they come from before installing.
4. If it says **"Certificate expired"**, set the phone's date to 2008, install, then set it back.

✅ **Worked when** a "Python" app appears in the phone's menu and opens.

### B2. Put the WiFi somewhere the N80 can join

The N80 only knows old WiFi security (WEP/WPA, maybe WPA2) and can't use WPA3 or
captive-portal networks like a school's. Simplest option: a **phone hotspot** or old router
set to **WPA2-Personal**, with **both the Mac and the N80 on it**.

✅ **Worked when** the N80's web browser can open a page on that network.

### B3. Stage 4: hello_n80.py

1. On the Mac, start `python server.py` and note its IP address.
2. Open `n80/hello_n80.py` and set `SERVER_HOST = "…"` to that IP.
3. Copy the file to the phone's memory card in **`E:\Python\`**. Use a card reader, USB
   "mass storage" mode, or Bluetooth.
4. On the phone: **Python → Options → Run script → hello_n80.py**. Pick your WiFi when asked.

✅ **Worked when** the phone says "Hello", shows a photo it just took, and prints `Mac says: ok`.
Each of the three checks tells you which part works, so if one fails, you know exactly where.

### B4. Stage 5: the talking camera

1. Set `SERVER_HOST` in `n80/n80_client.py` too, then copy it to `E:\Python\`.
2. Run it, then **Options → Start**, and pick your WiFi.

✅ **Worked when** the phone shows photos with boxes drawn on them and says what it sees.
Open http://localhost:8000 on the Mac to watch the same stream. Expect roughly one update
every 1–3 seconds: that's the old WiFi and camera, not the models.

---

## Tuning and next steps

- **Faster:** lower `PHOTO_SIZE` / `JPEG_QUALITY` in `n80_client.py`, or `YOLO_IMGSZ` in `vision/config.py`.
- **Expressions:** adjust the thresholds in `expression_from_blendshapes()` in `vision/detector.py`.
- **Personality (Week 11):** run a model on your Oracle node, open the tunnel
  `ssh -L 11434:127.0.0.1:11434 <your-node>`, then `python server.py --llm`.
  If the node doesn't answer within 6 s, the plain sentence is used, so the camera never stalls.
- **Recognize new things:** YOLO can be retrained on your own objects later. That's a separate project stage.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `faces: yunet` instead of `mediapipe` | `models/face_landmarker.task` is missing: run `python download_models.py` again. |
| `command not found: python` | Use `python3`, or activate the venv first (`source .venv/bin/activate`). |
| `Can't open the camera` | System Settings → Privacy & Security → Camera → allow Terminal. |
| Phone: `Can't reach Mac` | Not on the same WiFi, wrong IP in `SERVER_HOST`, server not running, or the macOS firewall blocked Python. Test from the Mac first: `curl http://<IP>:8000/ping`. |
| Phone: `KErrNotFound` / camera errors | Close the phone's own Camera app. Only one app can use the camera at a time. |
| Address changes each day | Home WiFi hands out addresses. Check the `phone on WiFi:` line and update `SERVER_HOST`. |

## Attribution

Co-authored with **Claude Opus 5.5** (Anthropic). Every commit where a model contributed
carries a `Co-Authored-By:` trailer naming it, per the course's attribution policy.
YOLO26 is © Ultralytics (AGPL-3.0). MediaPipe is © Google (Apache-2.0). OpenCV and YuNet are Apache-2.0.
