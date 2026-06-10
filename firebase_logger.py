import os


class FirebaseLogger:
    def __init__(self, cred_path: str, db_url: str):
        self._enabled = False
        self._ref = None
        if not os.path.exists(cred_path):
            print(f"[Firebase] {cred_path} bulunamadi — Firebase loglama devre disi.")
            return
        try:
            import firebase_admin
            from firebase_admin import credentials, db as firebase_db
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {"databaseURL": db_url})
            self._ref = firebase_db.reference("/ihlaller")
            self._enabled = True
            print("[Firebase] Baglanti basarili.")
        except Exception as e:
            print(f"[Firebase] Baglanti hatasi: {e} — devre disi.")

    def log_violation(self, timestamp: str, image_path: str, plate: str = ""):
        if not self._enabled:
            return
        try:
            self._ref.push({
                "tarih": timestamp,
                "durum": "Yaya Gecidi Ihlali",
                "goruntu": image_path,
                "plaka": plate if plate else "Okunamadi",
            })
        except Exception as e:
            print(f"[Firebase] Kayit hatasi: {e}")
