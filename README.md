# Secure Smart Classroom Attendance System — Web Application

**Version:** 0.5-web  
**Architecture:** Browser → FastAPI → SQLAlchemy → SQLite/PostgreSQL → AI engine

This build replaces the Tkinter presentation layer with a browser-based application while preserving the existing database schema, student/attendance concepts, face engine, quality checks and liveness foundation.

## Run on Windows (Python 3.11)

```powershell
py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Open Chrome at **http://127.0.0.1:8000**.

## Development login

A development seed is available if the database has no users:

- `admin` / `admin123`
- `teacher` / `teacher123`

The seed passwords are stored as secure scrypt hashes. Existing legacy SHA-256 hashes from the earlier desktop build are migrated to scrypt after a successful login.

## Shared database

Configure `.env`/environment variables. Default development database:

```text
DATABASE_URL=sqlite:///./data/attendance.db
```

For a shared deployment, switch to PostgreSQL, for example:

```text
DATABASE_URL=postgresql+psycopg://username:password@host:5432/attendance
```

Do not commit credentials. The same FastAPI server + PostgreSQL database can be accessed by multiple authorized browser users.

## Mandatory screens

1. Login
2. Dashboard
3. Student Registration
4. Student Management
5. Attendance Session Setup
6. Live Attendance
7. Attendance History
8. Reports & Analytics
9. Settings
10. About

## AI status

Face detection, face-quality checks, DeepFace/FaceNet embeddings and confidence-based matching are wired into the web API. The current liveness module is the preserved consecutive-frame motion foundation from the desktop build; it is **not** presented as a fully validated anti-spoofing system. The final blink/head-movement and print/phone/video replay evaluation still requires validation on the team's test dataset.

## Preserved vs changed

### Preserved
- Existing SQLite schema and existing local database file
- Student/class/session/attendance entities
- Face embedding storage concept
- OpenCV face detection
- Face quality checks
- DeepFace Facenet embedding adapter
- Liveness foundation
- Duplicate attendance protection
- Excel export

### Changed
- Tkinter UI → FastAPI + Jinja2 + Bootstrap/CSS/JavaScript
- Desktop navigation → browser routes/sidebar
- Direct SQLite calls → SQLAlchemy database layer
- Login now uses secure scrypt hashing for new/migrated passwords
- Browser camera access via `getUserMedia`
- Database configuration is environment-based and PostgreSQL-ready

## Accuracy

The project target remains **80–85% practical accuracy**. No inflated accuracy claim is made by the application. Thresholds must be calibrated against the team's validation dataset.
