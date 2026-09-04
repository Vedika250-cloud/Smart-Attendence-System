def test_imports():
    import main
    from app.ai.face_engine import FaceEngine
    from app.ai.liveness import LivenessDetector
    assert main.app.title.startswith('Secure Smart')
    assert FaceEngine().face_cascade is not None
    assert LivenessDetector() is not None
