from ultralytics import YOLO
import cv2
import json
from pathlib import Path
import math

# ================= SETTINGS =================
VIDEO_PATH = "test_videos/test4p.mp4"
VEH_MODEL_PATH = "yolov8m.pt"
SEATBELT_MODEL_PATH = "models/seatbelt_best_3.pt"   # <-- model seatbelt

CONF_VEH = 0.25
IOU_VEH  = 0.50

CONF_SEATBELT = 0.20
IOU_SEATBELT  = 0.40

OUT_VIDEO = Path("results/seatbelt_output.mp4")
OUT_JSON  = Path("results/seatbelt_events.json")

PERSON = 0
CAR = 2
BUS = 5
TRUCK = 7

COOLDOWN_SEC = 2.0

# ROI for chest/shoulder area (better for seatbelt)
ROI_Y1 = 0.15
ROI_Y2 = 0.65
ROI_X_PAD = 0.15

DEBUG = True
# ===========================================

OUT_VIDEO.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

veh_model = YOLO(VEH_MODEL_PATH)
seatbelt_model = YOLO(SEATBELT_MODEL_PATH)

cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    raise RuntimeError(f"Cannot open video: {VIDEO_PATH}")

fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter(str(OUT_VIDEO), fourcc, fps, (W, H))

cooldown_frames = 0
cooldown_max = int(COOLDOWN_SEC * fps)

events = []
frame_idx = 0

seatbelt_found = False

def center(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def crop_seatbelt_roi(frame, person_box):
    px1, py1, px2, py2 = person_box
    bw = px2 - px1
    bh = py2 - py1

    xpad = int(bw * ROI_X_PAD)
    x1 = max(0, px1 - xpad)
    x2 = min(W, px2 + xpad)

    # upper-middle body where seatbelt usually appears
    y1 = max(0, py1 + int(bh * ROI_Y1))
    y2 = min(H, py1 + int(bh * ROI_Y2))

    if x2 <= x1 or y2 <= y1:
        return None, (x1, y1, x2, y2)

    return frame[y1:y2, x1:x2], (x1, y1, x2, y2)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_idx += 1
    t_sec = frame_idx / fps

    # ---- 1) detect vehicles + persons ----
    vres = veh_model.predict(frame, conf=CONF_VEH, iou=IOU_VEH, verbose=False)

    persons = []
    cars = []

    for r in vres:
        if r.boxes is None:
            continue
        for b in r.boxes:
            cls = int(b.cls[0])
            x1, y1, x2, y2 = map(int, b.xyxy[0])
            conf = float(b.conf[0])

            if cls == PERSON:
                persons.append(((x1, y1, x2, y2), conf))
            elif cls in (CAR, TRUCK, BUS):
                cars.append(((x1, y1, x2, y2), conf))

    if DEBUG and frame_idx % int(fps) == 0:
        print(f"[frame {frame_idx}] persons={len(persons)} cars={len(cars)}")

    # draw cars
    for (cbox, cc) in cars:
        x1, y1, x2, y2 = cbox
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)

    if not cars or not persons:
        writer.write(frame)
        continue

    # ---- 2) pick biggest car, choose closest person ----
    cars_sorted = sorted(
        cars,
        key=lambda x: (x[0][2] - x[0][0]) * (x[0][3] - x[0][1]),
        reverse=True
    )
    car_box, _ = cars_sorted[0]
    car_c = center(car_box)

    best_person = None
    best_d = 1e9
    for (pbox, pc) in persons:
        d = dist(center(pbox), car_c)
        if d < best_d:
            best_d = d
            best_person = (pbox, pc)

    if best_person is None:
        writer.write(frame)
        continue

    pbox, _ = best_person
    px1, py1, px2, py2 = pbox
    cv2.rectangle(frame, (px1, py1), (px2, py2), (0, 255, 0), 2)

    # ---- 3) crop seatbelt ROI and run seatbelt detector ----
    roi_img, (rx1, ry1, rx2, ry2) = crop_seatbelt_roi(frame, pbox)
    cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (0, 255, 255), 2)

    seatbelt_detected = False
    if roi_img is not None and roi_img.size > 0:
        sres = seatbelt_model.predict(
            roi_img,
            conf=CONF_SEATBELT,
            iou=IOU_SEATBELT,
            verbose=False
        )

        for r in sres:
            if r.boxes is None:
                continue
            if len(r.boxes) > 0:
                seatbelt_detected = True

                # optional: draw detections inside ROI
                for b in r.boxes:
                    sx1, sy1, sx2, sy2 = map(int, b.xyxy[0])
                    cv2.rectangle(
                        frame,
                        (rx1 + sx1, ry1 + sy1),
                        (rx1 + sx2, ry1 + sy2),
                        (0, 0, 255),
                        2
                    )
                break

    if seatbelt_detected:
        cv2.putText(frame, "SEATBELT DETECTED", (30, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 3)

        if cooldown_frames == 0:
            event = {
                "type": "SEATBELT_DETECTED",
                "timestamp_sec": round(t_sec, 2),
                "frame_idx": frame_idx,
                "video": str(OUT_VIDEO).replace("\\", "/")
            }
            events.append(event)
            cooldown_frames = cooldown_max

            seatbelt_found = True
            print(f"[SEATBELT DETECTED] t={t_sec:.2f}s frame={frame_idx}")

    else:
        cv2.putText(frame, "NO SEATBELT", (30, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)

    if cooldown_frames > 0:
        cooldown_frames -= 1

    writer.write(frame)

cap.release()
writer.release()

OUT_JSON.write_text(json.dumps(events, indent=2), encoding="utf-8")

print("\n=== SEATBELT RESULT ===")
print("SEATBELT FOUND:", "YES" if seatbelt_found else "NO")
print("Events count:", len(events))
print("Output video:", OUT_VIDEO)
print("Events JSON :", OUT_JSON)