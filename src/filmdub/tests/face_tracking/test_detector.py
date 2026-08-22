"""Face detector and recognizer tests."""

import numpy as np
import pytest

from filmdub.workers.face_tracking.config import FaceTrackingConfig
from filmdub.workers.face_tracking.detector import FaceDetector, FaceRecognizer


class TestFaceDetector:
    """Test face detector."""

    def test_init(self):
        """Test detector initialization."""
        config = FaceTrackingConfig(min_face_size=30)
        detector = FaceDetector(config)

        assert detector.config.min_face_size == 30

    def test_detect_faces_empty_frame(self):
        """Test detecting faces in empty frame."""
        detector = FaceDetector()
        empty_frame = np.zeros((100, 100, 3), dtype=np.uint8)

        detections = detector.detect_faces(empty_frame, frame_number=0)

        assert isinstance(detections, list)
        # Empty frame should have no faces
        assert len(detections) == 0

    def test_detect_faces_with_face(self):
        """Test detecting faces in frame with synthetic face."""
        detector = FaceDetector()

        try:
            cv2 = __import__("cv2")
        except ImportError:
            pytest.skip("OpenCV not available")

        # Create a simple test frame with a face-like region
        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        # Draw a face-like rectangle
        cv2.rectangle(frame, (50, 50), (150, 150), (255, 255, 255), -1)

        detections = detector.detect_faces(frame, frame_number=0)

        # May or may not detect depending on Haar cascade
        assert isinstance(detections, list)

    def test_extract_face_crop(self):
        """Test extracting face crop."""
        detector = FaceDetector()

        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        frame[50:150, 50:150] = 255

        bbox = [50, 50, 100, 100]
        crop = detector.extract_face_crop(frame, bbox)

        assert crop is not None
        assert crop.shape[0] > 0
        assert crop.shape[1] > 0


class TestFaceRecognizer:
    """Test face recognizer."""

    def test_init(self):
        """Test recognizer initialization."""
        config = FaceTrackingConfig(recognition_threshold=0.6)
        recognizer = FaceRecognizer(config)

        assert recognizer.config.recognition_threshold == 0.6

    def test_compute_embedding_none(self):
        """Test computing embedding with None."""
        recognizer = FaceRecognizer()

        embedding = recognizer.compute_embedding(None)

        assert embedding is None

    def test_compute_embedding_empty(self):
        """Test computing embedding with empty array."""
        recognizer = FaceRecognizer()

        embedding = recognizer.compute_embedding(np.array([]))

        assert embedding is None

    def test_compute_embedding_valid(self):
        """Test computing embedding with valid face crop."""
        recognizer = FaceRecognizer()

        # Create a simple face crop
        face_crop = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)

        embedding = recognizer.compute_embedding(face_crop)

        assert embedding is not None
        assert isinstance(embedding, np.ndarray)
        assert len(embedding.shape) == 1

    def test_compare_embeddings_none(self):
        """Test comparing embeddings with None."""
        recognizer = FaceRecognizer()

        similarity = recognizer.compare_embeddings(None, None)

        assert similarity == 0.0

    def test_compare_embeddings_same(self):
        """Test comparing identical embeddings."""
        recognizer = FaceRecognizer()

        embedding = np.random.rand(128)
        embedding = embedding / np.linalg.norm(embedding)

        similarity = recognizer.compare_embeddings(embedding, embedding)

        assert similarity == pytest.approx(1.0, abs=0.01)

    def test_compare_embeddings_different(self):
        """Test comparing different embeddings."""
        recognizer = FaceRecognizer()

        embedding1 = np.random.rand(128)
        embedding1 = embedding1 / np.linalg.norm(embedding1)

        embedding2 = np.random.rand(128)
        embedding2 = embedding2 / np.linalg.norm(embedding2)

        similarity = recognizer.compare_embeddings(embedding1, embedding2)

        # Should be different
        assert similarity < 0.9
