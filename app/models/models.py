from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Text, Float, LargeBinary, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class User(Base):
    __tablename__='users'
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    full_name: Mapped[str] = mapped_column(String)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Course(Base):
    __tablename__='courses'
    course_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_code: Mapped[str] = mapped_column(String, unique=True)
    course_name: Mapped[str] = mapped_column(String)
    description: Mapped[str|None] = mapped_column(Text, nullable=True)
    semester: Mapped[str|None] = mapped_column(String, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Class(Base):
    __tablename__='classes'
    class_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_name: Mapped[str] = mapped_column(String)
    course_id: Mapped[int] = mapped_column(ForeignKey('courses.course_id'))
    faculty_id: Mapped[int] = mapped_column(ForeignKey('users.user_id'))
    academic_year: Mapped[str|None] = mapped_column(String, nullable=True)
    semester: Mapped[str|None] = mapped_column(String, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    course = relationship('Course')
    faculty = relationship('User')

class Student(Base):
    __tablename__='students'
    student_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    roll_no: Mapped[str] = mapped_column(String, unique=True)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    email: Mapped[str|None] = mapped_column(String, nullable=True)
    phone: Mapped[str|None] = mapped_column(String, nullable=True)
    class_id: Mapped[int] = mapped_column(ForeignKey('classes.class_id'))
    registration_date: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default='Active')
    class_ = relationship('Class')
    face_data = relationship('FaceData', back_populates='student', uselist=False, cascade='all, delete-orphan')

class FaceData(Base):
    __tablename__='face_data'
    face_data_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey('students.student_id', ondelete='CASCADE'), unique=True)
    face_embedding: Mapped[bytes|None] = mapped_column(LargeBinary, nullable=True)
    embedding_model: Mapped[str|None] = mapped_column(String, nullable=True)
    registration_date: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default='Active')
    student = relationship('Student', back_populates='face_data')

class AttendanceSession(Base):
    __tablename__='attendance_sessions'
    session_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey('classes.class_id'))
    session_date: Mapped[str] = mapped_column(String)
    start_time: Mapped[str] = mapped_column(String)
    end_time: Mapped[str|None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default='Active')
    class_ = relationship('Class')

class AttendanceRecord(Base):
    __tablename__='attendance_records'
    attendance_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey('students.student_id'))
    session_id: Mapped[int] = mapped_column(ForeignKey('attendance_sessions.session_id'))
    attendance_status: Mapped[str] = mapped_column(String, default='Present')
    recorded_time: Mapped[str] = mapped_column(String)
    recognition_confidence: Mapped[float|None] = mapped_column(Float, nullable=True)
    liveness_result: Mapped[str|None] = mapped_column(String, nullable=True)
    recognition_method: Mapped[str|None] = mapped_column(String, nullable=True)
    __table_args__=(UniqueConstraint('student_id','session_id',name='uq_attendance_student_session'),)
    student=relationship('Student')
    session=relationship('AttendanceSession')

class ExceptionLog(Base):
    __tablename__='exception_logs'
    exception_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int|None] = mapped_column(ForeignKey('attendance_sessions.session_id'), nullable=True)
    exception_type: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String, default='Medium')
    resolution_status: Mapped[str] = mapped_column(String, default='Unresolved')
