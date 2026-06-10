# Yaya gecidi tespit algoritmini debug eder.
# Kullanim: python test_detector.py
# Cikti: D:\SmartWalk\ klasorune debug goruntuleri kaydeder.

import sys
import os
sys.path.insert(0, 'D:/SmartWalk/lib')

import cv2
import numpy as np

VIDEO = r"D:\SmartWalk\video\crosswalk.mp4"
OUT_DIR = r"D:\SmartWalk"


def run_debug(frame):
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    roi_top = h // 3
    roi = gray[roi_top:h, :]

    os.makedirs(OUT_DIR, exist_ok=True)

    # Gri goruntu + ROI cizgisi
    gray_full = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    cv2.line(gray_full, (0, roi_top), (w, roi_top), (0, 255, 255), 2)
    cv2.putText(gray_full, "ROI baslangiç", (5, roi_top - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    cv2.imwrite(os.path.join(OUT_DIR, "dbg_0_gray.jpg"), gray_full)
    print(f"[1] Gri goruntu + ROI: dbg_0_gray.jpg  (boyut={w}x{h})")

    best = {"thresh": None, "area": 0, "img": None, "polygon": None}

    for thresh_val in [120, 140, 160, 180, 200, 220]:
        _, white = cv2.threshold(roi, thresh_val, 255, cv2.THRESH_BINARY)

        kw = max(20, w // 20)
        kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (kw, 3))
        stripes = cv2.morphologyEx(white, cv2.MORPH_OPEN, kernel_h)

        kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 25))
        merged = cv2.morphologyEx(stripes, cv2.MORPH_CLOSE, kernel_v)

        contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        total_area = sum(cv2.contourArea(c) for c in contours)

        # Gorsel
        vis = cv2.cvtColor(merged, cv2.COLOR_GRAY2BGR)
        for c in contours:
            a = cv2.contourArea(c)
            cv2.drawContours(vis, [c], -1, (0, 120, 255), 2)
            x, y, bw2, bh2 = cv2.boundingRect(c)
            cv2.putText(vis, f"{int(a)}", (x, max(0, y - 3)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 220, 0), 1)

        tag = f"T={thresh_val}  contour sayisi={len(contours)}  toplam_alan={int(total_area)}"
        cv2.putText(vis, tag, (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1)

        # Tum frame yuksekligi ile birlesik goster
        full = np.zeros((h, w, 3), dtype=np.uint8)
        full[roi_top:h, :] = vis
        cv2.line(full, (0, roi_top), (w, roi_top), (0, 255, 255), 1)
        fname = f"dbg_thresh_{thresh_val}.jpg"
        cv2.imwrite(os.path.join(OUT_DIR, fname), full)
        print(f"[T={thresh_val}]  kontur={len(contours)}  toplam_alan={int(total_area)}  → {fname}")

        if contours:
            largest = max(contours, key=cv2.contourArea)
            la = cv2.contourArea(largest)
            if la > best["area"]:
                best["area"] = la
                best["thresh"] = thresh_val
                x, y, bw2, bh2 = cv2.boundingRect(largest)
                y_real = y + roi_top
                pad = 5
                best["polygon"] = np.array([
                    [max(0, x - pad),       max(0, y_real - pad)],
                    [min(w, x + bw2 + pad), max(0, y_real - pad)],
                    [min(w, x + bw2 + pad), min(h, y_real + bh2 + pad)],
                    [max(0, x - pad),       min(h, y_real + bh2 + pad)],
                ], dtype=np.int32)

    # Sonuc
    result = frame.copy()
    if best["polygon"] is not None:
        poly = best["polygon"].reshape(-1, 1, 2)
        cv2.polylines(result, [poly], True, (0, 255, 0), 3)
        label = f"TESPIT EDILDI (T={best['thresh']}  alan={int(best['area'])})"
        cv2.putText(result, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        print(f"\n[OK] En iyi esik: T={best['thresh']}  buyuk_alan={int(best['area'])}")
        print(f"     Polygon: {best['polygon'].tolist()}")
    else:
        cv2.putText(result, "TESPIT EDILEMEDI", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        print("\n[FAIL] Hicbir esik ile tespit yapilamadi.")
        print("       Manuel koordinatlar kullanilacak.")

    cv2.imwrite(os.path.join(OUT_DIR, "dbg_result.jpg"), result)
    print(f"\n[Son] Sonuc: D:\\SmartWalk\\dbg_result.jpg")


def main():
    if not os.path.exists(VIDEO):
        print(f"[Hata] Video bulunamadi: {VIDEO}")
        print("       Baska bir yol girmek icin scripti duzenle.")
        sys.exit(1)

    cap = cv2.VideoCapture(VIDEO)
    # Ortadaki kareyi al
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        print("[Hata] Video okunamadi.")
        sys.exit(1)

    print(f"Analiz edilen kare: {total // 2}/{total}  boyut={frame.shape[1]}x{frame.shape[0]}")
    run_debug(frame)


if __name__ == "__main__":
    main()
