# scripts/run_all_video_seatbelt_phone.py
import os
import sys
import subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]

VENV_PY     = PROJECT_DIR / "venv" / "Scripts" / "python.exe"
VENV_OCR_PY = PROJECT_DIR / "venv_ocr" / "Scripts" / "python.exe"

SPEED_SCRIPT        = PROJECT_DIR / "scripts" / "speed_depth_output.py"
PLATE_EXPORT_SCRIPT = PROJECT_DIR / "scripts" / "plate_per_car_export.py"
PLATE_OCR_SCRIPT    = PROJECT_DIR / "scripts" / "paddle_plate_vote_per_car.py"

MASTER_CAR_EXPORT   = PROJECT_DIR / "scripts" / "master_car_export.py"
MASTER_ID_LINK      = PROJECT_DIR / "scripts" / "master_id_embed_link.py"

HELMET_PER_MOTO     = PROJECT_DIR / "scripts" / "helmet_per_moto_from_speed.py"
HELMET_MASTERBOARD  = PROJECT_DIR / "scripts" / "helmet_masterboard_vote.py"

# V5 base integration (speed+plate+helmet)
BASE_INTEGRATION    = PROJECT_DIR / "scripts" / "integration_speed_plate_helmet_master.py"

# seatbelt + phone
SEATBELT_SCRIPT     = PROJECT_DIR / "scripts" / "seatbelt_per_car_from_speed.py"
PHONE_SCRIPT        = PROJECT_DIR / "scripts" / "phone_per_car_from_speed.py"

# new add-on integration
ADDON_INTEGRATION   = PROJECT_DIR / "scripts" / "integration_speed_plate_helmet_seatbelt_phone_master.py"

def run_step(title: str, cmd: list[str], env: dict):
    print("\n" + "=" * 80)
    print(f"RUNNING: {title}")
    print("CMD:", " ".join(cmd))
    print("=" * 80)
    r = subprocess.run(cmd, env=env)
    if r.returncode != 0:
        print(f"[FAILED] {title} (exit code {r.returncode})")
        sys.exit(r.returncode)
    print(f"[OK] {title} finished")

def main():
    # usage:
    # python scripts/run_all_video_seatbelt_phone.py test_videos/test3.mp4
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_all_video_seatbelt_phone.py <video_path>")
        sys.exit(1)

    video_path = sys.argv[1]
    video_abs = str((PROJECT_DIR / video_path).resolve()) if not Path(video_path).is_absolute() else video_path

    env = os.environ.copy()
    env["VIDEO_PATH"] = video_abs

    run_step("Speed", [str(VENV_PY), str(SPEED_SCRIPT)], env)
    run_step("Plate per-car export", [str(VENV_PY), str(PLATE_EXPORT_SCRIPT)], env)
    run_step("Plate OCR per-car vote (PaddleOCR)", [str(VENV_OCR_PY), str(PLATE_OCR_SCRIPT)], env)

    run_step("Master car export (crops)", [str(VENV_PY), str(MASTER_CAR_EXPORT)], env)
    run_step("Master ID embedding link", [str(VENV_PY), str(MASTER_ID_LINK)], env)

    run_step("Helmet per moto (from speed)", [str(VENV_PY), str(HELMET_PER_MOTO)], env)
    run_step("Helmet Masterboard (per master)", [str(VENV_PY), str(HELMET_MASTERBOARD)], env)

    # base integration V5 output -> results/final_report.json
    run_step("Base Integration V5 (MASTER + Speed + Plate + Helmet)", [str(VENV_PY), str(BASE_INTEGRATION)], env)

    # seatbelt + phone
    
    run_step("Phone per car (from speed)", [str(VENV_PY), str(PHONE_SCRIPT)], env)
    run_step("Seatbelt per car (from speed)", [str(VENV_PY), str(SEATBELT_SCRIPT)], env)

    # add-on integration -> results/final_report_seatbelt_phone.json
    run_step("ADD-ON Integration (Seatbelt + Phone) on top of V5", [str(VENV_PY), str(ADDON_INTEGRATION)], env)

    print("\n✅ DONE: run_all_video_seatbelt_phone finished successfully.")
    print("Check:")
    print("- results/final_report.json (base V5)")
    print("- results/final_report_seatbelt_phone.json (with seatbelt + phone)")

if __name__ == "__main__":
    main()