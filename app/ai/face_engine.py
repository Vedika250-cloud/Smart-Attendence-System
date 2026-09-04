import cv2, numpy as np, logging
logger=logging.getLogger(__name__)
try:
    from deepface import DeepFace
except Exception as exc:
    DeepFace=None
    logger.warning('DeepFace unavailable: %s',exc)

class FaceEngine:
    def __init__(self, detector_backend='opencv', model_name='Facenet'):
        self.detector_backend=detector_backend
        self.model_name=model_name
        self.face_cascade=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
        self.profile_cascade=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_profileface.xml')
        # Pre-build the model to avoid latency on the first request
        if DeepFace is not None:
            try:
                DeepFace.build_model(self.model_name)
            except Exception as e:
                logger.warning('Failed to pre-build DeepFace model: %s', e)

    @property
    def available(self): return DeepFace is not None
    
    def detect_faces(self, frame):
        print("[5 FACE DETECTION] Starting")
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        faces = list(self.face_cascade.detectMultiScale(gray,1.1,5,minSize=(80,80)))
        if not faces:
            # Try profile face if frontal fails (useful during liveness challenges)
            faces = list(self.profile_cascade.detectMultiScale(gray,1.1,5,minSize=(80,80)))
            if not faces:
                # Try flipped profile (OpenCV profile cascade only detects one side)
                flipped = cv2.flip(gray, 1)
                flipped_faces = list(self.profile_cascade.detectMultiScale(flipped,1.1,5,minSize=(80,80)))
                faces = []
                width = gray.shape[1]
                for (x, y, w, h) in flipped_faces:
                    faces.append((width - x - w, y, w, h))
        print(f"[5 FACE DETECTION] faces={len(faces)}")
        return faces
    @staticmethod
    def quality_check(frame, box, margin=0.2):
        x, y, w, h = [int(v) for v in box]
        
        # Add a margin to the crop for better embedding context
        margin_x = int(w * margin)
        margin_y = int(h * margin)
        
        y1 = max(0, y - margin_y)
        y2 = min(frame.shape[0], y + h + margin_y)
        x1 = max(0, x - margin_x)
        x2 = min(frame.shape[1], x + w + margin_x)
        
        crop = frame[y1:y2, x1:x2]
        
        if crop.size == 0:
            return {'ok': False, 'reason': 'Invalid face crop'}
            
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))
        blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        
        if w < 80 or h < 80:
            return {'ok': False, 'reason': 'Face too small'}
            
        if brightness < 40:
            return {'ok': False, 'reason': 'Lighting too dark'}
            
        if brightness > 230:
            return {'ok': False, 'reason': 'Lighting too bright'}
            
        # Adaptive blur threshold based on face size
        # We lowered this significantly to accommodate downscaled webcams and soft lighting.
        adaptive_blur_threshold = max(5.0, 15.0 - (w / 100.0) * 3.0)
        
        logger.info("Quality Check: width=%d, height=%d, brightness=%.2f, blur=%.2f, blur_thresh=%.2f", w, h, brightness, blur, adaptive_blur_threshold)
        
        if blur < adaptive_blur_threshold:
            return {'ok': False, 'reason': 'Image too blurry'}
            
        return {
            'ok': True, 
            'reason': 'Quality acceptable', 
            'brightness': brightness, 
            'blur_score': blur,
            'face_width': w,
            'face_height': h,
            'crop': crop
        }
    def represent_embedding(self,face_bgr):
        if DeepFace is None: raise RuntimeError('DeepFace is unavailable')
        # Skip face detection since the input is already cropped. This prevents errors on tight crops and speeds up processing.
        result=DeepFace.represent(img_path=face_bgr,model_name=self.model_name,detector_backend='skip',enforce_detection=False,normalization='base')
        emb=np.asarray(result[0]['embedding'],dtype=np.float32); norm=np.linalg.norm(emb)
        if norm==0: raise RuntimeError('Invalid facial embedding')
        return emb/norm
    @staticmethod
    def average_embeddings(embeddings):
        a=np.vstack(embeddings).astype(np.float32); a=a.mean(axis=0); n=np.linalg.norm(a)
        if n==0: raise ValueError('Invalid averaged embedding')
        return a/n
    @staticmethod
    def embedding_to_blob(e): return np.asarray(e,dtype=np.float32).tobytes()
    @staticmethod
    def blob_to_embedding(b): return None if b is None else np.frombuffer(b,dtype=np.float32)
    def recognize_embedding(self,q,r,threshold=.75):
        q=np.asarray(q,dtype=np.float32); r=np.asarray(r,dtype=np.float32); qn=np.linalg.norm(q); rn=np.linalg.norm(r)
        if qn==0 or rn==0:return {'verified':False,'similarity':0.0,'confidence':0.0}
        sim=float(np.dot(q,r)/(qn*rn)); conf=max(0,min(1,(sim+1)/2))
        return {'verified':sim>=threshold,'similarity':sim,'confidence':conf,'threshold':threshold,'model':self.model_name}
