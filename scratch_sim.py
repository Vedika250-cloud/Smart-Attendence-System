import cv2
import time
import numpy as np
from app.ai.liveness import LivenessDetector

# Create dummy frame
frame = np.zeros((360, 640, 3), dtype=np.uint8)

class MockFaceLandmarks:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class MockResults:
    def __init__(self, landmarks=None):
        self.face_landmarks = [landmarks] if landmarks else []

# Monkeypatch face_mesh.detect
def run_simulation():
    ld = LivenessDetector()
    
    print("=== TEST LIVENESS PIPELINE ===")
    
    def simulate_frame(step, l_dist, r_dist):
        print(f"\n[FRAME {step}]")
        landmarks = {
            1: MockFaceLandmarks(0.5, 0.5),      # nose
            234: MockFaceLandmarks(0.5 - l_dist, 0.5), # left cheek
            454: MockFaceLandmarks(0.5 + r_dist, 0.5)  # right cheek
        }
        
        # Override detect to return our mock
        ld.face_mesh.detect = lambda img: MockResults(landmarks)
        
        res = ld.check(frame, face_box=(100,100,200,200))
        print(f"[API RESPONSE] live={res['live']}, reason='{res['reason']}'")
        return res

    # 1. Look straight (left and right distances are equal)
    simulate_frame(1, 0.2, 0.2)
    
    # 2. Turn left (left cheek gets closer to nose)
    simulate_frame(2, 0.1, 0.3)
    
    # 3. Turn right (right cheek gets closer to nose)
    res = simulate_frame(3, 0.3, 0.1)
    
    # 4. Stay turned right (should pass liveness entirely)
    res = simulate_frame(4, 0.3, 0.1)
    
    if res['live']:
        print("\nSUCCESS! Pipeline verified.")

run_simulation()
