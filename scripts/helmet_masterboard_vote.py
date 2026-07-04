# scripts/helmet_masterboard_vote.py  (MASTERBOARD FINAL - ROBUST)
import json
from pathlib import Path
from collections import defaultdict

# ================== PATHS ==================
HELMET_PER_MOTO = Path("results/helmet_per_moto.json")      # from helmet_per_moto_from_speed.py
MASTER_ID_MAP   = Path("results/master_id_map.json")        # from master_id_embed_link.py
OUT_JSON        = Path("results/helmet_per_master.json")    # FINAL output
# ===========================================

# ---------- Decision params ----------
MIN_VALID_VOTES = 4
RATIO_DECIDE = 0.55

# ✅ Fallback: إذا في أصوات كتيرة بس النسبة ما وصلت 0.55
FALLBACK_MIN_VALID = 12      # إذا valid votes >= 12
FALLBACK_MIN_MARGIN = 1      # فرق 1 vote بيكفي (بدكها تحسم وما تضل UNKNOWN)
# -----------------------------------

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

def decide(with_cnt: int, without_cnt: int):
    """
    returns: (final_decision, violation, rule)
    """
    valid = int(with_cnt) + int(without_cnt)
    if valid < MIN_VALID_VOTES:
        return ("UNKNOWN", False, "few_valid")

    r_without = without_cnt / max(1, valid)
    r_with    = with_cnt / max(1, valid)

    # ✅ strong decision (same as before)
    if r_without >= RATIO_DECIDE:
        return ("NO_HELMET", True, "ratio>=thr")
    if r_with >= RATIO_DECIDE:
        return ("HELMET_OK", False, "ratio>=thr")

    # ✅ fallback decision (NEW): if many votes, decide by majority
    margin = abs(without_cnt - with_cnt)
    if valid >= FALLBACK_MIN_VALID and margin >= FALLBACK_MIN_MARGIN:
        if without_cnt > with_cnt:
            return ("NO_HELMET", True, "fallback_majority")
        if with_cnt > without_cnt:
            return ("HELMET_OK", False, "fallback_majority")

    return ("UNKNOWN", False, "uncertain")

def parse_master_groups(master_map):
    """
    supports YOUR format:
    {
      "video": ...,
      "params": ...,
      "master_ids": { "M1":[3], "M2":[6], ... }
    }
    and older formats.
    returns dict master_id -> list[str tid]
    """
    groups = {}

    if not isinstance(master_map, dict):
        return groups

    # ✅ MAIN: master_ids dict
    if isinstance(master_map.get("master_ids"), dict):
        for mid, tids in master_map["master_ids"].items():
            if isinstance(tids, list) and tids:
                groups[str(mid)] = [str(x) for x in tids]
        return groups

    # fallback: {"M1":[...], "M2":[...]}
    if master_map and all(isinstance(v, list) for v in master_map.values()):
        for mid, tids in master_map.items():
            groups[str(mid)] = [str(x) for x in tids]
        return groups

    # fallback: {"masters":[{"master_id":"M1","tracks":[...]}]}
    if isinstance(master_map.get("masters"), list):
        for m in master_map["masters"]:
            mid = str(m.get("master_id") or m.get("id") or "").strip()
            tids = m.get("tracks") or m.get("track_ids") or []
            if mid and isinstance(tids, list) and tids:
                groups[mid] = [str(x) for x in tids]
        return groups

    return groups

def build_track_to_master(groups):
    track_to_master = {}
    for mid, tids in groups.items():
        for t in tids:
            track_to_master[str(t)] = str(mid)
    return track_to_master

def main():
    helmet_list = load_json(HELMET_PER_MOTO, [])
    if not isinstance(helmet_list, list) or len(helmet_list) == 0:
        print("ERROR: helmet_per_moto.json missing/empty:", HELMET_PER_MOTO)
        return

    master_map = load_json(MASTER_ID_MAP, {})
    groups = parse_master_groups(master_map)
    if not groups:
        print("ERROR: master_id_map.json missing/unknown format:", MASTER_ID_MAP)
        return

    track_to_master = build_track_to_master(groups)

    # aggregate votes per master
    agg = defaultdict(lambda: {
        "with": 0, "without": 0, "unknown": 0, "total": 0,
        "tracks": set(),
        "source_tracks": set()
    })

    for r in helmet_list:
        tid = r.get("track_id", None)
        if tid is None:
            continue
        tid = str(tid)

        mid = track_to_master.get(tid)
        if not mid:
            # track not in master map -> alone
            mid = f"T{tid}"

        v = r.get("votes", {}) or {}
        a = agg[mid]
        a["with"]    += int(v.get("with", 0) or 0)
        a["without"] += int(v.get("without", 0) or 0)
        a["unknown"] += int(v.get("unknown", 0) or 0)
        a["total"]   += int(v.get("total", 0) or 0)
        a["tracks"].add(tid)
        a["source_tracks"].add(tid)

    out = []
    for mid, v in agg.items():
        final, viol, rule = decide(v["with"], v["without"])
        out.append({
            "master_id": str(mid),
            "tracks": sorted(list(v["tracks"]), key=lambda x: int(x) if x.isdigit() else 10**9),
            "votes": {
                "with": v["with"],
                "without": v["without"],
                "unknown": v["unknown"],
                "total": v["total"]
            },
            "final_decision": final,
            "violation": bool(viol),
            "decision_rule": rule
        })

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("\n=== HELMET PER MASTER (FINAL) ===")
    print("Saved:", OUT_JSON)
    print("Masters:", len(out))
    for r in out[:25]:
        print(f"- {r['master_id']} tracks={r['tracks']} helmet={r['final_decision']} rule={r['decision_rule']} votes={r['votes']}")
if __name__ == "__main__":
    main()