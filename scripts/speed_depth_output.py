# scripts/speed_depth_output.py
from ultralytics import YOLO
import cv2
import math
import json
from pathlib import Path
from collections import defaultdict, deque

# ================= SETTINGS =================

import os
VIDEO_PATH = os.environ.get("VIDEO_PATH", "test_videos/test3.mp4")
MODEL_PATH = "yolov8n.pt"

CONF = 0.45
IOU  = 0.50
IMGSZ = 640
TRACKER = "bytetrack.yaml"

VEHICLE_CLS = {2, 3, 5, 7}  # car, motorcycle, bus, truck

CAR_W = 1.80
MOTO_W = 0.70
BUS_TRUCK_W = 2.50

HFOV_DEG = 50.0
SPEED_LIMIT_KMH = 60.0

EMA_ALPHA_Z   = 0.85
EMA_ALPHA_SPD = 0.85

MAX_KMH = 180.0
MIN_SPEED_KMH = 1.0       # خففناها شوي حتى البعيد يتحسب
MIN_SEEN_FRAMES = 8

# ✅ class-dependent thresholds (fix parked issue)
MIN_BW_CAR = 55
MIN_BW_MOTO = 28          # ✅ الموتو بوكس أصغر طبيعي
MIN_BW_BUS_TRUCK = 65

MIN_MOVING_CAR = 4.0
MIN_MOVING_MOTO = 2.5     # ✅ الموتو البعيد ما رح يوصل 4 بسهولة
MIN_MOVING_BUS_TRUCK = 4.0

MOVING_FRAMES_REQ_CAR = 6
MOVING_FRAMES_REQ_MOTO = 3  # ✅ أقل للموتو
MOVING_FRAMES_REQ_BUS_TRUCK = 6

MIN_Z_DELTA_M = 0.02      # ✅ خففناها شوي للبُعد
SPEED_DEADBAND_KMH = 1.2
OUTLIER_CAP_KMH = 160.0

Z_MED_N = 15

OUT_VIDEO = Path("results/speed_depth_multi_clean_output.mp4")
OUT_JSON  = Path("results/speed_depth_multi_clean_events.json")
# ===========================================

OUT_VIDEO.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

def ema(prev, x, a):
    return x if prev is None else (a * prev + (1.0 - a) * x)

def cls_width_m(cls_id: int) -> float:
    if cls_id == 3:
        return MOTO_W
    if cls_id in (5, 7):
        return BUS_TRUCK_W
    return CAR_W

def min_bw_for_cls(cls_id: int) -> int:
    if cls_id == 3:
        return MIN_BW_MOTO
    if cls_id in (5, 7):
        return MIN_BW_BUS_TRUCK
    return MIN_BW_CAR

def min_moving_for_cls(cls_id: int) -> float:
    if cls_id == 3:
        return MIN_MOVING_MOTO
    if cls_id in (5, 7):
        return MIN_MOVING_BUS_TRUCK
    return MIN_MOVING_CAR

def moving_req_for_cls(cls_id: int) -> int:
    if cls_id == 3:
        return MOVING_FRAMES_REQ_MOTO
    if cls_id in (5, 7):
        return MOVING_FRAMES_REQ_BUS_TRUCK
    return MOVING_FRAMES_REQ_CAR

def bottom_center_xyxy(bb):
    x1, y1, x2, y2 = bb
    return ((x1 + x2) / 2.0, float(y2))

model = YOLO(MODEL_PATH)

cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    raise RuntimeError(f"Cannot open video: {VIDEO_PATH}")

fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

writer = cv2.VideoWriter(str(OUT_VIDEO), cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))

f_px = (W / 2.0) / math.tan(math.radians(HFOV_DEG / 2.0))
cx = W / 2.0

track = defaultdict(lambda: {
    "seen": 0,
    "cls": None,

    "z_ema": None,
    "z_hist": deque(maxlen=Z_MED_N),

    "prev_t": None,
    "prev_x": None,
    "prev_z": None,

    "spd_ema": 0.0,
    "moving_hits": 0,

    "max_stable": 0.0,
    "max_raw": 0.0,

    "min_bw": 10**9,
    "max_bw": 0,
})

samples = []
frame_idx = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_idx += 1
    t_sec = frame_idx / fps

    results = model.track(
        frame,
        persist=True,
        conf=CONF,
        iou=IOU,
        imgsz=IMGSZ,
        tracker=TRACKER,
        verbose=False
    )

    dets = []
    for r in results:
        if r.boxes is None:
            continue
        for b in r.boxes:
            if b.id is None:
                continue
            cls = int(b.cls[0])
            if cls not in VEHICLE_CLS:
                continue
            tid = int(b.id[0])
            x1, y1, x2, y2 = map(int, b.xyxy[0])
            bw = max(1, x2 - x1)
            bh = max(1, y2 - y1)
            area = bw * bh
            ar = bw / float(max(1, bh))
            if cls in (5, 7) and ar < 0.8:
                continue
            if cls == 2 and ar < 0.7:
                continue

            dets.append((area, tid, cls, [x1, y1, x2, y2], bw))

    dets.sort(key=lambda x: x[0], reverse=True)
    dets = dets[:10]

    for _, tid, cls, bb, bw in dets:
        st = track[tid]
        st["seen"] += 1
        st["cls"] = cls
        st["min_bw"] = min(st["min_bw"], bw)
        st["max_bw"] = max(st["max_bw"], bw)

        # Z
        w_real = cls_width_m(cls)
        z_raw = (f_px * w_real) / float(max(1, bw))
        st["z_hist"].append(z_raw)
        z_med = sorted(st["z_hist"])[len(st["z_hist"]) // 2]
        st["z_ema"] = ema(st["z_ema"], z_med, EMA_ALPHA_Z)

        # X
        x_center, _ = bottom_center_xyxy(bb)
        X = ((x_center - cx) * st["z_ema"]) / f_px if st["z_ema"] is not None else 0.0

        # Speed
        spd_raw = 0.0
        can_speed = (bw >= min_bw_for_cls(cls)) and (st["z_ema"] is not None)

        if can_speed and st["prev_t"] is not None and st["prev_x"] is not None and st["prev_z"] is not None:
            dt = max(t_sec - st["prev_t"], 1e-6)
            dX = X - st["prev_x"]
            dZ = st["z_ema"] - st["prev_z"]
            dist_m = math.hypot(dX, dZ)
            spd_raw = (dist_m / dt) * 3.6

            if spd_raw < MIN_SPEED_KMH:
                spd_raw = 0.0
            if spd_raw > MAX_KMH:
                spd_raw = 0.0

            # extra clamp for spikes
            if spd_raw > OUTLIER_CAP_KMH:
                spd_raw = 0.0

        st["prev_t"] = t_sec
        st["prev_x"] = X
        st["prev_z"] = st["z_ema"]

        st["max_raw"] = max(st["max_raw"], float(spd_raw))
        st["spd_ema"] = ema(st["spd_ema"], spd_raw, EMA_ALPHA_SPD)
        st["max_stable"] = max(st["max_stable"], float(st["spd_ema"]))

        if st["spd_ema"] >= min_moving_for_cls(cls):
            st["moving_hits"] += 1

        # draw
        x1, y1, x2, y2 = bb
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)
        cv2.putText(frame, f"ID:{tid} cls:{cls} bw:{bw}", (x1, max(30, y1-28)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)

        show_speed = (st["seen"] >= MIN_SEEN_FRAMES and st["moving_hits"] >= 3)  # ✅ أسرع للظهور
        if show_speed:
            cv2.putText(frame, f"S:{st['spd_ema']:.1f}  Max:{st['max_stable']:.1f} km/h",
                        (x1, max(30, y1-6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0,0,255), 2)

        if frame_idx % max(1, int(fps)) == 0:
            samples.append({
                "timestamp_sec": round(t_sec, 2),
                "track_id": int(tid),
                "cls_id": int(cls),
                "bbox_xyxy": [int(x1), int(y1), int(x2), int(y2)],
                "bw": int(bw),
                "speed_now_kmh": round(float(st["spd_ema"]), 2),
                "max_stable_kmh": round(float(st["max_stable"]), 2),
            })

    writer.write(frame)

cap.release()
writer.release()

clean = {}
for tid, st in track.items():
    if st["seen"] < MIN_SEEN_FRAMES:
        continue

    req = moving_req_for_cls(int(st["cls"]) if st["cls"] is not None else 2)
    parked = (st["moving_hits"] < req)

    max_stable = 0.0 if parked else float(st["max_stable"])
    max_raw = 0.0 if parked else float(st["max_raw"])

    clean[str(tid)] = {
        "seen_frames": int(st["seen"]),
        "moving_frames": int(st["moving_hits"]),
        "parked": bool(parked),
        "cls_id": int(st["cls"]) if st["cls"] is not None else None,
        "min_bw": int(st["min_bw"]) if st["min_bw"] < 10**8 else None,
        "max_bw": int(st["max_bw"]),
        "max_stable_kmh": round(max_stable, 2),
        "max_raw_kmh": round(max_raw, 2),
        "violation": bool(max_stable >= SPEED_LIMIT_KMH),
    }

top_tid = None
top_speed = 0.0
for tid, info in clean.items():
    if info["parked"]:
        continue
    if info["max_stable_kmh"] > top_speed:
        top_speed = info["max_stable_kmh"]
        top_tid = int(tid) if tid.isdigit() else tid

out = {
    "summary": {
        "type": "BBOX_GROUND_SPEED",
        "speed_limit_kmh": float(SPEED_LIMIT_KMH),
        "top_track_id": top_tid,
        "top_max_stable_kmh": round(float(top_speed), 2),
        "hfov_deg": float(HFOV_DEG),
        "video_output": str(OUT_VIDEO).replace("\\", "/"),
    },
    "per_track": clean,
    "samples": samples
}

OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")

print("Done.")
print("Output video:", OUT_VIDEO)
print("Events JSON :", OUT_JSON)

print("\n--- Per-track summary (ALL) ---")
for tid, v in sorted(clean.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 10**9):
    tag = "PARKED" if v["parked"] else ("VIOLATION" if v["violation"] else "OK")
    print(f"ID {tid}: MaxStable={v['max_stable_kmh']} -> {tag} (moving_frames={v['moving_frames']}, cls={v['cls_id']}, bw={v['min_bw']}-{v['max_bw']})")
print("[OK] Speed finished")