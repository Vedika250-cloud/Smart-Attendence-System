import base64
import cv2
import numpy as np

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models import *
from app.ai.face_engine import FaceEngine
from app.ai.liveness import LivenessDetector
from app.services.attendance import mark_attendance
from app.config import RECOGNITION_THRESHOLD, LIVENESS_REQUIRED


router = APIRouter(prefix="/api")

_engine = FaceEngine()

# Memory stores for rate limiting and live processing
_liveness = {}
_registration_embeddings = {}

# Dictionary to track unknown faces during an attendance session
# Format: session_id -> { "unknown_id": embedding, ... }
_unknown_faces_session = {}
_unknown_counter = {}

# Dictionary to track if a session is currently registering an unknown person
# Format: session_id -> { "unknown_id": id, "embeddings": [], "liveness": LivenessDetector() }
_registration_mode = {}


def require_auth(request):
    if not request.session.get("user_id"):
        raise HTTPException(401, "Login required")


def decode_image(data):
    if "," in data:
        data = data.split(",", 1)[1]

    raw = base64.b64decode(data)
    print(f"[4 IMAGE DECODE] Base64 length = {len(data)}")

    frame = cv2.imdecode(
        np.frombuffer(raw, np.uint8),
        cv2.IMREAD_COLOR
    )

    if frame is None:
        print("[4 IMAGE DECODE] Failed to decode image")
        raise ValueError("Invalid camera frame")
        
    print(f"[4 IMAGE DECODE] success, shape={frame.shape}")
    
    if not hasattr(decode_image, "saved"):
        cv2.imwrite("debug_backend_frame.jpg", frame)
        print("[4 IMAGE DECODE] Saved debug_backend_frame.jpg")
        decode_image.saved = True

    return frame


# =========================================================
# STUDENT FACE REGISTRATION
# =========================================================

@router.post("/students/{student_id}/face-capture")
def face_capture(
    request: Request,
    student_id: int,
    payload: dict,
    db: Session = Depends(get_db)
):
    require_auth(request)

    s = db.get(Student, student_id)

    if not s:
        raise HTTPException(404, "Student not found")

    try:
        frame = decode_image(payload["image"])

    except Exception as e:
        raise HTTPException(400, str(e))

    faces = _engine.detect_faces(frame)
    is_liveness_active = f"reg-{student_id}" in _liveness

    if len(faces) != 1:
        if not is_liveness_active:
            return {
                "ok": False,
                "stage": "Face Detection",
                "message": "Exactly one face must be visible.",
                "count": len(faces)
            }
        else:
            # OpenCV missed the face, but liveness is active.
            # Let MediaPipe try to track it.
            box = None
            quality = {"ok": True, "reason": "Skipped (Liveness active)", "crop": frame}
    else:
        box = faces[0]
        quality = _engine.quality_check(frame, box)
        if not quality["ok"]:
            return {
                "ok": False,
                "stage": "Face Quality",
                "message": quality["reason"]
            }

    # -----------------------------------------------------
    # LIVENESS
    # -----------------------------------------------------
    live = _liveness.setdefault(
        f"reg-{student_id}",
        LivenessDetector()
    ).check(frame, box)

    # Initialize or get registration state
    reg_embs = _registration_embeddings.setdefault(f"reg-{student_id}", [])
    
    if live.get("message", "").startswith("⚠ Liveness failed"):
        _liveness.pop(f"reg-{student_id}", None)
        _registration_embeddings.pop(f"reg-{student_id}", None)
        return {
            "ok": False,
            "stage": "Liveness Failed",
            "message": "Registration timed out (possible spoof). Please try again.",
            "progress": 0
        }

    TARGET_SAMPLES = 5

    if not live["live"]:
        return {
            "ok": False,
            "stage": "Liveness Verification",
            "challenge": live.get("challenge", ""),
            "message": live["message"],
            "progress": live.get("progress", "0/2")
        }

    # -----------------------------------------------------
    # LIVENESS PASSED -> GENERATE EMBEDDING
    # -----------------------------------------------------
    
    if box is None:
        return {
            "ok": False,
            "stage": "Face Detection",
            "message": "Liveness verified. Please face the camera directly.",
            "progress": live.get("progress", 0)
        }

    # Extract crop using the new crop returned by quality_check
    crop = quality.get("crop")
    if crop is None: # fallback if crop not in quality
        x, y, w, h = [int(v) for v in box]
        crop = frame[y:y + h, x:x + w]

    try:
        emb = _engine.represent_embedding(crop)
    except Exception as e:
        return {
            "ok": False,
            "stage": "Recognition",
            "message": str(e)
        }
        
    # Add to our collection of embeddings
    reg_embs.append(emb)
    
    if len(reg_embs) < TARGET_SAMPLES:
        return {
            "ok": False,
            "stage": "Face Registration",
            "message": f"Liveness Verified. Capturing sample {len(reg_embs)}/{TARGET_SAMPLES}...",
            "progress": live.get("progress", 0)
        }

    # We have enough samples AND liveness passed
    try:
        final_emb = _engine.average_embeddings(reg_embs)
    except Exception as e:
        _liveness.pop(f"reg-{student_id}", None)
        _registration_embeddings.pop(f"reg-{student_id}", None)
        return {
            "ok": False,
            "stage": "Registration",
            "message": "Failed to average embeddings: " + str(e)
        }

    from app.ai.face_engine import FaceEngine as FE
    
    existing = db.scalar(select(FaceData).where(FaceData.student_id == student_id))

    if existing:
        existing.face_embedding = FE.embedding_to_blob(final_emb)
        existing.embedding_model = _engine.model_name
        existing.registration_date = (
            __import__("datetime")
            .datetime.now()
            .strftime("%Y-%m-%d")
        )
        existing.status = "Active"

    else:
        db.add(
            FaceData(
                student_id=s.student_id,
                face_embedding=FE.embedding_to_blob(final_emb),
                embedding_model=_engine.model_name,
                registration_date=(
                    __import__("datetime")
                    .datetime.now()
                    .strftime("%Y-%m-%d")
                ),
                status="Active"
            )
        )

    db.commit()

    _liveness.pop(f"reg-{student_id}", None)
    _registration_embeddings.pop(f"reg-{student_id}", None)

    return {
        "ok": True,
        "stage": "Face Registration",
        "message": "Facial embedding saved securely.",
        "samples_used": len(reg_embs),
        "liveness": "Passed"
    }


# =========================================================
# LIVE ATTENDANCE PROCESSING
# =========================================================

@router.post("/attendance/{session_id}/process-frame")
def process_frame(
    request: Request,
    session_id: int,
    payload: dict,
    db: Session = Depends(get_db)
):
    require_auth(request)

    session = db.get(
        AttendanceSession,
        session_id
    )

    if not session or session.status != "Active":
        return {
            "ok": False,
            "stage": "Session",
            "message": "Session is not active.",
            "decision": "rejected"
        }

    try:
        frame = decode_image(payload["image"])

    except Exception as e:
        return {
            "ok": False,
            "stage": "Camera",
            "message": str(e),
            "decision": "rejected"
        }


    # -----------------------------------------------------
    # FACE DETECTION
    # -----------------------------------------------------

    faces = _engine.detect_faces(frame)
    is_liveness_active = f"session-{session_id}" in _liveness

    if len(faces) == 0:
        if not is_liveness_active:
            return {
                "ok": False,
                "stage": "Face Detection",
                "message": "No face detected.",
                "decision": "waiting"
            }
        else:
            box = None
            quality = {"ok": True, "reason": "Skipped (Liveness active)", "crop": frame}
            
    elif len(faces) > 1:
        return {
            "ok": False,
            "stage": "Face Detection",
            "message": (
                "Multiple faces detected. Please allow only one student in front of the camera."
            ),
            "decision": "rejected"
        }
    else:
        box = faces[0]
        quality = _engine.quality_check(frame, box)
        if not quality["ok"]:
            return {
                "ok": False,
                "stage": "Face Quality",
                "message": quality["reason"],
                "decision": "rejected"
            }


    import logging

    # -----------------------------------------------------
    # LIVENESS
    # -----------------------------------------------------
    live = _liveness.setdefault(
        f"session-{session_id}",
        LivenessDetector()
    ).check(frame, box)

    if live.get("message", "").startswith("⚠ Liveness failed"):
        _liveness.pop(f"session-{session_id}", None)
        logging.warning("Liveness Failed: Challenge timed out. Possible spoof.")
        return {
            "ok": False,
            "stage": "Liveness Failed",
            "message": "Possible photo/video detected. Please use the camera directly.",
            "decision": "rejected"
        }

    if LIVENESS_REQUIRED and not live["live"]:
        # We don't log every frame of a running challenge as it would spam the logs
        return {
            "ok": False,
            "stage": "Liveness Verification",
            "challenge": live.get("challenge", ""),
            "message": live.get("message", live.get("reason", "")),
            "progress": live.get("progress", "0/2"),
            "decision": "waiting"  
        }
    
    # Only log when liveness passes for the first time or we do recognition
    
    # -----------------------------------------------------
    # FACE RECOGNITION
    # -----------------------------------------------------

    if box is None:
        return {
            "ok": False,
            "stage": "Face Detection",
            "message": "Liveness verified. Please face the camera directly for recognition.",
            "decision": "waiting"
        }

    crop = quality.get("crop")
    if crop is None:
        x, y, w, h = [int(v) for v in box]
        crop = frame[y:y + h, x:x + w]

    try:
        query = _engine.represent_embedding(crop)

    except Exception as e:
        return {
            "ok": False,
            "stage": "Recognition",
            "message": str(e),
            "decision": "rejected"
        }


    candidates = db.scalars(
        select(FaceData).where(
            FaceData.status == "Active",
            FaceData.face_embedding.is_not(None)
        )
    ).all()


    best = None

    for fd in candidates:

        result = _engine.recognize_embedding(
            query,
            _engine.blob_to_embedding(
                fd.face_embedding
            ),
            RECOGNITION_THRESHOLD
        )

        if (
            best is None
            or result["similarity"]
            > best["result"]["similarity"]
        ):
            best = {
                "fd": fd,
                "result": result
            }


    if (
        not best
        or not best["result"]["verified"]
    ):
        logging.info("Recognition Failed: No match found above threshold.")
        
        # --- NEW UNKNOWN PERSON TRACKING ---
        import uuid
        unknown_id = None
        
        # Check if this face matches an existing unknown person for this session
        session_unknowns = _unknown_faces_session.setdefault(session_id, {})
        for uid, uemb in session_unknowns.items():
            u_result = _engine.recognize_embedding(query, uemb, RECOGNITION_THRESHOLD)
            if u_result["verified"]:
                unknown_id = uid
                break
                
        if not unknown_id:
            # Create a new unknown ID
            count = _unknown_counter.get(session_id, 0) + 1
            _unknown_counter[session_id] = count
            unknown_id = f"Person #{count}"
            session_unknowns[unknown_id] = query
            
        return {
            "ok": False,
            "stage": "Recognition",
            "message": "Student not recognized.",
            "decision": "rejected",
            "unknowns": list(session_unknowns.keys()),
            "confidence": round((best["result"]["confidence"] if best else 0) * 100, 1)
        }
    # -----------------------------------------------------
    # MARK ATTENDANCE
    # -----------------------------------------------------

    student = best["fd"].student
    
    logging.info(f"Recognition Passed: Student {student.roll_no}, Similarity: {best['result']['similarity']:.4f}")

    try:

        mark_attendance(
            db,
            student.student_id,
            session_id,
            best["result"]["confidence"],
            "Passed",
            "DeepFace/Facenet"
        )
        
        logging.info(f"Attendance Decision: Accepted for {student.roll_no}")

    except ValueError:

        # Reset liveness for the next student
        _liveness.pop(
            f"session-{session_id}",
            None
        )
        
        logging.info(f"Attendance Decision: Duplicate for {student.roll_no}")

        return {
            "ok": True,
            "stage": "Duplicate Check",
            "message": (
                f"{student.first_name} "
                f"{student.last_name} "
                "already marked for this session."
            ),
            "confidence": round(
                best["result"]["confidence"] * 100,
                1
            ),
            "decision": "duplicate",
            "student": student.roll_no
        }


    # Reset liveness for the next student
    _liveness.pop(
        f"session-{session_id}",
        None
    )

    return {
    "ok": True,
    "stage": "Attendance Accepted",
    "message": (
        f"Attendance marked for "
        f"{student.first_name} "
        f"{student.last_name}."
    ),
    "student_name": (
        f"{student.first_name} "
        f"{student.last_name}"
    ),
    "student_roll": student.roll_no,
    "confidence": round(
        best["result"]["confidence"] * 100,
        1
    ),
    "decision": "accepted",
}

# =========================================================
# UNKNOWN PERSON REGISTRATION
# =========================================================

@router.post("/attendance/{session_id}/register-unknown/process-frame")
def process_unknown_frame(
    request: Request,
    session_id: int,
    payload: dict,
    target: str,
    db: Session = Depends(get_db)
):
    require_auth(request)

    session = db.get(AttendanceSession, session_id)
    if not session or session.status != "Active":
        return {"ok": False, "stage": "Session", "message": "Session is not active.", "decision": "rejected"}

    try:
        frame = decode_image(payload["image"])
    except Exception as e:
        return {"ok": False, "stage": "Camera", "message": str(e), "decision": "rejected"}

    faces = _engine.detect_faces(frame)
    if len(faces) == 0:
        return {"ok": False, "stage": "Face Detection", "message": "No face detected.", "decision": "waiting"}
    elif len(faces) > 1:
        return {"ok": False, "stage": "Face Detection", "message": "Multiple faces detected.", "decision": "rejected"}

    box = faces[0]
    quality = _engine.quality_check(frame, box)
    if not quality["ok"]:
        return {"ok": False, "stage": "Face Quality", "message": quality["reason"], "decision": "rejected"}

    crop = quality.get("crop")
    if crop is None:
        x, y, w, h = [int(v) for v in box]
        crop = frame[y:y + h, x:x + w]

    try:
        query = _engine.represent_embedding(crop)
    except Exception as e:
        return {"ok": False, "stage": "Recognition", "message": str(e), "decision": "rejected"}

    # 1. Verify this is the target Unknown Person
    target_emb = _unknown_faces_session.get(session_id, {}).get(target)
    if not target_emb:
        return {"ok": False, "stage": "Registration", "message": "Target unknown person not found.", "decision": "rejected"}
        
    match_result = _engine.recognize_embedding(query, target_emb, RECOGNITION_THRESHOLD)
    if not match_result["verified"]:
        return {"ok": False, "stage": "Locking", "message": f"Looking for {target}. Please face the camera.", "decision": "waiting"}

    # 2. Run fresh Liveness
    reg_state = _registration_mode.setdefault(f"session-{session_id}-{target}", {
        "liveness": LivenessDetector(),
        "embeddings": []
    })
    
    live = reg_state["liveness"].check(frame, box)
    if live.get("message", "").startswith("? Liveness failed"):
        _registration_mode.pop(f"session-{session_id}-{target}", None)
        return {"ok": False, "stage": "Liveness Failed", "message": "Liveness failed. Registration aborted.", "decision": "rejected"}

    if LIVENESS_REQUIRED and not live["live"]:
        return {
            "ok": False,
            "stage": "Liveness Verification",
            "challenge": live.get("challenge", ""),
            "message": live.get("message", live.get("reason", "")),
            "progress": live.get("progress", "0/2"),
            "decision": "waiting"  
        }

    # 3. Collect Embeddings
    reg_state["embeddings"].append(query)
    TARGET_SAMPLES = 5
    
    if len(reg_state["embeddings"]) < TARGET_SAMPLES:
        return {
            "ok": False,
            "stage": "Face Capture",
            "message": f"Capturing facial features... {len(reg_state['embeddings'])}/{TARGET_SAMPLES}",
            "decision": "waiting"
        }

    # Ready!
    try:
        final_emb = _engine.average_embeddings(reg_state["embeddings"])
        # Store it temporarily so the finalize endpoint can pick it up
        reg_state["final_embedding"] = final_emb
        return {
            "ok": True,
            "stage": "Capture Complete",
            "message": "Facial features captured. Ready to finalize.",
            "decision": "unknown_ready"
        }
    except Exception as e:
        _registration_mode.pop(f"session-{session_id}-{target}", None)
        return {"ok": False, "stage": "Capture", "message": str(e), "decision": "rejected"}


@router.post("/attendance/{session_id}/finalize-unknown")
def finalize_unknown(
    request: Request,
    session_id: int,
    payload: dict,
    db: Session = Depends(get_db)
):
    require_auth(request)
    target = payload.get("target")
    student_id = payload.get("student_id")
    
    if not target or not student_id:
        return {"ok": False, "message": "Missing target or student_id."}
        
    reg_state = _registration_mode.get(f"session-{session_id}-{target}")
    if not reg_state or "final_embedding" not in reg_state:
        return {"ok": False, "message": "No captured facial data found for this target. Try again."}
        
    student = db.get(Student, student_id)
    if not student:
        return {"ok": False, "message": "Selected student not found."}

    from app.ai.face_engine import FaceEngine as FE
    
    existing = db.scalar(select(FaceData).where(FaceData.student_id == student_id))
    if existing:
        existing.face_embedding = FE.embedding_to_blob(reg_state["final_embedding"])
        existing.embedding_model = _engine.model_name
        existing.registration_date = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
        existing.status = "Active"
    else:
        db.add(
            FaceData(
                student_id=student.student_id,
                face_embedding=FE.embedding_to_blob(reg_state["final_embedding"]),
                embedding_model=_engine.model_name,
                registration_date=__import__("datetime").datetime.now().strftime("%Y-%m-%d"),
                status="Active"
            )
        )
    db.commit()
    
    # Clean up state
    _registration_mode.pop(f"session-{session_id}-{target}", None)
    
    # Mark Attendance
    try:
        mark_attendance(
            db,
            student.student_id,
            session_id,
            1.0, # 100% confidence because it was just registered manually
            "Passed",
            "DeepFace/Facenet"
        )
    except ValueError:
        return {"ok": True, "message": "Saved face, but student is already marked present.", "decision": "duplicate"}
        
    return {"ok": True, "message": f"Successfully registered and marked present: {student.first_name} {student.last_name}", "decision": "accepted"}

