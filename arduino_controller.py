import time


class ArduinoController:
    def __init__(self, port: str, baud: int = 9600):
        self._serial = None
        if not port or port == "ARDUINO_PORT_BURAYA":
            print("[Arduino] Port ayarlanmamis — LED kontrol devre disi.")
            return
        try:
            import serial
            self._serial = serial.Serial(port, baud, timeout=1)
            time.sleep(2)  # Arduino reset sonrasi baglanti oturur
            print(f"[Arduino] {port} portuna baglandi.")
        except Exception as e:
            print(f"[Arduino] Baglanamadi ({port}): {e}")
            self._serial = None

    def send(self, signal: str):
        """'1' = ihlal (LED yak), '0' = guvenli (LED sondur)"""
        if self._serial is None:
            return
        try:
            self._serial.write(signal.encode())
        except Exception as e:
            print(f"[Arduino] Gonderim hatasi: {e}")

    def close(self):
        if self._serial and self._serial.is_open:
            self.send('0')  # Kapatmadan once LED'i sondur
            self._serial.close()
