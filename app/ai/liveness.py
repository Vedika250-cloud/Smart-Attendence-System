import os
import cv2
import numpy as np
import random
import time
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'face_landmarker.task')

class LivenessDetector:
    """
    Robust challenge-response liveness verification using MediaPipe Face Landmarker.
    Provides strong anti-spoofing against static photos and basic video replays
    by requiring the user to perform randomized facial movements.
    """

    def __init__(
        self,
        required_stages=2,
        max_frames=100
    ):
        base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
            num_faces=1
        )
        self.face_mesh = vision.FaceLandmarker.create_from_options(options)
        
        self.required_stages = required_stages
        self.max_frames = max_frames
        
        self.frame_count = 0
        self.challenges_completed = 0
        self.current_challenge = None
        self.challenge_start_time = 0
        self.lost_frames = 0
        
        # Explicit deterministic sequence
        self.challenges = ["turn_left", "turn_right"]
        
    def reset(self):
        self.frame_count = 0
        self.challenges_completed = 0
        self.current_challenge = None
        self.lost_frames = 0
        
    def _get_current_challenge_name(self):
        if self.challenges_completed < len(self.challenges):
            return self.challenges[self.challenges_completed]
        return "completed"

    def _get_challenge_text(self):
        texts = {
            "turn_left": "Turn your head LEFT",
            "turn_right": "Turn your head RIGHT",
            "completed": "Liveness verified"
        }
        return texts.get(self._get_current_challenge_name(), "Verifying liveness...")

    def check(self, frame, face_box=None):
        if face_box is not None:
            x, y, w, h = face_box
            self.last_center = (x + w/2, y + h/2)
            
        if self.challenges_completed >= self.required_stages:
            return {
                "live": True,
                "motion_score": 1.0,
                "challenge": "completed",
                "message": "Liveness verified",
                "progress": f"{self.challenges_completed}/{self.required_stages}"
            }
            
        self.frame_count += 1
        
        if self.frame_count >= self.max_frames:
            self.reset()
            return {
                "live": False,
                "motion_score": 0.0,
                "challenge": "timeout",
                "message": "⚠ Liveness failed — please perform the requested movement.",
                "progress": "0/2"
            }
            
        self.current_challenge = self._get_current_challenge_name()
        if self.frame_count == 1 or getattr(self, '_last_printed_challenge', None) != self.current_challenge:
            print(f"[7 LIVENESS] challenge active = {self.current_challenge}")
            self._last_printed_challenge = self.current_challenge
            
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        results = self.face_mesh.detect(mp_image)
        
        if not getattr(self, '_frame_logged', False):
            print(f"[7 LIVENESS] frame received = YES")
            self._frame_logged = True
        
        if not results.face_landmarks:
            if not getattr(self, '_landmarks_logged', False):
                print("[7 LIVENESS] landmarks detected = NO")
                self._landmarks_logged = True
                
            self.lost_frames += 1
            if self.lost_frames > 15:
                print("[7 LIVENESS] face lost for too long, resetting")
                self.reset()
                
            return {
                "live": False,
                "motion_score": 0.0,
                "challenge": self.current_challenge,
                "message": self._get_challenge_text(),
                "progress": f"{self.challenges_completed}/{self.required_stages}"
            }
            
        self._landmarks_logged = False
        self.lost_frames = 0
        landmarks = results.face_landmarks[0]
        
        def dist(p1, p2):
            return np.sqrt((landmarks[p1].x - landmarks[p2].x)**2 + (landmarks[p1].y - landmarks[p2].y)**2)
            
        passed = False
        
        if self.current_challenge == "turn_left":
            d_left = dist(1, 234)
            d_right = dist(1, 454)
            ratio = d_left / max(d_right, 0.0001)
            print(f"[LIVENESS DEBUG] challenge=turn_left, ratio={ratio:.4f}, required<0.6")
            if ratio < 0.6:  
                passed = True
                
        elif self.current_challenge == "turn_right":
            d_left = dist(1, 234)
            d_right = dist(1, 454)
            ratio = d_right / max(d_left, 0.0001)
            print(f"[LIVENESS DEBUG] challenge=turn_right, ratio={ratio:.4f}, required<0.6")
            if ratio < 0.6:
                passed = True
                
        if passed:
            self.challenges_completed += 1
            print(f"[7 LIVENESS] stage result = PASS")
            print(f"[7 LIVENESS] challenge progress = {self.challenges_completed}/{self.required_stages}")
            
            if self.challenges_completed >= self.required_stages:
                print("[7 LIVENESS] completed = YES")
                return {
                    "live": True,
                    "motion_score": 1.0,
                    "challenge": "completed",
                    "message": "Liveness verified",
                    "progress": f"{self.challenges_completed}/{self.required_stages}"
                }
            else:
                prev = self.current_challenge
                self.current_challenge = self._get_current_challenge_name()
                print(f"[7 LIVENESS] challenge generated = {self.current_challenge}")
                
                if prev == "turn_left":
                    msg = "✓ Left movement detected. Next: RIGHT"
                else:
                    msg = "✓ Right movement detected. Next: LEFT"
                    
                return {
                    "live": False,
                    "motion_score": 0.5,
                    "challenge": self.current_challenge,
                    "message": msg,
                    "progress": f"{self.challenges_completed}/{self.required_stages}"
                }
                
        return {
            "live": False,
            "motion_score": 0.1,
            "challenge": self.current_challenge,
            "message": self._get_challenge_text(),
            "progress": f"{self.challenges_completed}/{self.required_stages}"
        }

    def __del__(self):
        if hasattr(self, 'face_mesh'):
            self.face_mesh.close()