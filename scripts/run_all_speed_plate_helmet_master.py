# scripts/run_all_video.py
import os
import sys
import subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]

# --- paths to python in venvs ---
VENV_PY     = PROJECT_DIR / "venv" / "Scripts" / "python.exe"
VENV_OCR_PY = PROJECT_DIR / "venv_ocr" / "Scripts" / "python.exe"

# --- scripts ---
SPEED_SCRIPT        = PROJECT_DIR / "scripts" / "speed_depth_output.py"
PLATE_EXPORT_SCRIPT = PROJECT_DIR / "scripts" / "plate_per_car_export.py"
PLATE_OCR_SCRIPT    = PROJECT_DIR / "scripts" / "paddle_plate_vote_per_car.py"

MASTER_CAR_EXPORT   = PROJECT_DIR / "scripts" / "master_car_export.py"
MASTER_ID_LINK      = PROJECT_DIR / "scripts" / "master_id_embed_link.py"

HELMET_PER_MOTO     = PROJECT_DIR / "scripts" / "helmet_per_moto_from_speed.py"
HELMET_MASTERBOARD  = PROJECT_DIR / "scripts" / "helmet_masterboard_vote.py"

INTEGRATION_SCRIPT  = PROJECT_DIR / "scripts" / "integration_speed_plate_helmet_master.py"


def run_step(title: str, cmd: list[str], env: dict):
    print("\n" + "=" * 70)
    print(f"RUNNING: {title}")
    print("CMD:", " ".join(cmd))
    print("=" * 70)

    r = subprocess.run(cmd, env=env)
    if r.returncode != 0:
        print(f"[FAILED] {title} (exit code {r.returncode})")
        sys.exit(r.returncode)

    print(f"[OK] {title} finished")


def resolve_video_path(video_path: str) -> str:
    """
    Accepts:
      - relative path like test_videos/test3.mp4
      - absolute path like D:\\...\\test3.mp4
    Returns absolute Windows path (with backslashes).
    """
    p = Path(video_path)

    # if user provided relative path, resolve relative to PROJECT_DIR
    if not p.is_absolute():
        p = (PROJECT_DIR / p).resolve()
    else:
        p = p.resolve()

    # convert to windows-style string
    return str(p)


def main():
    # usage:
    # python scripts/run_all_video.py test_videos/test3.mp4
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_all_video.py <video_path>")
        print("Example: python scripts/run_all_video.py test_videos/test3.mp4")
        sys.exit(1)

    video_path = sys.argv[1]
    video_abs = resolve_video_path(video_path)

    if not Path(video_abs).exists():
        print("[ERROR] Video not found:", video_abs)
        sys.exit(1)

    # env with VIDEO_PATH injected
    env = os.environ.copy()
    env["VIDEO_PATH"] = video_abs
    env["PYTHONUTF8"] = "1"   # avoid console encoding issues on Windows

    # 1) speed
    run_step("Speed", [str(VENV_PY), str(SPEED_SCRIPT)], env)

    # 2) plate export
    run_step("Plate per-car export", [str(VENV_PY), str(PLATE_EXPORT_SCRIPT)], env)

    # 3) OCR vote (venv_ocr)
    run_step("Plate OCR per-car vote (PaddleOCR)", [str(VENV_OCR_PY), str(PLATE_OCR_SCRIPT)], env)

    # 4) master car export
    run_step("Master car export (crops)", [str(VENV_PY), str(MASTER_CAR_EXPORT)], env)

    # 5) master id embed link
    run_step("Master ID embedding link", [str(VENV_PY), str(MASTER_ID_LINK)], env)

    # 6) helmet per moto from speed
    run_step("Helmet per moto (from speed)", [str(VENV_PY), str(HELMET_PER_MOTO)], env)

    # 7) helmet per master
    run_step("Helmet Masterboard (per master)", [str(VENV_PY), str(HELMET_MASTERBOARD)], env)

    # 8) integration
    run_step("Integration (MASTER + Speed + Plate + Helmet)", [str(VENV_PY), str(INTEGRATION_SCRIPT)], env)

    print("\n✅ DONE: run_all_video finished successfully.")
if __name__ == "__main__":
    main()