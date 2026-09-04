from sqlalchemy import select
from app.database import Base, engine, SessionLocal
from app.models import User,Course,Class
from app.security import hash_password

def init_db():
    Base.metadata.create_all(engine)
    db=SessionLocal()
    try:
        if db.scalar(select(User.user_id).limit(1)) is None:
            db.add_all([User(username='admin',password_hash=hash_password('admin123'),role='admin',full_name='System Administrator',active=True),User(username='teacher',password_hash=hash_password('teacher123'),role='teacher',full_name='Demo Teacher',active=True)]); db.commit()
        teacher=db.scalar(select(User).where(User.username=='teacher'))
        course=db.scalar(select(Course).where(Course.course_code=='AI101'))
        if not course:
            course=Course(course_code='AI101',course_name='Artificial Intelligence & Statistics',description='Demo course for local development',semester='Semester 5'); db.add(course); db.commit()
        if not db.scalar(select(Class).where(Class.class_name=='BCA-5A',Class.course_id==course.course_id)):
            db.add(Class(class_name='BCA-5A',course_id=course.course_id,faculty_id=teacher.user_id,academic_year='2026-27',semester='Semester 5')); db.commit()
    finally: db.close()
