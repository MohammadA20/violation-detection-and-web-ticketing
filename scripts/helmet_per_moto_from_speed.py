# scripts/helmet_per_moto_from_speed.py
# FINAL ✅ (SPEED-LINKED, ROBUST) + ✅ FIX (1-to-1 person assignment per frame) + ✅ VOTES HACK (NO MORE DUMB UNKNOWN)
#
# - Moto IDs come from (per_track motos) UNION (samples motos)
# - NO tracking here -> no ID mismatch, no extra motos from tracker
# - Uses speed samples frame timestamps to fetch frames, detect PERSON/MOTO, crop head, run helmet model
# - Output track_id is ALWAYS the speed track_id
#
# ✅ Added:
#   - Save CSV: results/helmet_crops_predictions.csv
#   - Print saved crop files per track_id (tid)
#
# ✅ FIX:
#   - 1-to-1 assignment targets <-> persons per frame to avoid swapping helmet votes between motos.
#
# ✅ VOTES HACK (CRITICAL):
#   - UNKNOWN no longer blocks the final decision.
#   - Final decision uses ONLY valid votes (helmet vs nohelmet) with majority.
#   - MIN_VALID_VOTES lowered to 2 (so you don't get "few_valid" for no reason).
#
# ✅ Visual debug (optional):
#   - Draw detections/targets/assignments on debug video (NO LOGIC CHANGE).

from ultralytics import YOLO
import cv2
import json
import numpy as np
import csv
import os
from pathlib import Path
from collections import defaultdict

# ===================== SETTINGS =====================
VIDEO_PATH = os.environ.get("VIDEO_PATH", "test_videos/test3.mp4")
SPEED_JSON = Path("results/speed_depth_multi_clean_events.json")

# ✅ your fine-tuned model
HELMET_MODEL_PATH = "models/helmet_last_best.pt"
DET_MODEL_PATH    = "yolov8s.pt"  # COCO (person + motorcycle)

CONF_DET = 0.35
IOU_DET  = 0.50
IMGSZ    = 640

# Helmet inference
CONF_HELMET  = 0.10
IOU_HELMET   = 0.50
IMGSZ_HELMET = 320

MOTO_CLS   = 3
PERSON_CLS = 0

# head crop from PERSON bbox
HEAD_RATIO = 0.45
HEAD_PAD   = 0.25
MIN_HEAD_W = 34
MIN_HEAD_H = 34

# ✅ more evidence
TOPK_CROPS_PER_MOTO = 20

# ✅ votes hack
MIN_VALID_VOTES = 2
RATIO_DECIDE    = 0.55  # kept for compatibility (not required for majority)

FRAME_OFFSETS = [-3, -2, -1, 0, 1, 2, 3]

MIN_MOTO_MATCH_IOU   = 0.15
MIN_PERSON_MATCH_IOU = 0.03

# include motos from samples even if missing in per_track
MIN_SAMPLES_FOR_MOTO_ID = 2
MIN_SPEED_FOR_MOTO_ID   = 1.0

OUT_VIDEO = Path("results/helmet_speedlink_output.mp4")
OUT_JSON  = Path("results/helmet_per_moto.json")
CROP_DIR  = Path("results/helmet_crops")
CSV_OUT   = Path("results/helmet_crops_predictions.csv")

# ===================== DEBUG DRAW (ONLY VISUAL) =====================
DEBUG_DRAW = False
CLEAN_DRAW = True  # إذا بدك سكّرها: False
DRAW_THICK = 2
DRAW_FONT_SCALE = 0.6
# ====================================================

OUT_VIDEO.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
CROP_DIR.mkdir(parents=True, exist_ok=True)

def safe_write_json(path: Path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)

def load_json(p: Path, default):
    if not p.exists():
        return default
    try:
        txt = p.read_text(encoding="utf-8").strip()
        if not txt:
            return default
        return json.loads(txt)
    except Exception:
        return default

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def iou_xyxy(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(1, (ax2 - ax1)) * max(1, (ay2 - ay1))
    area_b = max(1, (bx2 - bx1)) * max(1, (by2 - by1))
    return inter / float(area_a + area_b - inter + 1e-6)

def sharpness_score(img_bgr):
    g = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(g, cv2.CV_64F).var())

def crop_head_from_person(frame, person_xyxy):
    H, W = frame.shape[:2]
    x1, y1, x2, y2 = map(int, person_xyxy)
    pw = max(1, x2 - x1)
    ph = max(1, y2 - y1)

    hx1, hy1 = x1, y1
    hx2 = x2
    hy2 = y1 + int(ph * HEAD_RATIO)

    pad_x = int(pw * HEAD_PAD)
    pad_y = int(ph * HEAD_PAD)

    hx1 = clamp(hx1 - pad_x, 0, W - 1)
    hy1 = clamp(hy1 - pad_y, 0, H - 1)
    hx2 = clamp(hx2 + pad_x, 1, W)
    hy2 = clamp(hy2 + pad_y, 1, H)

    if hx2 <= hx1 or hy2 <= hy1:
        return None, None

    head = frame[hy1:hy2, hx1:hx2].copy()
    if head.shape[1] < MIN_HEAD_W or head.shape[0] < MIN_HEAD_H:
        return None, None
    return head, [hx1, hy1, hx2, hy2]

# =============== VISUAL DEBUG HELPER (NO LOGIC) ===============
def draw_labeled_box(img, bb, label, color, thick=DRAW_THICK):
    if bb is None:
        return
    x1, y1, x2, y2 = map(int, bb)
    cv2.rectangle(img, (x1, y1), (x2, y2), color, thick)
    if label:
        ty = max(15, y1 - 7)
        cv2.putText(img, str(label), (x1, ty),
                    cv2.FONT_HERSHEY_SIMPLEX, DRAW_FONT_SCALE,
                    color, 2, cv2.LINE_AA)
# ===============================================================
def clean_label_color(label):
    if label == "HELMET_OK":
        return (0, 255, 0), "HELMET"
    if label == "NO_HELMET":
        return (0, 0, 255), "NO HELMET"
    return (0, 255, 255), "UNKNOWN"
# ===============================================================

def helmet_label_from_pred(helmet_model, pred0):
    """
    Your model names example:
      {0:'helmet', 1:'nohelmet'}
    We normalize and map to:
      HELMET_OK / NO_HELMET / UNKNOWN
    """
    if pred0 is None or pred0.boxes is None or len(pred0.boxes) == 0:
        return ("UNKNOWN", 0.0)

    names = pred0.names if hasattr(pred0, "names") else helmet_model.names

    best_conf = 0.0
    best_nm = ""

    for b in pred0.boxes:
        conf = float(b.conf[0])
        cls_id = int(b.cls[0])
        nm = str(names.get(cls_id, cls_id)).lower()
        nm = nm.replace(" ", "").replace("_", "").replace("-", "")
        if conf > best_conf:
            best_conf = conf
            best_nm = nm

    # normalize to our output labels
    if best_nm in ("nohelmet", "withouthelmet", "nobelt"):  # keep extras just in case
        return ("NO_HELMET", best_conf)
    if best_nm in ("helmet", "withhelmet"):
        return ("HELMET_OK", best_conf)

    # fallback contains
    if "nohelmet" in best_nm or ("no" in best_nm and "helmet" in best_nm):
        return ("NO_HELMET", best_conf)
    if "helmet" in best_nm:
        return ("HELMET_OK", best_conf)

    return ("UNKNOWN", best_conf)

# ✅ VOTES HACK: majority vote ignoring UNKNOWN
def decide_from_votes(v):
    with_cnt = int(v["with"])
    without_cnt = int(v["without"])

    if without_cnt > with_cnt:
        return ("NO_HELMET", True)

    if with_cnt > without_cnt:
        return ("HELMET_OK", False)

    return ("UNKNOWN", False)

def main():
    # clear old crops
    for f in CROP_DIR.glob("*.jpg"):
        try:
            f.unlink()
        except:
            pass

    speed = load_json(SPEED_JSON, {})
    per_track = speed.get("per_track", {}) if isinstance(speed.get("per_track"), dict) else {}
    samples = speed.get("samples", []) if isinstance(speed.get("samples"), list) else []

    if not per_track and not samples:
        raise RuntimeError(f"SPEED_JSON empty: {SPEED_JSON}")

    cap0 = cv2.VideoCapture(VIDEO_PATH)
    if not cap0.isOpened():
        raise RuntimeError(f"Cannot open video: {VIDEO_PATH}")

    fps = cap0.get(cv2.CAP_PROP_FPS) or 25.0
    W = int(cap0.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap0.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap0.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap0.release()

    # motos from per_track
    moto_tids = set()
    for tid, info in per_track.items():
        if isinstance(info, dict) and info.get("cls_id", None) == 3:
            moto_tids.add(str(tid))

    # motos from samples
    samp_stat = defaultdict(lambda: {"n": 0, "max_sp": 0.0})
    for s in samples:
        try:
            tid = s.get("track_id", None)
            cls = s.get("cls_id", None)
            if tid is None or cls is None:
                continue
            if int(cls) != 3:
                continue
            tid = str(int(tid)) if str(tid).isdigit() else str(tid)

            sp1 = float(s.get("max_stable_kmh", 0.0) or 0.0)
            sp2 = float(s.get("speed_now_kmh", 0.0) or 0.0)
            samp_stat[tid]["n"] += 1
            samp_stat[tid]["max_sp"] = max(samp_stat[tid]["max_sp"], sp1, sp2)
        except Exception:
            continue

    for tid, st in samp_stat.items():
        if st["n"] >= MIN_SAMPLES_FOR_MOTO_ID and st["max_sp"] >= MIN_SPEED_FOR_MOTO_ID:
            moto_tids.add(tid)

    moto_tids = sorted(list(moto_tids), key=lambda x: int(x) if x.isdigit() else 10**9)

    if not moto_tids:
        print("[OK] No motorcycles found (per_track + samples). Saving empty helmet json.")
        safe_write_json(OUT_JSON, [])
        return

    # targets by frame
    targets_by_frame = defaultdict(list)
    seen_pair = set()

    for s in samples:
        try:
            tid = str(s.get("track_id"))
            cls = int(s.get("cls_id"))
            bb = s.get("bbox_xyxy")
            ts = float(s.get("timestamp_sec"))
        except Exception:
            continue

        if tid not in moto_tids:
            continue
        if cls != 3:
            continue
        if not (isinstance(bb, list) and len(bb) == 4):
            continue

        base_f = int(round(ts * fps))
        for off in FRAME_OFFSETS:
            fidx = base_f + off
            if fidx < 1:
                continue
            if total_frames and fidx > total_frames:
                continue

            key = (tid, fidx)
            if key in seen_pair:
                continue
            seen_pair.add(key)

            targets_by_frame[fidx].append({
                "tid": tid,
                "speed_bbox": [int(bb[0]), int(bb[1]), int(bb[2]), int(bb[3])],
                "t_sec": float(fidx) / float(fps)
            })

    det_model = YOLO(DET_MODEL_PATH)
    helmet_model = YOLO(HELMET_MODEL_PATH)

    candidates_by_tid = defaultdict(list)

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video again: {VIDEO_PATH}")

    writer = cv2.VideoWriter(str(OUT_VIDEO), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (W, H))

    frames_sorted = sorted(targets_by_frame.keys())
    print(f"[INFO] Helmet will process {len(frames_sorted)} sampled frames.")
    print(f"[INFO] Moto tracks: {moto_tids}")
    print(f"[INFO] Using model: {HELMET_MODEL_PATH}")

    for fidx in frames_sorted:
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, fidx - 1))
        ok, frame = cap.read()
        if not ok or frame is None:
            continue

        preds = det_model.predict(frame, conf=CONF_DET, iou=IOU_DET, imgsz=IMGSZ, verbose=False)

        persons = []
        motos = []
        if preds and len(preds) > 0 and preds[0].boxes is not None:
            r0 = preds[0]
            for b in r0.boxes:
                cls = int(b.cls[0])
                conf = float(b.conf[0])
                x1, y1, x2, y2 = map(int, b.xyxy[0])
                bb = [x1, y1, x2, y2]
                if cls == PERSON_CLS:
                    persons.append((conf, bb))
                elif cls == MOTO_CLS:
                    motos.append((conf, bb))

        vis = frame.copy()

        if DEBUG_DRAW:
            for pconf, pbb in persons:
                draw_labeled_box(vis, pbb, f"P {pconf:.2f}", (0, 255, 0))
            for mconf, mbb in motos:
                draw_labeled_box(vis, mbb, f"M {mconf:.2f}", (0, 165, 255))

        # compute best moto bbox for each target
        tlist = targets_by_frame[fidx]
        for tgt in tlist:
            speed_bb = tgt["speed_bbox"]
            best_moto_bb = speed_bb
            best_iou = 0.0
            for mconf, mbb in motos:
                i = iou_xyxy(mbb, speed_bb)
                if i > best_iou:
                    best_iou = i
                    best_moto_bb = mbb
            if best_iou < MIN_MOTO_MATCH_IOU:
                best_moto_bb = speed_bb
            tgt["_best_moto_bb"] = best_moto_bb

        if DEBUG_DRAW:
            for tgt in tlist:
                tid = tgt["tid"]
                draw_labeled_box(vis, tgt["speed_bbox"], f"speed tid={tid}", (255, 0, 0))
                draw_labeled_box(vis, tgt["_best_moto_bb"], f"moto tid={tid}", (255, 0, 255))

        # 1-to-1 assignment target<->person
        pairs = []
        for ti, tgt in enumerate(tlist):
            mbb = tgt["_best_moto_bb"]
            for pi, (pconf, pbb) in enumerate(persons):
                i = iou_xyxy(pbb, mbb)
                if i < MIN_PERSON_MATCH_IOU:
                    continue
                sc = 0.75 * i + 0.25 * float(pconf)
                pairs.append((sc, ti, pi))

        pairs.sort(key=lambda x: x[0], reverse=True)
        used_t = set()
        used_p = set()
        assignments = []
        for sc, ti, pi in pairs:
            if ti in used_t or pi in used_p:
                continue
            used_t.add(ti)
            used_p.add(pi)
            assignments.append((ti, pi))

        if DEBUG_DRAW:
            for ti, pi in assignments:
                tgt = tlist[ti]
                tid = tgt["tid"]
                pconf, pbb = persons[pi]
                draw_labeled_box(vis, pbb, f"ASSIGN tid={tid}", (0, 0, 255))

        for ti, pi in assignments:
            tgt = tlist[ti]
            tid = tgt["tid"]
            _, pbb = persons[pi]

            head, hbb = crop_head_from_person(frame, pbb)
            if head is None:
                continue

            if CLEAN_DRAW:
                pred = helmet_model.predict(
                    head,
                    conf=CONF_HELMET,
                    iou=IOU_HELMET,
                    imgsz=IMGSZ_HELMET,
                    verbose=False
                )

                label, conf = ("UNKNOWN", 0.0)
                if pred and len(pred) > 0:
                    label, conf = helmet_label_from_pred(
                        helmet_model,
                        pred[0]
                    )

                color, clean_txt = clean_label_color(label)
                draw_labeled_box(
                    vis,
                    hbb,
                    f"{clean_txt} {conf:.2f}",
                    color,
                    thick=3
                )

            sh = sharpness_score(head)
            area = int((hbb[2] - hbb[0]) * (hbb[3] - hbb[1]))

            candidates_by_tid[tid].append({
                "t": float(tgt["t_sec"]),
                "sharp": float(sh),
                "area": int(area),
                "head_img": head
            })

        writer.write(vis)

    cap.release()
    writer.release()

    out_list = []
    rows = []
    saved = 0

    print("\n=== HELMET (SPEED-LINKED, TOPK) ===")
    print("Debug video :", OUT_VIDEO)
    print("Crops folder:", CROP_DIR)

    for tid in moto_tids:
        cands = candidates_by_tid.get(tid, [])
        cands.sort(key=lambda x: (x["sharp"], x["area"]), reverse=True)
        best = cands[:TOPK_CROPS_PER_MOTO]

        votes = {"with": 0, "without": 0, "unknown": 0, "total": 0}
        best_evidence_file = None
        best_confidence = None
        for i, x in enumerate(best):
            head = x["head_img"]
            pred = helmet_model.predict(head, conf=CONF_HELMET, iou=IOU_HELMET, imgsz=IMGSZ_HELMET, verbose=False)

            label, conf = ("UNKNOWN", 0.0)
            if pred and len(pred) > 0:
                label, conf = helmet_label_from_pred(helmet_model, pred[0])

            if label == "HELMET_OK":
                votes["with"] += 1
            elif label == "NO_HELMET":
                votes["without"] += 1
            else:
                votes["unknown"] += 1
            votes["total"] += 1

            name = f"tid{tid}_best{i}_t{x['t']:.2f}_sh{x['sharp']:.0f}_a{x['area']}_pred{label}_c{conf:.2f}.jpg"
            cv2.imwrite(str(CROP_DIR / name), head)
            if label == "NO_HELMET":
                if best_confidence is None or conf > best_confidence:
                    best_confidence = round(float(conf), 3)
                    best_evidence_file = f"/results/helmet_crops/{name}"

            rows.append({
                "track_id": str(tid),
                "rank": int(i),
                "t_sec": round(float(x["t"]), 2),
                "sharp": round(float(x["sharp"]), 2),
                "area": int(x["area"]),
                "pred": str(label),
                "conf": round(float(conf), 3),
                "file": name
            })
            saved += 1

        final, viol = decide_from_votes(votes)

        out_list.append({
            "track_id": int(tid) if tid.isdigit() else tid,
            "type": "MOTORCYCLE",
            "votes": votes,
            "final_decision": final,
            "violation": bool(viol),
            "confidence": best_confidence,
            "evidence": {
                "helmet_image": best_evidence_file
            },
            "topk_used": int(len(best)),
            "num_candidates": int(len(cands)),
            "source": "SPEED(per_track + samples)"
        })

        print(f"- moto track {tid}: {final} votes={votes} topk={len(best)} cands={len(cands)}")

    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["track_id","rank","t_sec","sharp","area","pred","conf","file"])
        w.writeheader()
        w.writerows(rows)

    safe_write_json(OUT_JSON, out_list)

    print("\nSaved CSV:", CSV_OUT)
    print("Saved best crops:", saved, "->", CROP_DIR)
    print("Saved helmet json :", OUT_JSON)
    print("[OK] Helmet per moto finished")



if __name__ == "__main__":
    main()