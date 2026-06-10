"""
ESP32MJPEGCapture — cv2.VideoCapture yerine kullanılır.
MJPEG boundary formatından bağımsız: JPEG başlangıç/bitiş
işaretçilerini (0xFF 0xD8 / 0xFF 0xD9) doğrudan arar.
"""
import threading
import time
import collections
import numpy as np
import cv2
import requests


class ESP32MJPEGCapture:
    CHUNK = 4096          # Bytes per read
    MAX_BUF = 1_000_000   # 1 MB — bozuk frame birikmesin
    FPS_WINDOW = 30       # Son kaç frame üzerinden FPS hesaplanır

    def __init__(self, url: str):
        self._url = url
        self._frame = None
        self._lock = threading.Lock()
        self._running = False
        self._disconnected = False
        self._thread = None
        # FPS takibi için son frame zamanları
        self._frame_times = collections.deque(maxlen=self.FPS_WINDOW)

    # --- cv2.VideoCapture arayüzü ---

    def isOpened(self) -> bool:
        return self._running and not self._disconnected

    def read(self):
        if not self._running:
            return False, None

        # İlk frame henüz gelmediyse kısa süre bekle (max 2sn, 50ms arayla)
        deadline = time.time() + 2.0
        while True:
            with self._lock:
                if self._frame is not None:
                    return True, self._frame.copy()
            if time.time() >= deadline or not self._running:
                break
            time.sleep(0.05)

        return False, None

    def release(self):
        self._running = False
        self._disconnected = False
        if self._thread:
            self._thread.join(timeout=3)
        self._thread = None

    def get_fps(self) -> float:
        """Son FPS_WINDOW frame arasındaki ortalama FPS değerini döner."""
        with self._lock:
            times = list(self._frame_times)
        if len(times) < 2:
            return 0.0
        elapsed = times[-1] - times[0]
        if elapsed <= 0:
            return 0.0
        return (len(times) - 1) / elapsed

    # --- Başlatma ---

    def open(self) -> bool:
        """Bağlantıyı kur ve arka plan thread'ini başlat."""
        self._disconnected = False
        try:
            # connect_timeout=5sn, read_timeout=15sn (tuple formatı)
            r = requests.get(self._url, stream=True, timeout=(5, 15))
            r.raise_for_status()
        except Exception as e:
            print(f"[ESP32Stream] Baglanti hatasi: {e}")
            return False

        self._running = True
        self._thread = threading.Thread(
            target=self._reader_loop,
            args=(r,),
            daemon=True,
        )
        self._thread.start()

        # İlk frame gelene kadar bekle (max 5sn)
        deadline = time.time() + 5
        while time.time() < deadline:
            with self._lock:
                if self._frame is not None:
                    return True
            time.sleep(0.05)

        print("[ESP32Stream] Uyari: 5sn icerisinde frame gelmedi.")
        return True   # Baglanti var ama goruntu henuz gelmedi, devam et

    def _reader_loop(self, response):
        buf = b""
        try:
            for chunk in response.iter_content(chunk_size=self.CHUNK):
                if not self._running:
                    break
                buf += chunk

                # Buffer cok buyuduyse basini kes
                if len(buf) > self.MAX_BUF:
                    last_soi = buf.rfind(b"\xff\xd8")
                    buf = buf[last_soi:] if last_soi != -1 else b""

                # Tüm tam JPEG frame'leri çıkar
                while True:
                    soi = buf.find(b"\xff\xd8")   # Start Of Image
                    eoi = buf.find(b"\xff\xd9")   # End Of Image
                    if soi == -1 or eoi == -1 or eoi < soi:
                        break
                    jpg_bytes = buf[soi: eoi + 2]
                    buf = buf[eoi + 2:]

                    frame = cv2.imdecode(
                        np.frombuffer(jpg_bytes, dtype=np.uint8),
                        cv2.IMREAD_COLOR,
                    )
                    if frame is not None:
                        with self._lock:
                            self._frame = frame
                            self._frame_times.append(time.time())

        except Exception as e:
            if self._running:
                print(f"[ESP32Stream] Stream kesildi: {e}")
        finally:
            self._running = False
            self._disconnected = True
            response.close()
