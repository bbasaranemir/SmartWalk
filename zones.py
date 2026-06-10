import cv2
import numpy as np
import supervision as sv
from config import POLYGON_COORDS


class CrosswalkZone:
    def __init__(self, frame_resolution: tuple = None, polygon_override: np.ndarray = None):
        # Otomatik tespit basarili olduysa onu, yoksa config'deki koordinatlari kullan
        poly = polygon_override if polygon_override is not None else POLYGON_COORDS
        self._poly = poly.reshape(-1, 1, 2).astype(np.float32)
        self.polygon = poly  # draw_ui icin ham koordinatlar

    def get_inside_detections(self, detections: sv.Detections) -> sv.Detections:
        if len(detections) == 0:
            return detections
        mask = np.array([
            cv2.pointPolygonTest(
                self._poly,
                (float((x1 + x2) / 2), float(y2)),
                measureDist=False,
            ) >= 0
            for x1, y1, x2, y2 in detections.xyxy
        ], dtype=bool)
        return detections[mask]
