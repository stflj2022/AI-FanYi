"""Face detector and recognizer implementations."""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None

if not CV2_AVAILABLE:
    logging.warning("OpenCV (cv2) not available. Face tracking features will be disabled.")

from .config import FaceTrackingConfig, get_config
from .models import FaceDetection

logger = logging.getLogger(__name__)


class FaceDetector:
    """Face detector using OpenCV DNN."""

    def __init__(self, config: Optional[FaceTrackingConfig] = None):
        """Initialize face detector."""
        self.config = config or get_config()
        self.model: Optional[cv2.dnn.Net] = None
        self._load_model()

    def _load_model(self):
        """Load face detection model."""
        if not CV2_AVAILABLE:
            self.cascade = None
            return

        try:
            # Use OpenCV's DNN module with a pre-trained model
            # For now, use Haar cascade as fallback
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.cascade = cv2.CascadeClassifier(cascade_path)

            if self.cascade.empty():
                logger.warning("Failed to load Haar cascade, face detection will not work")
            else:
                logger.info("Face detector initialized with Haar cascade")

        except Exception as e:
            logger.error(f"Failed to load face detection model: {e}")
            self.cascade = None

    def detect_faces(
        self,
        frame: np.ndarray,
        frame_number: int = 0,
        timestamp: float = 0.0,
    ) -> List[FaceDetection]:
        """Detect faces in a frame."""
        if not CV2_AVAILABLE or self.cascade is None:
            logger.warning("Face detector not available")
            return []

        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect faces
            faces = self.cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(self.config.min_face_size, self.config.min_face_size),
            )

            detections = []
            for i, (x, y, w, h) in enumerate(faces):
                # Check confidence (Haar cascade doesn't provide confidence, use size as proxy)
                confidence = min(1.0, (w * h) / (100 * 100))

                if confidence < self.config.detection_confidence:
                    continue

                detection = FaceDetection(
                    face_id=f"face_{frame_number}_{i}",
                    bbox=[int(x), int(y), int(w), int(h)],
                    confidence=float(confidence),
                    frame_number=frame_number,
                    timestamp=timestamp,
                )

                detections.append(detection)

            return detections

        except Exception as e:
            logger.error(f"Error detecting faces in frame {frame_number}: {e}")
            return []

    def extract_face_crop(
        self, frame: np.ndarray, bbox: List[int]
    ) -> Optional[np.ndarray]:
        """Extract face crop from frame."""
        try:
            x, y, w, h = bbox
            # Add padding
            padding = int(0.2 * max(w, h))
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(frame.shape[1], x + w + padding)
            y2 = min(frame.shape[0], y + h + padding)

            return frame[y1:y2, x1:x2].copy()

        except Exception as e:
            logger.error(f"Error extracting face crop: {e}")
            return None


class FaceRecognizer:
    """Face recognizer for computing embeddings."""

    def __init__(self, config: Optional[FaceTrackingConfig] = None):
        """Initialize face recognizer."""
        self.config = config or get_config()
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load face recognition model."""
        try:
            # For now, use a simple approach: compute embeddings from face crops
            # In production, this would load a model like ArcFace or FaceNet
            logger.info("Face recognizer initialized (using simple features)")
        except Exception as e:
            logger.error(f"Failed to load face recognition model: {e}")

    def compute_embedding(self, face_crop: np.ndarray) -> Optional[np.ndarray]:
        """Compute face embedding."""
        if not CV2_AVAILABLE:
            return None

        try:
            if face_crop is None or face_crop.size == 0:
                return None

            # Resize to standard size
            face_resized = cv2.resize(face_crop, (128, 128))

            # Convert to grayscale
            if len(face_resized.shape) == 3:
                face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
            else:
                face_gray = face_resized

            # Normalize
            face_normalized = face_gray.astype(np.float32) / 255.0

            # Flatten as simple embedding (in production, use deep learning model)
            embedding = face_normalized.flatten()

            # Normalize embedding
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            return embedding

        except Exception as e:
            logger.error(f"Error computing face embedding: {e}")
            return None

    def compare_embeddings(
        self, embedding1: np.ndarray, embedding2: np.ndarray
    ) -> float:
        """Compare two face embeddings, return similarity score."""
        try:
            if embedding1 is None or embedding2 is None:
                return 0.0

            # Validate shape consistency - fail early on mismatch
            if embedding1.shape != embedding2.shape:
                logger.warning(
                    f"Embedding shape mismatch: {embedding1.shape} vs {embedding2.shape}"
                )
                return 0.0

            # Compute cosine similarity
            dot_product = np.dot(embedding1, embedding2)
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            return float(similarity)

        except Exception as e:
            logger.error(f"Error comparing embeddings: {e}")
            return 0.0
