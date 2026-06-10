"""
Yaya gecidi otomatik tespit modulu.

Oncelik sirasi:
  1. crosswalk_zone.json varsa yukle (kalici kayit)
  2. Yoksa auto_detect_crosswalk() dene (Canny + HoughLinesP)
  3. O da basarisizsa ve interactive=True ise interaktif secici ac

Algoritma (v2 — HoughLines tabanli):
  - Canny kenar tespiti
  - HoughLinesP ile cizgi bul
  - aci filtresi: yatay ±15 derece arasi → yaya gecidi seridi adayi
  - Yatay cizgileri y konumuna gore grupla (gap-clustering)
  - En az 3 grup, tutarli araliklarsa: gecit tespit edildi
  - Tum gruplari kapsayan bounding box'u polygon olarak dondur
"""

import cv2
import numpy as np
import json
import os
from typing import Optional, Tuple, List

# crosswalk_setup icindeki JSON yolunu ve kaydedici'yi kullan
_BASE = os.path.dirname(os.path.abspath(__file__))
ZONE_JSON_PATH = os.path.join(_BASE, "crosswalk_zone.json")

# HoughLinesP parametreleri
HOUGH_RHO = 1
HOUGH_THETA = np.pi / 180
HOUGH_THRESHOLD = 30
HOUGH_MIN_LINE_LEN = 40
HOUGH_MAX_LINE_GAP = 15

# Yatay cizgi icin maksimum aci (derece)
MAX_ANGLE_DEG = 15.0

# Cluster icin maksimum y farki (piksel)
CLUSTER_GAP_PX = 18

# Gecit icin minimum grup sayisi
MIN_STRIPE_GROUPS = 3

# Aralik tutarlilik esigi (std/mean)
MAX_GAP_CV = 0.65   # coefficient of variation


# ---------------------------------------------------------------------------
# JSON kayit / yukle (crosswalk_setup ile ayni dosya)
# ---------------------------------------------------------------------------

def _save_json(polygon: np.ndarray, frame_size: tuple) -> None:
    data = {
        "polygon": polygon.tolist(),
        "frame_size": list(frame_size),
    }
    with open(ZONE_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[Yaya Gecidi] Zon JSON kaydedildi: {ZONE_JSON_PATH}")


def _load_json() -> Optional[np.ndarray]:
    if not os.path.exists(ZONE_JSON_PATH):
        return None
    try:
        with open(ZONE_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        polygon = np.array(data["polygon"], dtype=np.int32)
        print(f"[Yaya Gecidi] Kayitli zon yuklendi: {ZONE_JSON_PATH}")
        return polygon
    except Exception as e:
        print(f"[Yaya Gecidi] JSON yuklenemedi ({e}), otomatik tespite geciliyor.")
        return None


# ---------------------------------------------------------------------------
# Yardimci: HoughLines tabanli yatay serit tespiti
# ---------------------------------------------------------------------------

def _detect_horizontal_lines(
    gray_roi: np.ndarray,
    roi_offset_y: int,
) -> List[Tuple[float, float, float, float]]:
    """
    Canny + HoughLinesP ile yatay cizgileri bulur.

    Returns: [(x1, y1_abs, x2, y2_abs), ...] — mutlak koordinatlar
    """
    blurred = cv2.GaussianBlur(gray_roi, (5, 5), 0)
    edges = cv2.Canny(blurred, 30, 90, apertureSize=3)

    lines = cv2.HoughLinesP(
        edges,
        rho=HOUGH_RHO,
        theta=HOUGH_THETA,
        threshold=HOUGH_THRESHOLD,
        minLineLength=HOUGH_MIN_LINE_LEN,
        maxLineGap=HOUGH_MAX_LINE_GAP,
    )

    if lines is None:
        return []

    horizontal = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        if dx < 1:
            continue
        angle_deg = abs(np.degrees(np.arctan2(dy, dx)))
        if angle_deg <= MAX_ANGLE_DEG:
            horizontal.append((
                float(x1), float(y1 + roi_offset_y),
                float(x2), float(y2 + roi_offset_y),
            ))

    return horizontal


def _cluster_by_y(
    lines: List[Tuple[float, float, float, float]],
    gap: int = CLUSTER_GAP_PX,
) -> List[List[Tuple[float, float, float, float]]]:
    """
    Cizgileri y merkezine gore sirala, gap'ten buyuk atlayislarda yeni grup ac.
    """
    if not lines:
        return []

    # Y merkezi: her cizginin orta noktasi
    keyed = sorted(lines, key=lambda l: (l[1] + l[3]) / 2.0)
    clusters: List[List] = [[keyed[0]]]

    for line in keyed[1:]:
        y_mid = (line[1] + line[3]) / 2.0
        prev_y_mid = (clusters[-1][-1][1] + clusters[-1][-1][3]) / 2.0
        if abs(y_mid - prev_y_mid) <= gap:
            clusters[-1].append(line)
        else:
            clusters.append([line])

    return clusters


def _group_bbox(cluster: List[Tuple[float, float, float, float]]) -> Tuple[float, float, float, float]:
    """Bir grubun x_min, y_min, x_max, y_max'ini hesapla."""
    xs = [l[0] for l in cluster] + [l[2] for l in cluster]
    ys = [l[1] for l in cluster] + [l[3] for l in cluster]
    return min(xs), min(ys), max(xs), max(ys)


def _is_consistent_striped(clusters: List, frame_w: int) -> bool:
    """
    Cluster listesinin yaya gecidi karakteristiklerine sahip olup olmadigini denetler.
    Kriter:
      - En az MIN_STRIPE_GROUPS grup
      - Her grubun yatay uzunlugu >= frame_w * 0.15
      - Gruplar arasi Y araliginin tutarliligi (CV <= MAX_GAP_CV)
    """
    if len(clusters) < MIN_STRIPE_GROUPS:
        return False

    # Uzunluk filtresi
    valid = []
    for c in clusters:
        xmin, _, xmax, _ = _group_bbox(c)
        if (xmax - xmin) >= frame_w * 0.15:
            valid.append(c)

    if len(valid) < MIN_STRIPE_GROUPS:
        return False

    # Aralik tutarlilik kontrolu
    y_centers = []
    for c in valid:
        _, ymin, _, ymax = _group_bbox(c)
        y_centers.append((ymin + ymax) / 2.0)

    y_centers.sort()
    gaps = [y_centers[i + 1] - y_centers[i] for i in range(len(y_centers) - 1)]
    if not gaps:
        return False

    mean_gap = np.mean(gaps)
    std_gap = np.std(gaps)
    cv = std_gap / (mean_gap + 1e-6)

    return cv <= MAX_GAP_CV


# ---------------------------------------------------------------------------
# Ana otomatik tespit fonksiyonu
# ---------------------------------------------------------------------------

def auto_detect_crosswalk(frame: np.ndarray) -> Optional[np.ndarray]:
    """
    Goruntude yaya gecidi arar (Canny + HoughLinesP yontemi).

    Returns:
        np.ndarray shape (4,2) int32 kose koordinatlari, veya None.
    """
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # CLAHE: aydinlatma normalizasyonu
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # ROI: alt 2/3
    roi_top = h // 3
    roi = gray[roi_top:, :]

    lines = _detect_horizontal_lines(roi, roi_offset_y=roi_top)

    if not lines:
        print("[Yaya Gecidi] Oto-tespit: yatay cizgi bulunamadi.")
        return None

    clusters = _cluster_by_y(lines)

    if not _is_consistent_striped(clusters, w):
        print(f"[Yaya Gecidi] Oto-tespit: {len(clusters)} grup bulundu ancak tutarlilik yeterli degil.")
        return None

    # Tum gecerli gruplarin birlesik bounding box'u
    all_lines = [l for c in clusters for l in c]
    xs = [l[0] for l in all_lines] + [l[2] for l in all_lines]
    ys = [l[1] for l in all_lines] + [l[3] for l in all_lines]

    pad = 8
    x_min = max(0, int(min(xs)) - pad)
    x_max = min(w, int(max(xs)) + pad)
    y_min = max(0, int(min(ys)) - pad)
    y_max = min(h, int(max(ys)) + pad)

    polygon = np.array([
        [x_min, y_min],
        [x_max, y_min],
        [x_max, y_max],
        [x_min, y_max],
    ], dtype=np.int32)

    print(
        f"[Yaya Gecidi] Oto-tespit basarili. "
        f"Grup sayisi: {len(clusters)}, "
        f"Alan: ({x_min},{y_min})-({x_max},{y_max})"
    )
    return polygon


# ---------------------------------------------------------------------------
# Interaktif secici — crosswalk_setup'tan import et
# ---------------------------------------------------------------------------

def _run_interactive(frame: np.ndarray) -> Optional[np.ndarray]:
    """crosswalk_setup modulu yoksa None dondurur."""
    try:
        from crosswalk_setup import interactive_zone_picker
        return interactive_zone_picker(frame)
    except ImportError as e:
        print(f"[Yaya Gecidi] crosswalk_setup yuklenemedi: {e}")
        return None


# ---------------------------------------------------------------------------
# Ana giris noktasi
# ---------------------------------------------------------------------------

def detect_or_fallback(
    frame: np.ndarray,
    fallback_polygon: np.ndarray,
    interactive: bool = True,
) -> Tuple[np.ndarray, bool]:
    """
    Oncelik sirasi:
      1. crosswalk_zone.json varsa yukle
      2. Yoksa auto_detect_crosswalk() dene
      3. Basarisizsa ve interactive=True ise interaktif secici ac
      4. Hepsi basarisizsa fallback_polygon don

    Returns:
        (polygon: np.ndarray, auto_detected: bool)
    """
    h, w = frame.shape[:2]

    # --- 1. JSON kayit ---
    saved = _load_json()
    if saved is not None:
        return saved, True

    # --- 2. Otomatik tespit ---
    auto = auto_detect_crosswalk(frame)
    if auto is not None:
        _save_json(auto, (w, h))
        return auto, True

    print("[Yaya Gecidi] Otomatik tespit basarisiz.")

    # --- 3. Interaktif mod ---
    if interactive:
        print("[Yaya Gecidi] Interaktif zon secimi baslatiliyor...")
        chosen = _run_interactive(frame)
        if chosen is not None:
            # JSON kaydi crosswalk_setup icerisinde zaten yapildi
            return chosen, True
        print("[Yaya Gecidi] Interaktif secim iptal edildi.")

    # --- 4. Fallback ---
    print("[Yaya Gecidi] Config'deki manuel koordinatlar kullaniliyor.")
    return fallback_polygon, False
