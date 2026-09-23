# -*- coding: utf-8 -*-
# hello_n80.py - Milestones 2, 3 and 5 on the Nokia N80, one check at a time.
#
# Runs in PyS60 (Python for S60 3rd Edition, 1.4.5 or 2.0). Written in the old
# Python 2.2 style on purpose: the phone's Python is from 2006.
#
# Copy this file to the phone's memory card in E:\Python\ and run it from the
# Python app ("Run script"). It will:
#   1. speak "hello"                    -> proves Python + text-to-speech work
#   2. take a small photo and show it    -> proves the camera works from code
#   3. ask for a WiFi access point and ping your Mac's server -> proves networking
#
# Before step 3: start `python server.py` on the Mac and put its IP below.

SERVER_HOST = "192.168.1.20"      # <- your Mac's IP (server.py prints it)
SERVER_PORT = 8000
PHOTO_PATH = u"E:\\n80_hello.jpg"   # E: = memory card. No card? use u"C:\\Data\\n80_hello.jpg"

import appuifw, e32, camera, graphics, audio, httplib

canvas = appuifw.Canvas()
appuifw.app.body = canvas
appuifw.app.title = u"N80 hello"
lines = []


def show(msg, img=None):
    lines.append(unicode(msg))
    canvas.clear(0)
    if img is not None:
        canvas.blit(img)
    y = 20
    for l in lines[-6:]:
        canvas.text((5, y), l, fill=0x00ff00)
        y = y + 18
    e32.ao_yield()


def step_speak():
    show("1. speaking...")
    try:
        audio.say(u"Hello. I am the N80. I am learning to see.")
        show("   speech OK")
    except:
        show("   no audio.say on this PyS60")


def step_photo():
    show("2. camera sizes: " + str(camera.image_sizes()))
    img = camera.take_photo(size=smallest_size())
    try:
        img = img.resize((320, 240))
    except:
        pass
    img.save(PHOTO_PATH, quality=60)
    camera.release()
    show("   photo saved: " + str(img.size), img)


def smallest_size():
    best = None
    for s in camera.image_sizes():
        if s[0] >= 320 and (best is None or s[0] < best[0]):
            best = s
    return best or camera.image_sizes()[-1]


def choose_access_point():
    try:
        import btsocket as sock   # PyS60 2.0
    except ImportError:
        import socket as sock     # PyS60 1.4.x
    apid = sock.select_access_point()
    if apid is None:
        return 0
    ap = sock.access_point(apid)
    sock.set_default_access_point(ap)
    return 1


def step_network():
    show("3. choose your WiFi...")
    if not choose_access_point():
        show("   no access point chosen")
        return
    try:
        conn = httplib.HTTPConnection(SERVER_HOST, SERVER_PORT)
        conn.request("GET", "/ping")
        reply = conn.getresponse().read()
        conn.close()
        show("   Mac says: " + reply.strip())
    except:
        import sys
        show("   network error: " + str(sys.exc_info()[1]))


step_speak()
step_photo()
step_network()
show("Done. Press Exit.")

lock = e32.Ao_lock()
appuifw.app.exit_key_handler = lock.signal
lock.wait()
