"""Yalnız olay SONRASI değerlendirme; tespit algoritmasının girdisi değildir."""
import math
from vision_geometry import project
import numpy as np


def evaluate_bbox(bbox, frame):
    """Kaydedilmiş olayı bağımsız simülasyon kişi konumlarıyla ilişkilendir."""
    x, y, w, h = bbox
    best_iou, best_id = 0, None
    truth_boxes = []
    for index in range(3):
        phase = frame['sim_time'] * (.8 + .1 * index) + 8 * index
        east = (-30 + 35 * index) + 16 * math.sin(phase / 16)
        north = 150 + 70 * index + 3 * math.sin(phase / 7)
        corners = [[east + dx, north + dy, z]
                   for dx in (-.35, .35) for dy in (-.35, .35) for z in (0, 1.8)]
        uv, depth = project(corners, frame)
        if np.min(depth) <= 0:
            continue
        lo, hi = uv.min(axis=0), uv.max(axis=0)
        truth_boxes.append({'walker': index + 1, 'bbox': [*lo, *(hi - lo)]})
        width = max(0, min(x + w, hi[0]) - max(x, lo[0]))
        height = max(0, min(y + h, hi[1]) - max(y, lo[1]))
        intersection = width * height
        union = w * h + (hi[0] - lo[0]) * (hi[1] - lo[1]) - intersection
        iou = intersection / max(union, 1)
        if iou > best_iou:
            best_iou, best_id = float(iou), index + 1
    return {'best_walker': best_id, 'iou': best_iou,
            'true_positive': best_iou > .06, 'truth_boxes': truth_boxes}
