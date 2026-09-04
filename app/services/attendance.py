from datetime import datetime

from sqlalchemy import select, func

from sqlalchemy.orm import Session

from app.models import *


def now_date():
    return datetime.now().strftime('%Y-%m-%d')


def now_time():
    return datetime.now().strftime('%H:%M:%S')


def dashboard_stats(db: Session):

    return {
        'students': db.scalar(
            select(func.count(Student.student_id))
            .where(Student.status == 'Active')
        ) or 0,

        'classes': db.scalar(
            select(func.count(Class.class_id))
            .where(Class.active == True)
        ) or 0,

        'sessions': db.scalar(
            select(func.count(AttendanceSession.session_id))
        ) or 0,

        'attendance': db.scalar(
            select(func.count(AttendanceRecord.attendance_id))
        ) or 0
    }


def create_session(db, class_id):

    active = db.scalar(
        select(AttendanceSession).where(
            AttendanceSession.class_id == class_id,
            AttendanceSession.status == 'Active'
        )
    )

    if active:
        raise ValueError(
            'An attendance session is already active for this class.'
        )

    s = AttendanceSession(
        class_id=class_id,
        session_date=now_date(),
        start_time=now_time(),
        status='Active'
    )

    db.add(s)
    db.commit()
    db.refresh(s)

    return s


def mark_remaining_absent(db: Session, session):

    """
    Automatically mark all active students in this session's class
    as Absent if they do not already have an attendance record.
    """

    students = db.scalars(
        select(Student).where(
            Student.class_id == session.class_id,
            Student.status == 'Active'
        )
    ).all()

    absent_count = 0

    for student in students:

        existing = db.scalar(
            select(AttendanceRecord).where(
                AttendanceRecord.student_id == student.student_id,
                AttendanceRecord.session_id == session.session_id
            )
        )

        # Student already marked Present
        if existing:
            continue

        # Student was not marked during the session
        absent_record = AttendanceRecord(
            student_id=student.student_id,
            session_id=session.session_id,
            attendance_status='Absent',
            recorded_time=f'{now_date()} {now_time()}',
            recognition_confidence=0.0,
            liveness_result='Not Checked',
            recognition_method='Not Recognized'
        )

        db.add(absent_record)

        absent_count += 1

    db.commit()

    return absent_count


def close_session(db: Session, session):

    # First mark all students who were not recognized as Absent
    absent_count = mark_remaining_absent(db, session)

    # Then close the session
    session.end_time = now_time()
    session.status = 'Completed'

    db.commit()

    return absent_count


def mark_attendance(
    db,
    student_id,
    session_id,
    confidence,
    liveness='Passed',
    method='DeepFace'
):

    existing = db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.session_id == session_id
        )
    )

    if existing:
        raise ValueError(
            'Attendance is already recorded for this student in this session.'
        )

    r = AttendanceRecord(
        student_id=student_id,
        session_id=session_id,
        attendance_status='Present',
        recorded_time=f'{now_date()} {now_time()}',
        recognition_confidence=confidence,
        liveness_result=liveness,
        recognition_method=method
    )

    db.add(r)
    db.commit()
    db.refresh(r)

    return r