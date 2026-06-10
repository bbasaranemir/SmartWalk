"""
ESP32Controller — WiFi üzerinden HTTP ile OLED ekranını kontrol eder.

ESP32 tarafında /status endpoint'i beklenir:
  GET /status?state=1&plate=34ABC123   → ihlal ekranı
  GET /status?state=0                  → temiz ekran
"""
import threading
import requests
from config import ESP32_BASE_URL


class ESP32Controller:
    def __init__(self, base_url: str = ESP32_BASE_URL, timeout: float = 3.0):
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._enabled = bool(base_url)
        if self._enabled:
            print(f"[ESP32] OLED kontrolu aktif: {self._base}/status")

    def send(self, signal: str, plate: str = ""):
        """
        signal: '1' = ihlal (OLED ihlal ekrani), '0' = guvenli (OLED temiz)
        Ana thread'i bloke etmemek icin arka planda gonderir.
        """
        if not self._enabled:
            return
        t = threading.Thread(
            target=self._post,
            args=(signal, plate),
            daemon=True,
        )
        t.start()

    def _post(self, signal: str, plate: str):
        params = {"state": signal}
        if plate:
            params["plate"] = plate
        try:
            requests.get(
                f"{self._base}/status",
                params=params,
                timeout=self._timeout,
            )
        except requests.exceptions.ConnectionError:
            print("[ESP32] OLED: baglanti hatasi (ESP32 ulasılamaz?)")
        except requests.exceptions.Timeout:
            print("[ESP32] OLED: istek zaman asimi")
        except Exception as e:
            print(f"[ESP32] OLED gonderim hatasi: {e}")

    def close(self):
        """Program kapanirken ekrani temizle."""
        if self._enabled:
            self._post("0", "")
