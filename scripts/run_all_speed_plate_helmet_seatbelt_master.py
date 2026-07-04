import os
import sys
import subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]

def pick_venv_python(venv_dir: Path) -> Path:
    """
    Windows: venv/Scripts/python.exe
    Linux/macOS: venv/bin/python
    """
    cand_win = venv_dir / "Scripts" / "python.exe"
    cand_nix = venv_dir / "bin" / "python"
    if cand_win.exists():
        return cand_win
    if cand_nix.exists():
        return cand_nix
    raise FileNotFoundError(f"Cannot find python in venv: {venv_dir}")

# --- paths to python in venvs ---
VENV_PY     = pick_venv_python(PROJECT_DIR / "venv")
VENV_OCR_PY = pick_venv_python(PROJECT_DIR / "venv_ocr")

# --- scripts ---
SPEED_SCRIPT        = PROJECT_DIR / "scripts" / "speed_depth_output.py"
PLATE_EXPORT_SCRIPT = PROJECT_DIR / "scripts" / "plate_per_car_export.py"
PLATE_OCR_SCRIPT    = PROJECT_DIR / "scripts" / "paddle_plate_vote_per_car.py"

MASTER_CAR_EXPORT   = PROJECT_DIR / "scripts" / "master_car_export.py"
MASTER_ID_LINK      = PROJECT_DIR / "scripts" / "master_id_embed_link.py"

HELMET_PER_MOTO     = PROJECT_DIR / "scripts" / "helmet_per_moto_from_speed.py"
HELMET_MASTERBOARD  = PROJECT_DIR / "scripts" / "helmet_masterboard_vote.py"

# ✅ NEW seatbelt step ( لازم يكون عندك هالملف )
SEATBELT_PER_CAR_SCRIPT = PROJECT_DIR / "scripts" / "seatbelt_per_car_from_speed.py"

# ✅ NEW integration (اللي عملناه: speed + plate + helmet + seatbelt)
INTEGRATION_SCRIPT  = PROJECT_DIR / "scripts" / "integration_speed_plate_helmet_seatbelt_master.py"


def run_step(title: str, cmd: list[str], env: dict):
    print("\n" + "=" * 70)
    print(f"RUNNING: {title}")
    print("CMD:", " ".join(cmd))
    print("=" * 70)

    r = subprocess.run(cmd, env=env, cwd=str(PROJECT_DIR))
    if r.returncode != 0:
        print(f"[FAILED] {title} (exit code {r.returncode})")
        sys.exit(r.returncode)

    print(f"[OK] {title} finished")


def main():
    # usage:
    # python scripts/run_all_video.py test_videos/test3.mp4
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_all_video.py <video_path>")
        print("Example: python scripts/run_all_video.py test_videos/test3.mp4")
        sys.exit(1)

    video_path_arg = sys.argv[1]
    vp = Path(video_path_arg)

    if vp.is_absolute():
        video_abs = str(vp)
    else:
        cand = (PROJECT_DIR / vp)
        if cand.exists():
            video_abs = str(cand.resolve())
        else:
            # fallback: relative to current working dir
            video_abs = str(vp.resolve())

    if not Path(video_abs).exists():
        print(f"[ERROR] Video not found: {video_abs}")
        sys.exit(2)

    # env with VIDEO_PATH injected
    env = os.environ.copy()
    env["VIDEO_PATH"] = video_abs

    print("\n" + "=" * 70)
    print("PROJECT_DIR:", PROJECT_DIR)
    print("VIDEO_PATH :", video_abs)
    print("=" * 70)

    # 1) speed
    run_step("1) Speed", [str(VENV_PY), str(SPEED_SCRIPT)], env)

    # 2) plate export
    run_step("2) Plate per-car export", [str(VENV_PY), str(PLATE_EXPORT_SCRIPT)], env)

    # 3) OCR vote (venv_ocr)
    run_step("3) Plate OCR per-car vote (PaddleOCR)", [str(VENV_OCR_PY), str(PLATE_OCR_SCRIPT)], env)

    # 4) master car export
    run_step("4) Master car export (crops)", [str(VENV_PY), str(MASTER_CAR_EXPORT)], env)

    # 5) master id embed link
    run_step("5) Master ID embedding link", [str(VENV_PY), str(MASTER_ID_LINK)], env)

    # 6) helmet per moto from speed
    run_step("6) Helmet per moto (from speed)", [str(VENV_PY), str(HELMET_PER_MOTO)], env)

    # 7) helmet per master
    run_step("7) Helmet Masterboard (per master)", [str(VENV_PY), str(HELMET_MASTERBOARD)], env)

    # 8) ✅ seatbelt per car (from speed)
    run_step("8) Seatbelt per car (from speed)", [str(VENV_PY), str(SEATBELT_PER_CAR_SCRIPT)], env)

    # 9) ✅ integration (MASTER + Speed + Plate + Helmet + Seatbelt)
    run_step("9) Integration (MASTER + Speed + Plate + Helmet + Seatbelt)",
             [str(VENV_PY), str(INTEGRATION_SCRIPT)], env)

    print("\n✅ DONE: run_all_video finished successfully.")
if __name__ == "__main__":
    main()