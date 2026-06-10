import os
import supervision as sv
from ultralytics import YOLO

# Model dosyasini D diskine kaydet
_MODEL_DIR = 'D:/SmartWalk/models'
os.makedirs(_MODEL_DIR, exist_ok=True)


class SmartWalkDetector:
    def __init__(self, model_path: str = None):
        if model_path is None:
            model_path = os.path.join(_MODEL_DIR, 'yolov8n.pt')
        self.model = YOLO(model_path)

    def detect(self, frame) -> sv.Detections:
        results = self.model(frame, verbose=False)[0]
        return sv.Detections.from_ultralytics(results)
