# SmartWalk — Edge-AI Tabanlı Yaya Geçidi İhlal Tespit Sistemi

**Bilecik Şeyh Edebali Üniversitesi — YBS Bölümü — Proje-I**

> ESP32-S3 kamera + YOLOv8n nesne tespiti kullanarak yaya geçidi ihlallerini gerçek zamanlı algılayan, Telegram bildirimi gönderen ve Firebase'e kaydeden akıllı trafik güvenlik sistemi.

## Özellikler

- ESP32-S3-WROOM-CAM üzerinden WiFi MJPEG akışı (port 80)
- YOLOv8n ile kişi ve araç tespiti
- Polygon tabanlı yaya geçidi bölge filtresi
- Canny + HoughLinesP ile otomatik yaya geçidi tespiti
- İnteraktif 4-nokta bölge seçici (fare arayüzü)
- Telegram Bot API ile fotoğraflı anlık bildirim
- Firebase Realtime Database loglama
- SH1106 OLED ekranda IP adresi gösterimi

## Dosya Yapısı

```
SmartWalk/
├── main.py                  # Ana uygulama döngüsü
├── config.py                # Yapılandırma parametreleri
├── detector.py              # YOLOv8n sarmalayıcısı
├── zones.py                 # PolygonZone filtresi
├── crosswalk_detector.py    # Otomatik yaya geçidi tespiti
├── crosswalk_setup.py       # İnteraktif bölge seçici
├── esp32_stream.py          # MJPEG okuyucu (JPEG marker tabanlı)
├── esp32_controller.py      # ESP32 OLED HTTP kontrolü
├── violation_handler.py     # İhlal işleyici (thread)
├── telegram_notifier.py     # Telegram bildirim modülü
├── firebase_logger.py       # Firebase loglama
├── plate_reader.py          # EasyOCR plaka okuma (opsiyonel)
├── esp32_firmware/
│   └── esp32_firmware.ino   # Arduino kodu (ESP32-S3)
└── rapor/                   # LaTeX rapor dosyaları
```

## Kurulum

```bash
pip install ultralytics supervision opencv-python requests firebase-admin
```

## Kullanım

```bash
# ESP32 kamera ile
python main.py --esp32

# Video dosyası ile test
python main.py --video test.mp4

# Webcam ile test
python main.py
```

## Donanım

| Bileşen | Model |
|---|---|
| Mikrodenetleyici | ESP32-S3-WROOM-CAM |
| Kamera | OV2640 (entegre) |
| Ekran | SH1106 1.3" OLED (I2C) |
| Çözünürlük | VGA 640×480 |
| Bağlantı | 802.11 b/g/n WiFi |

## Hazırlayanlar

- Emir BAŞARAN
- Berkay AKIN

**Danışman:** Hüseyin PARMAKSIZ  
**Bilecik Şeyh Edebali Üniversitesi — 2026**
