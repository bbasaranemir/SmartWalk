import sys
import os
sys.path.insert(0, 'D:/SmartWalk/lib')

import cv2

# Webcam mi ESP32 mi?
# 0 = webcam | "http://192.168.1.XXX/capture" = ESP32
SOURCE = 0

if isinstance(SOURCE, int):
    cap = cv2.VideoCapture(SOURCE)
    ret, frame = cap.read()
    cap.release()
else:
    import urllib.request
    import numpy as np
    try:
        with urllib.request.urlopen(SOURCE, timeout=5) as r:
            frame = cv2.imdecode(np.frombuffer(r.read(), dtype=np.uint8), cv2.IMREAD_COLOR)
        ret = frame is not None
    except Exception as e:
        print(f"ESP32 baglanti hatasi: {e}")
        ret, frame = False, None

if ret and frame is not None:
    path = r"D:\SmartWalk\frame_for_polygon.jpg"
    cv2.imwrite(path, frame)
    print(f"Frame kaydedildi: {path}")
    print("")
    print("Simdi su siteye git:")
    print("https://roboflow.github.io/polygonzone/")
    print("")
    print("O resmi yukle, yaya gecidinin 4 kosesini isaretlenle,")
    print("cikan koordinatlari kopyalayip buraya yapistir.")
else:
    print("Frame alinamadi. Kamera baglantiyi kontrol et.")
