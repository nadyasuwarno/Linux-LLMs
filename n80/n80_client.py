# -*- coding: utf-8 -*-
# n80_client.py - the Nokia N80 side of the talking camera (Milestones 7-9).
#
# Loop: take a small photo -> send it to the Mac -> get back a sentence and a
# picture with boxes drawn on it -> show the picture -> speak the sentence.
#
# Runs in PyS60 (Python for S60 3rd Edition, 1.4.5 or 2.0). Python 2.2 style on
# purpose. Copy to E:\Python\ on the phone and run it from the Python app.
# Test with hello_n80.py first; this assumes all three of its checks passed.
#
# It talks to server.py exactly like fake_phone.py does, so if fake_phone.py
# works against your server, the only new variable here is the phone itself.

SERVER_HOST = "192.168.1.20"      # <- your Mac's IP (server.py prints it)
SERVER_PORT = 8000
PHOTO_SIZE = (320, 240)
JPEG_QUALITY = 60
PAUSE = 0.3                         # seconds between photos
PHOTO_PATH = u"E:\\n80v_photo.jpg"        # E: = memory card
ANNOTATED_PATH = u"E:\\n80v_annotated.jpg"
SPEAK = 1

import appuifw, e32, camera, graphics, audio, httplib, sys

state = {"running": 1, "active": 0, "img": None, "text": u"Options > Start",
         "info": u"", "sizes": None}


# ---------------------------------------------------------------- screen
def redraw(rect=None):
    try:
        canvas.clear(0)
        if state["img"] is not None:
            canvas.blit(state["img"])
        w, h = canvas.size
        canvas.rectangle((0, h - 46, w, h), fill=0x000000)
        canvas.text((4, h - 28), state["text"][:40], fill=0xffffff)
        canvas.text((4, h - 8), state["info"][:40], fill=0x00ff00)
    except:
        pass

canvas = appuifw.Canvas(redraw_callback=redraw)
appuifw.app.body = canvas
appuifw.app.title = u"N80 vision"


def status(text=None, info=None):
    if text is not None:
        state["text"] = unicode(text)
    if info is not None:
        state["info"] = unicode(info)
    redraw()
    e32.ao_yield()


# ---------------------------------------------------------------- camera
def photo_size():
    if state["sizes"] is None:
        state["sizes"] = camera.image_sizes()
    best = None
    for s in state["sizes"]:
        if s[0] >= PHOTO_SIZE[0] and (best is None or s[0] < best[0]):
            best = s
    return best or state["sizes"][-1]


def take_jpeg():
    img = camera.take_photo(size=photo_size())
    if img.size != PHOTO_SIZE:
        try:
            img = img.resize(PHOTO_SIZE)
        except:
            pass              # older PyS60: send it bigger, the Mac copes
    img.save(PHOTO_PATH, quality=JPEG_QUALITY)
    f = open(PHOTO_PATH, "rb")
    data = f.read()
    f.close()
    return data


# ---------------------------------------------------------------- network
def choose_access_point():
    try:
        import btsocket as sock   # PyS60 2.0
    except ImportError:
        import socket as sock     # PyS60 1.4.x
    apid = sock.select_access_point()
    if apid is None:
        return 0
    sock.set_default_access_point(sock.access_point(apid))
    return 1


def http(method, path, body=None, headers={}):
    conn = httplib.HTTPConnection(SERVER_HOST, SERVER_PORT)
    conn.request(method, path, body, headers)
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    return resp.status, data


def parse(reply):
    fields = {}
    for line in reply.split("\n"):
        if line.find("=") > 0:
            k, v = line.split("=", 1)
            fields[k.strip()] = v.strip()
    return fields


# ---------------------------------------------------------------- one cycle
def cycle():
    status(info=u"photo...")
    jpeg = take_jpeg()

    status(info=u"sending %d KB..." % (len(jpeg) / 1024))
    code, reply = http("POST", "/frame?client=n80", jpeg, {"Content-Type": "image/jpeg"})
    if code != 200:
        status(info=u"server said %d" % code)
        return
    fields = parse(reply)

    code, pic = http("GET", "/annotated.jpg")
    if code == 200:
        f = open(ANNOTATED_PATH, "wb")
        f.write(pic)
        f.close()
        state["img"] = graphics.Image.open(ANNOTATED_PATH)

    info = u"%s ms on Mac" % fields.get("ms", "?")
    status(text=fields.get("text", ""), info=info)
    if SPEAK and fields.get("speak") == "1" and fields.get("text"):
        audio.say(unicode(fields["text"]))


# ---------------------------------------------------------------- menu
def start():
    if not choose_access_point():
        status(info=u"no WiFi chosen")
        return
    try:
        code, reply = http("GET", "/ping")
        status(text=u"Connected to Mac", info=unicode(reply.strip()))
    except:
        status(text=u"Can't reach Mac", info=unicode(str(sys.exc_info()[1])))
        return
    state["active"] = 1


def pause():
    state["active"] = 0
    status(info=u"paused")


def toggle_voice():
    global SPEAK
    SPEAK = 1 - SPEAK
    status(info=(SPEAK and u"voice on") or u"voice off")


def quit():
    state["running"] = 0

appuifw.app.menu = [(u"Start", start), (u"Pause", pause), (u"Voice on/off", toggle_voice)]
appuifw.app.exit_key_handler = quit
status()

while state["running"]:
    if state["active"]:
        try:
            cycle()
        except:
            status(info=u"error: " + unicode(str(sys.exc_info()[1])))
            e32.ao_sleep(2)
    e32.ao_sleep(PAUSE)

try:
    camera.release()
except:
    pass
appuifw.app.set_exit()
