# scripts/master_keyframes_bridge.py
import json
from pathlib import Path

RESULTS_DIR = Path("results")
SRC = RESULTS_DIR / "master_car_tracks.json"
OUT = RESULTS_DIR / "master_keyframes.json"

def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if not SRC.exists():
        raise FileNotFoundError(f"Missing: {SRC} (run master_car_export.py first)")

    data = json.loads(SRC.read_text(encoding="utf-8"))
    tracks = data.get("tracks", [])
    if not isinstance(tracks, list):
        raise RuntimeError("master_car_tracks.json: 'tracks' must be a list")

    keyframes = []
    for t in tracks:
        if not isinstance(t, dict):
            continue
        tid = t.get("track_id", None)
        imgs = t.get("images", [])
        if tid is None or not isinstance(imgs, list):
            continue

        for im in imgs:
            if not isinstance(im, dict):
                continue
            img_path = im.get("img_path")
            if not img_path:
                continue
            # optional fields
            ts = float(im.get("timestamp_sec", 0.0))
            bbox = im.get("bbox_xyxy", None)
            # cls_id not available here, keep None (helmet script should handle)
            keyframes.append({
                "track_id": int(tid),
                "timestamp_sec": round(ts, 3),
                "bbox_xyxy": bbox,
                "crop_path": str(img_path).replace("\\", "/"),
                "cls_id": None
            })

    OUT.write_text(json.dumps({"video": data.get("video", ""), "keyframes": keyframes}, indent=2), encoding="utf-8")
    print("Saved:", OUT)
    print("Source:", SRC)
    print("Keyframes:", len(keyframes))

if __name__ == "__main__":
    main()
