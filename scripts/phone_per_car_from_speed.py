# scripts/phone_per_car_from_speed.py
# FINAL V1 ✅ (Speed-linked) + Driver-side (person-in-glass) + Debug like seatbelt
#
# الفكرة نفس seatbelt:
# - target frames من speed.samples (للـ cars فقط)
# - YOLO COCO لاختيار car bbox + person bbox
# - glass ROI من car bbox
# - لازم Person جوّا الإزاز (anti-sky/noise)
# - قص ROI حوالين الشخص (driver) + topK + votes
#
# الناتج:
# - results/phone_per_car.json
# - results/phone_crops/*.jpg
# - results/phone_crops_predictions.csv
# - results/phone_speedlink_output.mp4 (Debug)

from ultralytics import YOLO
import cv2
import json
import csv
import os
import math
import numpy as np
from pathlib import Path
from collections import defaultdict, Counter, deque

# ===================== SETTINGS =====================
VIDEO_PATH = os.environ.get("VIDEO_PATH", "test_videos/test3.mp4")
SPEED_JSON = Path("results/speed_depth_multi_clean_events.json")

# لاستبعاد المواتير (نفس فكرة seatbelt)
HELMET_PER_MOTO_JSON = Path("results/helmet_per_moto.json")

PHONE_MODEL_PATH = "models/phone_best_2.pt"   # ✅ عدّلها إذا اسم الموديل مختلف عندك
DET_MODEL_PATH   = "yolov8s.pt"             # COCO (car/person/moto)

CONF_DET  = 0.35
IOU_DET   = 0.50
IMGSZ_DET = 640

CONF_PHONE  = 0.10
IOU_PHONE   = 0.50
IMGSZ_PHONE = 320

# COCO
PERSON_CLS = 0
MOTO_CLS   = 3
CARLIKE_CLS_DET   = {2, 5, 7}  # car,bus,truck
CARLIKE_CLS_SPEED = {2, 5, 7}

FRAME_OFFSETS = [-8, -6, -4, -2, 0, 2, 4, 6, 8]

# Glass ROI من car bbox (ركزنا عالواجهة الأمامية)
GLASS_X_PAD = 0.05
GLASS_Y1    = 0.10
GLASS_Y2    = 0.68

# Driving side inference
DRIVING_SIDE = "LHD"  # LHD / RHD
DRIVER_SIDE_DEFAULT = "right"  # لــ LHD غالباً driver باليمين بالصورة لما السيارة عم تقرب

# لازم person داخل glass بنسبة صغيرة
PERSON_MIN_OV_IN_GLASS = 0.06

# ROI حوالين الشخص (driver)
P_ROI_PAD_X   = 0.18
P_ROI_PAD_Y   = 0.10
P_ROI_Y2_FRAC = 0.88

TOPK_CROPS_PER_CAR = 12
MAX_KEEP_PER_TID   = 60

MIN_VALID_VOTES = 1
RATIO_DECIDE    = 0.55

# anti-moto per frame
MOTO_SKIP_OV_SMALL = 0.55
MOTO_SKIP_IOU      = 0.20

# car sanity
CAR_MIN_AREA_FRAC = 0.005
CAR_MAX_AREA_FRAC = 0.50
CAR_AR_MIN = 0.85
CAR_AR_MAX = 6.5

# outputs
OUT_VIDEO = Path("results/phone_speedlink_output.mp4")
OUT_JSON  = Path("results/phone_per_car.json")
CROP_DIR  = Path("results/phone_crops")
CSV_OUT   = Path("results/phone_crops_predictions.csv")

OUT_VIDEO.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
CROP_DIR.mkdir(parents=True, exist_ok=True)

# DEBUG
DEBUG_DRAW_ALL_DETS = True
DEBUG_DRAW_TARGETS  = True
DEBUG_DRAW_SKIPS    = True
DEBUG_FPS_OUT       = 10.0
# ====================================================

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

def norm_tid(x):
    if x is None:
        return None
    s = str(x).strip()
    if s.isdigit():
        return str(int(s))
    return s

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def area_xyxy(bb):
    x1, y1, x2, y2 = bb
    return max(0, x2 - x1) * max(0, y2 - y1)

def inter_area(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)
    return iw * ih

def iou_xyxy(a, b):
    ia = inter_area(a, b)
    if ia <= 0:
        return 0.0
    aa = max(1, area_xyxy(a))
    ab = max(1, area_xyxy(b))
    return ia / float(aa + ab - ia + 1e-6)

def overlap_small(a, b):
    ia = inter_area(a, b)
    if ia <= 0:
        return 0.0
    aa = max(1, area_xyxy(a))
    ab = max(1, area_xyxy(b))
    return ia / float(min(aa, ab))

def center(bb):
    return ((bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0)

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def crop_box(frame, bb):
    H, W = frame.shape[:2]
    x1, y1, x2, y2 = map(int, bb)
    x1 = clamp(x1, 0, W - 1)
    y1 = clamp(y1, 0, H - 1)
    x2 = clamp(x2, 1, W)
    y2 = clamp(y2, 1, H)
    if x2 <= x1 or y2 <= y1:
        return None
    return frame[y1:y2, x1:x2].copy()

def sharpness_score(img_bgr):
    g = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(g, cv2.CV_64F).var())

def looks_like_sky(img_bgr):
    try:
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        s = hsv[:, :, 1].astype(np.float32)
        v = hsv[:, :, 2].astype(np.float32)
        mean_s = float(np.mean(s))
        mean_v = float(np.mean(v))
        g = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
        std_g = float(np.std(g))
        return (mean_v > 175 and mean_s < 55 and std_g < 35)
    except Exception:
        return False

def glass_roi_from_carbb(car_bb):
    x1, y1, x2, y2 = car_bb


    w = max(1, x2 - x1)
    h = max(1, y2 - y1)
    gx1 = int(x1 + GLASS_X_PAD * w)
    gx2 = int(x2 - GLASS_X_PAD * w)
    gy1 = int(y1 + GLASS_Y1 * h)
    gy2 = int(y1 + GLASS_Y2 * h)
    return [gx1, gy1, gx2, gy2]

def bb_valid(bb, min_w=40, min_h=40):
    return (bb[2] - bb[0] >= min_w) and (bb[3] - bb[1] >= min_h)

def clip_to(bb, outer):
    x1, y1, x2, y2 = bb
    ox1, oy1, ox2, oy2 = outer
    return [max(x1, ox1), max(y1, oy1), min(x2, ox2), min(y2, oy2)]

def roi_from_person_in_glass(pbb, glass_bb):
    px1, py1, px2, py2 = pbb
    pw = max(1, px2 - px1)
    ph = max(1, py2 - py1)

    rx1 = int(px1 - P_ROI_PAD_X * pw)
    rx2 = int(px2 + P_ROI_PAD_X * pw)
    ry1 = int(py1 - P_ROI_PAD_Y * ph)
    ry2 = int(py1 + P_ROI_Y2_FRAC * ph + P_ROI_PAD_Y * ph)

    return clip_to([rx1, ry1, rx2, ry2], glass_bb)

def expected_driver_image_side(direction, driving_side):
    driving_side = (driving_side or "LHD").upper()
    if direction == "approach":
        return "right" if driving_side == "LHD" else "left"
    if direction == "away":
        return "left" if driving_side == "LHD" else "right"
    return None

def infer_direction_from_width_hist(w_hist):
    if len(w_hist) < 6:
        return None
    w0 = float(w_hist[0]); w1 = float(w_hist[-1])
    if w0 <= 1:
        return None
    delta = w1 - w0
    if abs(delta) < 0.06 * w0:
        return None
    return "approach" if delta > 0 else "away"

def car_bbox_sane(bb, W, H):
    x1, y1, x2, y2 = bb
    w = max(1, x2 - x1)
    h = max(1, y2 - y1)
    ar = w / float(h)
    a = float(area_xyxy(bb))
    frac = a / float(max(1, W * H))
    if frac < CAR_MIN_AREA_FRAC or frac > CAR_MAX_AREA_FRAC:
        return False
    if ar < CAR_AR_MIN or ar > CAR_AR_MAX:
        return False
    return True

def choose_car_bbox_for_tid(speed_bb, car_dets, last_bb, W, H):
    # continuity
    if last_bb is not None:
        best, best_sc = None, -1e18
        lc = center(last_bb)
        la = max(1.0, float(area_xyxy(last_bb)))
        for conf, bb in car_dets:
            if not car_bbox_sane(bb, W, H):
                continue
            i = iou_xyxy(bb, last_bb)
            cc = center(bb)
            cd = dist(cc, lc)
            aa = float(area_xyxy(bb))
            sc = 1.8 * i + 0.15 * float(conf)
            sc -= 0.40 * (cd / (math.sqrt(la) + 1e-6))
            sc -= 0.10 * abs(math.log((aa / la) + 1e-6))
            if sc > best_sc:
                best_sc, best = sc, bb
        if best is not None and iou_xyxy(best, last_bb) >= 0.08:
            return best

    # hint from speed bb (بس كـ hint لاختيار car bbox)
    if speed_bb is not None and area_xyxy(speed_bb) > 50:
        sa = float(area_xyxy(speed_bb))
        sc0 = center(speed_bb)
        best, best_sc = None, -1e18
        for conf, bb in car_dets:
            if not car_bbox_sane(bb, W, H):
                continue
            ov = overlap_small(bb, speed_bb)
            ii = iou_xyxy(bb, speed_bb)
            contain = inter_area(bb, speed_bb) / max(1.0, sa)
            bc = center(bb)
            cd = dist(bc, sc0)
            sc = 0.55 * contain + 0.25 * ov + 0.15 * ii + 0.05 * float(conf)
            sc -= 0.10 * (cd / (math.sqrt(sa) + 1e-6))
            if sc > best_sc:
                best_sc, best = sc, bb
        if best is not None:
            return best

    sane = [bb for conf, bb in car_dets if car_bbox_sane(bb, W, H)]
    if len(sane) == 1:
        return sane[0]
    return None

# ================= phone label =================
def phone_label_from_pred(model, pred0):
    if pred0 is None or pred0.boxes is None or len(pred0.boxes) == 0:
        return ("UNKNOWN", 0.0)

    names = pred0.names if hasattr(pred0, "names") else model.names

    best_conf = 0.0
    best_nm = ""

    for b in pred0.boxes:
        conf = float(b.conf[0])
        cls_id = int(b.cls[0])

        nm_raw = str(names.get(cls_id, cls_id)).lower()
        nm = nm_raw.replace(" ", "").replace("_", "").replace("-", "")

        if conf > best_conf:
            best_conf = conf
            best_nm = nm

    if best_nm == "nomobileusage":
        return ("NO_PHONE", best_conf)

    if best_nm == "mobileusage":
        return ("PHONE", best_conf)

    return ("UNKNOWN", best_conf)

def decide_phone_from_votes(v):
    # votes["with"] = PHONE (VIOLATION)
    # votes["without"] = NO_PHONE (OK)
    with_cnt = int(v["with"])
    without_cnt = int(v["without"])
    valid = with_cnt + without_cnt

    if valid < MIN_VALID_VOTES:
        return ("UNKNOWN", False)

    if with_cnt / max(1, valid) >= RATIO_DECIDE:
        return ("PHONE", True)

    if without_cnt / max(1, valid) >= RATIO_DECIDE:
        return ("NO_PHONE", False)

    return ("UNKNOWN", False)

# ===== debug drawing =====
def draw_box(img, bb, color, text=None, thick=2):
    x1, y1, x2, y2 = map(int, bb)
    cv2.rectangle(img, (x1, y1), (x2, y2), color, thick)
    if text:
        cv2.putText(img, text, (x1, max(20, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

# ===================== MAIN =====================
def main():
    print("[RUN] phone_per_car_from_speed V1")
    print("[VIDEO_PATH]", VIDEO_PATH)
    print("[PHONE_MODEL]", PHONE_MODEL_PATH)

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

    # gate motos by helmet json
    helmet_lst = load_json(HELMET_PER_MOTO_JSON, [])
    moto_tids_from_helmet = set()
    if isinstance(helmet_lst, list):
        for r in helmet_lst:
            tid = norm_tid(r.get("track_id"))
            if tid is not None:
                moto_tids_from_helmet.add(str(tid))

    # cls hist from samples
    cls_hist = defaultdict(Counter)
    for s in samples:
        try:
            tid = norm_tid(s.get("track_id"))
            cls = int(s.get("cls_id", -1))
            if tid is None:
                continue
            cls_hist[str(tid)][cls] += 1
        except:
            pass

    # strict car tids
    car_tids = set()
    for tid, info in per_track.items():
        tid = norm_tid(tid)
        if tid is None:
            continue
        if bool(info.get("parked", False)):
            continue

        if float(info.get("max_stable_kmh", 0.0) or 0.0) <= 0:
            continue
        if str(tid) in moto_tids_from_helmet:
            continue
        if not isinstance(info, dict):
            continue
        cls = info.get("cls_id", None)
        if cls is None:
            continue
        if int(cls) in CARLIKE_CLS_SPEED:
            if cls_hist[str(tid)].get(MOTO_CLS, 0) > 0:
                continue
            car_tids.add(str(tid))

    for tid, hist in cls_hist.items():
        if tid in moto_tids_from_helmet:
            continue
        if hist.get(MOTO_CLS, 0) > 0:
            continue
        c = sum(hist.get(k, 0) for k in CARLIKE_CLS_SPEED)
        if c >= 2:
            car_tids.add(str(tid))

    car_tids = sorted(list(car_tids), key=lambda x: int(x) if x.isdigit() else 10**9)
    print("[INFO] cars =", car_tids)

    if not car_tids:
        print("[OK] No cars -> empty phone json.")
        safe_write_json(OUT_JSON, [])
        with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["track_id","rank","t_sec","sharp","area","side","pred","conf","file"])
            w.writeheader()
        return

    # build targets by frame (from speed samples)
    targets_by_frame = defaultdict(list)
    seen_pair = set()

    for s in samples:
        try:
            tid = norm_tid(s.get("track_id"))
            cls = int(s.get("cls_id"))
            bb  = s.get("bbox_xyxy")
            ts  = float(s.get("timestamp_sec"))
        except:
            continue

        if tid is None or str(tid) not in car_tids:
            continue
        if cls not in CARLIKE_CLS_SPEED:
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
            key = (str(tid), fidx)
            if key in seen_pair:
                continue
            seen_pair.add(key)

            targets_by_frame[fidx].append({
                "tid": str(tid),
                "speed_bbox": [int(bb[0]), int(bb[1]), int(bb[2]), int(bb[3])],
                "t_sec": float(fidx) / float(fps)
            })

    frames_sorted = sorted(targets_by_frame.keys())
    print(f"[INFO] frames={len(frames_sorted)} (from speed samples)")

    det_model = YOLO(DET_MODEL_PATH)
    phone_model = YOLO(PHONE_MODEL_PATH)
    print("PHONE CLASSES =", phone_model.names)

    # state per tid
    state = {tid: {"last_bb": None, "w_hist": deque(maxlen=12), "direction": None, "expected_side": None} for tid in car_tids}
    candidates_by_tid = defaultdict(list)

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        raise RuntimeError("Cannot open video again")
    writer = cv2.VideoWriter(str(OUT_VIDEO), cv2.VideoWriter_fourcc(*"mp4v"), DEBUG_FPS_OUT, (W, H))

    for fidx in frames_sorted:
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, fidx - 1))
        ok, frame = cap.read()
        if not ok or frame is None:
            continue

        vis = frame.copy()

        preds = det_model.predict(frame, conf=CONF_DET, iou=IOU_DET, imgsz=IMGSZ_DET, verbose=False)

        persons, cars_det, motos_det = [], [], []
        if preds and len(preds) > 0 and preds[0].boxes is not None:
            r0 = preds[0]
            for b in r0.boxes:
                cls = int(b.cls[0])
                conf = float(b.conf[0])
                x1, y1, x2, y2 = map(int, b.xyxy[0])
                bb = [x1, y1, x2, y2]
                if cls == PERSON_CLS:
                    persons.append((conf, bb))
                elif cls in CARLIKE_CLS_DET:
                    cars_det.append((conf, bb))
                elif cls == MOTO_CLS:
                    motos_det.append((conf, bb))

        if DEBUG_DRAW_ALL_DETS:
            for conf, bb in cars_det:
                draw_box(vis, bb, (0, 255, 0), f"CAR {conf:.2f}", 2)
            for conf, bb in persons:
                draw_box(vis, bb, (255, 120, 0), f"P {conf:.2f}", 2)
            for conf, bb in motos_det:
                draw_box(vis, bb, (0, 0, 255), f"MOTO {conf:.2f}", 2)

        tlist = targets_by_frame.get(fidx, [])
        cv2.putText(vis, f"f={fidx} targets={len(tlist)} carsDet={len(cars_det)} P={len(persons)} M={len(motos_det)}",
                    (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

        for tgt in tlist:
            tid = tgt["tid"]
            speed_bb = tgt["speed_bbox"]

            if DEBUG_DRAW_TARGETS:
                draw_box(vis, speed_bb, (255, 0, 255), f"speed tid={tid}", 2)

            # skip moto-like
            best_m_ov, best_m_iou = 0.0, 0.0
            for _, mbb in motos_det:
                best_m_ov = max(best_m_ov, overlap_small(mbb, speed_bb))
                best_m_iou = max(best_m_iou, iou_xyxy(mbb, speed_bb))
            if best_m_ov >= MOTO_SKIP_OV_SMALL or best_m_iou >= MOTO_SKIP_IOU:
                if DEBUG_DRAW_SKIPS:
                    cv2.putText(vis, f"tid={tid} SKIP:moto_like", (10, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
                continue

            st = state.get(tid)
            last_bb = st["last_bb"] if st else None

            car_bb = choose_car_bbox_for_tid(speed_bb, cars_det, last_bb, W, H)
            if car_bb is None:
                if DEBUG_DRAW_SKIPS:
                    cv2.putText(vis, f"tid={tid} SKIP:no_car_bb", (10, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
                continue

            draw_box(vis, car_bb, (0, 255, 255), f"tid={tid} CAR_PICK", 3)
            print(f"[CAR_BB] tid={tid} car_bb={car_bb}")

            if st is not None:
                st["last_bb"] = car_bb
                w_now = max(1, car_bb[2] - car_bb[0])
                st["w_hist"].append(float(w_now))
                st["direction"] = infer_direction_from_width_hist(st["w_hist"])
                st["expected_side"] = expected_driver_image_side(st["direction"], DRIVING_SIDE) or st["expected_side"]

            glass = glass_roi_from_carbb(car_bb)
            if not bb_valid(glass, 55, 55):
                if DEBUG_DRAW_SKIPS:
                    cv2.putText(vis, f"tid={tid} SKIP:bad_glass", (10, 112), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
                continue

            draw_box(vis, glass, (255, 180, 0), "GLASS", 2)

            # fallback: no person detector needed
            chosen_side = DRIVER_SIDE_DEFAULT

            x1, y1, x2, y2 = car_bb
            car_w = x2 - x1
            car_h = y2 - y1
            if car_w < 300 or car_h < 220:
                continue
            w = x2 - x1
            h = y2 - y1
            roi = [
                int(x1 + 0.35 * w),
                int(y1 + 0.02 * h),
                int(x2 - 0.02 * w),
                int(y1 + 0.65 * h)
                ]
            
            if not bb_valid(roi, 50, 50):
                if DEBUG_DRAW_SKIPS:
                    cv2.putText(vis, f"tid={tid} SKIP:bad_roi", (10, 168), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
                continue

            draw_box(vis, roi, (0, 255, 255), "ROI", 3)

            crop_img = crop_box(frame, roi)
            crop_img = cv2.resize(

               crop_img,
               None,
               fx=2.0,
               fy=2.0,
               interpolation=cv2.INTER_CUBIC
            )

            if crop_img is None or crop_img.size == 0:
                if DEBUG_DRAW_SKIPS:
                    cv2.putText(vis, f"tid={tid} SKIP:crop_fail", (10, 196), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
                continue

            if looks_like_sky(crop_img):
                if DEBUG_DRAW_SKIPS:
                    cv2.putText(vis, f"tid={tid} SKIP:sky", (10, 224), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
                continue

            sh = sharpness_score(crop_img)
            ar = int(crop_img.shape[0] * crop_img.shape[1])

            candidates_by_tid[tid].append({"t": float(tgt["t_sec"]), "sharp": float(sh), "area": int(ar), "img": crop_img, "side": chosen_side})
            if len(candidates_by_tid[tid]) > MAX_KEEP_PER_TID:
                candidates_by_tid[tid].sort(key=lambda x: (x["area"], x["sharp"]), reverse=True)
                candidates_by_tid[tid] = candidates_by_tid[tid][:MAX_KEEP_PER_TID]

            cv2.putText(vis, f"tid={tid} CAND_OK", (10, 252), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

        writer.write(vis)

    cap.release()
    writer.release()

    # inference + save
    out_list, rows = [], []
    saved = 0

    for tid in car_tids:
        cands = candidates_by_tid.get(str(tid), [])
        cands.sort(key=lambda x: (x["area"], x["sharp"]), reverse=True)
        best = cands[:TOPK_CROPS_PER_CAR]

        # votes["with"]=PHONE, votes["without"]=NO_PHONE
        votes = {"with": 0, "without": 0, "unknown": 0, "total": 0}

        for i, x in enumerate(best):
            img = x["img"]
            pred = phone_model.predict(img, conf=CONF_PHONE, iou=IOU_PHONE, imgsz=IMGSZ_PHONE, verbose=False)

            label, conf = ("UNKNOWN", 0.0)
            if pred and len(pred) > 0:
                label, conf = phone_label_from_pred(phone_model, pred[0])

            if label == "PHONE":
               votes["with"] += 1
            elif label == "NO_PHONE":
               votes["without"] += 1
            else:
                votes["unknown"] += 1
            votes["total"] += 1

            name = f"tid{tid}_best{i}_t{x['t']:.2f}_side{x['side']}_sh{x['sharp']:.0f}_pred{label}_c{conf:.2f}.jpg"
            cv2.imwrite(str(CROP_DIR / name), img)

            rows.append({
                "track_id": str(tid),
                "rank": int(i),
                "t_sec": round(float(x["t"]), 2),
                "sharp": round(float(x["sharp"]), 2),
                "area": int(x["area"]),
                "side": str(x["side"]),
                "pred": str(label),
                "conf": round(float(conf), 3),
                "file": name
            })
            saved += 1

        final, viol = decide_phone_from_votes(votes)

        out_list.append({
            "track_id": int(tid) if str(tid).isdigit() else str(tid),
            "type": "CAR",
            "votes": votes,
            "final_decision": final,          # PHONE / NO_PHONE / UNKNOWN
            "violation": bool(viol),          # True if PHONE
            "topk_used": int(len(best)),
            "num_candidates": int(len(cands)),
            "source": "PHONE_SPEEDLINK_V1"
        })

    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["track_id","rank","t_sec","sharp","area","side","pred","conf","file"])
        w.writeheader()
        w.writerows(rows)

    safe_write_json(OUT_JSON, out_list)

    print("\n=== PHONE DONE (V1) ===")
    print("Saved crops:", saved, "->", CROP_DIR)
    print("Saved CSV  :", CSV_OUT)
    print("Saved JSON :", OUT_JSON)
    print("Debug video:", OUT_VIDEO)

if __name__ == "__main__":
    main()