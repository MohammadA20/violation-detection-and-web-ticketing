# scripts/master_car_export.py
from ultralytics import YOLO
import cv2
import json
from pathlib import Path
from collections import defaultdict

# ================= SETTINGS =================
import os
VIDEO_PATH = os.environ.get("VIDEO_PATH", "test_videos/test3.mp4")

MODEL_PATH = "yolov8n.pt"

CONF = 0.45
IOU = 0.50
IMGSZ = 640
TRACKER = "bytetrack.yaml"

# COCO: person=0, car=2, motorcycle=3, bus=5, truck=7
VEHICLE_CLS = {2, 3, 5, 7}

# Export
OUT_DIR = Path("results/master_cars")
OUT_JSON = Path("results/master_car_tracks.json")

TOPK_PER_TRACK = 8

# ✅ خففنا الفلاتر حتى ما يصير 0
MIN_AREA = 1200          # كان 3500 (قاسي عالبعيد)
MIN_SHARPNESS = 12.0     # كان 35 (قاسي)

PAD_RATIO = 0.08
# ===========================================


def sharpness_score(bgr):
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(g, cv2.CV_64F).var())

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def crop_with_pad(frame, x1, y1, x2, y2, pad_ratio):
    w = x2 - x1
    h = y2 - y1
    pad = int(max(w, h) * pad_ratio)

    x1p = clamp(x1 - pad, 0, frame.shape[1] - 1)
    y1p = clamp(y1 - pad, 0, frame.shape[0] - 1)
    x2p = clamp(x2 + pad, 1, frame.shape[1])
    y2p = clamp(y2 + pad, 1, frame.shape[0])

    if x2p <= x1p or y2p <= y1p:
        return None, (x1, y1, x2, y2)
    return frame[y1p:y2p, x1p:x2p].copy(), (x1p, y1p, x2p, y2p)

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    model = YOLO(MODEL_PATH)

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {VIDEO_PATH}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_idx = 0

    # candidates[tid] = list of dicts
    candidates = defaultdict(list)

    # ============ PASS 1: collect candidates ============
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        ts = frame_idx / fps

        res = model.track(
            frame,
            persist=True,
            conf=CONF,
            iou=IOU,
            imgsz=IMGSZ,
            tracker=TRACKER,
            verbose=False
        )

        for r in res:
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
                w = x2 - x1
                h = y2 - y1
                if w <= 1 or h <= 1:
                    continue

                area = w * h
                if area < MIN_AREA:
                    continue

                crop, bbp = crop_with_pad(frame, x1, y1, x2, y2, PAD_RATIO)
                if crop is None or crop.size == 0:
                    continue

                sharp = sharpness_score(crop)

                # ✅ بدل ما نفلتر الشاربنس ونخسر كل شي: نخليه يدخل بس score أقل
                # score = area + (sharp * weight) بس إذا sharp ضعيف رح ينزل
                score = float(area) + 600.0 * float(sharp)

                candidates[tid].append({
                    "score": float(score),
                    "area": int(area),
                    "sharp": round(float(sharp), 2),
                    "timestamp_sec": round(float(ts), 3),
                    "frame_idx": int(frame_idx),
                    "cls_id": int(cls),
                    "bbox_xyxy": [int(bbp[0]), int(bbp[1]), int(bbp[2]), int(bbp[3])],
                })

    cap.release()

    # ============ PASS 2: export TOPK per track ============
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        raise RuntimeError("Cannot reopen video for export")

    tracks_out = []

    for tid, items in candidates.items():
        if not items:
            continue

        # sort by score
        items.sort(key=lambda d: d["score"], reverse=True)

        picked = []
        used_sec = set()

        # ✅ pick 1 per second to diversify
        for d in items:
            sec = int(d["timestamp_sec"])
            if sec in used_sec:
                continue
            used_sec.add(sec)

            # ✅ soft sharpness gate: if very low, skip unless we have nothing yet
            if d["sharp"] < MIN_SHARPNESS and len(picked) >= 2:
                continue

            picked.append(d)
            if len(picked) >= TOPK_PER_TRACK:
                break

        # ✅ fallback: إذا ما طلع ولا وحدة بسبب الشاربنس، خذ أول وحدة بأي حال
        if not picked:
            picked = items[:min(TOPK_PER_TRACK, len(items))]

        tdir = OUT_DIR / f"track_{tid}"
        tdir.mkdir(parents=True, exist_ok=True)

        exports = []
        for k, d in enumerate(picked):
            fidx = int(d["frame_idx"])
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, fidx - 1))
            ok, frame = cap.read()
            if not ok:
                continue

            x1, y1, x2, y2 = d["bbox_xyxy"]
            crop = frame[y1:y2, x1:x2].copy()
            if crop is None or crop.size == 0:
                continue

            out_path = tdir / f"img_{k:03d}_t{d['timestamp_sec']}_sh{d['sharp']}_a{d['area']}.jpg"
            cv2.imwrite(str(out_path), crop)

            exports.append({
                "img_path": str(out_path).replace("\\", "/"),
                "timestamp_sec": d["timestamp_sec"],
                "bbox_xyxy": d["bbox_xyxy"],
                "sharp": d["sharp"],
                "area": d["area"],
                "cls_id": d["cls_id"],
            })

        tracks_out.append({
            "track_id": int(tid),
            "num_candidates": int(len(items)),
            "num_exported": int(len(exports)),
            "images": exports
        })

    cap.release()

    OUT_JSON.write_text(json.dumps({
        "video": VIDEO_PATH,
        "tracks_exported": len(tracks_out),
        "tracks": tracks_out
    }, indent=2), encoding="utf-8")

    print("Done.")
    print("Tracks exported:", len(tracks_out))
    print("JSON:", OUT_JSON)
    print("Images folder:", OUT_DIR)
if __name__ == "__main__":
    main()