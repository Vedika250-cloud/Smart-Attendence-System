from datetime import datetime

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, func

from app.database import get_db
from app.models import *
from app.services.attendance import dashboard_stats, create_session, close_session
from app.config import APP_TITLE, APP_VERSION

router = APIRouter()


def user_required(request):
    if not request.session.get("user_id"):
        return False
    return True


def ctx(request, **kw):
    return {
        "request": request,
        "user": {
            "full_name": request.session.get("full_name"),
            "role": request.session.get("role"),
        },
        "title": APP_TITLE,
        "version": APP_VERSION,
        **kw,
    }


@router.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    if not user_required(request):
        return RedirectResponse("/login", 303)

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=ctx(request, stats=dashboard_stats(db)),
    )


@router.get("/students/register")
def student_register(request: Request, db: Session = Depends(get_db)):
    if not user_required(request):
        return RedirectResponse("/login", 303)

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="students/register.html",
        context=ctx(
            request,
            classes=db.scalars(
                select(Class).where(Class.active == True)
            ).all(),
        ),
    )


@router.post("/students/register")
def student_register_post(
    request: Request,
    roll_no: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    class_id: int = Form(...),
    db: Session = Depends(get_db),
):
    if not user_required(request):
        return RedirectResponse("/login", 303)

    if db.scalar(select(Student).where(Student.roll_no == roll_no.strip())):
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="students/register.html",
            context=ctx(
                request,
                classes=db.scalars(
                    select(Class).where(Class.active == True)
                ).all(),
                error="Roll number already exists.",
            ),
        )

    s = Student(
        roll_no=roll_no.strip(),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        email=email.strip() or None,
        phone=phone.strip() or None,
        class_id=class_id,
        registration_date=datetime.now().strftime("%Y-%m-%d"),
        status="Active",
    )

    db.add(s)
    db.commit()
    db.refresh(s)

    return RedirectResponse(
        f"/students/{s.student_id}/face?new=1",
        303,
    )


@router.get("/students/{student_id}/face")
def face_capture_page(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
):
    if not user_required(request):
        return RedirectResponse("/login", 303)

    s = db.get(Student, student_id)

    if not s:
        raise HTTPException(404)

    msg = None
    if request.query_params.get("new") == "1":
        msg = "Student registered successfully. Student profile created. You can now register the student's facial profile."

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="students/face.html",
        context=ctx(request, student=s, message=msg),
    )


@router.get("/students")
def students(
    request: Request,
    q: str = "",
    db: Session = Depends(get_db),
):
    if not user_required(request):
        return RedirectResponse("/login", 303)

    stmt = select(Student).order_by(Student.student_id.desc())

    if q:
        stmt = stmt.where(
            or_(
                Student.roll_no.contains(q),
                Student.first_name.contains(q),
                Student.last_name.contains(q),
            )
        )

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="students/manage.html",
        context=ctx(
            request,
            students=db.scalars(stmt).all(),
            q=q,
        ),
    )


@router.get("/students/{student_id}/edit")
def student_edit(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
):
    if not user_required(request):
        return RedirectResponse("/login", 303)

    s = db.get(Student, student_id)

    if not s:
        raise HTTPException(404, "Student not found")

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="students/edit.html",
        context=ctx(
            request,
            student=s,
            classes=db.scalars(
                select(Class).where(Class.active == True)
            ).all(),
        ),
    )


@router.post("/students/{student_id}/edit")
def student_edit_post(
    request: Request,
    student_id: int,
    roll_no: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    class_id: int = Form(...),
    db: Session = Depends(get_db),
):
    if not user_required(request):
        return RedirectResponse("/login", 303)

    s = db.get(Student, student_id)

    if not s:
        raise HTTPException(404, "Student not found")

    duplicate = db.scalar(
        select(Student).where(
            Student.roll_no == roll_no.strip(),
            Student.student_id != student_id,
        )
    )

    if duplicate:
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="students/edit.html",
            context=ctx(
                request,
                student=s,
                classes=db.scalars(
                    select(Class).where(Class.active == True)
                ).all(),
                error="Roll number already exists.",
            ),
        )

    s.roll_no = roll_no.strip()
    s.first_name = first_name.strip()
    s.last_name = last_name.strip()
    s.email = email.strip() or None
    s.phone = phone.strip() or None
    s.class_id = class_id

    db.commit()

    return RedirectResponse("/students", 303)


@router.post("/students/{student_id}/delete")
def student_delete(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
):
    if not user_required(request):
        return RedirectResponse("/login", 303)

    if request.session.get("role") != "admin":
        raise HTTPException(403, "Admin role required")

    s = db.get(Student, student_id)

    if s:
        db.delete(s)
        db.commit()

    return RedirectResponse("/students", 303)


@router.get('/attendance/session')
def session_setup(request: Request, db: Session = Depends(get_db)):
    if not user_required(request):
        return RedirectResponse('/login', 303)

    classes = db.scalars(
        select(Class).where(Class.active == True)
    ).all()

    active = db.scalar(
        select(AttendanceSession)
        .where(AttendanceSession.status == 'Active')
        .order_by(AttendanceSession.session_id.desc())
    )

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="attendance/session.html",
        context=ctx(
            request,
            classes=classes,
            active=active
        )
    )

@router.post("/attendance/session")
def session_start(
    request: Request,
    class_id: int = Form(...),
    db: Session = Depends(get_db),
):
    if not user_required(request):
        return RedirectResponse("/login", 303)

    try:
        s = create_session(db, class_id)

    except ValueError as e:
        classes = db.scalars(
            select(Class).where(Class.active == True)
        ).all()

        return request.app.state.templates.TemplateResponse(
            request=request,
            name="attendance/session.html",
            context=ctx(
                request,
                classes=classes,
                error=str(e),
            ),
        )

    return RedirectResponse(
        f"/attendance/live/{s.session_id}?new=1",
        303,
    )

@router.get("/attendance/live/{session_id}")
def live(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
):
    if not user_required(request):
        return RedirectResponse("/login", 303)

    s = db.get(AttendanceSession, session_id)

    if not s:
        raise HTTPException(404)
        
    msg = None
    if request.query_params.get("new") == "1":
        msg = "Attendance session started successfully."

    students = db.scalars(
        select(Student).where(
            Student.class_id == s.class_id,
            Student.status == "Active"
        ).order_by(Student.roll_no)
    ).all()

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="attendance/live.html",
        context=ctx(request, session=s, message=msg, students=students),
    )


@router.post("/attendance/session/{session_id}/end")
def session_end(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
):
    if not user_required(request):
        return RedirectResponse("/login", 303)

    s = db.get(AttendanceSession, session_id)

    if s and s.status == "Active":
        absent_count = close_session(db, s)

        request.session["session_message"] = (
            f"Session completed. "
            f"{absent_count} student(s) automatically marked Absent."
        )

    return RedirectResponse("/", 303)


@router.get("/attendance/history")
def history(
    request: Request,
    q: str = "",
    db: Session = Depends(get_db),
):
    if not user_required(request):
        return RedirectResponse("/login", 303)

    stmt = (
        select(AttendanceRecord)
        .join(AttendanceRecord.student)
        .join(AttendanceRecord.session)
        .order_by(AttendanceRecord.attendance_id.desc())
    )

    if q:
        stmt = stmt.where(
            or_(
                Student.roll_no.contains(q),
                Student.first_name.contains(q),
                Student.last_name.contains(q),
            )
        )

    records = db.scalars(stmt).all()

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="attendance/history.html",
        context=ctx(
            request,
            records=records,
            q=q,
        ),
    )


@router.get("/reports")
def reports(
    request: Request,
    from_date: str = None,
    to_date: str = None,
    session_id: str = None,
    course_id: str = None,
    class_id: str = None,
    student_id: str = None,
    status: str = None,
    recognition_method: str = None,
    liveness_result: str = None,
    db: Session = Depends(get_db),
):
    if not user_required(request):
        return RedirectResponse("/login", 303)

    from app.services.report import get_filtered_attendance_data
    from app.models.models import Course, Class, AttendanceSession, Student
    
    # We need to pass filter options to the template to populate the dropdowns
    courses = db.scalars(select(Course).where(Course.active == True)).all()
    classes = db.scalars(select(Class).where(Class.active == True)).all()
    sessions = db.scalars(select(AttendanceSession).order_by(AttendanceSession.session_date.desc(), AttendanceSession.session_id.desc())).all()
    students = db.scalars(select(Student).where(Student.status == "Active").order_by(Student.roll_no)).all()

    report_data = get_filtered_attendance_data(
        db,
        from_date=from_date,
        to_date=to_date,
        session_id=session_id,
        course_id=course_id,
        class_id=class_id,
        student_id=student_id,
        status=status,
        recognition_method=recognition_method,
        liveness_result=liveness_result
    )
    
    # Calculate summary stats for the UI
    total_sessions = len(report_data)
    total_students = sum(d["stats"]["total"] for d in report_data)
    total_present = sum(d["stats"]["present"] for d in report_data)
    total_absent = sum(d["stats"]["absent"] for d in report_data)
    avg_pct = (total_present / total_students * 100) if total_students > 0 else 0
    total_records = sum(len(d["rows"]) for d in report_data)
    
    summary = {
        "sessions": total_sessions,
        "students": total_students,
        "present": total_present,
        "absent": total_absent,
        "avg_pct": round(avg_pct, 1),
        "records": total_records
    }
    
    filters = {
        "from_date": from_date or "",
        "to_date": to_date or "",
        "session_id": session_id or "",
        "course_id": course_id or "",
        "class_id": class_id or "",
        "student_id": student_id or "",
        "status": status or "All",
        "recognition_method": recognition_method or "All",
        "liveness_result": liveness_result or "All"
    }

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="reports/analytics.html",
        context=ctx(
            request,
            report_data=report_data,
            summary=summary,
            filters=filters,
            courses=courses,
            classes=classes,
            sessions=sessions,
            students=students
        ),
    )


@router.get("/reports/export")
def export_report(
    request: Request,
    from_date: str = None,
    to_date: str = None,
    session_id: str = None,
    course_id: str = None,
    class_id: str = None,
    student_id: str = None,
    status: str = None,
    recognition_method: str = None,
    liveness_result: str = None,
    db: Session = Depends(get_db),
):
    if not user_required(request):
        return RedirectResponse("/login", 303)

    from app.services.report import generate_excel_report
    from fastapi.responses import Response

    filters = {
        "from_date": from_date,
        "to_date": to_date,
        "session_id": session_id,
        "course_id": course_id,
        "class_id": class_id,
        "student_id": student_id,
        "status": status,
        "recognition_method": recognition_method,
        "liveness_result": liveness_result
    }

    try:
        excel_data = generate_excel_report(db, filters)
        return Response(
            content=excel_data,
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": (
                    "attachment; filename=Attendance_Report.xlsx"
                )
            },
        )
    except Exception as e:
        import logging
        logging.error(f"Excel export failed: {e}")
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="reports/analytics.html",
            context=ctx(request, report_data=[], summary={}, filters={}, error="Unable to generate the attendance report. Please try again."),
        )


@router.get("/settings")
def settings(request: Request):
    if not user_required(request):
        return RedirectResponse("/login", 303)

    from app.config import RECOGNITION_THRESHOLD, LIVENESS_REQUIRED

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="settings.html",
        context=ctx(
            request,
            threshold=RECOGNITION_THRESHOLD,
            liveness=LIVENESS_REQUIRED,
        ),
    )


@router.get("/about")
def about(request: Request):
    if not user_required(request):
        return RedirectResponse("/login", 303)

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="about.html",
        context=ctx(request),
    )
