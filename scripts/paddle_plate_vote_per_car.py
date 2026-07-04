# scripts/paddle_plate_vote_per_car.py
import json
import re
from pathlib import Path
from collections import defaultdict, Counter

import cv2
from paddleocr import PaddleOCR

# ================= SETTINGS =================
CROPS_DIR = Path("results/plates_crops_per_car")          
OUT_OCR_JSON = Path("results/plate_ocr_per_car.json")     
OUT_VOTED_JSON = Path("results/plate_voted_per_car.json") 

# قبول القراءة
MIN_ACCEPT_CONF = 0.55          
MAX_LEN = 7                      
MIN_LEN = 2


PLATE_RE = re.compile(r"^[A-Z][0-9]{1,6}$")

# ===========================================

def norm_text(s: str) -> str:
    s = (s or "").upper()
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

def fix_leading_ocr(txt: str) -> str:
    """
    إذا أول خانة طلعت رقم بالغلط:
      0 -> O
      1 -> I
    (بتحل مشكلة O قرأها 0)
    """
    if not txt:
        return txt
    if txt[0].isdigit():
        if txt[0] == "0":
            return "O" + txt[1:]
        if txt[0] == "1":
            return "I" + txt[1:]
    return txt

def accept_plate(txt: str, conf: float) -> bool:
    if not txt or conf < MIN_ACCEPT_CONF:
        return False
    if not (MIN_LEN <= len(txt) <= MAX_LEN):
        return False
    return bool(PLATE_RE.match(txt))

def get_car_id_from_filename(name: str):
    """
    متوقع اسم ملف مثل:
    car2_k0_t4.84_c0.816.jpg
    """
    m = re.search(r"car(\d+)_", name)
    if not m:
        return None
    return int(m.group(1))

def main():
    CROPS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_OCR_JSON.parent.mkdir(parents=True, exist_ok=True)

    # OCR engine
    ocr = PaddleOCR(use_angle_cls=True, lang="en")

    records = []
    per_car_reads = defaultdict(list)  # car_id -> list of (text, conf, crop_path)

    imgs = sorted([p for p in CROPS_DIR.glob("*.jpg")])
    if not imgs:
        print("No crops found in:", CROPS_DIR)
        OUT_OCR_JSON.write_text("[]", encoding="utf-8")
        OUT_VOTED_JSON.write_text("[]", encoding="utf-8")
        return

    for img_path in imgs:
        car_id = get_car_id_from_filename(img_path.name)
        if car_id is None:
            # إذا اسم الملف غير متوقع
            continue

        img = cv2.imread(str(img_path))
        if img is None:
            continue

        
        result = ocr.ocr(img, cls=True)

        best_txt = None
        best_conf = 0.0

        
        lines = []
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
            lines = result[0]  # list of line items
        

        for line in lines:
            try:
                
                text, conf = line[1][0], float(line[1][1])
            except Exception:
                continue

            t = norm_text(text)
            t = fix_leading_ocr(t)

            if conf > best_conf:
                best_conf = conf
                best_txt = t

        accepted = False
        final_txt = None

        if best_txt:
            
            if accept_plate(best_txt, best_conf):
                accepted = True
                final_txt = best_txt

        rec = {
            "car_id": car_id,
            "crop_path": str(img_path).replace("\\", "/"),
            "ocr_text": final_txt,
            "ocr_conf": round(best_conf, 3) if accepted else 0.0,
            "accepted": bool(accepted),
        }
        records.append(rec)

        if accepted:
            per_car_reads[car_id].append((final_txt, float(best_conf), str(img_path).replace("\\", "/")))

    # Save detailed OCR
    OUT_OCR_JSON.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print("Saved:", OUT_OCR_JSON)

    # Voting per car_id
    voted = []
    for car_id, reads in sorted(per_car_reads.items(), key=lambda x: x[0]):
        # read texts
        texts = [t for (t, _, _) in reads]
        if not texts:
            continue

        cnt = Counter(texts)
        final_plate, votes = cnt.most_common(1)[0]

        # pick best confidence among same plate
        best_conf = 0.0
        for t, c, _ in reads:
            if t == final_plate and c > best_conf:
                best_conf = c

        voted.append({
            "car_id": car_id,
            "final_plate": final_plate,
            "ocr_conf": best_conf,
            "reads": len(reads),
            "candidates": dict(cnt),
        })

    OUT_VOTED_JSON.write_text(json.dumps(voted, indent=2), encoding="utf-8")
    print("Saved:", OUT_VOTED_JSON)

if __name__ == "__main__":
    main()
