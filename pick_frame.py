# Video acilir, istedigin kareye gelince 'S' tusuna bas - frame kaydedilir.
# Cikmak icin 'Q' tusuna bas.
# Kullanim: python pick_frame.py VIDEO_DOSYA_YOLU

import sys
import os
sys.path.insert(0, 'D:/SmartWalk/lib')

import cv2

if len(sys.argv) < 2:
    print("Kullanim: python pick_frame.py <video_yolu>")
    print("Ornek:    python pick_frame.py D:\\SmartWalk\\video\\test.mp4")
    sys.exit(1)

video_path = sys.argv[1]

if not os.path.exists(video_path):
    print(f"Dosya bulunamadi: {video_path}")
    sys.exit(1)

cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print("Video acilamadi.")
    sys.exit(1)

print("=" * 50)
print("KONTROLLER:")
print("  SPACE  → Duraklat / Devam ettir")
print("  S      → Bu kareyi kaydet")
print("  Q      → Cik")
print("=" * 50)

paused = False
saved_path = r"D:\SmartWalk\frame_for_polygon.jpg"

while True:
    if not paused:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

    cv2.imshow("Kare Sec - SPACE=Duraklat  S=Kaydet  Q=Cik", frame)
    key = cv2.waitKey(30) & 0xFF

    if key == ord('q'):
        break
    elif key == ord(' '):
        paused = not paused
        print("DURAKLATILDI" if paused else "DEVAM EDİYOR")
    elif key == ord('s'):
        cv2.imwrite(saved_path, frame)
        print(f"Kaydedildi: {saved_path}")
        print("")
        print("Simdi su siteye git:")
        print("https://roboflow.github.io/polygonzone/")
        print("frame_for_polygon.jpg dosyasini yukle, yaya gecidini ciz.")
        break

cap.release()
cv2.destroyAllWindows()
