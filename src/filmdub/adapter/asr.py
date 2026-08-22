"""
ASR (Automatic Speech Recognition) Adapter

Provides a unified interface for speech transcription
that can be used by M02 (media analysis) and M05 (audio analysis).
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ASRAdapterInterface(ABC):
    """Abstract interface for ASR operations"""

    @abstractmethod
    async def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        word_timestamps: bool = True
    ) -> Dict[str, Any]:
        """
        Transcribe audio file

        Args:
            audio_path: Path to audio file
            language: Language code (e.g., "en", "zh"). If None, auto-detect
            word_timestamps: Whether to include word-level timestamps

        Returns:
            Dict containing:
                - text: Full transcript
                - segments: List of segment dicts with start, end, text
                - language: Detected language
                - word_segments: (optional) List of word-level timestamps
        """
        pass

    @abstractmethod
    async def transcribe_with_speakers(
        self,
        audio_path: Path,
        num_speakers: Optional[int] = None,
        language: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Transcribe audio with speaker diarization

        Args:
            audio_path: Path to audio file
            num_speakers: Number of speakers (if None, auto-detect)
            language: Language code (if None, auto-detect)

        Returns:
            List of segments with speaker labels:
                - start: Start time
                - end: End time
                - text: Transcript text
                - speaker: Speaker ID (e.g., "SPEAKER_00")
        """
        pass


class FasterWhisperASRAdapter(ASRAdapterInterface):
    """Faster-Whisper ASR adapter implementation"""

    def __init__(self, model_size: str = "large-v3", device: str = "cpu"):
        """
        Initialize Faster-Whisper ASR adapter

        Args:
            model_size: Model size (tiny, base, small, medium, large-v1, large-v2, large-v3)
            device: Device to use (cpu, cuda)
        """
        self.model_size = model_size
        self.device = device
        self._model = None

    def _load_model(self):
        """Lazy load the model"""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                logger.info(f"Loading Faster-Whisper model: {self.model_size}")
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type="int8" if self.device == "cpu" else "float16"
                )
            except ImportError:
                raise ImportError(
                    "faster-whisper not installed. Install with: pip install faster-whisper"
                )

    async def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        word_timestamps: bool = True
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Faster-Whisper

        Returns:
            Dict with text, segments, language, and optionally word_segments
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        self._load_model()

        try:
            segments, info = self._model.transcribe(
                str(audio_path),
                language=language,
                word_timestamps=word_timestamps,
                vad_filter=True  # Use voice activity detection
            )

            # Collect results
            result_segments = []
            all_words = []

            for segment in segments:
                seg_dict = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                }
                result_segments.append(seg_dict)

                if word_timestamps and hasattr(segment, "words"):
                    for word in segment.words:
                        all_words.append({
                            "word": word.word,
                            "start": word.start,
                            "end": word.end
                        })

            result = {
                "text": " ".join([s["text"] for s in result_segments]),
                "segments": result_segments,
                "language": info.language,
                "language_probability": info.language_probability
            }

            if all_words:
                result["word_segments"] = all_words

            logger.info(
                f"Transcribed {audio_path.name}: "
                f"{len(result_segments)} segments, "
                f"language={info.language} ({info.language_probability:.2f})"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to transcribe {audio_path}: {e}")
            raise

    async def transcribe_with_speakers(
        self,
        audio_path: Path,
        num_speakers: Optional[int] = None,
        language: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Transcribe with speaker diarization

        Note: This requires pyannote.audio for speaker diarization.
        Falls back to basic transcription if diarization is not available.
        """
        try:
            from pyannote.audio import Pipeline
        except ImportError:
            logger.warning(
                "pyannote.audio not available, falling back to transcription without speakers"
            )
            result = await self.transcribe(audio_path, language)
            # Return segments with default speaker
            return [
                {
                    "start": s["start"],
                    "end": s["end"],
                    "text": s["text"],
                    "speaker": "SPEAKER_00"
                }
                for s in result["segments"]
            ]

        # Full speaker diarization pipeline
        self._load_model()

        try:
            # Load diarization pipeline
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=False  # May need HF token
            )

            # Run diarization
            diarization = pipeline(str(audio_path))

            # Run transcription
            transcribe_result = await self.transcribe(audio_path, language)

            # Map speakers to segments
            segments_with_speakers = []
            for seg in transcribe_result["segments"]:
                # Find speaker for this segment
                speaker = "SPEAKER_00"
                mid_time = (seg["start"] + seg["end"]) / 2
                for turn, _, spk in diarization.itertracks(yield_label=True):
                    if turn.start <= mid_time <= turn.end:
                        speaker = spk
                        break

                segments_with_speakers.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"],
                    "speaker": speaker
                })

            logger.info(
                f"Transcribed with speakers: {len(segments_with_speakers)} segments"
            )

            return segments_with_speakers

        except Exception as e:
            logger.error(f"Speaker diarization failed: {e}, falling back to basic transcription")
            result = await self.transcribe(audio_path, language)
            return [
                {
                    "start": s["start"],
                    "end": s["end"],
                    "text": s["text"],
                    "speaker": "SPEAKER_00"
                }
                for s in result["segments"]
            ]


class ASRAdapter(ASRAdapterInterface):
    """
    Factory for creating ASR adapters

    Currently supports Faster-Whisper.
    Can be extended for other ASR backends (e.g., qwen-tts ASR if available).
    """

    def __init__(self, backend: str = "faster-whisper", **kwargs):
        if backend == "faster-whisper":
            self._adapter = FasterWhisperASRAdapter(**kwargs)
        else:
            raise ValueError(f"Unsupported ASR backend: {backend}")

    async def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        word_timestamps: bool = True
    ) -> Dict[str, Any]:
        return await self._adapter.transcribe(audio_path, language, word_timestamps)

    async def transcribe_with_speakers(
        self,
        audio_path: Path,
        num_speakers: Optional[int] = None,
        language: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return await self._adapter.transcribe_with_speakers(
            audio_path, num_speakers, language
        )
