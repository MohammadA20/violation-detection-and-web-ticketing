import subprocess
from pathlib import Path
import sys

PROJECT_DIR = Path(__file__).resolve().parents[1]

SPEED_SCRIPT        = "scripts/speed_depth_output.py"
PLATE_EXPORT_SCRIPT = "scripts/plate_per_car_export.py"
PLATE_OCR_SCRIPT    = "scripts/paddle_plate_vote_per_car.py"   # (venv_ocr)

MASTER_CAR_EXPORT   = "scripts/master_car_export.py"
MASTER_ID_EMBED     = "scripts/master_id_embed_link.py"

INTEGRATION_SCRIPT  = "scripts/integration_speed_plate_master.py"

VENV_PY     = PROJECT_DIR / "venv" / "Scripts" / "python.exe"
VENV_OCR_PY = PROJECT_DIR / "venv_ocr" / "Scripts" / "python.exe"

def run_cmd(title, cmd):
    print("\n" + "=" * 70)
    print("RUNNING:", title)
    print("CMD:", " ".join(str(x) for x in cmd))
    print("=" * 70 + "\n")
    res = subprocess.run(cmd, cwd=str(PROJECT_DIR))
    if res.returncode != 0:
        print(f"[FAILED] {title} (exit code {res.returncode})")
        sys.exit(1)
    print(f"[OK] {title} finished")

def main():
    run_cmd("Speed", [str(VENV_PY), SPEED_SCRIPT])
    run_cmd("Plate per-car export", [str(VENV_PY), PLATE_EXPORT_SCRIPT])
    run_cmd("Plate OCR per-car vote (PaddleOCR)", [str(VENV_OCR_PY), PLATE_OCR_SCRIPT])

    run_cmd("Master car export (crops)", [str(VENV_PY), MASTER_CAR_EXPORT])
    run_cmd("Master ID embedding link", [str(VENV_PY), MASTER_ID_EMBED])

    run_cmd("Integration (MASTER + Speed + Plate)", [str(VENV_PY), INTEGRATION_SCRIPT])

    print("\n✅ DONE: run_all_speed_plate_master finished successfully.")

if __name__ == "__main__":
    main()
