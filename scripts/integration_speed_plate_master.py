import json
from pathlib import Path
from collections import Counter

SPEED_JSON = Path("results/speed_depth_multi_clean_events.json")
MASTER_ID_MAP = Path("results/master_id_map.json")
PLATE_VOTED = Path("results/plate_voted_per_car.json")

OUT_JSON = Path("results/final_report_speed_plate_master.json")

def load(p, default):
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default

def idx_by_carid_plate(lst):
    d = {}
    if isinstance(lst, list):
        for r in lst:
            cid = r.get("car_id")
            if cid is None:
                continue
            d[str(cid)] = r
    return d

# -------- load inputs --------
speed = load(SPEED_JSON, {})
per_track = speed.get("per_track", {}) if isinstance(speed.get("per_track"), dict) else {}
speed_limit = float(speed.get("summary", {}).get("speed_limit_kmh", 60.0))

master_map = load(MASTER_ID_MAP, {})
master_groups = {}


if isinstance(master_map, dict):
    if master_map and all(isinstance(v, list) for v in master_map.values()):
        master_groups = {str(k): [str(x) for x in v] for k, v in master_map.items()}
    elif "masters" in master_map and isinstance(master_map["masters"], list):
        for m in master_map["masters"]:
            mid = str(m.get("master_id"))
            tracks = [str(x) for x in (m.get("tracks") or [])]
            if mid and tracks:
                master_groups[mid] = tracks


if not master_groups:
    master_groups = {f"T{tid}": [str(tid)] for tid in per_track.keys()}

plates = load(PLATE_VOTED, [])
plate_by_carid = idx_by_carid_plate(plates)

# -------- helper to decide master type by cls majority --------
def master_type(tracks):
    cls_counts = Counter()
    for tid in tracks:
        info = per_track.get(str(tid), {})
        c = info.get("cls_id", None)
        if isinstance(c, int):
            cls_counts[c] += 1
    
    if cls_counts and cls_counts.get(3, 0) >= max(1, sum(cls_counts.values()) * 0.5):
        return "MOTORCYCLE"
    return "CAR"

def master_speed(tracks):
    
    best = 0.0
    best_tid = None
    for tid in tracks:
        info = per_track.get(str(tid), {})
        if info.get("parked", False):
            continue
        ms = float(info.get("max_stable_kmh", 0.0) or 0.0)
        if ms > best:
            best = ms
            best_tid = tid
    return best, best_tid

def pick_plate_for_master(tracks):
    
    best_plate = "UNKNOWN"
    best_conf = 0.0
    for tid in tracks:
        p = plate_by_carid.get(str(tid))
        if not p:
            continue
        val = p.get("final_plate", "UNKNOWN") or "UNKNOWN"
        conf = float(p.get("ocr_conf", 0.0) or 0.0)
        if val != "UNKNOWN" and conf > best_conf:
            best_plate = val
            best_conf = conf
    return best_plate, best_conf

cars_out = []
motos_out = []

car_idx = 0
moto_idx = 0

for mid, tracks in master_groups.items():
    # keep only tracks that exist in speed per_track
    tracks = [t for t in tracks if str(t) in per_track]
    if not tracks:
        continue

    typ = master_type(tracks)
    sp, sp_from_tid = master_speed(tracks)
    plate_val, plate_conf = pick_plate_for_master(tracks)

    if typ == "CAR":
        # remove car if plate unknown
        if plate_val == "UNKNOWN":
            continue

        car_idx += 1
        cars_out.append({
            "car_id": car_idx,
            "master_id": mid,
            "tracks": tracks,
            "speed": {
                "max_stable_kmh": round(sp, 2),
                "limit_kmh": speed_limit,
                "violation": bool(sp >= speed_limit)
            },
            "plate": {
                "value": plate_val,
                "ocr_conf": round(plate_conf, 3)
            }
        })

    else:
        # keep motos even if plate unknown
        if sp <= 0.5:
            
            continue

        moto_idx += 1
        motos_out.append({
            "moto_id": moto_idx,
            "master_id": mid,
            "tracks": tracks,
            "speed": {
                "max_stable_kmh": round(sp, 2),
                "limit_kmh": speed_limit,
                "violation": bool(sp >= speed_limit)
            },
            "plate": {
                "value": plate_val,
                "ocr_conf": round(plate_conf, 3)
            }
        })

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps({"cars": cars_out, "motorcycles": motos_out}, indent=2), encoding="utf-8")

print("\n=== FINAL REPORT (MASTER + SPEED + PLATE ONLY) ===")
print(f"Cars: {len(cars_out)} | Motorcycles: {len(motos_out)}")
for c in cars_out:
    print(f"- CAR id={c['car_id']} master={c['master_id']} speed={c['speed']['max_stable_kmh']} plate={c['plate']['value']}")
for m in motos_out:
    print(f"- MOTO id={m['moto_id']} master={m['master_id']} speed={m['speed']['max_stable_kmh']} plate={m['plate']['value']}")
print("\nSaved:", OUT_JSON)
