# Yaya gecidi poligonunu fareyle sec, config.py'ye otomatik kaydet.
# Kullanim: python set_polygon.py --video D:\SmartWalk\video\crosswalk.mp4
#           python set_polygon.py --demo        (webcam)
#
# ADIMLAR:
#   1. Video acilir — SPACE ile duraklat
#   2. Yaya gecidinin 4 kosesine SOL TIKLA (saat yonu)
#   3. 4 nokta tamamlaninca ENTER'a bas → config.py guncellenir
#   4. Geri almak icin Z tusi
#   5. Iptal: Q

import sys
import os
import re
sys.path.insert(0, 'D:/SmartWalk/lib')

import cv2
import numpy as np
import argparse

CONFIG_PATH = r"D:\SmartWalk\config.py"

points = []
frame_display = None
frame_clean = None


def draw_state(img):
    vis = img.copy()
    n = len(points)
    colors = [(0, 120, 255), (0, 200, 255), (0, 255, 200), (0, 255, 0)]

    for i, pt in enumerate(points):
        cv2.circle(vis, pt, 6, colors[i], -1)
        cv2.putText(vis, str(i + 1), (pt[0] + 8, pt[1] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, colors[i], 2)

    if n >= 2:
        for i in range(n - 1):
            cv2.line(vis, points[i], points[i + 1], (0, 200, 255), 2)
    if n == 4:
        cv2.line(vis, points[3], points[0], (0, 255, 0), 2)
        cv2.fillPoly(vis, [np.array(points)], (0, 255, 100))
        alpha_vis = cv2.addWeighted(vis, 0.4, img.copy(), 0.6, 0)
        vis = alpha_vis
        cv2.polylines(vis, [np.array(points).reshape(-1, 1, 2)], True, (0, 255, 0), 2)
        cv2.putText(vis, "ENTER = Kaydet   Z = Geri al   Q = Iptal",
                    (10, vis.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    else:
        remaining = 4 - n
        msg = f"Yaya gecidinin {n+1}. kosesine tikla  ({remaining} nokta kaldi)"
        cv2.putText(vis, msg, (10, vis.shape[0] - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 2)

    return vis


def mouse_cb(event, x, y, flags, param):
    global frame_display
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(points) < 4:
            points.append((x, y))
            print(f"  Nokta {len(points)}: ({x}, {y})")
        frame_display = draw_state(frame_clean)


def save_to_config(pts):
    coords = str([[p[0], p[1]] for p in pts])
    new_line = f"POLYGON_COORDS = np.array({coords}, dtype=np.int32)"

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    updated = re.sub(
        r"POLYGON_COORDS\s*=\s*np\.array\([\s\S]*?dtype=np\.int32\)",
        new_line,
        content
    )

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"\n[OK] config.py guncellendi:")
    print(f"     {new_line}")


def main():
    global frame_display, frame_clean, points

    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    if args.demo:
        cap = cv2.VideoCapture(0)
    elif args.video:
        cap = cv2.VideoCapture(args.video)
    else:
        print("Kullanim:")
        print("  python set_polygon.py --video D:\\SmartWalk\\video\\crosswalk.mp4")
        print("  python set_polygon.py --demo")
        sys.exit(1)

    if not cap.isOpened():
        print("[Hata] Kaynak acilamadi.")
        sys.exit(1)

    # Video ortasina atla
    if args.video:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)

    ret, frame = cap.read()
    cap.release()
    if not ret:
        print("[Hata] Frame alinamadi.")
        sys.exit(1)

    frame_clean = frame.copy()
    frame_display = draw_state(frame_clean)

    win = "Yaya Gecidi Sec - Sol Tikla (4 nokta) | ENTER=Kaydet  Z=Geri  Q=Iptal"
    cv2.namedWindow(win)
    cv2.setMouseCallback(win, mouse_cb)

    print("\n=== YAYA GECIDI BELIRLEME ===")
    print("Adim 1: Video penceresinde yaya gecidinin 4 kosesine tikla (saat yonu)")
    print("Adim 2: 4 nokta tamam → ENTER'a bas → config.py otomatik guncellenir")
    print("Not   : Z = son noktayi sil   Q = iptal\n")

    paused = True  # Bastan duraklat — kullanici noktaları secsin

    while True:
        cv2.imshow(win, frame_display)
        key = cv2.waitKey(30) & 0xFF

        if key == ord('q'):
            print("Iptal edildi.")
            break

        elif key == ord('z') and points:
            removed = points.pop()
            print(f"  Nokta silindi: {removed}")
            frame_display = draw_state(frame_clean)

        elif key == 13 and len(points) == 4:  # ENTER
            save_to_config(points)
            print("\n[SmartWalk] Artik su komutla baslat:")
            if args.video:
                print(f"  python D:\\SmartWalk\\main.py --video {args.video}")
            else:
                print("  python D:\\SmartWalk\\main.py --demo")
            break

        elif key == 13 and len(points) != 4:
            print(f"  Henuz {len(points)} nokta var, 4 tane gerekli!")

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
