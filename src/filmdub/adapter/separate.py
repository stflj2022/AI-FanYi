"""
Audio Separation Adapter

Provides a unified interface for source separation
that can be used by M02 (media analysis) and M05 (audio analysis).
Supports separating vocals, drums, bass, and other stems.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path
import logging
import subprocess
import tempfile
import os

logger = logging.getLogger(__name__)


class AudioSeparationAdapterInterface(ABC):
    """Abstract interface for audio separation operations"""

    @abstractmethod
    async def separate(
        self,
        audio_path: Path,
        output_dir: Path,
        stems: Optional[List[str]] = None
    ) -> dict:
        """
        Separate audio into stems

        Args:
            audio_path: Path to input audio file
            output_dir: Directory to save separated stems
            stems: List of stems to extract (e.g., ["vocals", "drums", "bass", "other"])
                   If None, extract all available stems

        Returns:
            Dict mapping stem names to output file paths
        """
        pass

    @abstractmethod
    async def separate_vocals_only(
        self,
        audio_path: Path,
        output_path: Path
    ) -> Path:
        """
        Extract only vocals from audio

        Args:
            audio_path: Path to input audio file
            output_path: Path to save vocals

        Returns:
            Path to vocals file
        """
        pass


class HTDemucsAdapter(AudioSeparationAdapterInterface):
    """HTDemucs audio separation adapter implementation"""

    def __init__(self, model: str = "htdemucs", device: str = "cpu"):
        """
        Initialize HTDemucs adapter

        Args:
            model: Model name (htdemucs, htdemucs_ft, htdemucs_6s, mdx, mdx_extra, mdx_q)
            device: Device to use (cpu, cuda)
        """
        self.model = model
        self.device = device
        self._separator = None
        self._loaded = False

    def _load_model(self):
        """Lazy load the separation model"""
        if not self._loaded:
            try:
                import torch
                from demucs import pretrained
                from demucs.apply import apply_model

                logger.info(f"Loading HTDemucs model: {self.model}")
                self._separator = pretrained.get_model(self.model)
                self._separator.eval()

                if self.device == "cuda" and torch.cuda.is_available():
                    self._separator = self._separator.cuda()
                    logger.info("Using CUDA for HTDemucs")
                else:
                    logger.info("Using CPU for HTDemucs")

                self._loaded = True
                self._apply_model = apply_model

            except ImportError:
                raise ImportError(
                    "demucs not installed. Install with: pip install demucs"
                )

    def _extract_audio_from_video(self, video_path: Path) -> Path:
        """
        Extract audio from video file using ffmpeg if needed

        Args:
            video_path: Path to video file

        Returns:
            Path to extracted audio file (wav format)
        """
        # Check if already an audio file
        if video_path.suffix.lower() not in ['.mp4', '.mkv', '.avi', '.mov', '.webm']:
            return video_path

        # Extract audio using ffmpeg
        temp_dir = Path(tempfile.mkdtemp())
        audio_output = temp_dir / f"{video_path.stem}.wav"

        try:
            subprocess.run([
                'ffmpeg', '-i', str(video_path),
                '-vn', '-acodec', 'pcm_s16le',
                '-ar', '44100', '-ac', '2',
                str(audio_output)
            ], check=True, capture_output=True)
            logger.info(f"Extracted audio from video: {video_path} -> {audio_output}")
            return audio_output
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to extract audio from video: {e}")
            raise RuntimeError(f"Failed to extract audio from video: {e}")

    async def separate(
        self,
        audio_path: Path,
        output_dir: Path,
        stems: Optional[List[str]] = None
    ) -> dict:
        """
        Separate audio into stems using HTDemucs

        Returns:
            Dict mapping stem names to output file paths
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        self._load_model()

        output_dir.mkdir(parents=True, exist_ok=True)

        # Extract audio from video if needed
        input_audio = self._extract_audio_from_video(audio_path)
        is_temp_extracted = input_audio != audio_path

        try:
            import torch
            import torchaudio

            # Load audio - use soundfile backend if torchcodec is not available
            try:
                waveform, sample_rate = torchaudio.load(str(input_audio))
            except (ImportError, RuntimeError):
                # Fallback to soundfile backend
                import torchaudio.transforms as T
                import soundfile as sf
                audio_data, sf_sample_rate = sf.read(str(input_audio))
                sample_rate = sf_sample_rate
                # Convert to tensor and add channel dimension if needed
                waveform = torch.from_numpy(audio_data).float().t()
                if waveform.dim() == 1:
                    waveform = waveform.unsqueeze(0)
                # Ensure stereo
                if waveform.shape[0] == 1:
                    waveform = waveform.repeat(2, 1)

            # Ensure stereo
            if waveform.shape[0] == 1:
                waveform = waveform.repeat(2, 1)

            # Add batch dimension
            waveform = waveform.unsqueeze(0)

            # Move to device
            if self.device == "cuda" and torch.cuda.is_available():
                waveform = waveform.cuda()

            # Apply separation using apply_model
            with torch.no_grad():
                sources = self._apply_model(self._separator, waveform)

            # Get available stems
            available_stems = self._separator.sources
            if stems is None:
                stems = available_stems

            # Save each stem
            result = {}
            for i, stem in enumerate(available_stems):
                if stem in stems:
                    # Remove batch dimension and move to CPU
                    stem_audio = sources[:, i, :, :].squeeze(0).cpu()

                    # Save
                    output_path = output_dir / f"{audio_path.stem}_{stem}.wav"

                    # Try torchaudio.save, fallback to soundfile
                    try:
                        torchaudio.save(str(output_path), stem_audio, sample_rate)
                    except (ImportError, RuntimeError):
                        # Fallback to soundfile
                        import soundfile as sf
                        # Convert to numpy and transpose (channels, samples) -> (samples, channels)
                        stem_numpy = stem_audio.numpy().T
                        sf.write(str(output_path), stem_numpy, sample_rate)

                    result[stem] = output_path
                    logger.info(f"Saved {stem} to {output_path}")

            return result

        except Exception as e:
            logger.error(f"Failed to separate {audio_path}: {e}")
            raise
        finally:
            # Clean up temporary extracted audio
            if is_temp_extracted and input_audio.exists():
                try:
                    os.remove(input_audio)
                    # Remove temp directory if empty
                    input_audio.parent.rmdir()
                except Exception as e:
                    logger.warning(f"Failed to clean up temp audio file: {e}")

    async def separate_vocals_only(
        self,
        audio_path: Path,
        output_path: Path
    ) -> Path:
        """
        Extract only vocals from audio

        Returns:
            Path to vocals file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Separate all stems
        temp_dir = output_path.parent / f"{output_path.stem}_temp"
        result = await self.separate(audio_path, temp_dir, stems=["vocals"])

        # Move vocals to output path
        vocals_path = result.get("vocals")
        if vocals_path:
            import shutil
            shutil.move(str(vocals_path), str(output_path))
            # Clean up temp dir
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            logger.info(f"Extracted vocals to {output_path}")
            return output_path
        else:
            raise RuntimeError("Failed to extract vocals: vocals stem not found")


class AudioSeparationAdapter(AudioSeparationAdapterInterface):
    """
    Factory for creating audio separation adapters

    Currently supports HTDemucs.
    Can be extended for other backends (e.g., Spleeter, Demucs).
    """

    def __init__(self, backend: str = "htdemucs", **kwargs):
        if backend == "htdemucs":
            self._adapter = HTDemucsAdapter(**kwargs)
        else:
            raise ValueError(f"Unsupported separation backend: {backend}")

    async def separate(
        self,
        audio_path: Path,
        output_dir: Path,
        stems: Optional[List[str]] = None
    ) -> dict:
        return await self._adapter.separate(audio_path, output_dir, stems)

    async def separate_vocals_only(
        self,
        audio_path: Path,
        output_path: Path
    ) -> Path:
        return await self._adapter.separate_vocals_only(audio_path, output_path)
