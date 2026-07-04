import time
import subprocess
from pathlib import Path
import pandas as pd

# ====== SETTINGS ======
DATA_YAML = "datasets/helmet2/data.yaml"
MODEL = "yolov8s.pt"
EPOCHS = 200
IMGSZ = 640
BATCH = 8
DEVICE = "0"

TARGET_MAP5095 = 0.90   # غيّرها إذا بدك
CHECK_EVERY_SEC = 20
# ======================

def find_latest_results_csv(run_dir="runs/detect"):
    base = Path(run_dir)
    if not base.exists():
        return None
    csvs = sorted(base.glob("train*/results.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    return csvs[0] if csvs else None

def read_map5095(csv_path: Path):
    try:
        df = pd.read_csv(csv_path)
        # عمود YOLO عادة هي: metrics/mAP50-95(B)
        col = None
        for c in df.columns:
            if "mAP50-95" in c:
                col = c
                break
        if col is None or df.empty:
            return None
        return float(df[col].iloc[-1])
    except Exception:
        return None

def main():
    cmd = [
        "yolo", "detect", "train",
        f"model={MODEL}",
        f"data={DATA_YAML}",
        f"epochs={EPOCHS}",
        f"imgsz={IMGSZ}",
        f"batch={BATCH}",
        f"device={DEVICE}",
        "patience=25",
        "cos_lr=True",
        "optimizer=AdamW",
        "lr0=0.003",
        "warmup_epochs=3",
        "mosaic=0.7",
        "mixup=0.1",
        "cache=ram",
    ]

    p = subprocess.Popen(cmd)

    best_csv = None
    while p.poll() is None:
        time.sleep(CHECK_EVERY_SEC)
        csv_path = find_latest_results_csv()
        if not csv_path:
            continue
        if best_csv is None:
            best_csv = csv_path

        m = read_map5095(csv_path)
        if m is None:
            continue

        print(f"[monitor] mAP50-95 = {m:.4f}  (target={TARGET_MAP5095})")
        if m >= TARGET_MAP5095:
            print("[monitor] ✅ Target reached. Stopping training...")
            p.terminate()  # إيقاف طبيعي
            break

    print("Done. Check runs/detect/train*/weights/best.pt")
if __name__ == "__main__":
    main()