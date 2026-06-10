import re

# Turk plaka formati: 34 ABC 1234 veya 06 A 1234 gibi
_PLATE_PATTERN = re.compile(r'\d{2}\s*[A-Z]{1,3}\s*\d{2,4}')


class PlateReader:
    def __init__(self):
        self._reader = None   # None = henuz yuklenmedi
        self._available = True  # False = yukleme basarisiz, tekrar deneme

    def _load(self):
        if not self._available or self._reader is not None:
            return
        try:
            import easyocr
            print("[Plaka] EasyOCR yukleniyor...")
            self._reader = easyocr.Reader(['tr', 'en'], gpu=False, verbose=False)
            print("[Plaka] EasyOCR hazir.")
        except Exception as e:
            print(f"[Plaka] EasyOCR yuklenemedi: {e} — plaka okuma devre disi.")
            self._available = False

    def read(self, frame, box) -> str:
        """
        frame: tam kare (numpy array)
        box: (x1, y1, x2, y2) arac sinir kutusu
        Donus: plaka metni veya bos string
        """
        self._load()
        if self._reader is None:
            return ""

        x1, y1, x2, y2 = map(int, box)
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return ""

        try:
            results = self._reader.readtext(crop, detail=0)
        except Exception as e:
            print(f"[Plaka] OCR hatasi: {e}")
            return ""

        combined = " ".join(results).upper().strip()

        match = _PLATE_PATTERN.search(combined)
        if match:
            return re.sub(r'\s+', ' ', match.group()).strip()

        return combined if combined else ""
