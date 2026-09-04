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

