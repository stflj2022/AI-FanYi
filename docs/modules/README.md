# FilmDub AI

A modular, worker-based AI film dubbing system.

## Architecture

FilmDub AI is built on the principle of independent, serially-executed workers:

```
User Input
    ↓
Module 01: Project & Media Intake (CPU)
    ↓
Module 02: Research (CPU + LLM)
    ↓
Module 03: Character Database (CPU)
    ↓
Module 04: Audio Analysis (GPU - Speaker Diarization)
    ↓
Module 05: Speaker → Character Mapping (CPU)
    ↓
Module 06: Voice Profile (CPU)
    ↓
Module 07: Subtitle Manager (CPU)
    ↓
Module 08: Dialogue Alignment (GPU - WhisperX)
    ↓
Module 09: Plot Memory (CPU + LLM)
    ↓
Module 10: Translation (CPU + LLM, optional)
    ↓
Module 11: TTS (GPU - Qwen3-TTS)
    ↓
Module 12: Timing (CPU)
    ↓
Module 13: Source Separation (GPU)
    ↓
Module 14: Mixing (CPU)
    ↓
Module 15: Render (FFmpeg)
    ↓
Module 16: QC + Human Review
    ↓
Final Output
```

## Key Principles

1. **Independent Workers**: Each module is a separate process that exits when done
2. **Serial Execution**: Workers run one at a time, freeing GPU resources between modules
3. **No Cross-Module Imports**: Modules communicate only via standard files/APIs
4. **Immutable Assets**: Original media files are never modified
5. **Standardized Data Exchange**: JSON, JSONL, WAV, SRT/VTT, SQLite

## Project Structure

```
filmdub/
├── apps/
│   ├── api/          # FastAPI backend
│   └── web/          # Next.js frontend
├── core/
│   ├── config/       # Configuration
│   ├── database/     # Database connection
│   ├── models/       # SQLAlchemy models
│   ├── schemas/      # Pydantic schemas
│   └── storage/      # File storage management
├── workers/
│   └── media_intake/ # Module 01 worker
├── migrations/       # Database migrations
├── tests/            # Test suite
├── docker/           # Docker configurations
├── scripts/          # Utility scripts
└── projects/         # Project data storage
```

## Module 01: Project & Media Intake

**Definition**: Project & Media Intake is the immutable ingestion layer of FilmDub AI. It converts user-supplied audiovisual files into validated, hashed, versioned Project/Episode/Media assets and machine-readable manifests, without performing any AI inference or modifying the source media.

### Capabilities
- File upload and integrity checking (SHA-256)
- FFprobe media analysis
- Video/Audio/Subtitle stream extraction
- Project/Episode/Media ID generation
- SQLite database initialization
- Job system with status tracking

### What Module 01 Does NOT Do
- IMDb/TMDB search
- Character recognition
- ASR/Whisper
- Speaker diarization
- Translation
- TTS
- Source separation
- Video re-encoding

## Getting Started

### Prerequisites
- Python 3.12+
- FFmpeg / FFprobe
- Docker (optional, for containerized deployment)

### Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install FFmpeg (Debian/Ubuntu)
sudo apt install ffmpeg
```

### Running Module 01

```bash
# Create a project
python -m filmdub.cli project create --title "Breaking Bad" --target-language zh-CN

# Import media
python -m filmdub.cli media import --project proj_01JABC /path/to/video.mkv

# Start API server
python -m filmdub.apps.api.main

# Start web UI
cd apps/web && npm run dev
```

## License

MIT
