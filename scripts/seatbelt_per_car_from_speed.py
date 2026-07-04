from ultralytics import YOLO
import cv2, json, csv
from pathlib import Path
from collections import defaultdict

SEATBELT_MODEL_PATH = "models/seatbelt_best_2.pt"

PHONE_CROP_DIR = Path("results/phone_crops")
OUT_JSON = Path("results/seatbelt_per_car.json")
CSV_OUT = Path("results/seatbelt_crops_predictions.csv")
CROP_DIR = Path("results/seatbelt_crops")

CONF_SB = 0.10
IOU_SB = 0.50
IMGSZ_SB = 320

MIN_VALID_VOTES = 1
RATIO_DECIDE = 0.55

CROP_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

def seatbelt_label_from_pred(model, pred0):
    if pred0 is None or pred0.boxes is None or len(pred0.boxes) == 0:
        return ("UNKNOWN", 0.0)

    names = pred0.names if hasattr(pred0, "names") else model.names
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

    if best_nm == "noseatbelt":
        return ("NO_SEATBELT", best_conf)

    if best_nm == "seatbelt":
        return ("SEATBELT_OK", best_conf)

    return ("UNKNOWN", best_conf)

def decide_from_votes(v):
    with_cnt = int(v["with"])
    without_cnt = int(v["without"])
    valid = with_cnt + without_cnt

    if valid < MIN_VALID_VOTES:
        return ("UNKNOWN", False)

    if without_cnt / max(1, valid) >= RATIO_DECIDE:
        return ("NO_SEATBELT", True)

    if with_cnt / max(1, valid) >= RATIO_DECIDE:
        return ("SEATBELT_OK", False)

    return ("UNKNOWN", False)

def row_score(r):
    conf = float(r.get("conf", 0.0))
    area = float(r.get("area", 1))
    return conf * area

def main():
    print("[RUN] seatbelt from phone crops")
    model = YOLO(SEATBELT_MODEL_PATH)
    print("SEATBELT CLASSES =", model.names)

    for f in CROP_DIR.glob("*.jpg"):
        try:
            f.unlink()
        except:
            pass

    files = sorted(PHONE_CROP_DIR.glob("*.jpg"))
    by_tid = defaultdict(list)

    for p in files:
        name = p.name
        if not name.startswith("tid"):
            continue

        tid = name.split("_")[0].replace("tid", "")
        img = cv2.imread(str(p))
        if img is None:
            continue

        by_tid[tid].append((p, img))

    out_list = []
    rows = []
    saved = 0

    for tid, items in sorted(
        by_tid.items(),
        key=lambda kv: int(kv[0]) if kv[0].isdigit() else 999999
    ):
        votes = {"with": 0, "without": 0, "unknown": 0, "total": 0}
        evidence_files = []
        tid_rows = []

        for i, (src_path, img) in enumerate(items):
            pred = model.predict(
                img,
                conf=CONF_SB,
                iou=IOU_SB,
                imgsz=IMGSZ_SB,
                verbose=False
            )

            label, conf = ("UNKNOWN", 0.0)

            if pred and len(pred) > 0:
                label, conf = seatbelt_label_from_pred(model, pred[0])

            if label == "SEATBELT_OK":
                votes["with"] += 1
            elif label == "NO_SEATBELT":
                votes["without"] += 1
            else:
                votes["unknown"] += 1

            votes["total"] += 1

            h, w = img.shape[:2]
            area = int(w * h)

            out_name = f"tid{tid}_phonecrop{i}_pred{label}_c{conf:.2f}.jpg"
            out_path = CROP_DIR / out_name
            cv2.imwrite(str(out_path), img)

            evidence_path = str(out_path).replace("\\", "/")
            evidence_files.append(evidence_path)

            row = {
                "track_id": tid,
                "rank": i,
                "pred": label,
                "conf": round(float(conf), 3),
                "area": area,
                "score": round(float(conf) * float(area), 3),
                "source_phone_crop": src_path.name,
                "file": out_name,
                "evidence_path": evidence_path
            }

            rows.append(row)
            tid_rows.append(row)

            saved += 1

        final, viol = decide_from_votes(votes)

        best_row = None

        for r in tid_rows:
            if final == "NO_SEATBELT" and r["pred"] == "NO_SEATBELT":
                if best_row is None or row_score(r) > row_score(best_row):
                    best_row = r

            elif final == "SEATBELT_OK" and r["pred"] == "SEATBELT_OK":
                if best_row is None or row_score(r) > row_score(best_row):
                    best_row = r

        if best_row is None:
            for r in tid_rows:
                if best_row is None or row_score(r) > row_score(best_row):
                    best_row = r

        best_evidence = best_row["evidence_path"] if best_row else None

        out_list.append({
            "track_id": int(tid) if str(tid).isdigit() else tid,
            "type": "CAR",
            "votes": votes,
            "final_decision": final,
            "violation": bool(viol),
            "topk_used": len(items),
            "num_candidates": len(items),
            "evidence": [best_evidence] if best_evidence else evidence_files,
            "evidence_paths": [best_evidence] if best_evidence else evidence_files,
            "all_evidence": evidence_files,
            "best_evidence": best_evidence,
            "source": "SEATBELT_FROM_PHONE_CROPS"
        })

    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "track_id",
                "rank",
                "pred",
                "conf",
                "area",
                "score",
                "source_phone_crop",
                "file",
                "evidence_path"
            ]
        )
        w.writeheader()
        w.writerows(rows)

    OUT_JSON.write_text(json.dumps(out_list, indent=2), encoding="utf-8")

    print("Saved crops:", saved, "->", CROP_DIR)
    print("Saved JSON :", OUT_JSON)
    print("Saved CSV  :", CSV_OUT)

if __name__ == "__main__":
    main()