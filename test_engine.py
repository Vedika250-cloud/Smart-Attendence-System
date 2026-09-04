import cv2
import numpy as np
from app.ai.face_engine import FaceEngine

def test_engine():
    engine = FaceEngine()
    print("Engine available:", engine.available)
    
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(img, (200, 100), (400, 300), (255, 255, 255), -1)
    
    try:
        faces = engine.detect_faces(img)
        print("Faces detected:", len(faces))
    except Exception as e:
        print("Error during face detection:", e)

if __name__ == "__main__":
    test_engine()
