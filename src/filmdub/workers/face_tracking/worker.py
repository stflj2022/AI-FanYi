"""M03 Face Tracking Worker implementation."""

import logging
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID, uuid4

import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None

from .config import FaceTrackingConfig, get_config
from .detector import FaceDetector, FaceRecognizer
from .models import (
    CharacterAppearance,
    FaceDetection,
    FaceTrack,
    M03Input,
    M03Output,
)

logger = logging.getLogger(__name__)


class M03Worker:
    """M03 Face Tracking Worker - detects and tracks faces in video."""

    def __init__(
        self,
        config: Optional[FaceTrackingConfig] = None,
        detector: Optional[FaceDetector] = None,
        recognizer: Optional[FaceRecognizer] = None,
    ):
        """Initialize M03 Worker."""
        self.config = config or get_config()
        self.detector = detector or FaceDetector(self.config)
        self.recognizer = recognizer or FaceRecognizer(self.config)

    async def process(self, input_data: M03Input) -> M03Output:
        """Process face tracking task."""
        logger.info(f"Starting face tracking for {input_data.video_path}")

        video_path = Path(input_data.video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {input_data.video_path}")

        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV not available, cannot process video")

        # Open video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video: {input_data.video_path}")

        try:
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0

            logger.info(
                f"Video: {total_frames} frames, {fps:.2f} FPS, {duration:.2f}s"
            )

            # Process frames
            all_detections = []
            frame_number = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Sample frames
                if frame_number % input_data.sampling_rate != 0:
                    frame_number += 1
                    continue

                timestamp = frame_number / fps if fps > 0 else 0

                # Detect faces
                detections = self.detector.detect_faces(
                    frame, frame_number, timestamp
                )

                # Extract embeddings
                for detection in detections:
                    face_crop = self.detector.extract_face_crop(frame, detection.bbox)
                    if face_crop is not None:
                        embedding = self.recognizer.compute_embedding(face_crop)
                        detection.embedding = embedding

                all_detections.extend(detections)

                frame_number += 1

                if frame_number % 100 == 0:
                    logger.debug(f"Processed {frame_number}/{total_frames} frames")

            # Create tracks
            tracks = self._create_tracks(all_detections)

            # Match to characters
            character_appearances = self._match_to_characters(
                tracks, input_data.character_database
            )

            logger.info(
                f"Face tracking completed: {len(all_detections)} detections, "
                f"{len(tracks)} tracks, {len(character_appearances)} characters"
            )

            return M03Output(
                project_id=input_data.project_id,
                job_id=input_data.job_id,
                video_path=str(video_path),
                total_frames=total_frames,
                fps=fps,
                duration=duration,
                faces_detected=len(all_detections),
                tracks_created=len(tracks),
                characters_found=len(character_appearances),
                face_tracks=tracks,
                character_appearances=character_appearances,
            )

        finally:
            cap.release()

    def _find_matching_track(
        self, detection: FaceDetection, tracks: List[FaceTrack]
    ) -> Optional[FaceTrack]:
        """Find a matching track for a detection based on temporal and similarity criteria."""
        for track in tracks:
            # Check temporal proximity
            if abs(detection.frame_number - track.last_frame) > self.config.max_age:
                continue

            # Check embedding similarity
            if (
                track.representative_embedding is not None
                and detection.embedding is not None
            ):
                similarity = self.recognizer.compare_embeddings(
                    track.representative_embedding, detection.embedding
                )

                if similarity > self.config.recognition_threshold:
                    return track

        return None

    def _update_track(self, track: FaceTrack, detection: FaceDetection) -> None:
        """Update a track with a new detection."""
        track.detections.append(detection)
        track.last_frame = detection.frame_number
        track.total_frames += 1
        # Update average confidence using moving average
        track.average_confidence = (
            track.average_confidence * (len(track.detections) - 1) + detection.confidence
        ) / len(track.detections)

    def _create_track(self, track_id: int, detection: FaceDetection) -> FaceTrack:
        """Create a new track from a detection."""
        return FaceTrack(
            track_id=f"track_{track_id}",
            detections=[detection],
            first_frame=detection.frame_number,
            last_frame=detection.frame_number,
            total_frames=1,
            average_confidence=detection.confidence,
            representative_embedding=detection.embedding,
        )

    def _create_tracks(self, detections: List[FaceDetection]) -> List[FaceTrack]:
        """Create face tracks from detections using simple clustering."""
        if not detections:
            return []

        tracks: List[FaceTrack] = []
        track_id_counter = 0

        for detection in detections:
            # Try to find matching existing track
            matched_track = self._find_matching_track(detection, tracks)

            if matched_track:
                # Update existing track
                self._update_track(matched_track, detection)
            else:
                # Create new track
                new_track = self._create_track(track_id_counter, detection)
                tracks.append(new_track)
                track_id_counter += 1

        return tracks

    def _match_to_characters(
        self, tracks: List[FaceTrack], character_database: Optional[Dict]
    ) -> List[CharacterAppearance]:
        """Match face tracks to characters from database."""
        appearances = []

        if not character_database or "characters" not in character_database:
            # Create unknown character appearances
            for track in tracks:
                appearance = CharacterAppearance(
                    character_id=None,
                    character_name=f"Unknown_{track.track_id}",
                    track_ids=[track.track_id],
                    appearances=[
                        {
                            "track_id": track.track_id,
                            "first_frame": track.first_frame,
                            "last_frame": track.last_frame,
                            "total_frames": track.total_frames,
                            "average_confidence": track.average_confidence,
                        }
                    ],
                    total_screen_time=track.total_frames / 30.0,  # Approximate
                    first_appearance=track.first_frame / 30.0,
                    last_appearance=track.last_frame / 30.0,
                )
                appearances.append(appearance)
            return appearances

        # Match to known characters (simplified - would need character face embeddings in real implementation)
        characters = character_database.get("characters", [])

        for i, track in enumerate(tracks):
            # For now, assign to character based on index (real implementation would use face matching)
            if i < len(characters):
                char = characters[i]
                character_id = UUID(char.get("id", str(uuid4())))
                character_name = char.get("name", f"Character_{i}")
            else:
                character_id = None
                character_name = f"Unknown_{track.track_id}"

            appearance = CharacterAppearance(
                character_id=character_id,
                character_name=character_name,
                track_ids=[track.track_id],
                appearances=[
                    {
                        "track_id": track.track_id,
                        "first_frame": track.first_frame,
                        "last_frame": track.last_frame,
                        "total_frames": track.total_frames,
                        "average_confidence": track.average_confidence,
                    }
                ],
                total_screen_time=track.total_frames / 30.0,
                first_appearance=track.first_frame / 30.0,
                last_appearance=track.last_frame / 30.0,
            )
            appearances.append(appearance)

        return appearances
