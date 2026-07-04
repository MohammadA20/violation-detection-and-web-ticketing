from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional
from pathlib import Path
import json
import uuid
from datetime import datetime, timedelta
import os
import secrets
import shutil
from jose import JWTError, jwt

app = FastAPI(title="Thesis Traffic Violations API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "violations.json"
AUDIT_PATH = BASE_DIR / "data" / "audit_log.json"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

RESULTS_DIR = r"D:\Violations_Detect_Web_Ticket\results"
app.mount("/results", StaticFiles(directory=RESULTS_DIR), name="results")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@12345")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret-key-2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()


class ViolationIn(BaseModel):
    plate: str
    violation_type: str
    timestamp: Optional[str] = None
    location: Optional[str] = None
    confidence: Optional[float] = None
    evidence_images: List[str] = Field(default_factory=list)


class Violation(ViolationIn):
    id: str
    status: str = "PENDING"
    admin_comment: Optional[str] = None
    objection_text: Optional[str] = None
    objection_evidence: Optional[str] = None
    objection_status: Optional[str] = None
    archived: bool = False


class StatusUpdate(BaseModel):
    status: str
    admin_comment: Optional[str] = None
    objection_status: Optional[str] = None


class ObjectionRequest(BaseModel):
    objection_text: str
    objection_evidence: Optional[str] = None


class ArchiveUpdate(BaseModel):
    archived: bool


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "admin"


class PaymentResponse(BaseModel):
    message: str
    violation: Violation


class StatsResponse(BaseModel):
    total: int
    pending: int
    approved: int
    rejected: int
    paid: int
    unpaid: int
    archived: int


def read_json_file(path: Path, default):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = default

    return data


def write_json_file(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def read_all() -> List[dict]:
    data = read_json_file(DATA_PATH, [])
    return data if isinstance(data, list) else []


def write_all(items: List[dict]) -> None:
    write_json_file(DATA_PATH, items)


def read_audit_log() -> List[dict]:
    data = read_json_file(AUDIT_PATH, [])
    return data if isinstance(data, list) else []


def write_audit_log(items: List[dict]) -> None:
    write_json_file(AUDIT_PATH, items)


def add_audit_log(action: str, actor: str, violation_id: Optional[str] = None, details: Optional[dict] = None):
    logs = read_audit_log()

    logs.append({
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "actor": actor,
        "action": action,
        "violation_id": violation_id,
        "details": details or {},
    })

    write_audit_log(logs)


def normalize_plate(plate: str) -> str:
    return plate.strip().upper()


def find_violation(items: List[dict], violation_id: str) -> Optional[dict]:
    for item in items:
        if item.get("id") == violation_id:
            return item
    return None


def normalize_existing_item(item: dict) -> dict:
    item.setdefault("admin_comment", None)
    item.setdefault("objection_text", None)
    item.setdefault("objection_evidence", None)
    item.setdefault("objection_status", None)
    item.setdefault("archived", False)
    return item


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "role": "admin"
    })

    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        return True

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.get("/")
def root():
    return {"status": "ok", "message": "Backend is running"}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/jpg"}

    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    ext = Path(file.filename).suffix.lower()
    safe_name = f"{uuid.uuid4()}{ext}"
    file_path = UPLOAD_DIR / safe_name

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "filename": safe_name,
        "url": f"http://127.0.0.1:8000/uploads/{safe_name}"
    }


@app.post("/api/auth/admin/login", response_model=AdminLoginResponse)
def admin_login(payload: AdminLoginRequest):
    valid_username = secrets.compare_digest(payload.username, ADMIN_USERNAME)
    valid_password = secrets.compare_digest(payload.password, ADMIN_PASSWORD)

    if not valid_username or not valid_password:
        add_audit_log(
            action="ADMIN_LOGIN_FAILED",
            actor=payload.username,
            details={"reason": "Invalid username or password"}
        )
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token({"sub": payload.username})

    add_audit_log(
        action="ADMIN_LOGIN_SUCCESS",
        actor=payload.username,
        details={"role": "admin"}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": "admin",
    }


@app.get("/api/audit-log")
def get_audit_log(admin: bool = Depends(require_admin)):
    return read_audit_log()


@app.get("/api/violations", response_model=List[Violation])
def list_violations(include_archived: bool = False):
    items = [normalize_existing_item(item) for item in read_all()]

    if include_archived:
        return items

    return [item for item in items if not item.get("archived", False)]


@app.get("/api/violations/{violation_id}", response_model=Violation)
def get_violation(violation_id: str):
    items = [normalize_existing_item(item) for item in read_all()]
    violation = find_violation(items, violation_id)

    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")

    return violation


@app.get("/api/owner/{plate}/violations", response_model=List[Violation])
def get_owner_violations(plate: str, include_archived: bool = True):
    items = [normalize_existing_item(item) for item in read_all()]
    target_plate = normalize_plate(plate)

    owner_items = [
        item for item in items
        if normalize_plate(item.get("plate", "")) == target_plate
    ]

    if include_archived:
        return owner_items

    return [item for item in owner_items if not item.get("archived", False)]


@app.post("/api/violations", response_model=Violation)
def create_violation(v: ViolationIn):
    items = read_all()

    new_item = v.model_dump()
    new_item["plate"] = normalize_plate(new_item["plate"])
    new_item["id"] = str(uuid.uuid4())
    new_item["status"] = "PENDING"
    new_item["admin_comment"] = None
    new_item["objection_text"] = None
    new_item["objection_evidence"] = None
    new_item["objection_status"] = None
    new_item["archived"] = False

    if not new_item.get("timestamp"):
        new_item["timestamp"] = datetime.now().isoformat(timespec="seconds")

    items.append(new_item)
    write_all(items)

    add_audit_log(
        action="VIOLATION_CREATED",
        actor="system",
        violation_id=new_item["id"],
        details={
            "plate": new_item["plate"],
            "violation_type": new_item["violation_type"],
            "status": new_item["status"],
        }
    )

    return new_item


@app.patch("/api/violations/{violation_id}", response_model=Violation)
def update_violation_status(
    violation_id: str,
    payload: StatusUpdate,
    admin: bool = Depends(require_admin),
):
    allowed_statuses = {"PENDING", "APPROVED", "REJECTED", "PAID"}
    allowed_objection_statuses = {"PENDING_REVIEW", "ACCEPTED", "REJECTED"}

    status = payload.status.upper()

    if status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    items = read_all()
    violation = find_violation(items, violation_id)

    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")

    normalize_existing_item(violation)

    old_status = violation.get("status")
    old_objection_status = violation.get("objection_status")

    violation["status"] = status
    violation["admin_comment"] = payload.admin_comment

    if payload.objection_status:
        objection_status = payload.objection_status.upper()

        if objection_status not in allowed_objection_statuses:
            raise HTTPException(status_code=400, detail="Invalid objection status")

        violation["objection_status"] = objection_status

    if status == "PAID":
        violation["archived"] = True

    write_all(items)

    add_audit_log(
        action="VIOLATION_STATUS_UPDATED",
        actor="admin",
        violation_id=violation_id,
        details={
            "old_status": old_status,
            "new_status": violation["status"],
            "old_objection_status": old_objection_status,
            "new_objection_status": violation.get("objection_status"),
            "admin_comment": payload.admin_comment,
            "archived": violation.get("archived", False),
        }
    )

    return violation


@app.patch("/api/violations/{violation_id}/archive", response_model=Violation)
def update_archive_status(
    violation_id: str,
    payload: ArchiveUpdate,
    admin: bool = Depends(require_admin),
):
    items = read_all()
    violation = find_violation(items, violation_id)

    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")

    normalize_existing_item(violation)

    old_archived = violation.get("archived", False)
    violation["archived"] = payload.archived

    write_all(items)

    add_audit_log(
        action="ARCHIVE_STATUS_UPDATED",
        actor="admin",
        violation_id=violation_id,
        details={
            "old_archived": old_archived,
            "new_archived": payload.archived,
        }
    )

    return violation


@app.post("/api/violations/{violation_id}/pay", response_model=PaymentResponse)
def pay_violation(violation_id: str):
    items = read_all()
    violation = find_violation(items, violation_id)

    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")

    normalize_existing_item(violation)

    if violation.get("status") != "APPROVED":
        raise HTTPException(
            status_code=400,
            detail="Payment allowed only after approval"
        )

    violation["status"] = "PAID"
    violation["archived"] = True
    write_all(items)

    add_audit_log(
        action="VIOLATION_PAID",
        actor="owner",
        violation_id=violation_id,
        details={
            "plate": violation.get("plate"),
            "status": "PAID",
            "archived": True,
        }
    )

    return {
        "message": "Payment successful",
        "violation": violation,
    }


@app.post("/api/violations/{violation_id}/object")
def submit_objection(violation_id: str, payload: ObjectionRequest):
    items = read_all()
    violation = find_violation(items, violation_id)

    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")

    normalize_existing_item(violation)

    if violation.get("status") != "APPROVED":
        raise HTTPException(
            status_code=400,
            detail="Only approved violations can be disputed"
        )

    violation["objection_text"] = payload.objection_text
    violation["objection_evidence"] = payload.objection_evidence
    violation["objection_status"] = "PENDING_REVIEW"

    write_all(items)

    add_audit_log(
        action="OWNER_SUBMITTED_OBJECTION",
        actor="owner",
        violation_id=violation_id,
        details={
            "plate": violation.get("plate"),
            "objection_text": payload.objection_text,
            "has_evidence": bool(payload.objection_evidence),
            "objection_status": "PENDING_REVIEW",
        }
    )

    return {
        "message": "Objection submitted successfully",
        "violation": violation
    }


@app.get("/api/stats", response_model=StatsResponse)
def get_stats():
    items = [normalize_existing_item(item) for item in read_all()]
    active_items = [item for item in items if not item.get("archived", False)]

    total = len(active_items)
    pending = len([item for item in active_items if item.get("status") == "PENDING"])
    approved = len([item for item in active_items if item.get("status") == "APPROVED"])
    rejected = len([item for item in active_items if item.get("status") == "REJECTED"])
    paid = len([item for item in active_items if item.get("status") == "PAID"])
    unpaid = total - paid
    archived = len([item for item in items if item.get("archived", False)])

    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "paid": paid,
        "unpaid": unpaid,
        "archived": archived,
    }


# ================= AI FINAL REPORT =================

AI_RESULTS_PATH = Path(
    r"D:\Violations_Detect_Web_Ticket\results\final_report.json"
)


@app.get("/api/ai/final-report")
def get_ai_final_report():
    if not AI_RESULTS_PATH.exists():
        return {
            "cars": [],
            "motorcycles": []
        }

    try:
        data = json.loads(
            AI_RESULTS_PATH.read_text(encoding="utf-8")
        )

        return data

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ================= IMPORT AI FINAL REPORT TO VIOLATIONS =================

def ai_make_violation(
    plate,
    violation_type,
    confidence=None,
    details=None,
    evidence_images=None,
):
    fixed_images = []

    for img in (evidence_images or []):
        if not img:
            continue

        img = str(img).replace("\\", "/")

        if img.startswith("http://") or img.startswith("https://"):
            fixed_images.append(img)
        else:
            fixed_images.append(f"http://127.0.0.1:8000{img}")

    return {
        "plate": normalize_plate(plate),
        "violation_type": violation_type,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "location": "AI Detection Video",
        "confidence": confidence,
        "evidence_images": fixed_images,
        "id": str(uuid.uuid4()),
        "status": "PENDING",
        "admin_comment": None,
        "objection_text": None,
        "objection_evidence": None,
        "objection_status": None,
        "archived": False,
        "ai_details": details or {},
    }

def ai_duplicate_exists(items, plate, violation_type, master_id, run_id):
    plate = normalize_plate(plate)

    for item in items:
        same_plate = normalize_plate(item.get("plate", "")) == plate
        same_type = item.get("violation_type") == violation_type

        details = item.get("ai_details", {}) or {}

        same_master = details.get("master_id") == master_id
        same_run = details.get("run_id") == run_id

        if same_plate and same_type and same_master and same_run:
            return True

    return False


@app.post("/api/ai/import-final-report")
def import_ai_final_report(admin: bool = Depends(require_admin)):
    if not AI_RESULTS_PATH.exists():
        raise HTTPException(status_code=404, detail="final_report.json not found")

    try:
        report = json.loads(AI_RESULTS_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    items = read_all()
    created = []
    run_id = report.get("run_id")
    for car in report.get("cars", []):
        plate = car.get("plate", {}).get("value", "UNKNOWN")

        if not plate or plate == "UNKNOWN":
            continue

        speed = car.get("speed", {}) or {}
        seatbelt = car.get("seatbelt", {}) or {}
        phone = car.get("phone", {}) or {}
        master_id = car.get("master_id")
        evidence = car.get("evidence", {}) or {}
        seatbelt_img = evidence.get("seatbelt_image")
        phone_img = evidence.get("phone_image")

        if speed.get("violation") is True:
            violation_type = "SPEEDING"

            if not ai_duplicate_exists(
                items,
                plate,
                violation_type,
                master_id,
                run_id
            ):
                v = ai_make_violation(
                    plate=plate,
                    violation_type=violation_type,
                    confidence=car.get("confidence"),
                    evidence_images=[seatbelt_img] if seatbelt_img else [],
                    details={
                        "source": "AI",
                        "run_id": run_id,
                        "speed": speed,
                        "master_id": master_id,
                        "tracks": car.get("tracks", []),
                    },
                )
                items.append(v)
                created.append(v)

        if seatbelt.get("violation") is True:
            violation_type = "NO_SEATBELT"

            if not ai_duplicate_exists(
                items,
                plate,
                violation_type,
                master_id,
                run_id
            ):
                v = ai_make_violation(
                    plate=plate,
                    violation_type=violation_type,
                    evidence_images=[seatbelt_img] if seatbelt_img else [],
                    confidence=car.get("confidence"),
                    
                    details={
                        "source": "AI",
                        "run_id": run_id,
                        "speed": speed,
                        "master_id": master_id,
                        "tracks": car.get("tracks", []),
                    },
                )
                items.append(v)
                created.append(v)

        if phone.get("violation") is True:
            violation_type = "PHONE_USAGE"

            if not ai_duplicate_exists(
                items,
                plate,
                violation_type,
                master_id,
                run_id
            ):
                v = ai_make_violation(
                    plate=plate,
                    violation_type=violation_type,
                    confidence=car.get("confidence"),
                    evidence_images=[phone_img] if phone_img else [],
                    details={
                        "source": "AI",
                        "run_id": run_id,
                        "speed": speed,
                        "master_id": master_id,
                        "tracks": car.get("tracks", []),
                    },
                )
                items.append(v)
                created.append(v)

    for moto in report.get("motorcycles", []):
        plate = moto.get("plate", {}).get("value", "UNKNOWN")

        if not plate or plate == "UNKNOWN":
            continue

        speed = moto.get("speed", {}) or {}
        helmet = moto.get("helmet", {}) or {}
        master_id = moto.get("master_id")
        evidence = moto.get("evidence", {}) or {}
        helmet_img = evidence.get("helmet_image")

        if speed.get("violation") is True:
            violation_type = "SPEEDING_MOTORCYCLE"

            if not ai_duplicate_exists(
                items,
                plate,
                violation_type,
                master_id,
                run_id
            ):
                v = ai_make_violation(
                    plate=plate,
                    violation_type=violation_type,
                    confidence=moto.get("confidence"),
                    evidence_images=[helmet_img] if helmet_img else [],
                    details={
                        "source": "AI",
                        "run_id": run_id,
                        "speed": speed,
                        "master_id": master_id,
                        "tracks": moto.get("tracks", []),
                    },
                )
                items.append(v)
                created.append(v)

        if helmet.get("violation") is True:
            violation_type = "NO_HELMET"

            helmet_img = evidence.get("helmet_image")
            helmet_conf = helmet.get("confidence")

            if not ai_duplicate_exists(
                items,
                plate,
                violation_type,
                master_id,
                run_id
            ):
                v = ai_make_violation(
                    plate=plate,
                    violation_type=violation_type,
                    confidence=helmet_conf,
                    evidence_images=[helmet_img] if helmet_img else [],
                    details={
                        "source": "AI",
                        "run_id": run_id,
                        "speed": speed,
                        "helmet": helmet,
                        "master_id": master_id,
                        "tracks": moto.get("tracks", []),
                        "evidence": evidence,
                    },
                )
                items.append(v)
                created.append(v)

    write_all(items)

    add_audit_log(
        action="AI_FINAL_REPORT_IMPORTED",
        actor="admin",
        details={
            "created_count": len(created)
        }
    )

    return {
        "message": "AI final report imported successfully",
        "created_count": len(created),
        "created": created,
    }