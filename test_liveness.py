import cv2
from app.ai.liveness import LivenessDetector

print('Loading image...')
frame = cv2.imread('debug_backend_frame.jpg')
if frame is None:
    print('No image found!')
    exit(1)
print(f'Frame shape: {frame.shape}, dtype: {frame.dtype}')

print('Init detector...')
ld = LivenessDetector()

print('Checking...')
res = ld.check(frame)
print(res)
