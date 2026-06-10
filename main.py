"""
SmartWalk — Edge-AI Tabanli Yaya Gecidi Ihlal Tespit Sistemi

Calistirma:
    python main.py                  # ESP32 kamera
    python main.py --demo           # Webcam (demo modu)
    python main.py --video yol.mp4  # Video dosyasi
"""

import sys
import os

# Kutuphaneler D diskinde
sys.path.insert(0, 'D:/SmartWalk/lib')

# YOLO modelini ve ciktilarini C degil D diskine kaydet
os.environ['YOLO_CONFIG_DIR'] = 'D:/SmartWalk/yolo_config'
os.makedirs('D:/SmartWalk/yolo_config', exist_ok=True)

import time
import urllib.request
import argparse
from enum import Enum
from typing import Optional

import cv2
import numpy as np
import supervision as sv

from config import (
    CAMERA_URL,
    PERSON_CLASS_ID,
    VEHICLE_CLASS_IDS,
    FRAME_SKIP,
    POLYGON_COORDS,
    FIREBASE_CRED_PATH,
    FIREBASE_DB_URL,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    ENABLE_PLATE_READER,
    ARDUINO_PORT,
    ARDUINO_BAUD,
)
from detector import SmartWalkDetector
from zones import CrosswalkZone
from firebase_logger import FirebaseLogger
from violation_handler import ViolationHandler
from crosswalk_detector import detect_or_fallback
from telegram_notifier import TelegramNotifier
from plate_reader import PlateReader
from arduino_controller import ArduinoController
from esp32_controller import ESP32Controller
from esp32_stream import ESP32MJPEGCapture


class State(Enum):
    SAFE = "GUVENLI"
    PEDESTRIAN = "YAYA ALGILANDI - YOL VER"
    VIOLATION = "IHLAL!"


STATE_COLORS = {
    State.SAFE: (0, 200, 0),
    State.PEDESTRIAN: (0, 200, 255),
    State.VIOLATION: (0, 0, 255),
}

CLASS_LABELS = {
    0: "Yaya",
    2: "Arac",
    3: "Motosiklet",
    5: "Otobus",
    7: "Kamyon",
}


def fetch_frame_from_esp32(url: str):
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            img_array = np.frombuffer(resp.read(), dtype=np.uint8)
            return cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"[Kamera] Frame alinamadi: {e}")
        return None


def draw_ui(frame, state: State, detections: sv.Detections, flash_on: bool, polygon=None):
    color = STATE_COLORS[state]
    poly = polygon if polygon is not None else POLYGON_COORDS
    pts = poly.reshape((-1, 1, 2))
    cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=3)

    if state == State.VIOLATION and flash_on:
        overlay = frame.copy()
        cv2.fillPoly(overlay, [pts], color=(0, 0, 180))
        cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)

    label = state.value
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), _ = cv2.getTextSize(label, font, 0.8, 2)
    cv2.rectangle(frame, (8, 8), (tw + 16, th + 20), color, -1)
    cv2.putText(frame, label, (12, th + 12), font, 0.8, (255, 255, 255), 2)

    if detections is not None and len(detections) > 0 and detections.class_id is not None:
        for box, class_id, conf in zip(
            detections.xyxy, detections.class_id, detections.confidence
        ):
            cid = int(class_id)
            if cid not in CLASS_LABELS:
                continue
            x1, y1, x2, y2 = map(int, box)
            box_color = (0, 255, 0) if cid == PERSON_CLASS_ID else (255, 80, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
            tag = f"{CLASS_LABELS[cid]} {conf:.0%}"
            cv2.putText(frame, tag, (x1, max(y1 - 6, 10)), font, 0.55, box_color, 2)

    return frame


def build_capture(args):
    if args.demo:
        return cv2.VideoCapture(0)
    if args.video:
        cap = cv2.VideoCapture(args.video)
        if not cap.isOpened():
            print(f"[Hata] Video acilamadi: {args.video}")
            sys.exit(1)
        return cap
    # ESP32 stream modu — ozel MJPEG okuyucu (boundary formatindan bagimsiz)
    print(f"[Kamera] ESP32 baglaniliyor: {CAMERA_URL}")
    cap = ESP32MJPEGCapture(CAMERA_URL)
    if not cap.open():
        print("[Hata] ESP32 stream acilamadi. IP ve URL'yi kontrol et.")
        print("       Demo icin: python main.py --demo")
        sys.exit(1)
    print("[Kamera] ESP32 baglantisi basarili.")
    return cap


def reconnect_esp32(max_tries: int = 10, wait_sec: float = 3.0):
    """ESP32 stream kopunca yeniden baglanmaya calisir."""
    for attempt in range(1, max_tries + 1):
        print(f"[Kamera] Yeniden baglaniliyor... ({attempt}/{max_tries})")
        time.sleep(wait_sec)
        cap = ESP32MJPEGCapture(CAMERA_URL)
        if cap.open():
            print("[Kamera] Yeniden baglandi.")
            return cap
    print("[Kamera] Baglanti saglanamadi, program kapatiliyor.")
    return None


def process_frame(frame, detector, zone, violation_handler):
    all_detections = detector.detect(frame)

    relevant_ids = list({PERSON_CLASS_ID} | VEHICLE_CLASS_IDS)
    if len(all_detections) > 0 and all_detections.class_id is not None:
        class_mask = np.isin(all_detections.class_id, relevant_ids)
        all_detections = all_detections[class_mask]

    inside = zone.get_inside_detections(all_detections)

    if len(inside) > 0 and inside.class_id is not None:
        persons_inside = inside[np.isin(inside.class_id, [PERSON_CLASS_ID])]
        vehicles_inside = inside[np.isin(inside.class_id, list(VEHICLE_CLASS_IDS))]
    else:
        persons_inside = sv.Detections.empty()
        vehicles_inside = sv.Detections.empty()

    if len(persons_inside) == 0:
        state = State.SAFE
    elif len(vehicles_inside) == 0:
        state = State.PEDESTRIAN
    else:
        state = State.VIOLATION
        violation_handler.handle(frame, vehicle_boxes=vehicles_inside.xyxy.tolist())

    return state, inside


def main():
    parser = argparse.ArgumentParser(description="SmartWalk ihlal tespit sistemi")
    parser.add_argument("--demo", action="store_true", help="Webcam demo modu")
    parser.add_argument("--video", type=str, help="Video dosyasi yolu")
    args = parser.parse_args()

    print("[SmartWalk] Baslatiliyor...")

    detector = SmartWalkDetector()
    logger = FirebaseLogger(FIREBASE_CRED_PATH, FIREBASE_DB_URL)
    notifier = TelegramNotifier(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    plate_reader = PlateReader() if ENABLE_PLATE_READER else None
    arduino = ArduinoController(ARDUINO_PORT, ARDUINO_BAUD)
    esp32   = ESP32Controller()   # WiFi üzerinden OLED kontrolü
    violation_handler = ViolationHandler(
        logger=logger,
        notifier=notifier,
        plate_reader=plate_reader,
    )

    cap = build_capture(args)

    ret, first_frame = cap.read()
    if not ret or first_frame is None:
        # ESP32 stream için: 3 kez 1'er saniye bekleyerek tekrar dene
        for _attempt in range(3):
            print(f"[Kamera] Ilk frame bekleniyor... ({_attempt + 1}/3)")
            time.sleep(1)
            ret, first_frame = cap.read()
            if ret and first_frame is not None:
                break
    if not ret or first_frame is None:
        print("[Hata] Ilk frame okunamadi.")
        sys.exit(1)

    h, w = first_frame.shape[:2]

    # Yaya gecidini otomatik tespit et, basarisizsa config'deki manuel koordinatlar
    auto_polygon, auto_detected = detect_or_fallback(first_frame, POLYGON_COORDS)
    zone = CrosswalkZone(frame_resolution=(w, h), polygon_override=auto_polygon)

    print(f"[SmartWalk] Cozunurluk: {w}x{h} | Hazir.")
    print("[SmartWalk] Cikmak icin 'q' tusuna basin.")

    frame_count = 0
    flash_timer = 0
    last_drawn = None
    prev_state = None        # Arduino'ya sadece state degisince sinyal gonder
    violation_streak = 0     # Art arda kac VIOLATION frame goruldu
    VIOLATION_CONFIRM = 3    # Bildirim icin gereken art arda frame sayisi
    WARMUP_FRAMES = 20       # Baslangicta bu kadar frame'i ihlal sayma

    # Ilk frame: gosterim icin isle, ama bildirim tetikleme
    state = State.SAFE
    inside = sv.Detections.empty()
    last_drawn = first_frame.copy()
    draw_ui(last_drawn, state, inside, flash_on=False, polygon=zone.polygon)
    cv2.imshow("SmartWalk", last_drawn)
    cv2.waitKey(1)

    is_video = bool(args.video)   # Video modunda yeniden baglanma olmaz

    while True:
        try:
            ret, frame = cap.read()
        except Exception as e:
            print(f"[Kamera] Okuma hatasi: {e}")
            ret = False
            frame = None

        # --- Baglanti koptu ---
        if not ret or frame is None:
            if is_video:
                print("[Bilgi] Video bitti.")
                break

            print("[Kamera] Stream kesildi, yeniden baglaniliyor...")
            cap.release()
            cap = reconnect_esp32()
            if cap is None:
                break
            frame_count = 0
            continue

        frame_count += 1

        if frame_count % FRAME_SKIP == 0:
            try:
                all_detections = detector.detect(frame)
                relevant_ids = list({PERSON_CLASS_ID} | VEHICLE_CLASS_IDS)
                if len(all_detections) > 0 and all_detections.class_id is not None:
                    class_mask = np.isin(all_detections.class_id, relevant_ids)
                    all_detections = all_detections[class_mask]
                inside = zone.get_inside_detections(all_detections)

                if len(inside) > 0 and inside.class_id is not None:
                    persons_inside  = inside[np.isin(inside.class_id, [PERSON_CLASS_ID])]
                    vehicles_inside = inside[np.isin(inside.class_id, list(VEHICLE_CLASS_IDS))]
                else:
                    persons_inside  = sv.Detections.empty()
                    vehicles_inside = sv.Detections.empty()

                if len(persons_inside) == 0:
                    state = State.SAFE
                    violation_streak = 0
                elif len(vehicles_inside) == 0:
                    state = State.PEDESTRIAN
                    violation_streak = 0
                else:
                    violation_streak += 1
                    state = State.VIOLATION
                    # Warmup bitmeden ve art arda N frame olmadan bildirim yok
                    if frame_count > WARMUP_FRAMES and violation_streak == VIOLATION_CONFIRM:
                        violation_handler.handle(frame, vehicle_boxes=vehicles_inside.xyxy.tolist())

                # Sadece state degistiginde sinyal gonder
                if state != prev_state:
                    sig = '1' if state == State.VIOLATION else '0'
                    arduino.send(sig)          # Opsiyonel fiziksel Arduino
                    esp32.send(sig)            # ESP32 OLED ekrani guncelle
                    prev_state = state

                flash_timer = (flash_timer + 1) % 10
                flash_on = flash_timer < 5
                last_drawn = frame.copy()
                draw_ui(last_drawn, state, inside, flash_on, polygon=zone.polygon)

            except Exception as e:
                print(f"[Hata] Frame isleme hatasi: {e}")
                # Son gecerli ekrani goster, islemeye devam et

        if last_drawn is not None:
            cv2.imshow("SmartWalk", last_drawn)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    if cap:
        cap.release()
    arduino.close()
    esp32.close()   # Kapanirken OLED'i temizle
    cv2.destroyAllWindows()
    print("[SmartWalk] Kapatildi.")


if __name__ == "__main__":
    main()
