"""
Interaktif yaya gecidi bolge secici.

Kullanim:
    from crosswalk_setup import interactive_zone_picker
    polygon = interactive_zone_picker(frame)   # np.ndarray (4,2) veya None

Kullanici 4 kosesi tiklarken geri donuslu gorsel rehberlik saglar.
"""

import cv2
import numpy as np
import json
import os
from typing import Optional

ZONE_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crosswalk_zone.json")

# Pencere ve gorsel ayarlar
WINDOW_NAME = "SmartWalk - Zon Secici"
NOKTA_RENGI = (0, 255, 255)        # Sari-yesil
CIZGI_RENGI = (0, 200, 255)        # Turuncu
TAMAMLANDI_RENGI = (0, 255, 0)     # Yesil
HATA_RENGI = (0, 0, 255)           # Kirmizi
NOKTA_RADIUS = 6
FONT = cv2.FONT_HERSHEY_SIMPLEX


# ---------------------------------------------------------------------------
# JSON kayit / yukle
# ---------------------------------------------------------------------------

def save_zone_json(polygon: np.ndarray, frame_size: tuple) -> None:
    """Polygon'u JSON dosyasina kaydet."""
    data = {
        "polygon": polygon.tolist(),
        "frame_size": list(frame_size),   # [w, h]
    }
    with open(ZONE_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[Zon Secici] Kaydedildi: {ZONE_JSON_PATH}")


def load_zone_json() -> Optional[np.ndarray]:
    """JSON dosyasini yukle. Dosya yoksa None dondur."""
    if not os.path.exists(ZONE_JSON_PATH):
        return None
    try:
        with open(ZONE_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        polygon = np.array(data["polygon"], dtype=np.int32)
        print(f"[Zon Secici] Kayitli zon yuklendi: {ZONE_JSON_PATH}")
        return polygon
    except Exception as e:
        print(f"[Zon Secici] JSON yuklenemedi: {e}")
        return None


# ---------------------------------------------------------------------------
# Gorsel yardimci
# ---------------------------------------------------------------------------

def _render_frame(base: np.ndarray, noktalar: list, tamamlandi: bool) -> np.ndarray:
    """Mevcut noktalar ve yonlendirme mesajiyla frame'i cizer."""
    vis = base.copy()
    h, w = vis.shape[:2]

    # Arka plan yarim saydam bilgi cubugu
    overlay = vis.copy()
    cv2.rectangle(overlay, (0, 0), (w, 60), (30, 30, 30), -1)
    cv2.addWeighted(overlay, 0.65, vis, 0.35, 0, vis)

    # Ana yonlendirme mesaji
    if tamamlandi:
        msg = "KAYDET: Enter  |  TEKRAR: R  |  IPTAL: Esc"
        renk = TAMAMLANDI_RENGI
    else:
        siradaki = len(noktalar) + 1
        koseler = ["Sol-Ust", "Sag-Ust", "Sag-Alt", "Sol-Alt"]
        hedef = koseler[len(noktalar)] if len(noktalar) < 4 else ""
        msg = f"Yaya gecidinin 4 kosesine tiklayin  [{siradaki}/4: {hedef}]"
        renk = (255, 255, 255)

    cv2.putText(vis, msg, (10, 22), FONT, 0.55, renk, 1, cv2.LINE_AA)
    cv2.putText(vis, "IPTAL: Esc  |  SON NOKTAYI SIL: Z", (10, 46),
                FONT, 0.42, (180, 180, 180), 1, cv2.LINE_AA)

    # Noktalar
    for i, (px, py) in enumerate(noktalar):
        cv2.circle(vis, (px, py), NOKTA_RADIUS + 2, (0, 0, 0), -1)   # golge
        cv2.circle(vis, (px, py), NOKTA_RADIUS, NOKTA_RENGI, -1)
        cv2.putText(vis, str(i + 1), (px + 9, py - 9),
                    FONT, 0.5, NOKTA_RENGI, 1, cv2.LINE_AA)

    # Cizgiler
    if len(noktalar) >= 2:
        for i in range(len(noktalar) - 1):
            cv2.line(vis, noktalar[i], noktalar[i + 1], CIZGI_RENGI, 2, cv2.LINE_AA)

    # Tamamlandiginda kapanma cizgisi + dolu poligon
    if tamamlandi and len(noktalar) == 4:
        pts = np.array(noktalar, dtype=np.int32)
        cv2.line(vis, noktalar[-1], noktalar[0], CIZGI_RENGI, 2, cv2.LINE_AA)
        fill = vis.copy()
        cv2.fillPoly(fill, [pts], (0, 255, 0))
        cv2.addWeighted(fill, 0.18, vis, 0.82, 0, vis)
        cv2.polylines(vis, [pts], True, TAMAMLANDI_RENGI, 2, cv2.LINE_AA)

    return vis


# ---------------------------------------------------------------------------
# Ana interaktif secici
# ---------------------------------------------------------------------------

def interactive_zone_picker(frame: np.ndarray) -> Optional[np.ndarray]:
    """
    CV2 penceresi acar, kullanicidan 4 kose noktasi tiklatir.

    Tuslar:
        Sol klik  — nokta ekle
        Z         — son noktayi sil
        Enter     — onayla ve polygon dondur (4 nokta tamamsa)
        R         — sifirla
        Esc       — iptal (None dondur)

    Returns:
        np.ndarray shape (4,2) int32, veya None (iptal edilirse).
    """
    h, w = frame.shape[:2]

    # Goruntuyu pencere boyutuna sigdir (cok buyukse)
    max_disp_w, max_disp_h = 960, 720
    scale = min(max_disp_w / w, max_disp_h / h, 1.0)
    disp_w = int(w * scale)
    disp_h = int(h * scale)

    base = cv2.resize(frame, (disp_w, disp_h), interpolation=cv2.INTER_LINEAR)

    noktalar = []
    tamamlandi = False
    sonuc = None

    def on_mouse(event, mx, my, flags, param):
        nonlocal noktalar, tamamlandi
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(noktalar) < 4:
                noktalar.append((mx, my))
                if len(noktalar) == 4:
                    tamamlandi = True

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, disp_w, disp_h)
    cv2.setMouseCallback(WINDOW_NAME, on_mouse)

    print("[Zon Secici] Pencere acildi. Yaya gecidinin 4 kosesine tiklayin.")
    print("             Sira: Sol-Ust → Sag-Ust → Sag-Alt → Sol-Alt")
    print("             Z: son nokta sil | R: sifirla | Enter: kaydet | Esc: iptal")

    while True:
        vis = _render_frame(base, noktalar, tamamlandi)
        cv2.imshow(WINDOW_NAME, vis)
        key = cv2.waitKey(30) & 0xFF

        if key == 27:                          # Esc — iptal
            print("[Zon Secici] Iptal edildi.")
            sonuc = None
            break

        elif key in (13, 10):                  # Enter — onayla
            if tamamlandi and len(noktalar) == 4:
                # Kordinatlari gercek frame boyutuna geri olcekle
                raw = np.array(noktalar, dtype=np.float32)
                raw[:, 0] /= scale
                raw[:, 1] /= scale
                sonuc = raw.astype(np.int32)
                print(f"[Zon Secici] Onaylandi: {sonuc.tolist()}")
                break
            else:
                print("[Zon Secici] Lutfen once 4 noktayi tamamlayin.")

        elif key in (ord('r'), ord('R')):       # R — sifirla
            noktalar = []
            tamamlandi = False
            print("[Zon Secici] Sifirlandi, yeniden tiklayin.")

        elif key in (ord('z'), ord('Z')):       # Z — son noktayi sil
            if noktalar:
                noktalar.pop()
                tamamlandi = len(noktalar) == 4
                print(f"[Zon Secici] Son nokta silindi. ({len(noktalar)}/4)")

    cv2.destroyWindow(WINDOW_NAME)

    # Basarili ise JSON'a kaydet
    if sonuc is not None:
        save_zone_json(sonuc, (w, h))

    return sonuc


# ---------------------------------------------------------------------------
# Dogrudan calistirma (test amacli)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        img = cv2.imread(sys.argv[1])
        if img is None:
            print(f"[Hata] Goruntu acilamadi: {sys.argv[1]}")
            sys.exit(1)
    else:
        # Webcam'den ilk frame al
        cap = cv2.VideoCapture(0)
        ret, img = cap.read()
        cap.release()
        if not ret or img is None:
            print("[Hata] Kameradan goruntu alinamadi.")
            sys.exit(1)

    poly = interactive_zone_picker(img)
    if poly is not None:
        print(f"[Sonuc] Polygon: {poly.tolist()}")
    else:
        print("[Sonuc] Secim yapilmadi.")
