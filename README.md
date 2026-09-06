# 🎓 AI-Based Smart Attendance System

An AI-powered Smart Attendance System that automates classroom attendance using **Face Recognition**, **Liveness Detection**, and **Real-Time Camera Verification**. The system eliminates manual attendance, prevents proxy attendance, detects spoofing attempts, and allows administrators to register previously unknown students during an active attendance session.

---

# ✨ Features

## 👤 Student Management
- Add and manage student records
- Register students with facial data
- Store secure face embeddings
- Update student information

## 🎥 Smart Attendance
- Real-time webcam attendance
- Automatic face detection
- Face quality verification
- AI-based face recognition
- Liveness detection
- Automatic attendance marking
- Duplicate attendance prevention

## 🔒 Security Features
- Liveness Detection (Anti-Spoofing)
- Rejects photo/video attacks
- Unknown face detection
- Secure facial embedding storage
- Session-based attendance

## 👥 Unknown Student Registration
When an unknown person is detected:

- Detects unregistered faces
- Administrator selects the corresponding student
- Captures face samples
- Stores facial embeddings
- Automatically marks attendance after successful registration

## 📊 Attendance Reports
- Session-wise attendance
- Student attendance history
- Attendance statistics
- Search and filter functionality

---

# 🚀 System Workflow

```
Camera
   │
   ▼
Face Detection
   │
   ▼
Face Quality Check
   │
   ▼
Liveness Detection
   │
   ▼
Face Recognition
   │
 ┌──────────────┴──────────────┐
 │                             │
Known Face                Unknown Face
 │                             │
 ▼                             ▼
Attendance              Register Student
Marked                  Save Face Data
```

---

# 🧠 AI Pipeline

1. Capture live camera frame
2. Detect face using OpenCV
3. Verify face quality
4. Perform liveness detection
5. Generate FaceNet embedding
6. Compare embedding with database
7. Recognize registered student
8. Mark attendance
9. Display attendance confirmation popup

---

# 🛠 Technology Stack

## Backend
- Python
- FastAPI
- SQLAlchemy

## Artificial Intelligence
- DeepFace
- FaceNet
- OpenCV
- MediaPipe
- NumPy

## Frontend
- HTML5
- CSS3
- JavaScript
- Jinja2 Templates

## Database
- SQLite

## Server
- Uvicorn

---

# 📁 Project Structure

```
AI-Smart-Attendance-System/
│
├── app/
│   ├── ai/
│   ├── routers/
│   ├── static/
│   ├── templates/
│   ├── models/
│   ├── services/
│   └── ...
│
├── data/
├── tests/
│
├── .env.example
├── .gitignore
├── implementation_plan.md
├── main.py
├── requirements.txt
├── README.md
├── test_engine.py
├── test_liveness.py
└── test_report.py
```

---

# ⚙ Installation

## Clone the Repository

```bash
git clone https://github.com/your-username/AI-Smart-Attendance-System.git
```

## Open the Project

```bash
cd webapp
```

## Create Virtual Environment

```bash
python -m venv .venv
```

## Activate Virtual Environment (Windows)

```powershell
.\.venv\Scripts\Activate.ps1
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Run the Application

```bash
uvicorn main:app --reload
```

---

# 🌐 Open in Browser

```
http://127.0.0.1:8000
```

---

# 👨‍💻 User Workflow

## Administrator

```
Login
   ↓
Create Course
   ↓
Create Class
   ↓
Register Students
   ↓
Capture Face Samples
   ↓
Start Attendance Session
   ↓
View Reports
```

---

## Attendance Process

```
Student stands before camera
             ↓
      Face Detection
             ↓
      Face Quality Check
             ↓
     Liveness Detection
             ↓
      Face Recognition
             ↓
     Attendance Marked
```

If an unknown face is detected:

```
Unknown Person
        ↓
Administrator selects student
        ↓
Face Registration
        ↓
Attendance Marked
```

---

# 📸 Screenshots

### Login Page

<img width="1600" height="720" alt="Login" src="https://github.com/user-attachments/assets/9d4454b7-777e-440d-9232-510090362f38" />

---

### Dashboard

<img width="1916" height="865" alt="dashboard" src="https://github.com/user-attachments/assets/f26fbaf0-829c-4e1e-9f0b-6f4e38cbc974" />


---

### Student Registration

<img width="1600" height="728" alt="Student registration" src="https://github.com/user-attachments/assets/731f5b78-0871-44cb-b109-2653ad518764" />


---

### Face Registration

<img width="1600" height="740" alt="Start Session" src="https://github.com/user-attachments/assets/d007a5cf-31ed-4c88-9ac9-9aa838ffaac0" />


---


### Attendance Success Popup

<img width="1600" height="916" alt="Attendance marked" src="https://github.com/user-attachments/assets/7d11c298-004e-435a-a4da-f467dbfe2858" />

---

### Attendance Reports

<img width="1600" height="717" alt="Reports and analytics" src="https://github.com/user-attachments/assets/fa81f43c-c882-4b13-b358-2a2e1459a677" />


---

# 📊 Key Features

- ✅ AI-Based Face Recognition
- ✅ DeepFace FaceNet Embeddings
- ✅ Real-Time Attendance
- ✅ Liveness Detection
- ✅ Anti-Spoofing Protection
- ✅ Unknown Student Registration
- ✅ Duplicate Attendance Prevention
- ✅ Attendance Reports
- ✅ Responsive User Interface

---

# 🔐 Security

- Admin Authentication
- Liveness Detection
- Face Quality Verification
- Duplicate Attendance Prevention
- Unknown Face Detection
- Secure Facial Embedding Storage

---

# 📈 Future Scope

- Mobile Application
- Cloud Database Integration
- Multi-Camera Attendance
- Deep Learning-Based Anti-Spoofing
- Email/SMS Notifications
- Advanced Analytics Dashboard
- Role-Based Access Control
- Cloud Deployment

---

# 👥 Contributors

- Aashmita Tiwari
- Mahek Yadav
- Mishti Joshi
- Vedika Singh


---

# 🙏 Acknowledgements

This project was developed as part of an academic AI & Statistics project.

Special thanks to the open-source communities behind:

- FastAPI
- DeepFace
- FaceNet
- OpenCV
- MediaPipe
- SQLAlchemy
- NumPy

---

# 📄 License

This project is intended for **educational and academic purposes**.
