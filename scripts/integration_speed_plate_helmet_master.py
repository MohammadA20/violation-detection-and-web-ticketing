# scripts/integration_speed_plate_helmet_master.py
# FINAL V5 (stable across test3 + test6)
#
# Fixes BOTH:
# - test6: remove spurious entity with helmet_total==0 even if bw missing (fallback to time+center)
# - test3: remove/absorb weak spurious entity (speed low / mv low / short bw/time)
# - Helmet vote decontamination: if entity has strong track(s), ignore votes from weak tracks

import json
import math
import re
from pathlib import Path
from collections import defaultdict

VERSION = "INTEGRATION_FINAL_V5_TEST3_TEST6"
DEBUG = True  # خلّيها True أول مرة لتشوف ليش عم يندمج/ما يندمج. بعدين فيك تعملها False.

SPEED_JSON       = Path("results/speed_depth_multi_clean_events.json")
MASTER_ID_MAP    = Path("results/master_id_map.json")
PLATE_VOTED      = Path("results/plate_voted_per_car.json")
HELMET_PER_MOTO  = Path("results/helmet_per_moto.json")
OUT_JSON         = Path("results/final_report.json")

# ---------------- Helmet decision ----------------
MIN_VALID_VOTES = 4
RATIO_DECIDE = 0.55
FALLBACK_MIN_VALID = 12
FALLBACK_MIN_MARGIN = 1
# -----------------------------------------------

# ---------------- Split / duplicate grouping ----------------
DUP_MAX_DT_SEC = 0.60
DUP_SIZE_RATIO_MAX = 1.9

DUP_IOU_STRONG = 0.45
DUP_IOU_MED    = 0.25
DUP_CENTER_MED_PX  = 90
DUP_CENTER_WEAK_PX = 140

STITCH_GAP_SEC = 1.2
STITCH_DIST_PX = 160
STITCH_SIZE_RATIO_MAX = 1.8
STITCH_MED_CENTER_MAX_PX = 260

STITCH_GAP_SEC_EXT = 6.0
STITCH_DIST_PX_EXT = 90
STITCH_SIZE_RATIO_MAX_EXT = 1.6
STITCH_MED_CENTER_MAX_PX_EXT = 180
# ------------------------------------------------

# ---------------- Weak / spurious definitions ----------------
WEAK_MOVING_FRAMES = 6
WEAK_MAX_SPEED_KMH = 7.0
WEAK_N_SAMPLES     = 3
WEAK_BW_LEN_FRAMES = 20
WEAK_TIME_LEN_SEC  = 1.2

MERGE_CENTER_MAX_PX = 220  # safety
BW_CONTAIN_PAD = 3
BW_OVERLAP_FULL = 0.95
TIME_OVERLAP_FULL = 0.85
# ------------------------------------------------------------

# ---------------- Salvage ----------------
MIN_SAMPLES_FOR_SALVAGE = 2
MIN_SPEED_FOR_SALVAGE = 1.0
# ------------------------------------------------------------


# ================= helpers =================
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

def center_xyxy(bb):
    x1, y1, x2, y2 = bb
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def iou_xyxy(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(1.0, (ax2 - ax1)) * max(1.0, (ay2 - ay1))
    area_b = max(1.0, (bx2 - bx1)) * max(1.0, (by2 - by1))
    return float(inter / (area_a + area_b - inter + 1e-6))

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

def decide_helmet(with_cnt: int, without_cnt: int):
    valid = int(with_cnt) + int(without_cnt)
    if valid < MIN_VALID_VOTES:
        return ("UNKNOWN", False, "few_valid")

    r_without = without_cnt / max(1, valid)
    r_with = with_cnt / max(1, valid)

    if r_without >= RATIO_DECIDE:
        return ("NO_HELMET", True, "ratio>=thr")
    if r_with >= RATIO_DECIDE:
        return ("HELMET_OK", False, "ratio>=thr")

    margin = abs(without_cnt - with_cnt)
    if valid >= FALLBACK_MIN_VALID and margin >= FALLBACK_MIN_MARGIN:
        if without_cnt > with_cnt:
            return ("NO_HELMET", True, "fallback_majority")
        if with_cnt > without_cnt:
            return ("HELMET_OK", False, "fallback_majority")

    return ("UNKNOWN", False, "uncertain")

def parse_master_groups(master_map: dict):
    groups = {}
    if not isinstance(master_map, dict):
        return groups

    if isinstance(master_map.get("master_ids"), dict):
        for mid, tids in master_map["master_ids"].items():
            if isinstance(tids, list) and tids:
                groups[str(mid)] = [norm_tid(x) for x in tids if norm_tid(x) is not None]
        return groups

    if master_map and all(isinstance(v, list) for v in master_map.values()):
        for mid, tids in master_map.items():
            groups[str(mid)] = [norm_tid(x) for x in tids if norm_tid(x) is not None]
        return groups

    if isinstance(master_map.get("masters"), list):
        for m in master_map["masters"]:
            mid = str(m.get("master_id") or m.get("id") or "").strip()
            tids = m.get("tracks") or m.get("track_ids") or []
            if mid and isinstance(tids, list) and tids:
                groups[mid] = [norm_tid(x) for x in tids if norm_tid(x) is not None]
        return groups

    return groups

def master_type(tracks, per_track):
    for tid in tracks:
        c = per_track.get(str(tid), {}).get("cls_id", None)
        if c == 3:
            return "MOTORCYCLE"
    return "CAR"

def master_speed(tracks, per_track):
    best = 0.0
    best_tid = None

    for tid in tracks:
        info = per_track.get(str(tid), {})
        if info.get("parked", False):
            continue
        ms = float(info.get("max_stable_kmh", info.get("max_raw_kmh", 0.0)) or 0.0)
        if ms > best:
            best = ms
            best_tid = str(tid)

    if best_tid is None:
        for tid in tracks:
            info = per_track.get(str(tid), {})
            ms = float(info.get("max_stable_kmh", info.get("max_raw_kmh", 0.0)) or 0.0)
            if ms > best:
                best = ms
                best_tid = str(tid)

    return best, best_tid

def index_plate_by_carid(lst):
    d = {}
    if isinstance(lst, list):
        for r in lst:
            cid = r.get("car_id")
            if cid is None:
                continue
            d[str(cid)] = r
    return d

def pick_plate_for_master(tracks, plate_by_carid):
    best_plate = "UNKNOWN"
    best_conf = 0.0
    best_from = None
    for tid in tracks:
        p = plate_by_carid.get(str(tid))
        if not p:
            continue
        val = str(p.get("final_plate") or "UNKNOWN").strip().upper()
        conf = float(p.get("ocr_conf", 0.0) or 0.0)
        if val != "UNKNOWN" and conf > best_conf:
            best_plate = val
            best_conf = conf
            best_from = str(tid)
    return best_plate, best_conf, best_from

def index_helmet_by_track(lst):
    d = {}
    if isinstance(lst, list):
        for r in lst:
            tid = r.get("track_id", None)
            if tid is None:
                continue
            d[norm_tid(tid)] = r
    return d

def helmet_total_votes(helmet_by_track, tid):
    r = helmet_by_track.get(str(tid))
    if not r:
        return 0
    v = r.get("votes", {}) or {}
    return int(v.get("total", 0) or 0)

def per_track_meta(per_track, tid):
    info = per_track.get(str(tid), {}) if isinstance(per_track.get(str(tid), {}), dict) else {}
    mv = int(info.get("moving_frames", 0) or 0)
    ms = float(info.get("max_stable_kmh", info.get("max_raw_kmh", 0.0)) or 0.0)
    return mv, ms


# ================= BW helpers (deep) =================
def _parse_bw_value(v):
    if v is None:
        return None
    if isinstance(v, (list, tuple)) and len(v) >= 2:
        try:
            a = int(v[0]); b = int(v[1])
            if b < a:
                a, b = b, a
            return (a, b)
        except Exception:
            return None
    if isinstance(v, dict) and ("start" in v) and ("end" in v):
        try:
            a = int(v["start"]); b = int(v["end"])
            if b < a:
                a, b = b, a
            return (a, b)
        except Exception:
            return None
    if isinstance(v, str):
        m = re.search(r"(\d+)\D+(\d+)", v)
        if m:
            a = int(m.group(1)); b = int(m.group(2))
            if b < a:
                a, b = b, a
            return (a, b)
    return None

def bw_from_info_deep(info, depth=3):
    if not isinstance(info, dict) or depth <= 0:
        return None

    # direct keys
    for k in ["bw", "best_window", "best_bw", "moving_bw", "window", "moving_window", "bestWindow", "BW"]:
        if k in info:
            bw = _parse_bw_value(info.get(k))
            if bw:
                return bw

    # heuristic scan
    for k, v in info.items():
        kk = str(k).lower()
        if ("bw" in kk) or ("window" in kk):
            bw = _parse_bw_value(v)
            if bw:
                return bw

    # recurse
    for v in info.values():
        if isinstance(v, dict):
            bw = bw_from_info_deep(v, depth=depth - 1)
            if bw:
                return bw

    return None

def bw_len(bw):
    if not bw:
        return 0
    return max(0, int(bw[1]) - int(bw[0]))

def bw_overlap_ratio(a, b):
    if not a or not b:
        return 0.0
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    if inter <= 0:
        return 0.0
    base = max(1, min(bw_len(a), bw_len(b)))
    return float(inter / base)

def bw_contained(inner, outer, pad=BW_CONTAIN_PAD):
    if not inner or not outer:
        return False
    return (inner[0] >= outer[0] - pad) and (inner[1] <= outer[1] + pad)


# ================= DSU =================
class DSU:
    def __init__(self, items):
        self.p = {str(x): str(x) for x in items}

    def find(self, x):
        x = str(x)
        if x not in self.p:
            self.p[x] = x
        if self.p[x] != x:
            self.p[x] = self.find(self.p[x])
        return self.p[x]

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


# ================= samples processing =================
def collect_moto_samples(samples, track_set):
    by = defaultdict(list)
    if not isinstance(samples, list):
        return by
    for s in samples:
        try:
            tid = norm_tid(s.get("track_id"))
            if tid is None or tid not in track_set:
                continue
            if int(s.get("cls_id", -1)) != 3:
                continue
            bb = s.get("bbox_xyxy", None)
            ts = s.get("timestamp_sec", None)
            if ts is None or not isinstance(bb, list) or len(bb) != 4:
                continue
            bb = [float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3])]
            by[tid].append({"t": float(ts), "bb": bb})
        except Exception:
            continue
    for tid in list(by.keys()):
        by[tid].sort(key=lambda x: x["t"])
    return by

def max_temporal_iou(sa, sb, max_dt=DUP_MAX_DT_SEC):
    i, j = 0, 0
    best = 0.0
    while i < len(sa) and j < len(sb):
        ta = sa[i]["t"]
        tb = sb[j]["t"]
        dt = ta - tb
        if abs(dt) <= max_dt:
            best = max(best, iou_xyxy(sa[i]["bb"], sb[j]["bb"]))
            if ta <= tb:
                i += 1
            else:
                j += 1
        elif dt < -max_dt:
            i += 1
        else:
            j += 1
    return best

def min_temporal_center_dist(sa, sb, max_dt=DUP_MAX_DT_SEC):
    i, j = 0, 0
    best = 1e18
    while i < len(sa) and j < len(sb):
        ta = sa[i]["t"]
        tb = sb[j]["t"]
        dt = ta - tb
        if abs(dt) <= max_dt:
            ca = center_xyxy(sa[i]["bb"])
            cb = center_xyxy(sb[j]["bb"])
            best = min(best, dist(ca, cb))
            if ta <= tb:
                i += 1
            else:
                j += 1
        elif dt < -max_dt:
            i += 1
        else:
            j += 1
    return best

def track_stats_from_samples(samples_by_tid, tid, per_track):
    s = samples_by_tid.get(str(tid), [])
    mv, ms = per_track_meta(per_track, tid)

    if not s:
        return {
            "tid": str(tid),
            "n": 0,
            "start_t": 1e18,
            "end_t": -1e18,
            "duration": 0.0,
            "start_bb": None,
            "end_bb": None,
            "start_c": None,
            "end_c": None,
            "med_c": None,
            "moving_frames": mv,
            "max_sp": ms,
        }

    start = s[0]
    end = s[-1]
    centers = [center_xyxy(x["bb"]) for x in s]
    xs = sorted([c[0] for c in centers])
    ys = sorted([c[1] for c in centers])
    mid = len(xs) // 2
    med_center = (xs[mid], ys[mid])

    start_t = float(start["t"])
    end_t = float(end["t"])
    return {
        "tid": str(tid),
        "n": len(s),
        "start_t": start_t,
        "end_t": end_t,
        "duration": max(0.0, end_t - start_t),
        "start_bb": start["bb"],
        "end_bb": end["bb"],
        "start_c": center_xyxy(start["bb"]),
        "end_c": center_xyxy(end["bb"]),
        "med_c": med_center,
        "moving_frames": mv,
        "max_sp": ms,
    }


# ================= split + post merge =================
def is_weak_track_stats(st, helmet_total: int):
    n  = int(st.get("n", 0) or 0)
    mv = int(st.get("moving_frames", 0) or 0)
    sp = float(st.get("max_sp", 0.0) or 0.0)

    if (mv <= WEAK_MOVING_FRAMES and sp <= WEAK_MAX_SPEED_KMH):
        return True
    if (n > 0 and n <= WEAK_N_SAMPLES and sp <= WEAK_MAX_SPEED_KMH):
        return True
    if helmet_total == 0 and (mv <= WEAK_MOVING_FRAMES or sp <= WEAK_MAX_SPEED_KMH or (n > 0 and n <= WEAK_N_SAMPLES)):
        return True
    return False

def split_moto_tracks_into_entities(master_id, moto_tracks, samples, per_track, helmet_by_track):
    if not moto_tracks:
        return [], {}

    tids = [str(t) for t in moto_tracks]
    track_set = set(tids)
    samples_by_tid = collect_moto_samples(samples, track_set)
    stats = {t: track_stats_from_samples(samples_by_tid, t, per_track) for t in tids}

    # If not enough samples to split reliably -> one entity
    n_with_samples = sum(1 for t in tids if stats[t].get("n", 0) > 0)
    if n_with_samples < 2:
        return [tids], stats

    dsu = DSU(tids)

    # 1) overlap duplicate merge
    for i in range(len(tids)):
        for j in range(i + 1, len(tids)):
            A = stats[tids[i]]
            B = stats[tids[j]]

            if A["n"] == 0 or B["n"] == 0:
                continue

            ov = min(A["end_t"], B["end_t"]) - max(A["start_t"], B["start_t"])
            if ov <= 0:
                continue

            sr = size_ratio(A["end_bb"], B["end_bb"])
            if sr > DUP_SIZE_RATIO_MAX:
                continue

            miou = max_temporal_iou(samples_by_tid[A["tid"]], samples_by_tid[B["tid"]], max_dt=DUP_MAX_DT_SEC)
            if miou >= DUP_IOU_STRONG:
                dsu.union(A["tid"], B["tid"])
                continue

            mcd = min_temporal_center_dist(samples_by_tid[A["tid"]], samples_by_tid[B["tid"]], max_dt=DUP_MAX_DT_SEC)
            if miou >= DUP_IOU_MED and mcd <= DUP_CENTER_MED_PX:
                dsu.union(A["tid"], B["tid"])
                continue

            # weak assist fallback
            htA = helmet_total_votes(helmet_by_track, A["tid"])
            htB = helmet_total_votes(helmet_by_track, B["tid"])
            weakA = is_weak_track_stats(A, htA)
            weakB = is_weak_track_stats(B, htB)

            durA = max(1e-6, float(A.get("duration", 0.0) or 0.0))
            durB = max(1e-6, float(B.get("duration", 0.0) or 0.0))
            ov_ratio = ov / max(1e-6, min(durA, durB))
            d_med = dist(A["med_c"], B["med_c"])

            if (weakA or weakB) and ov_ratio >= 0.60 and d_med <= DUP_CENTER_WEAK_PX:
                dsu.union(A["tid"], B["tid"])
                continue

    # 2) stitch sequential splits mutual-best
    best_succ = {}
    best_prev = {}

    def weakish_for_stitch(st):
        ht = helmet_total_votes(helmet_by_track, st["tid"])
        return is_weak_track_stats(st, ht)

    def consider_link(A, B):
        if A["n"] == 0 or B["n"] == 0:
            return
        gap = B["start_t"] - A["end_t"]
        if gap < -0.20:
            return

        d_end = dist(A["end_c"], B["start_c"])
        d_med = dist(A["med_c"], B["med_c"])
        sr = size_ratio(A["end_bb"], B["start_bb"])

        ok_norm = (
            gap <= STITCH_GAP_SEC and
            d_end <= STITCH_DIST_PX and
            d_med <= STITCH_MED_CENTER_MAX_PX and
            sr <= STITCH_SIZE_RATIO_MAX
        )

        ok_ext = False
        if len(tids) == 2 or weakish_for_stitch(A) or weakish_for_stitch(B):
            ok_ext = (
                gap <= STITCH_GAP_SEC_EXT and
                d_end <= STITCH_DIST_PX_EXT and
                d_med <= STITCH_MED_CENTER_MAX_PX_EXT and
                sr <= STITCH_SIZE_RATIO_MAX_EXT
            )

        if not (ok_norm or ok_ext):
            return

        gap_n = gap / (STITCH_GAP_SEC if ok_norm else STITCH_GAP_SEC_EXT)
        d_n   = d_end / (STITCH_DIST_PX if ok_norm else STITCH_DIST_PX_EXT)
        sr_n  = max(0.0, sr - 1.0) / (((STITCH_SIZE_RATIO_MAX if ok_norm else STITCH_SIZE_RATIO_MAX_EXT) - 1.0) + 1e-6)
        med_n = d_med / (STITCH_MED_CENTER_MAX_PX if ok_norm else STITCH_MED_CENTER_MAX_PX_EXT)
        sc = gap_n + d_n + sr_n + med_n

        a = A["tid"]; b = B["tid"]
        if (a not in best_succ) or (sc < best_succ[a][1]):
            best_succ[a] = (b, sc)
        if (b not in best_prev) or (sc < best_prev[b][1]):
            best_prev[b] = (a, sc)

    tids_sorted = sorted(tids, key=lambda t: stats[t]["start_t"])
    for i in range(len(tids_sorted)):
        A = stats[tids_sorted[i]]
        for j in range(i + 1, len(tids_sorted)):
            B = stats[tids_sorted[j]]
            if A["n"] > 0 and B["n"] > 0 and (B["start_t"] - A["end_t"]) > (STITCH_GAP_SEC_EXT + 3.0):
                break
            consider_link(A, B)

    for a, (b, sc) in best_succ.items():
        if b in best_prev and best_prev[b][0] == a:
            dsu.union(a, b)

    comps = defaultdict(list)
    for t in tids:
        comps[dsu.find(t)].append(t)

    entities = list(comps.values())

    def t_start(tid):
        return stats.get(str(tid), {}).get("start_t", 1e18)

    for e in entities:
        e.sort(key=t_start)
    entities.sort(key=lambda e: min([t_start(x) for x in e]) if e else 1e18)

    if DEBUG and len(entities) > 1:
        print(f"[FIX] Moto master {master_id} entities (pre-post) -> {entities}")

    return entities, stats


def merge_spurious_entities_post(master_id, entities, per_track, helmet_by_track, stats_map):
    """
    Post merge spurious entities using:
    - BW containment/overlap if BW exists (deep)
    - else time containment/overlap from stats_map (samples-derived)
    Safety:
    - require A weaker than B
    - require center distance <= MERGE_CENTER_MAX_PX when possible
    """
    if not entities or len(entities) <= 1:
        return entities

    def ent_meta(ent):
        starts, ends = [], []
        t0s, t1s = [], []
        meds = []
        mv_sum = 0
        sp_max = 0.0
        ht_sum = 0

        for tid in ent:
            tid = str(tid)
            info = per_track.get(tid, {}) or {}
            mv_sum += int(info.get("moving_frames", 0) or 0)
            sp_max = max(sp_max, float(info.get("max_stable_kmh", info.get("max_raw_kmh", 0.0)) or 0.0))
            ht_sum += helmet_total_votes(helmet_by_track, tid)

            bw = bw_from_info_deep(info)
            if bw:
                starts.append(bw[0]); ends.append(bw[1])

            st = stats_map.get(tid, {})
            if st and st.get("n", 0) > 0:
                t0s.append(float(st["start_t"]))
                t1s.append(float(st["end_t"]))
                if st.get("med_c") is not None:
                    meds.append(st["med_c"])

        bw_u = (min(starts), max(ends)) if starts and ends else None
        bw_l = bw_len(bw_u) if bw_u else 0

        t_u = (min(t0s), max(t1s)) if t0s and t1s else None
        t_l = (t_u[1] - t_u[0]) if t_u else 0.0

        mc = None
        if meds:
            mc = (sum(c[0] for c in meds)/len(meds), sum(c[1] for c in meds)/len(meds))

        # weak entity heuristic
        weak = False
        if ht_sum == 0:
            weak = True
        if (mv_sum <= WEAK_MOVING_FRAMES and sp_max <= WEAK_MAX_SPEED_KMH):
            weak = True
        if bw_u and bw_l <= WEAK_BW_LEN_FRAMES and sp_max <= WEAK_MAX_SPEED_KMH + 2.0:
            weak = True
        if t_u and t_l <= WEAK_TIME_LEN_SEC and sp_max <= WEAK_MAX_SPEED_KMH + 2.0:
            weak = True

        return {
            "bw": bw_u, "bw_len": bw_l,
            "t": t_u, "t_len": float(t_l),
            "mc": mc,
            "mv": mv_sum, "sp": sp_max, "ht": ht_sum,
            "weak": bool(weak),
        }

    def time_overlap_ratio(a, b):
        if not a or not b:
            return 0.0
        inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
        if inter <= 0:
            return 0.0
        la = max(1e-6, float(a[1] - a[0]))
        lb = max(1e-6, float(b[1] - b[0]))
        base = max(1e-6, min(la, lb))
        return float(inter / base)

    def time_contained(inner, outer, pad_sec=0.25):
        if not inner or not outer:
            return False
        return (inner[0] >= outer[0] - pad_sec) and (inner[1] <= outer[1] + pad_sec)

    changed = False

    while True:
        metas = [ent_meta(e) for e in entities]

        if DEBUG and len(entities) > 1:
            print(f"[DBG] {master_id} post-merge check:")
            for e, m in zip(entities, metas):
                print("   ent=", e, "weak=", m["weak"], "ht=", m["ht"],
                      "mv=", m["mv"], "sp=", round(m["sp"], 2),
                      "bw=", m["bw"], "t=", m["t"])

        merged_any = False

        for i in range(len(entities)):
            Aent = entities[i]
            A = metas[i]
            if not A["weak"]:
                continue

            best_j = None
            best_sc = 1e18

            for j in range(len(entities)):
                if j == i:
                    continue
                Bent = entities[j]
                B = metas[j]

                # host must be stronger (avoid merging true different motos)
                if B["weak"]:
                    continue

                # A must be weaker than B
                if not (A["mv"] <= B["mv"] and A["sp"] <= B["sp"] + 0.01):
                    # allow ht==0 spurious even if speed close, but still require mv smaller
                    if not (A["ht"] == 0 and A["mv"] <= B["mv"]):
                        continue

                ok = False
                contained = False
                ov = 0.0

                # BW mode
                if A["bw"] and B["bw"]:
                    contained = bw_contained(A["bw"], B["bw"], pad=BW_CONTAIN_PAD)
                    ov = bw_overlap_ratio(A["bw"], B["bw"])
                    if contained or ov >= BW_OVERLAP_FULL:
                        ok = True

                # TIME mode
                if (not ok) and A["t"] and B["t"]:
                    contained = time_contained(A["t"], B["t"], pad_sec=0.25)
                    ov = time_overlap_ratio(A["t"], B["t"])
                    if contained or ov >= TIME_OVERLAP_FULL:
                        ok = True

                # very strict fallback: only if exactly 2 entities and A is zero-helmet clearly weaker
                if (not ok) and len(entities) == 2 and A["ht"] == 0:
                    mv_ok = (B["mv"] > 0 and A["mv"] <= 0.75 * B["mv"])
                    sp_ok = (B["sp"] > 0 and A["sp"] <= 0.90 * B["sp"])
                    if mv_ok and sp_ok:
                        ok = True
                        contained = True
                        ov = 1.0

                if not ok:
                    continue

                # center safety if available
                if A["mc"] is not None and B["mc"] is not None:
                    if dist(A["mc"], B["mc"]) > MERGE_CENTER_MAX_PX:
                        continue

                # score
                sc = 0.0 if contained else (1.0 - ov)
                sc += 0.001 * abs(A["sp"] - B["sp"])

                if sc < best_sc:
                    best_sc = sc
                    best_j = j

            if best_j is not None:
                host = entities[best_j]
                victim = entities[i]
                entities[best_j] = list(dict.fromkeys([*host, *victim]))
                del entities[i]
                changed = True
                merged_any = True
                if DEBUG:
                    print(f"[FIX] {master_id}: merged spurious entity {victim} -> {host}")
                break

        if not merged_any:
            break

    if changed and DEBUG:
        print(f"[FIX] Moto master {master_id} entities (post) -> {entities}")

    return entities


# ================= Helmet vote decontamination =================
def is_weak_track_for_votes(per_track, stats_map, tid, helmet_by_track):
    tid = str(tid)
    st = stats_map.get(tid, {"n": 0, "moving_frames": 0, "max_sp": 0.0})
    ht = helmet_total_votes(helmet_by_track, tid)

    n  = int(st.get("n", 0) or 0)
    mv = int(st.get("moving_frames", 0) or 0)
    sp = float(st.get("max_sp", 0.0) or 0.0)

    if (mv <= WEAK_MOVING_FRAMES and sp <= WEAK_MAX_SPEED_KMH):
        return True
    if (n > 0 and n <= WEAK_N_SAMPLES and sp <= WEAK_MAX_SPEED_KMH):
        return True

    info = per_track.get(tid, {}) or {}
    bw = bw_from_info_deep(info)
    if bw and bw_len(bw) <= WEAK_BW_LEN_FRAMES and sp <= WEAK_MAX_SPEED_KMH + 2.0:
        return True

    if ht == 0 and (mv <= WEAK_MOVING_FRAMES or sp <= WEAK_MAX_SPEED_KMH):
        return True

    return False

def aggregate_helmet_votes_entity(ent_tracks, per_track, stats_map, helmet_by_track):
    weak_flags = {str(t): is_weak_track_for_votes(per_track, stats_map, t, helmet_by_track) for t in ent_tracks}
    has_strong = any(not weak_flags[str(t)] for t in ent_tracks)

    votes = {"with": 0, "without": 0, "unknown": 0, "total": 0}
    used = 0
    skipped = 0

    for t in ent_tracks:
        tid = str(t)
        if has_strong and weak_flags[tid]:
            skipped += 1
            continue
        r = helmet_by_track.get(tid)
        if not r:
            continue
        v = r.get("votes", {}) or {}
        votes["with"] += int(v.get("with", 0) or 0)
        votes["without"] += int(v.get("without", 0) or 0)
        votes["unknown"] += int(v.get("unknown", 0) or 0)
        votes["total"] += int(v.get("total", 0) or 0)
        used += 1

    return votes, used, skipped


# ================= Salvage =================
def salvage_missing_motos_from_samples(speed, per_track):
    samples = speed.get("samples", [])
    if not isinstance(samples, list) or not samples:
        return 0

    agg = defaultdict(lambda: {"n": 0, "max_sp": 0.0})
    for s in samples:
        try:
            tid = norm_tid(s.get("track_id", None))
            cls = s.get("cls_id", None)
            if tid is None or cls is None:
                continue
            if int(cls) != 3:
                continue
            sp1 = float(s.get("max_stable_kmh", 0.0) or 0.0)
            sp2 = float(s.get("speed_now_kmh", 0.0) or 0.0)
            agg[tid]["n"] += 1
            agg[tid]["max_sp"] = max(agg[tid]["max_sp"], sp1, sp2)
        except Exception:
            continue

    added = 0
    for tid, a in agg.items():
        if tid in per_track:
            continue
        if a["n"] < MIN_SAMPLES_FOR_SALVAGE:
            continue
        if a["max_sp"] < MIN_SPEED_FOR_SALVAGE:
            continue

        per_track[tid] = {
            "seen_frames": int(a["n"]),
            "moving_frames": int(a["n"]),
            "parked": False,
            "cls_id": 3,
            "max_stable_kmh": round(float(a["max_sp"]), 2),
            "max_raw_kmh": round(float(a["max_sp"]), 2),
            "violation": False,
            "_note": "SALVAGED_FROM_SAMPLES_STRICT"
        }
        added += 1

    return added


# ================= MAIN =================
def main():
    print(f"RUNNING: {VERSION}")
    print("FILE:", Path(__file__).resolve())

    speed = load_json(SPEED_JSON, {})
    per_track = speed.get("per_track", {}) if isinstance(speed.get("per_track"), dict) else {}
    samples = speed.get("samples", []) if isinstance(speed.get("samples"), list) else []
    speed_limit = float(speed.get("summary", {}).get("speed_limit_kmh", 60.0) or 60.0)

    per_track = {norm_tid(k): v for k, v in per_track.items() if norm_tid(k) is not None}

    added = salvage_missing_motos_from_samples(speed, per_track)
    if added > 0:
        print(f"[FIX] Added {added} missing MOTORCYCLE tracks from speed.samples into per_track (strict)")

    master_map = load_json(MASTER_ID_MAP, {})
    groups = parse_master_groups(master_map)

    masters = {}
    if groups:
        for mid, tids in groups.items():
            kept = [t for t in tids if str(t) in per_track]
            if kept:
                masters[str(mid)] = kept

    # ALWAYS add leftover tracks as T<tid>
    used = set()
    for mid, tids in masters.items():
        for t in tids:
            used.add(str(t))
    for tid in per_track.keys():
        if str(tid) not in used:
            masters[f"T{tid}"] = [str(tid)]

    plate_by_carid = index_plate_by_carid(load_json(PLATE_VOTED, []))
    helmet_by_track = index_helmet_by_track(load_json(HELMET_PER_MOTO, []))

    cars_out = []
    motos_out = []
    car_id = 0
    moto_id = 0

    for mid in sorted(masters.keys(), key=lambda x: (0 if x.startswith("M") else 1, x)):
        tracks = masters[mid]
        typ = master_type(tracks, per_track)

        if typ == "CAR":
            sp, sp_tid = master_speed(tracks, per_track)
            plate_val, plate_conf, plate_from = pick_plate_for_master(tracks, plate_by_carid)
            if plate_val == "UNKNOWN":
                continue

            car_id += 1
            cars_out.append({
                "car_id": car_id,
                "master_id": mid,
                "tracks": tracks,
                "speed": {
                    "max_stable_kmh": round(sp, 2),
                    "limit_kmh": round(speed_limit, 2),
                    "violation": bool(sp >= speed_limit),
                    "from_track": sp_tid
                },
                "plate": {
                    "value": str(plate_val),
                    "ocr_conf": round(float(plate_conf), 3),
                    "from_track": plate_from
                },
                "helmet": {
                    "final_decision": "ITS_CAR",
                    "violation": False
                }
            })
            continue

        # MOTORCYCLE master
        moto_tracks = [t for t in tracks if per_track.get(str(t), {}).get("cls_id", None) == 3]
        if not moto_tracks:
            continue

        entities, stats_map = split_moto_tracks_into_entities(mid, moto_tracks, samples, per_track, helmet_by_track)

        # ✅ Post merge spurious: fixes test6 + test3
        entities = merge_spurious_entities_post(mid, entities, per_track, helmet_by_track, stats_map)

        if not entities:
            entities = [moto_tracks]

        for idx, ent_tracks in enumerate(entities, start=1):
            ent_mid = mid if len(entities) == 1 else f"{mid}#{idx}"

            sp, sp_tid = master_speed(ent_tracks, per_track)

            votes, used_tracks, skipped = aggregate_helmet_votes_entity(ent_tracks, per_track, stats_map, helmet_by_track)
            if DEBUG and skipped > 0:
                print(f"[FIX] Helmet votes for {ent_mid}: used_tracks={used_tracks}, skipped_weak_tracks={skipped}")

            final, viol, rule = decide_helmet(votes["with"], votes["without"])

            moto_id += 1
            motos_out.append({
                "moto_id": moto_id,
                "master_id": ent_mid,
                "parent_master": mid,
                "tracks": ent_tracks,
                "speed": {
                    "max_stable_kmh": round(sp, 2),
                    "limit_kmh": round(speed_limit, 2),
                    "violation": bool(sp >= speed_limit),
                    "from_track": sp_tid
                },
                "helmet": {
                    "final_decision": final,
                    "violation": bool(viol),
                    "decision_rule": rule,
                    "votes": votes,
                    "tracks_used": int(used_tracks),
                    "skipped_weak_tracks": int(skipped)
                },
                "plate": {
                    "value": "UNKNOWN",
                    "ocr_conf": 0.0,
                    "from_track": None
                }
            })

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({"cars": cars_out, "motorcycles": motos_out}, indent=2), encoding="utf-8")

    print("\n=== FINAL REPORT (MASTER + SPEED + PLATE + HELMET) ===")
    print(f"Cars: {len(cars_out)} | Motorcycles: {len(motos_out)}")
    for c in cars_out:
        print(f"- CAR id={c['car_id']} master={c['master_id']} speed={c['speed']['max_stable_kmh']} plate={c['plate']['value']}")
    for m in motos_out:
        print(f"- MOTO id={m['moto_id']} master={m['master_id']} speed={m['speed']['max_stable_kmh']} helmet={m['helmet']['final_decision']} plate={m['plate']['value']}")
    print("\nSaved:", OUT_JSON)
if __name__ == "__main__":
    main()