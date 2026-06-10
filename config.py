import os
import numpy as np

# Bu dosyanin bulundugu klasor
_BASE = os.path.dirname(os.path.abspath(__file__))

# ESP32-S3 kamera URL — port 80, path /  (Arduino kodundaki startOzelCameraServer ile uyumlu)
ESP32_BASE_URL = "http://192.168.248.133"
CAMERA_URL     = ESP32_BASE_URL + "/"

# Yaya gecidi poligon koordinatlari (piksel).
# Roboflow PolygonZone aracından alin: https://roboflow.github.io/polygonzone/
POLYGON_COORDS = np.array([
    [196, 228],
    [544, 233],
    [595, 311],
    [157, 296],
], dtype=np.int32)

# YOLO COCO sinif ID'leri
PERSON_CLASS_ID = 0
VEHICLE_CLASS_IDS = {2, 3, 5, 7}  # car, motorcycle, bus, truck

# Firebase (opsiyonel)
FIREBASE_CRED_PATH = os.path.join(_BASE, "serviceAccountKey.json")
FIREBASE_DB_URL = "https://<proje-id>-default-rtdb.firebaseio.com"

# Yerel ihlal fotograflari dizini
VIOLATIONS_DIR = os.path.join(_BASE, "Ihlaller")

# Her kacinci frame islenir (1 = her frame, 2 = her ikinci)
FRAME_SKIP = 2

# ----- TELEGRAM -----
# 1. Telegram'da @BotFather'a yaz, /newbot de, token'i kopyala
# 2. Bota bir mesaj at, sonra tarayicida su URL'yi ac:
#    https://api.telegram.org/bot<TOKEN>/getUpdates
#    "id" alanindaki sayiyi TELEGRAM_CHAT_ID'ye yaz
TELEGRAM_BOT_TOKEN = "8400232761:AAG11-eE9bxUjS1NdquUihSVYF4cZiLanwc"
TELEGRAM_CHAT_ID   = "1104699339"

# ----- PLAKA OKUMA -----
# True yapilirsa EasyOCR aktif olur (ilk calistirmada model indirilir ~200MB)
ENABLE_PLATE_READER = False   # Disk dolu — EasyOCR devre disi

# ----- ARDUINO LED -----
# Arduino'nun bagli oldugu COM portu (Windows: "COM3", "COM4" vb.)
# Bulmak icin: Arduino IDE -> Araclar -> Port
# Kullanmayacaksan "ARDUINO_PORT_BURAYA" olarak birak
ARDUINO_PORT = "ARDUINO_PORT_BURAYA"
ARDUINO_BAUD = 9600
