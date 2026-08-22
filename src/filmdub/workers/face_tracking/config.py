"""Face tracking module configuration."""

from pydantic_settings import BaseSettings


class FaceTrackingConfig(BaseSettings):
    """Face tracking module configuration."""

    # Face detection model
    detection_model: str = "retinaface"  # retinaface, mtcnn, yoloface
    detection_confidence: float = 0.7

    # Face recognition model
    recognition_model: str = "arcface"  # arcface, facenet
    recognition_threshold: float = 0.5

    # Clustering
    clustering_algorithm: str = "dbscan"  # dbscan, agglomerative
    clustering_eps: float = 0.5
    clustering_min_samples: int = 3

    # Tracking
    tracking_iou_threshold: float = 0.3
    max_age: int = 30

    # Sampling
    frame_sample_rate: int = 5  # Sample every N frames
    min_face_size: int = 50  # Minimum face size in pixels

    # Output
    output_dir: str = "data/face_tracking"
    save_embeddings: bool = True
    save_crops: bool = False

    class Config:
        env_prefix = "FACE_TRACKING_"
        env_file = ".env"
        extra = "forbid"  # 禁止额外字段，确保配置严格


def get_config() -> FaceTrackingConfig:
    """Get face tracking configuration."""
    return FaceTrackingConfig()
