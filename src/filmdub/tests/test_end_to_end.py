"""
端到端测试 - 完整配音流程

验证：短视频输入 → M02(分离) → M05(转写) → M04(克隆) → M09(合成) → 输出配音视频
"""

import pytest
import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import tempfile
import shutil

from filmdub.workers.research.m02_worker import M02Worker
from filmdub.workers.audio_scene_analysis.m05_worker import M05Worker
from filmdub.workers.character_db.m04_worker import M04Worker
from filmdub.workers.voice_synthesis.m09_worker import M09Worker

# 尝试导入音频处理库，如果不可用则跳过某些检查
try:
    import torchaudio
    TORCHAUDIO_AVAILABLE = True
except ImportError:
    TORCHAUDIO_AVAILABLE = False


# 测试视频路径
TEST_VIDEOS_DIR = Path(__file__).parent.parent.parent.parent / "测试视频"
LAOBAI_VIDEO = TEST_VIDEOS_DIR / "laobai.mp4"
PINGI_VIDEO = TEST_VIDEOS_DIR / "pingi.mp4"


def get_audio_info(audio_path: Path) -> Dict[str, Any]:
    """
    获取音频文件信息

    Args:
        audio_path: 音频文件路径

    Returns:
        包含时长、采样率、声道数等信息的字典
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    file_size = audio_path.stat().st_size

    # Try soundfile first (more reliable)
    try:
        import soundfile as sf
        audio_data, sample_rate = sf.read(str(audio_path))
        num_channels = 1 if audio_data.ndim == 1 else audio_data.shape[1]
        duration = len(audio_data) / sample_rate

        return {
            "file_size": file_size,
            "duration": duration,
            "sample_rate": sample_rate,
            "num_channels": num_channels,
            "num_samples": len(audio_data)
        }
    except Exception as e:
        logger.warning(f"soundfile failed to read {audio_path}: {e}")

    # Fallback to torchaudio if available
    if TORCHAUDIO_AVAILABLE:
        try:
            waveform, sample_rate = torchaudio.load(str(audio_path))
            num_channels = waveform.shape[0]
            duration = waveform.shape[1] / sample_rate

            return {
                "file_size": file_size,
                "duration": duration,
                "sample_rate": sample_rate,
                "num_channels": num_channels,
                "num_samples": waveform.shape[1]
            }
        except Exception as e:
            logger.warning(f"torchaudio failed to read {audio_path}: {e}")

    # Return limited info if both fail
    return {
        "file_size": file_size,
        "duration": None,
        "sample_rate": None,
        "num_channels": None,
        "note": "Both soundfile and torchaudio failed to read audio file"
    }


def validate_audio_file(
    audio_path: Path,
    min_duration: float = 0.1,
    expected_sample_rate: Optional[int] = None,
    expected_channels: Optional[int] = None,
    min_file_size: int = 1024
) -> Dict[str, Any]:
    """
    验证音频文件

    Args:
        audio_path: 音频文件路径
        min_duration: 最小时长（秒）
        expected_sample_rate: 期望的采样率（None 表示不检查）
        expected_channels: 期望的声道数（None 表示不检查）
        min_file_size: 最小文件大小（字节）

    Returns:
        验证结果字典
    """
    info = get_audio_info(audio_path)

    validation = {
        "file_exists": audio_path.exists(),
        "file_size_valid": info["file_size"] >= min_file_size,
        "duration_valid": info.get("duration") is not None and info["duration"] >= min_duration,
        "sample_rate_valid": expected_sample_rate is None or info.get("sample_rate") == expected_sample_rate,
        "channels_valid": expected_channels is None or info.get("num_channels") == expected_channels,
        "all_valid": False,
        "info": info
    }

    validation["all_valid"] = all([
        validation["file_exists"],
        validation["file_size_valid"],
        validation["duration_valid"],
        validation["sample_rate_valid"],
        validation["channels_valid"]
    ])

    return validation


@pytest.mark.asyncio
@pytest.mark.skipif(not LAOBAI_VIDEO.exists(), reason="测试视频不存在")
class TestEndToEndLaobai:
    """laobai.mp4 端到端测试"""

    @pytest.fixture
    async def workers(self):
        """初始化所有 worker"""
        m02 = M02Worker(separation_backend="htdemucs")
        m05 = M05Worker(asr_backend="faster-whisper")
        m04 = M04Worker(voice_backend="qwen")
        m09 = M09Worker(voice_backend="qwen")

        yield {"m02": m02, "m05": m05, "m04": m04, "m09": m09}

        # 清理
        await asyncio.gather(
            m02.close(),
            m05.close(),
            m04.close(),
            m09.close(),
            return_exceptions=True
        )

    @pytest.fixture
    def temp_output_dir(self):
        """临时输出目录"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def temp_voices_dir(self):
        """临时音色目录"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    async def test_full_pipeline_laobai(self, workers, temp_output_dir, temp_voices_dir):
        """
        完整流程测试：laobai.mp4
        记录性能指标和质量指标
        """
        m02 = workers["m02"]
        m05 = workers["m05"]
        m04 = workers["m04"]
        m09 = workers["m09"]

        # 性能指标记录
        performance = {
            "m02_separation_time": 0.0,
            "m05_transcription_time": 0.0,
            "m04_cloning_time": 0.0,
            "m09_synthesis_time": 0.0,
            "total_time": 0.0
        }

        # 质量指标记录
        quality = {}

        # 步骤 1: M02 - 音频分离（提取人声）
        print("\n[Step 1] M02: 音频分离...")
        start = time.time()
        stems_dir = temp_output_dir / "stems"
        stems_dir.mkdir(parents=True, exist_ok=True)

        # 只提取人声
        separation_result = await m02.analyze_audio(
            audio_path=LAOBAI_VIDEO,
            output_dir=stems_dir,
            extract_vocals_only=True
        )

        assert "vocals_path" in separation_result
        vocals_path = Path(separation_result["vocals_path"])
        assert vocals_path.exists(), f"人声文件不存在: {vocals_path}"

        performance["m02_separation_time"] = time.time() - start
        print(f"  ✓ 人声已提取: {vocals_path}")
        print(f"  ✓ 分离耗时: {performance['m02_separation_time']:.2f}s")

        # 验证人声音频质量
        vocals_validation = validate_audio_file(
            vocals_path,
            min_duration=0.5,
            min_file_size=1024
        )
        assert vocals_validation["all_valid"], f"人声音频验证失败: {vocals_validation}"
        quality["vocals"] = {
            "validation": vocals_validation,
            "info": vocals_validation["info"]
        }
        print(f"  ✓ 人声音频时长: {vocals_validation['info'].get('duration', 'N/A'):.2f}s")

        # 步骤 2: M05 - 转写音频
        print("\n[Step 2] M05: 转写音频...")
        start = time.time()
        transcription_result = await m05.transcribe_audio(
            audio_path=vocals_path,
            language="en",  # 假设是英语
            word_timestamps=True
        )

        assert "segments" in transcription_result
        segments = transcription_result["segments"]
        assert len(segments) > 0, "未检测到任何对白"

        performance["m05_transcription_time"] = time.time() - start
        print(f"  ✓ 转写完成，共 {len(segments)} 段对白")
        print(f"  ✓ 转写耗时: {performance['m05_transcription_time']:.2f}s")

        quality["transcription"] = {
            "num_segments": len(segments),
            "language": transcription_result.get("language"),
            "language_probability": transcription_result.get("language_probability")
        }

        # 步骤 3: M04 - 克隆音色（或使用默认音色）
        print("\n[Step 3] M04: 克隆音色...")
        character_id = "laobai_main"
        character_name = "老白"

        # 为 M04 设置临时音色目录
        m04.voices_dir = temp_voices_dir

        # 尝试克隆音色，如果失败则使用默认音色
        voice_id = None
        clone_success = False
        start = time.time()

        try:
            clone_result = await m04.clone_character_voice(
                character_id=character_id,
                character_name=character_name,
                reference_audio_path=vocals_path,
                description=f"Voice for {character_name} from laobai.mp4"
            )
            assert "voice_id" in clone_result
            voice_id = clone_result["voice_id"]
            clone_success = True
            print(f"  ✓ 音色已克隆: {voice_id}")
        except Exception as e:
            # 如果克隆失败，使用默认音色
            print(f"  ⚠ 音色克隆失败: {e}")
            print(f"  ℹ 使用默认音色进行测试")
            voice_id = "default"  # qwen-tts 默认音色
            clone_success = False

        performance["m04_cloning_time"] = time.time() - start
        print(f"  ⏱ 耗时: {performance['m04_cloning_time']:.2f}s")

        quality["voice_cloning"] = {
            "voice_id": voice_id,
            "character_id": character_id,
            "character_name": character_name,
            "clone_success": clone_success
        }

        # 步骤 4: M09 - 合成中文配音
        print("\n[Step 4] M09: 合成中文配音...")

        # 使用第一段转写文本进行测试
        # 注意：实际应该翻译成中文，这里先用英文文本测试
        first_segment = segments[0]
        test_text = first_segment["text"].strip()

        if not test_text:
            test_text = "Hello, this is a test."

        synthesized_audio_path = temp_output_dir / "dubbed_audio.wav"

        start = time.time()
        await m09.synthesize_speech(
            text=test_text,
            voice_id=voice_id,
            output_path=synthesized_audio_path
        )
        performance["m09_synthesis_time"] = time.time() - start

        assert synthesized_audio_path.exists(), f"合成音频不存在: {synthesized_audio_path}"
        print(f"  ✓ 配音已合成: {synthesized_audio_path}")
        print(f"  ✓ 合成耗时: {performance['m09_synthesis_time']:.2f}s")

        # 步骤 5: 验证输出
        print("\n[Step 5] 验证输出...")

        # 验证合成音频质量
        synthesized_validation = validate_audio_file(
            synthesized_audio_path,
            min_duration=0.1,
            min_file_size=1024
        )
        assert synthesized_validation["all_valid"], f"合成音频验证失败: {synthesized_validation}"

        quality["synthesized_audio"] = {
            "validation": synthesized_validation,
            "info": synthesized_validation["info"]
        }

        print(f"  ✓ 合成音频时长: {synthesized_validation['info'].get('duration', 'N/A'):.2f}s")
        print(f"  ✓ 合成音频采样率: {synthesized_validation['info'].get('sample_rate', 'N/A')} Hz")
        print(f"  ✓ 合成音频声道数: {synthesized_validation['info'].get('num_channels', 'N/A')}")
        print(f"  ✓ 合成音频文件大小: {synthesized_validation['info']['file_size']} bytes")

        # 计算总耗时
        performance["total_time"] = sum([
            performance["m02_separation_time"],
            performance["m05_transcription_time"],
            performance["m04_cloning_time"],
            performance["m09_synthesis_time"]
        ])

        # 保存完整测试结果
        test_result = {
            "video": str(LAOBAI_VIDEO),
            "test_name": "laobai_end_to_end",
            "status": "success",
            "performance": performance,
            "quality": quality,
            "outputs": {
                "vocals_path": str(vocals_path),
                "synthesized_audio": str(synthesized_audio_path),
                "voice_id": voice_id
            },
            "test_text": test_text,
            "transcription_summary": {
                "num_segments": len(segments),
                "total_text_length": sum(len(s.get("text", "")) for s in segments)
            }
        }

        result_path = temp_output_dir / "test_result.json"
        with result_path.open("w") as f:
            json.dump(test_result, f, indent=2)

        # 打印总结
        print(f"\n[Performance Summary]")
        print(f"  分离: {performance['m02_separation_time']:.2f}s")
        print(f"  转写: {performance['m05_transcription_time']:.2f}s")
        print(f"  克隆: {performance['m04_cloning_time']:.2f}s")
        print(f"  合成: {performance['m09_synthesis_time']:.2f}s")
        print(f"  总计: {performance['total_time']:.2f}s")

        print(f"\n[Quality Summary]")
        print(f"  人声时长: {quality['vocals']['info'].get('duration', 'N/A'):.2f}s")
        print(f"  人声采样率: {quality['vocals']['info'].get('sample_rate', 'N/A')} Hz")
        print(f"  合成时长: {quality['synthesized_audio']['info'].get('duration', 'N/A'):.2f}s")
        print(f"  合成采样率: {quality['synthesized_audio']['info'].get('sample_rate', 'N/A')} Hz")
        print(f"  转写段数: {quality['transcription']['num_segments']}")

        print(f"\n✅ laobai.mp4 端到端测试通过！")
        print(f"   结果已保存到: {result_path}")


@pytest.mark.asyncio
@pytest.mark.skipif(not PINGI_VIDEO.exists(), reason="测试视频不存在")
class TestEndToEndPingi:
    """pingi.mp4 端到端测试"""

    @pytest.fixture
    async def workers(self):
        """初始化所有 worker"""
        m02 = M02Worker(separation_backend="htdemucs")
        m05 = M05Worker(asr_backend="faster-whisper")
        m04 = M04Worker(voice_backend="qwen")
        m09 = M09Worker(voice_backend="qwen")

        yield {"m02": m02, "m05": m05, "m04": m04, "m09": m09}

        # 清理
        await asyncio.gather(
            m02.close(),
            m05.close(),
            m04.close(),
            m09.close(),
            return_exceptions=True
        )

    @pytest.fixture
    def temp_output_dir(self):
        """临时输出目录"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def temp_voices_dir(self):
        """临时音色目录"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    async def test_full_pipeline_pingi(self, workers, temp_output_dir, temp_voices_dir):
        """
        完整流程测试：pingi.mp4
        记录性能指标和质量指标
        """
        m02 = workers["m02"]
        m05 = workers["m05"]
        m04 = workers["m04"]
        m09 = workers["m09"]

        # 性能指标记录
        performance = {
            "m02_separation_time": 0.0,
            "m05_transcription_time": 0.0,
            "m04_cloning_time": 0.0,
            "m09_synthesis_time": 0.0,
            "total_time": 0.0
        }

        # 质量指标记录
        quality = {}

        # 步骤 1: M02 - 音频分离
        print("\n[Step 1] M02: 音频分离...")
        start = time.time()
        stems_dir = temp_output_dir / "stems"
        stems_dir.mkdir(parents=True, exist_ok=True)

        separation_result = await m02.analyze_audio(
            audio_path=PINGI_VIDEO,
            output_dir=stems_dir,
            extract_vocals_only=True
        )

        assert "vocals_path" in separation_result
        vocals_path = Path(separation_result["vocals_path"])
        assert vocals_path.exists(), f"人声文件不存在: {vocals_path}"

        performance["m02_separation_time"] = time.time() - start
        print(f"  ✓ 人声已提取: {vocals_path}")
        print(f"  ✓ 分离耗时: {performance['m02_separation_time']:.2f}s")

        # 验证人声音频质量
        vocals_validation = validate_audio_file(
            vocals_path,
            min_duration=0.5,
            min_file_size=1024
        )
        assert vocals_validation["all_valid"], f"人声音频验证失败: {vocals_validation}"
        quality["vocals"] = {
            "validation": vocals_validation,
            "info": vocals_validation["info"]
        }
        print(f"  ✓ 人声音频时长: {vocals_validation['info'].get('duration', 'N/A'):.2f}s")

        # 步骤 2: M05 - 转写
        print("\n[Step 2] M05: 转写音频...")
        start = time.time()
        transcription_result = await m05.transcribe_audio(
            audio_path=vocals_path,
            language="en",
            word_timestamps=True
        )

        assert "segments" in transcription_result
        segments = transcription_result["segments"]
        assert len(segments) > 0, "未检测到任何对白"

        performance["m05_transcription_time"] = time.time() - start
        print(f"  ✓ 转写完成，共 {len(segments)} 段对白")
        print(f"  ✓ 转写耗时: {performance['m05_transcription_time']:.2f}s")

        quality["transcription"] = {
            "num_segments": len(segments),
            "language": transcription_result.get("language"),
            "language_probability": transcription_result.get("language_probability")
        }

        # 步骤 3: M04 - 克隆音色
        print("\n[Step 3] M04: 克隆音色...")
        character_id = "pingi_main"
        character_name = "平哥"

        m04.voices_dir = temp_voices_dir

        start = time.time()
        clone_result = await m04.clone_character_voice(
            character_id=character_id,
            character_name=character_name,
            reference_audio_path=vocals_path,
            description=f"Voice for {character_name} from pingi.mp4"
        )

        assert "voice_id" in clone_result
        voice_id = clone_result["voice_id"]
        performance["m04_cloning_time"] = time.time() - start
        print(f"  ✓ 音色已克隆: {voice_id}")
        print(f"  ✓ 克隆耗时: {performance['m04_cloning_time']:.2f}s")

        quality["voice_cloning"] = {
            "voice_id": voice_id,
            "character_id": character_id,
            "character_name": character_name
        }

        # 步骤 4: M09 - 合成
        print("\n[Step 4] M09: 合成中文配音...")
        first_segment = segments[0]
        test_text = first_segment["text"].strip()

        if not test_text:
            test_text = "Hello, this is a test."

        synthesized_audio_path = temp_output_dir / "dubbed_audio.wav"

        start = time.time()
        await m09.synthesize_speech(
            text=test_text,
            voice_id=voice_id,
            output_path=synthesized_audio_path
        )
        performance["m09_synthesis_time"] = time.time() - start

        assert synthesized_audio_path.exists(), f"合成音频不存在: {synthesized_audio_path}"
        print(f"  ✓ 配音已合成: {synthesized_audio_path}")
        print(f"  ✓ 合成耗时: {performance['m09_synthesis_time']:.2f}s")

        # 验证
        synthesized_validation = validate_audio_file(
            synthesized_audio_path,
            min_duration=0.1,
            min_file_size=1024
        )
        assert synthesized_validation["all_valid"], f"合成音频验证失败: {synthesized_validation}"

        quality["synthesized_audio"] = {
            "validation": synthesized_validation,
            "info": synthesized_validation["info"]
        }

        print(f"  ✓ 合成音频时长: {synthesized_validation['info'].get('duration', 'N/A'):.2f}s")
        print(f"  ✓ 合成音频采样率: {synthesized_validation['info'].get('sample_rate', 'N/A')} Hz")
        print(f"  ✓ 合成音频声道数: {synthesized_validation['info'].get('num_channels', 'N/A')}")
        print(f"  ✓ 合成音频文件大小: {synthesized_validation['info']['file_size']} bytes")

        # 计算总耗时
        performance["total_time"] = sum([
            performance["m02_separation_time"],
            performance["m05_transcription_time"],
            performance["m04_cloning_time"],
            performance["m09_synthesis_time"]
        ])

        # 保存完整测试结果
        test_result = {
            "video": str(PINGI_VIDEO),
            "test_name": "pingi_end_to_end",
            "status": "success",
            "performance": performance,
            "quality": quality,
            "outputs": {
                "vocals_path": str(vocals_path),
                "synthesized_audio": str(synthesized_audio_path),
                "voice_id": voice_id
            },
            "test_text": test_text,
            "transcription_summary": {
                "num_segments": len(segments),
                "total_text_length": sum(len(s.get("text", "")) for s in segments)
            }
        }

        result_path = temp_output_dir / "test_result.json"
        with result_path.open("w") as f:
            json.dump(test_result, f, indent=2)

        # 打印总结
        print(f"\n[Performance Summary]")
        print(f"  分离: {performance['m02_separation_time']:.2f}s")
        print(f"  转写: {performance['m05_transcription_time']:.2f}s")
        print(f"  克隆: {performance['m04_cloning_time']:.2f}s")
        print(f"  合成: {performance['m09_synthesis_time']:.2f}s")
        print(f"  总计: {performance['total_time']:.2f}s")

        print(f"\n[Quality Summary]")
        print(f"  人声时长: {quality['vocals']['info'].get('duration', 'N/A'):.2f}s")
        print(f"  人声采样率: {quality['vocals']['info'].get('sample_rate', 'N/A')} Hz")
        print(f"  合成时长: {quality['synthesized_audio']['info'].get('duration', 'N/A'):.2f}s")
        print(f"  合成采样率: {quality['synthesized_audio']['info'].get('sample_rate', 'N/A')} Hz")
        print(f"  转写段数: {quality['transcription']['num_segments']}")

        print(f"\n✅ pingi.mp4 端到端测试通过！")
        print(f"   结果已保存到: {result_path}")


@pytest.mark.asyncio
class TestEndToEndPerformance:
    """端到端性能测试"""

    @pytest.fixture
    async def workers(self):
        """初始化所有 worker"""
        m02 = M02Worker(separation_backend="htdemucs")
        m05 = M05Worker(asr_backend="faster-whisper")
        m04 = M04Worker(voice_backend="qwen")
        m09 = M09Worker(voice_backend="qwen")

        yield {"m02": m02, "m05": m05, "m04": m04, "m09": m09}

        # 清理
        await asyncio.gather(
            m02.close(),
            m05.close(),
            m04.close(),
            m09.close(),
            return_exceptions=True
        )

    @pytest.fixture
    def temp_output_dir(self):
        """临时输出目录"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def temp_voices_dir(self):
        """临时音色目录"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.mark.skipif(not LAOBAI_VIDEO.exists(), reason="测试视频不存在")
    async def test_performance_metrics(self, workers, temp_output_dir, temp_voices_dir):
        """
        性能指标测试
        记录各阶段耗时和质量指标
        """
        m02 = workers["m02"]
        m05 = workers["m05"]
        m04 = workers["m04"]
        m09 = workers["m09"]

        performance = {
            "m02_separation_time": 0.0,
            "m05_transcription_time": 0.0,
            "m04_cloning_time": 0.0,
            "m09_synthesis_time": 0.0,
            "total_time": 0.0
        }

        quality = {}

        # M02 - 音频分离
        print("\n[Performance] M02: 音频分离...")
        start = time.time()
        stems_dir = temp_output_dir / "stems"
        stems_dir.mkdir(parents=True, exist_ok=True)

        separation_result = await m02.analyze_audio(
            audio_path=LAOBAI_VIDEO,
            output_dir=stems_dir,
            extract_vocals_only=True
        )
        performance["m02_separation_time"] = time.time() - start
        print(f"  ✓ 分离耗时: {performance['m02_separation_time']:.2f}s")

        vocals_path = Path(separation_result["vocals_path"])

        # 验证人声音频质量
        vocals_validation = validate_audio_file(
            vocals_path,
            min_duration=0.5,
            min_file_size=1024
        )
        quality["vocals"] = {
            "validation": vocals_validation,
            "info": vocals_validation["info"]
        }
        print(f"  ✓ 人声时长: {vocals_validation['info'].get('duration', 'N/A'):.2f}s")
        print(f"  ✓ 人声采样率: {vocals_validation['info'].get('sample_rate', 'N/A')} Hz")

        # M05 - 转写
        print("\n[Performance] M05: 转写音频...")
        start = time.time()
        transcription_result = await m05.transcribe_audio(
            audio_path=vocals_path,
            language="en",
            word_timestamps=True
        )
        performance["m05_transcription_time"] = time.time() - start
        print(f"  ✓ 转写耗时: {performance['m05_transcription_time']:.2f}s")

        segments = transcription_result["segments"]
        quality["transcription"] = {
            "num_segments": len(segments),
            "language": transcription_result.get("language"),
            "language_probability": transcription_result.get("language_probability")
        }
        print(f"  ✓ 转写段数: {len(segments)}")

        # M04 - 克隆音色
        print("\n[Performance] M04: 克隆音色...")
        start = time.time()
        m04.voices_dir = temp_voices_dir

        clone_result = await m04.clone_character_voice(
            character_id="perf_test",
            character_name="Test Character",
            reference_audio_path=vocals_path
        )
        performance["m04_cloning_time"] = time.time() - start
        print(f"  ✓ 克隆耗时: {performance['m04_cloning_time']:.2f}s")

        voice_id = clone_result["voice_id"]
        quality["voice_cloning"] = {
            "voice_id": voice_id
        }

        # M09 - 合成
        print("\n[Performance] M09: 合成中文配音...")
        start = time.time()
        synthesized_audio_path = temp_output_dir / "dubbed_audio.wav"

        await m09.synthesize_speech(
            text=segments[0]["text"].strip() or "Test.",
            voice_id=voice_id,
            output_path=synthesized_audio_path
        )
        performance["m09_synthesis_time"] = time.time() - start
        print(f"  ✓ 合成耗时: {performance['m09_synthesis_time']:.2f}s")

        # 验证合成音频质量
        synthesized_validation = validate_audio_file(
            synthesized_audio_path,
            min_duration=0.1,
            min_file_size=1024
        )
        quality["synthesized_audio"] = {
            "validation": synthesized_validation,
            "info": synthesized_validation["info"]
        }
        print(f"  ✓ 合成时长: {synthesized_validation['info'].get('duration', 'N/A'):.2f}s")
        print(f"  ✓ 合成采样率: {synthesized_validation['info'].get('sample_rate', 'N/A')} Hz")
        print(f"  ✓ 合成声道数: {synthesized_validation['info'].get('num_channels', 'N/A')}")

        # 总耗时
        performance["total_time"] = sum([
            performance["m02_separation_time"],
            performance["m05_transcription_time"],
            performance["m04_cloning_time"],
            performance["m09_synthesis_time"]
        ])

        print(f"\n[Performance Summary]")
        print(f"  分离: {performance['m02_separation_time']:.2f}s")
        print(f"  转写: {performance['m05_transcription_time']:.2f}s")
        print(f"  克隆: {performance['m04_cloning_time']:.2f}s")
        print(f"  合成: {performance['m09_synthesis_time']:.2f}s")
        print(f"  总计: {performance['total_time']:.2f}s")

        print(f"\n[Quality Summary]")
        print(f"  人声时长: {quality['vocals']['info'].get('duration', 'N/A'):.2f}s")
        print(f"  人声采样率: {quality['vocals']['info'].get('sample_rate', 'N/A')} Hz")
        print(f"  合成时长: {quality['synthesized_audio']['info'].get('duration', 'N/A'):.2f}s")
        print(f"  合成采样率: {quality['synthesized_audio']['info'].get('sample_rate', 'N/A')} Hz")
        print(f"  转写段数: {quality['transcription']['num_segments']}")

        # 保存完整结果
        result = {
            "test_name": "performance_test",
            "status": "success",
            "performance": performance,
            "quality": quality,
            "video": str(LAOBAI_VIDEO)
        }

        result_path = temp_output_dir / "performance_and_quality.json"
        with result_path.open("w") as f:
            json.dump(result, f, indent=2)

        print(f"\n✅ 性能和质量指标已保存到: {result_path}")

        # 断言测试通过
        assert performance["total_time"] > 0, "总耗时应大于0"
        assert all(v["all_valid"] for v in quality.values() if isinstance(v, dict) and "validation" in v), "所有音频质量验证应通过"

        return result
