"""Stage 3 test: pretend to be the N80 so you can test server.py before touching the phone.

It does exactly what n80/n80_client.py does on the phone: take a small photo,
POST it to /frame, read the key=value reply, speak if told to, fetch /annotated.jpg.

    python fake_phone.py                              # uses the Mac webcam
    python fake_phone.py --images samples/            # uses photos from a folder instead
    python fake_phone.py --server http://192.168.1.20:8000   # a server on another machine
"""
import argparse
import itertools
import time
import urllib.request
from pathlib import Path

import cv2

from vision import config
from vision.media import MacVoice, phone_size, to_jpeg

ap = argparse.ArgumentParser()
ap.add_argument("--server", default=f"http://localhost:{config.SERVER_PORT}")
ap.add_argument("--images", help="folder of .jpg/.png to send instead of the webcam")
ap.add_argument("--every", type=float, default=0.5, help="seconds to wait between photos")
ap.add_argument("--count", type=int, default=0, help="stop after this many photos (0 = forever)")
ap.add_argument("--quiet", action="store_true")
a = ap.parse_args()

voice = MacVoice(enabled=not a.quiet)


def photos():
    if a.images:
        files = sorted(p for p in Path(a.images).iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
        if not files:
            raise SystemExit(f"No images in {a.images}")
        for p in itertools.cycle(files):
            yield cv2.imread(str(p))
    else:
        cam = cv2.VideoCapture(0)
        if not cam.isOpened():
            raise SystemExit("Can't open the webcam (allow Terminal in Privacy & Security > Camera).")
        while True:
            ok, f = cam.read()
            if ok:
                yield f


print(urllib.request.urlopen(a.server + "/ping", timeout=5).read().decode().strip(), "- server reachable")
for n, img in enumerate(photos(), 1):
    jpeg = to_jpeg(phone_size(img))
    t0 = time.time()
    req = urllib.request.Request(a.server + "/frame?client=fake-phone", data=jpeg,
                                 headers={"Content-Type": "image/jpeg"})
    reply = urllib.request.urlopen(req, timeout=15).read().decode()
    fields = dict(line.split("=", 1) for line in reply.strip().splitlines() if "=" in line)
    rtt = int((time.time() - t0) * 1000)
    print(f"#{n} sent {len(jpeg) // 1024} KB, round trip {rtt} ms -> {fields.get('text')}"
          + ("  [speak]" if fields.get("speak") == "1" else ""))
    if fields.get("speak") == "1":
        voice.say(fields["text"])
    urllib.request.urlretrieve(a.server + "/annotated.jpg", "last_annotated.jpg")
    if a.count and n >= a.count:
        break
    time.sleep(a.every)
