"""M03 Worker tests."""

import tempfile
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None

from filmdub.workers.face_tracking.config import FaceTrackingConfig
from filmdub.workers.face_tracking.detector import FaceDetector, FaceRecognizer
from filmdub.workers.face_tracking.models import M03Input
from filmdub.workers.face_tracking.worker import M03Worker


class TestM03Worker:
    """Test M03 Face Tracking Worker."""

    def test_init_default(self):
        """Test initialization with defaults."""
        worker = M03Worker()

        assert worker.config is not None
        assert worker.detector is not None
        assert worker.recognizer is not None

    def test_init_custom(self):
        """Test initialization with custom components."""
        config = FaceTrackingConfig(min_face_size=30)
        detector = FaceDetector(config)
        recognizer = FaceRecognizer(config)

        worker = M03Worker(config=config, detector=detector, recognizer=recognizer)

        assert worker.config.min_face_size == 30
        assert worker.detector is detector
        assert worker.recognizer is recognizer

    @pytest.mark.asyncio
    async def test_process_nonexistent_video(self):
        """Test processing nonexistent video."""
        worker = M03Worker()

        input_data = M03Input(
            project_id=uuid4(),
            job_id=uuid4(),
            video_path="/nonexistent/video.mp4",
        )

        with pytest.raises(FileNotFoundError):
            await worker.process(input_data)

    @pytest.mark.asyncio
    async def test_process_simple_video(self):
        """Test processing a simple test video."""
        # Create a temporary test video
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "test_video.mp4"

            # Create a simple video with 10 frames
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(str(video_path), fourcc, 30.0, (320, 240))

            for i in range(30):  # 1 second at 30 fps
                frame = np.zeros((240, 320, 3), dtype=np.uint8)
                # Draw a face-like region
                cv2.rectangle(frame, (100, 80), (220, 160), (200, 200, 200), -1)
                # Add text with frame number
                cv2.putText(
                    frame, str(i), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2
                )
                out.write(frame)

            out.release()

            # Process the video
            worker = M03Worker()
            input_data = M03Input(
                project_id=uuid4(),
                job_id=uuid4(),
                video_path=str(video_path),
                sampling_rate=5,  # Sample every 5 frames
            )

            output = await worker.process(input_data)

            assert output.project_id == input_data.project_id
            assert output.job_id == input_data.job_id
            assert output.total_frames == 30
            assert output.fps == pytest.approx(30.0, abs=1.0)
            assert output.duration == pytest.approx(1.0, abs=0.1)
            assert output.faces_detected >= 0
            assert output.tracks_created >= 0
            assert isinstance(output.face_tracks, list)
            assert isinstance(output.character_appearances, list)

    @pytest.mark.asyncio
    async def test_create_tracks_empty(self):
        """Test creating tracks from empty detections."""
        worker = M03Worker()

        tracks = worker._create_tracks([])

        assert tracks == []

    def test_create_tracks_simple(self):
        """Test creating tracks from simple detections."""
        worker = M03Worker()

        from filmdub.workers.face_tracking.models import FaceDetection

        # Create some detections
        detections = [
            FaceDetection(
                face_id="face_0_0",
                bbox=[100, 100, 50, 50],
                confidence=0.9,
                embedding=np.random.rand(128),
                frame_number=0,
                timestamp=0.0,
            ),
            FaceDetection(
                face_id="face_5_0",
                bbox=[105, 105, 50, 50],
                confidence=0.85,
                embedding=np.random.rand(128),
                frame_number=5,
                timestamp=0.17,
            ),
        ]

        tracks = worker._create_tracks(detections)

        assert len(tracks) >= 1

    def test_match_to_characters_no_database(self):
        """Test matching to characters without database."""
        worker = M03Worker()

        from filmdub.workers.face_tracking.models import FaceDetection, FaceTrack

        track = FaceTrack(
            track_id="track_0",
            detections=[
                FaceDetection(
                    face_id="face_0",
                    bbox=[100, 100, 50, 50],
                    confidence=0.9,
                    frame_number=0,
                    timestamp=0.0,
                )
            ],
            first_frame=0,
            last_frame=0,
            total_frames=1,
            average_confidence=0.9,
        )

        appearances = worker._match_to_characters([track], None)

        assert len(appearances) == 1
        assert appearances[0].character_id is None
        assert "Unknown" in appearances[0].character_name

    def test_match_to_characters_with_database(self):
        """Test matching to characters with database."""
        worker = M03Worker()

        from filmdub.workers.face_tracking.models import FaceDetection, FaceTrack

        track = FaceTrack(
            track_id="track_0",
            detections=[
                FaceDetection(
                    face_id="face_0",
                    bbox=[100, 100, 50, 50],
                    confidence=0.9,
                    frame_number=0,
                    timestamp=0.0,
                )
            ],
            first_frame=0,
            last_frame=0,
            total_frames=1,
            average_confidence=0.9,
        )

        character_database = {
            "characters": [
                {"id": str(uuid4()), "name": "John Doe"},
            ]
        }

        appearances = worker._match_to_characters([track], character_database)

        assert len(appearances) == 1
        # Should match to the first character
        assert "John Doe" in appearances[0].character_name
