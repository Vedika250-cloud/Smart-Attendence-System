import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
LOG_DIR = BASE_DIR / 'logs'
EXPORT_DIR = BASE_DIR / 'exports'
for d in (DATA_DIR, LOG_DIR, EXPORT_DIR): d.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{(DATA_DIR / "attendance.db").as_posix()}')
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-only-change-me')
APP_TITLE = 'Secure Smart Classroom Attendance System'
APP_VERSION = '0.8-ux'
RECOGNITION_THRESHOLD = float(os.getenv('RECOGNITION_THRESHOLD', '0.65'))
LIVENESS_REQUIRED = os.getenv('LIVENESS_REQUIRED', 'true').lower() == 'true'
