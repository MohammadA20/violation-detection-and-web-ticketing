# scripts/plate_per_car_export.py
import cv2
import json
import os
from pathlib import Path
from collections import defaultdict
from ultralytics import YOLO

# ================= SETTINGS =================
VIDEO_PATH = os.environ.get("VIDEO_PATH", "test_videos/test3.mp4")

VEH_MODEL_PATH   = "yolov8n.pt"
PLATE_MODEL_PATH = "models/plate_best.pt"

CONF_VEH = 0.45
IOU_VEH  = 0.50

CONF_PLT = 0.18
IOU_PLT  = 0.50
IMGSZ_PLT = 1280

TRACKER = "bytetrack.yaml"
VEHICLE_CLS = {2, 3, 5, 7}  # car,bus,truck

OUT_DIR  = Path("results/plates_crops_per_car")
OUT_JSON = Path("results/plate_detections_per_car.json")

TOPK_PER_CAR = 3
MAX_PLATES_PER_FRAME = 10

PAD_RATIO = 0.25
MIN_PLATE_AREA = 900
MIN_AR = 1.4
MAX_AR = 7.0
# ===========================================

# ================= HARD MODE (ONLY ON FAIL) =================
HARD_ENABLE = True

CAR_PAD_FALLBACK_1 = 0.10
CAR_PAD_FALLBACK_2 = 0.18

HARD_IMGSZ_PLT = 1600

RELAX_ENABLE = True
RELAX_MIN_PLATE_AREA = max(450, int(MIN_PLATE_AREA * 0.50))
RELAX_MIN_AR = max(0.95, MIN_AR - 0.55)
RELAX_MAX_AR = max(10.0, MAX_AR + 3.0)

GATE_TO_ORIG_VEH_BBOX = True
GATE_PAD_RATIO = 0.08
# ============================================================

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def crop(frame, bb, pad=0.0):
    x1, y1, x2, y2 = bb
    w = x2 - x1
    h = y2 - y1
    p = int(max(w, h) * pad)

    x1 = clamp(x1 - p, 0, frame.shape[1] - 1)
    y1 = clamp(y1 - p, 0, frame.shape[0] - 1)
    x2 = clamp(x2 + p, 0, frame.shape[1] - 1)
    y2 = clamp(y2 + p, 0, frame.shape[0] - 1)

    if x2 <= x1 or y2 <= y1:
        return None, (x1, y1, x2, y2)

    return frame[y1:y2, x1:x2].copy(), (x1, y1, x2, y2)

def _collect_plate_raw_dets(preds):
    raw = []
    for r in preds:
        if r.boxes is None:
            continue
        for b in r.boxes:
            conf = float(b.conf[0])
            px1, py1, px2, py2 = map(int, b.xyxy[0])
            raw.append((conf, [px1, py1, px2, py2]))
    return raw

def _filter_plate_dets(raw_dets, min_area, min_ar, max_ar):
    dets = []
    for conf, bb in raw_dets:
        px1, py1, px2, py2 = bb
        w = max(1, px2 - px1)
        h = max(1, py2 - py1)
        area = w * h
        ar = w / float(h)

        if area < min_area:
            continue
        if ar < min_ar or ar > max_ar:
            continue

        dets.append((conf, bb, area))
    return dets

def _gate_plate_center_to_vehicle(pbb_in_crop, crop_bbox_in_frame, orig_vbb, frame_w, frame_h):
    if not GATE_TO_ORIG_VEH_BBOX:
        return True

    px1, py1, px2, py2 = pbb_in_crop
    cx_crop = 0.5 * (px1 + px2)
    cy_crop = 0.5 * (py1 + py2)

    cx = crop_bbox_in_frame[0] + cx_crop
    cy = crop_bbox_in_frame[1] + cy_crop

    ox1, oy1, ox2, oy2 = orig_vbb
    ow = max(1, ox2 - ox1)
    oh = max(1, oy2 - oy1)
    p = int(max(ow, oh) * float(GATE_PAD_RATIO))

    gx1 = clamp(ox1 - p, 0, frame_w - 1)
    gy1 = clamp(oy1 - p, 0, frame_h - 1)
    gx2 = clamp(ox2 + p, 0, frame_w - 1)
    gy2 = clamp(oy2 + p, 0, frame_h - 1)

    return (gx1 <= cx <= gx2) and (gy1 <= cy <= gy2)

def _detect_plates_in_car(plate_model, car_img, conf, iou, imgsz):
    preds = plate_model.predict(car_img, conf=conf, iou=iou, imgsz=imgsz, verbose=False)
    return _collect_plate_raw_dets(preds)

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    veh_model = YOLO(VEH_MODEL_PATH)
    plate_model = YOLO(PLATE_MODEL_PATH)

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {VIDEO_PATH}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frame_idx = 0
    cand = defaultdict(list)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        t_sec = frame_idx / fps

        vres = veh_model.track(
            frame,
            persist=True,
            conf=CONF_VEH,
            iou=IOU_VEH,
            imgsz=640,
            tracker=TRACKER,
            verbose=False
        )

        vehicles = []
        for r in vres:
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
                vehicles.append((tid, [x1, y1, x2, y2]))

        for tid, vbb in vehicles:
            car_img, car_crop_bb = crop(frame, vbb, pad=0.0)
            if car_img is None:
                continue

            raw = _detect_plates_in_car(
                plate_model,
                car_img,
                conf=CONF_PLT,
                iou=IOU_PLT,
                imgsz=IMGSZ_PLT
            )
            dets = _filter_plate_dets(raw, MIN_PLATE_AREA, MIN_AR, MAX_AR)

            if HARD_ENABLE and (not dets):
                car_img2, car_crop_bb2 = crop(frame, vbb, pad=float(CAR_PAD_FALLBACK_1))
                if car_img2 is not None:
                    raw2 = _detect_plates_in_car(
                        plate_model,
                        car_img2,
                        conf=CONF_PLT,
                        iou=IOU_PLT,
                        imgsz=IMGSZ_PLT
                    )
                    dets2 = _filter_plate_dets(raw2, MIN_PLATE_AREA, MIN_AR, MAX_AR)

                    dets2 = [
                        (conf, bb, area)
                        for (conf, bb, area) in dets2
                        if _gate_plate_center_to_vehicle(bb, car_crop_bb2, vbb, frame_w, frame_h)
                    ]

                    if dets2:
                        dets = dets2
                        car_img = car_img2

                if not dets:
                    car_img3, car_crop_bb3 = crop(frame, vbb, pad=float(CAR_PAD_FALLBACK_2))
                    if car_img3 is not None:
                        raw3 = _detect_plates_in_car(
                            plate_model,
                            car_img3,
                            conf=CONF_PLT,
                            iou=IOU_PLT,
                            imgsz=HARD_IMGSZ_PLT
                        )

                        dets3 = _filter_plate_dets(raw3, MIN_PLATE_AREA, MIN_AR, MAX_AR)

                        if RELAX_ENABLE and (not dets3):
                            dets3 = _filter_plate_dets(
                                raw3,
                                RELAX_MIN_PLATE_AREA,
                                RELAX_MIN_AR,
                                RELAX_MAX_AR
                            )

                        dets3 = [
                            (conf, bb, area)
                            for (conf, bb, area) in dets3
                            if _gate_plate_center_to_vehicle(bb, car_crop_bb3, vbb, frame_w, frame_h)
                        ]

                        if dets3:
                            dets = dets3
                            car_img = car_img3

            dets.sort(key=lambda x: x[0], reverse=True)
            dets = dets[:MAX_PLATES_PER_FRAME]

            for conf, pbb, area in dets:
                plate_crop, pbbp = crop(car_img, pbb, pad=PAD_RATIO)
                if plate_crop is None or plate_crop.size == 0:
                    continue

                fname = f"car{tid}_t{t_sec:.2f}_c{conf:.3f}.jpg"
                out_path = OUT_DIR / fname
                cv2.imwrite(str(out_path), plate_crop)

                cand[str(tid)].append({
                    "car_id": int(tid),
                    "timestamp_sec": round(float(t_sec), 3),
                    "conf": round(float(conf), 3),
                    "bbox_xyxy": pbbp,
                    "crop_path": str(out_path).replace("\\", "/"),
                    "score": float(conf) + 0.000001 * float(area)
                })

    cap.release()

    records = []
    for tid, items in cand.items():
        items.sort(key=lambda d: d["score"], reverse=True)
        best = items[:TOPK_PER_CAR]

        for d in best:
            records.append({
                "car_id": d["car_id"],
                "timestamp_sec": d["timestamp_sec"],
                "conf": d["conf"],
                "bbox_xyxy": d["bbox_xyxy"],
                "crop_path": d["crop_path"]
            })

    OUT_JSON.write_text(json.dumps(records, indent=2), encoding="utf-8")

    print(f"Done. Saved {len(records)} plate crops.")
    print("JSON:", OUT_JSON)

if __name__ == "__main__":
    main()