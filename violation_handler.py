import cv2
import os
import threading
from datetime import datetime
from config import VIOLATIONS_DIR


class ViolationHandler:
    COOLDOWN_SECONDS = 30  # Ayni ihlal icin en fazla 30 sn'de bir bildirim

    def __init__(self, logger=None, notifier=None, plate_reader=None):
        os.makedirs(VIOLATIONS_DIR, exist_ok=True)
        self.logger = logger
        self.notifier = notifier
        self.plate_reader = plate_reader
        self._last_violation_time = None
        self._lock = threading.Lock()

    def handle(self, frame, vehicle_boxes=None) -> bool:
        """
        Ihlal aninda cagrilir. Cooldown dolmadiysa islem yapmaz.
        Bildirimi arka planda thread'de gonderir — ana loop'u bloke etmez.
        """
        now = datetime.now()
        with self._lock:
            if self._last_violation_time:
                elapsed = (now - self._last_violation_time).total_seconds()
                if elapsed < self.COOLDOWN_SECONDS:
                    return False
            self._last_violation_time = now

        # Frame'i kopyala (thread gecikebilir, orijinal degisebilir)
        frame_copy = frame.copy()
        boxes_copy = list(vehicle_boxes) if vehicle_boxes else []

        thread = threading.Thread(
            target=self._process,
            args=(frame_copy, boxes_copy, now),
            daemon=True,
        )
        thread.start()
        return True

    def _process(self, frame, vehicle_boxes, timestamp):
        """Arka planda calisir: kaydet, plaka oku, bildirim gonder."""
        ts = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        path = os.path.join(VIOLATIONS_DIR, f"ihlal_{ts}.jpg")

        ok = cv2.imwrite(path, frame)
        if ok:
            print(f"[Ihlal] Kaydedildi: {path}")
        else:
            print(f"[Ihlal] UYARI: Fotograf kaydedilemedi: {path}")

        # Plaka okuma
        plate = ""
        if self.plate_reader and vehicle_boxes:
            plate = self.plate_reader.read(frame, vehicle_boxes[0])
            if plate:
                print(f"[Plaka] Tespit: {plate}")
            else:
                print("[Plaka] Okunamadi.")

        plate_info = f"Plaka: {plate}" if plate else "Plaka: Okunamadi"
        message = f"YAYA GECIDI IHLALI\nTarih: {ts}\n{plate_info}"

        # Firebase
        if self.logger:
            try:
                self.logger.log_violation(ts, path, plate)
            except Exception as e:
                print(f"[Firebase] Loglama hatasi: {e}")

        # Telegram
        if self.notifier:
            self.notifier.send(message, photo_path=path if ok else None)
