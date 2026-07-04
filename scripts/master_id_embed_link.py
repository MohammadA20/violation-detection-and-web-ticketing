# scripts/master_id_embed_link.py
import json
import math
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from collections import Counter

import numpy as np
import torch
from torchvision.models import resnet50, ResNet50_Weights
from PIL import Image

IN_JSON = Path("results/master_car_tracks.json")
OUT_JSON = Path("results/master_id_map.json")

# ---------- BASE LINKING ----------
SIM_THR = 0.75
MAX_GAP_SEC = 2.0
MAX_DIST_PX = 280
MIN_IMAGES = 2

# ---------- EXTRA FOR MOTORCYCLES (fix duplicate moto IDs) ----------
MOTO_CLS = 3
MOTO_SIM_THR = 0.60
MOTO_MAX_GAP_SEC = 6.0
MOTO_MAX_DIST_PX = 420

# "hard stitch" when tracking splits for < 0.8s
HARD_GAP_SEC = 0.8
HARD_DIST_PX = 120
HARD_SIM_THR = 0.45
# ----------------------------------

@dataclass
class Tracklet:
    tid: int
    cls_id: int
    start_t: float
    end_t: float
    start_center: Tuple[float, float]
    end_center: Tuple[float, float]
    start_bbox: Tuple[float, float, float, float]
    end_bbox: Tuple[float, float, float, float]
    emb: np.ndarray
    n_imgs: int

class DSU:
    def __init__(self):
        self.p = {}
    def find(self, x):
        x = int(x)
        if x not in self.p:
            self.p[x] = x
        if self.p[x] != x:
            self.p[x] = self.find(self.p[x])
        return self.p[x]
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra

def center_xyxy(bb):
    x1, y1, x2, y2 = bb
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

def bbox_wh(bb):
    x1, y1, x2, y2 = bb
    return (max(1.0, x2 - x1), max(1.0, y2 - y1))

def size_ratio(bb_a, bb_b):
    wa, ha = bbox_wh(bb_a)
    wb, hb = bbox_wh(bb_b)
    aa = wa * ha
    ab = wb * hb
    if aa <= 1e-6 or ab <= 1e-6:
        return 999.0
    r = aa / ab
    return r if r >= 1.0 else (1.0 / r)

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a) + 1e-9
    nb = np.linalg.norm(b) + 1e-9
    return float(np.dot(a, b) / (na * nb))

def load_tracks() -> List[dict]:
    if not IN_JSON.exists():
        raise RuntimeError(f"Missing {IN_JSON}. Run master_car_export.py first.")
    data = json.loads(IN_JSON.read_text(encoding="utf-8"))
    tracks = data.get("tracks", [])
    if not isinstance(tracks, list):
        raise RuntimeError("master_car_tracks.json: tracks must be a list")
    return tracks

def build_embedder():
    weights = ResNet50_Weights.DEFAULT
    model = resnet50(weights=weights)
    model.fc = torch.nn.Identity()
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    tfm = weights.transforms()
    return model, tfm, device

@torch.no_grad()
def embed_images(model, tfm, device, img_paths: List[str]) -> Optional[np.ndarray]:
    feats = []
    for p in img_paths:
        try:
            im = Image.open(p).convert("RGB")
        except Exception:
            continue
        x = tfm(im).unsqueeze(0).to(device)
        f = model(x).squeeze(0).detach().cpu().numpy().astype(np.float32)
        feats.append(f)
    if not feats:
        return None
    emb = np.mean(np.stack(feats, axis=0), axis=0)
    emb /= (np.linalg.norm(emb) + 1e-9)
    return emb

def dominant_cls(images: List[dict]) -> int:
    cls_list = []
    for d in images:
        c = d.get("cls_id", None)
        if isinstance(c, int):
            cls_list.append(c)
    if not cls_list:
        return -1
    return Counter(cls_list).most_common(1)[0][0]

def tracklet_from_record(rec: dict, model, tfm, device) -> Optional[Tracklet]:
    tid = rec.get("track_id", None)
    images = rec.get("images", [])
    if tid is None or not isinstance(images, list) or len(images) < MIN_IMAGES:
        return None
    tid = int(tid)

    images = [x for x in images if isinstance(x, dict) and x.get("img_path")]
    if len(images) < MIN_IMAGES:
        return None
    images.sort(key=lambda d: float(d.get("timestamp_sec", 0.0)))

    # cls_id (dominant)
    cls_id = dominant_cls(images)

    img_paths = [d["img_path"] for d in images if d.get("img_path")]
    emb = embed_images(model, tfm, device, img_paths)
    if emb is None:
        return None

    start_t = float(images[0].get("timestamp_sec", 0.0))
    end_t   = float(images[-1].get("timestamp_sec", start_t))

    bb0 = images[0].get("bbox_xyxy", [0, 0, 0, 0])
    bb1 = images[-1].get("bbox_xyxy", [0, 0, 0, 0])
    if not (isinstance(bb0, list) and len(bb0) == 4 and isinstance(bb1, list) and len(bb1) == 4):
        return None

    bb0 = tuple(map(float, bb0))
    bb1 = tuple(map(float, bb1))

    return Tracklet(
        tid=tid,
        cls_id=int(cls_id),
        start_t=start_t,
        end_t=end_t,
        start_center=center_xyxy(bb0),
        end_center=center_xyxy(bb1),
        start_bbox=bb0,
        end_bbox=bb1,
        emb=emb,
        n_imgs=len(img_paths),
    )

def main():
    tracks = load_tracks()
    model, tfm, device = build_embedder()

    tracklets: List[Tracklet] = []
    for rec in tracks:
        tl = tracklet_from_record(rec, model, tfm, device)
        if tl:
            tracklets.append(tl)

    if not tracklets:
        raise RuntimeError("No valid tracklets. Check master_car_export output.")

    tracklets.sort(key=lambda t: t.start_t)
    dsu = DSU()

    GLOBAL_MAX_GAP = max(MAX_GAP_SEC, MOTO_MAX_GAP_SEC)

    for i in range(len(tracklets)):
        A = tracklets[i]
        for j in range(i + 1, len(tracklets)):
            B = tracklets[j]

            gap = B.start_t - A.end_t
            if gap < -0.3:
                continue
            if gap > GLOBAL_MAX_GAP:
                break  # because sorted by start_t

            # ✅ only link same class
            if A.cls_id != B.cls_id:
                continue

            dx = A.end_center[0] - B.start_center[0]
            dy = A.end_center[1] - B.start_center[1]
            dpx = math.hypot(dx, dy)

            sim = cosine(A.emb, B.emb)

            # base thresholds
            max_gap = MAX_GAP_SEC
            max_dist = MAX_DIST_PX
            sim_thr = SIM_THR

            # ✅ relax for motorcycles
            if A.cls_id == MOTO_CLS:
                max_gap = MOTO_MAX_GAP_SEC
                max_dist = MOTO_MAX_DIST_PX
                sim_thr = MOTO_SIM_THR

                # hard stitch (very short split)
                if gap <= HARD_GAP_SEC and dpx <= HARD_DIST_PX and sim >= HARD_SIM_THR:
                    dsu.union(A.tid, B.tid)
                    continue

            if gap <= max_gap and dpx <= max_dist and sim >= sim_thr:
                # small bbox size sanity check (prevents some bad merges)
                if size_ratio(A.end_bbox, B.start_bbox) <= 2.8:
                    dsu.union(A.tid, B.tid)

    groups: Dict[int, List[int]] = {}
    for tl in tracklets:
        root = dsu.find(tl.tid)
        groups.setdefault(root, []).append(tl.tid)

    group_list = sorted([sorted(v) for v in groups.values()], key=lambda g: g[0])

    master_map = {}
    for idx, members in enumerate(group_list, start=1):
        master_map[f"M{idx}"] = members

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({
        "video": json.loads(IN_JSON.read_text(encoding="utf-8")).get("video", ""),
        "params": {
            "SIM_THR": SIM_THR,
            "MAX_GAP_SEC": MAX_GAP_SEC,
            "MAX_DIST_PX": MAX_DIST_PX,
            "MIN_IMAGES": MIN_IMAGES,
            "MOTO_SIM_THR": MOTO_SIM_THR,
            "MOTO_MAX_GAP_SEC": MOTO_MAX_GAP_SEC,
            "MOTO_MAX_DIST_PX": MOTO_MAX_DIST_PX,
            "HARD_GAP_SEC": HARD_GAP_SEC,
            "HARD_DIST_PX": HARD_DIST_PX,
            "HARD_SIM_THR": HARD_SIM_THR
        },
        "master_ids": master_map
    }, indent=2), encoding="utf-8")

    print("\n=== MASTER ID (EMBEDDING LINK) ===")
    print("Tracklets:", len(tracklets))
    print("MasterIDs:", len(master_map))
    for mid, members in master_map.items():
        print(f"- {mid}: {members}")
    print("Saved:", OUT_JSON)
if __name__ == "__main__":
    main()    