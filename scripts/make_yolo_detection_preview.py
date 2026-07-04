import cv2
import os
from pathlib import Path
from ultralytics import YOLO

VIDEO_PATH = os.environ.get("VIDEO_PATH", "test_videos/test4p.mp4")
MODEL_PATH = "yolov8n.pt"

CONF = 0.45
VEHICLE_CLS = {2, 3, 5, 7}  # car, motorcycle, bus, truck

OUT_PATH = Path("results/yolo_detection_video.mp4")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

model = YOLO(MODEL_PATH)

cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    raise RuntimeError(f"Cannot open video: {VIDEO_PATH}")

fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

writer = cv2.VideoWriter(
    str(OUT_PATH),
    cv2.VideoWriter_fourcc(*"mp4v"),
    fps,
    (w, h)
)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model.predict(
        frame,
        conf=CONF,
        verbose=False
    )

    vis = frame.copy()

    for r in results:
        if r.boxes is None:
            continue

        for b in r.boxes:
            cls = int(b.cls[0])
            conf = float(b.conf[0])

            if cls not in VEHICLE_CLS:
                continue

            x1, y1, x2, y2 = map(int, b.xyxy[0])

            if cls == 2:
                label = "car"
            elif cls == 3:
                label = "motorcycle"
            elif cls == 5:
                label = "bus"
            elif cls == 7:
                label = "truck"
            else:
                label = "vehicle"

            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 3)
            cv2.putText(
                vis,
                f"{label} {conf:.2f}",
                (x1, max(30, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
                cv2.LINE_AA
            )

    writer.write(vis)

cap.release()
writer.release()

print(f"Saved: {OUT_PATH}")