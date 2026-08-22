"""
端到端测试 - 完整配音流程

验证：短视频输入 → M02(分离) → M05(转写) → M04(克隆) → M09(合成) → 输出配音视频
"""

import pytest
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List
import tempfile
import shutil

from filmdub.workers.research.m02_worker import M02Worker
from filmdub.workers.audio_scene_analysis.m05_worker import M05Worker
from filmdub.workers.character_db.m04_worker import M04Worker
from filmdub.workers.voice_synthesis.m09_worker import M09Worker


# 测试视频路径
TEST_VIDEOS_DIR = Path(__file__).parent.parent.parent.parent / "测试视频"
LAOBAI_VIDEO = TEST_VIDEOS_DIR / "laobai.mp4"
PINGI_VIDEO = TEST_VIDEOS_DIR / "pingi.mp4"


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
        """
        m02 = workers["m02"]
        m05 = workers["m05"]
        m04 = workers["m04"]
        m09 = workers["m09"]

        # 步骤 1: M02 - 音频分离（提取人声）
        print("\n[Step 1] M02: 音频分离...")
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

        print(f"  ✓ 人声已提取: {vocals_path}")

        # 步骤 2: M05 - 转写音频
        print("\n[Step 2] M05: 转写音频...")
        transcription_result = await m05.transcribe_audio(
            audio_path=vocals_path,
            language="en",  # 假设是英语
            word_timestamps=True
        )

        assert "segments" in transcription_result
        segments = transcription_result["segments"]
        assert len(segments) > 0, "未检测到任何对白"

        print(f"  ✓ 转写完成，共 {len(segments)} 段对白")

        # 步骤 3: M04 - 克隆音色
        print("\n[Step 3] M04: 克隆音色...")
        character_id = "laobai_main"
        character_name = "老白"

        # 为 M04 设置临时音色目录
        m04.voices_dir = temp_voices_dir

        clone_result = await m04.clone_character_voice(
            character_id=character_id,
            character_name=character_name,
            reference_audio_path=vocals_path,
            description=f"Voice for {character_name} from laobai.mp4"
        )

        assert "voice_id" in clone_result
        voice_id = clone_result["voice_id"]
        print(f"  ✓ 音色已克隆: {voice_id}")

        # 步骤 4: M09 - 合成中文配音
        print("\n[Step 4] M09: 合成中文配音...")

        # 使用第一段转写文本进行测试
        # 注意：实际应该翻译成中文，这里先用英文文本测试
        first_segment = segments[0]
        test_text = first_segment["text"].strip()

        if not test_text:
            test_text = "Hello, this is a test."

        synthesized_audio_path = temp_output_dir / "dubbed_audio.wav"

        await m09.synthesize_speech(
            text=test_text,
            voice_id=voice_id,
            output_path=synthesized_audio_path
        )

        assert synthesized_audio_path.exists(), f"合成音频不存在: {synthesized_audio_path}"
        print(f"  ✓ 配音已合成: {synthesized_audio_path}")

        # 步骤 5: 验证输出
        print("\n[Step 5] 验证输出...")

        # 验证音频文件大小合理（至少 1KB）
        assert synthesized_audio_path.stat().st_size > 1024, "合成音频文件过小"

        print(f"  ✓ 音频文件大小: {synthesized_audio_path.stat().st_size} bytes")

        # 保存测试结果
        test_result = {
            "video": str(LAOBAI_VIDEO),
            "vocals_path": str(vocals_path),
            "transcription_segments": len(segments),
            "voice_id": voice_id,
            "synthesized_audio": str(synthesized_audio_path),
            "test_text": test_text,
            "output_file_size": synthesized_audio_path.stat().st_size,
            "status": "success"
        }

        result_path = temp_output_dir / "test_result.json"
        with result_path.open("w") as f:
            json.dump(test_result, f, indent=2)

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
        """
        m02 = workers["m02"]
        m05 = workers["m05"]
        m04 = workers["m04"]
        m09 = workers["m09"]

        # 步骤 1: M02 - 音频分离
        print("\n[Step 1] M02: 音频分离...")
        stems_dir = temp_output_dir / "stems"
        stems_dir.mkdir(parents=True, exist_ok=True)

        separation_result = await m02.analyze_audio(
            audio_path=PINGI_VIDEO,
            output_dir=stems_dir,
            extract_vocals_only=True
        )

        assert "vocals_path" in separation_result
        vocals_path = Path(separation_result["vocals_path"])
        assert vocals_path.exists()

        print(f"  ✓ 人声已提取: {vocals_path}")

        # 步骤 2: M05 - 转写
        print("\n[Step 2] M05: 转写音频...")
        transcription_result = await m05.transcribe_audio(
            audio_path=vocals_path,
            language="en",
            word_timestamps=True
        )

        assert "segments" in transcription_result
        segments = transcription_result["segments"]
        assert len(segments) > 0

        print(f"  ✓ 转写完成，共 {len(segments)} 段对白")

        # 步骤 3: M04 - 克隆音色
        print("\n[Step 3] M04: 克隆音色...")
        character_id = "pingi_main"
        character_name = "平哥"

        m04.voices_dir = temp_voices_dir

        clone_result = await m04.clone_character_voice(
            character_id=character_id,
            character_name=character_name,
            reference_audio_path=vocals_path,
            description=f"Voice for {character_name} from pingi.mp4"
        )

        assert "voice_id" in clone_result
        voice_id = clone_result["voice_id"]
        print(f"  ✓ 音色已克隆: {voice_id}")

        # 步骤 4: M09 - 合成
        print("\n[Step 4] M09: 合成中文配音...")
        first_segment = segments[0]
        test_text = first_segment["text"].strip()

        if not test_text:
            test_text = "Hello, this is a test."

        synthesized_audio_path = temp_output_dir / "dubbed_audio.wav"

        await m09.synthesize_speech(
            text=test_text,
            voice_id=voice_id,
            output_path=synthesized_audio_path
        )

        assert synthesized_audio_path.exists()
        print(f"  ✓ 配音已合成: {synthesized_audio_path}")

        # 验证
        assert synthesized_audio_path.stat().st_size > 1024

        print(f"\n✅ pingi.mp4 端到端测试通过！")


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
        记录各阶段耗时
        """
        import time

        m02 = workers["m02"]
        m05 = workers["m05"]
        m04 = workers["m04"]
        m09 = workers["m09"]

        performance = {}

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

        # 保存性能指标
        result_path = temp_output_dir / "performance.json"
        with result_path.open("w") as f:
            json.dump(performance, f, indent=2)

        print(f"\n✅ 性能指标已保存到: {result_path}")
