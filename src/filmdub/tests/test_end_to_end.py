"""
端到端测试：短视频完整配音流程

测试视频路径：
- laobai.mp4
- pingi.mp4

流程：
短视频输入 → M02(分离) → M05(转写) → M04(克隆) → M09(合成) → 输出配音视频
"""

import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import time

logger = logging.getLogger(__name__)

from filmdub.workers.research.m02_worker import M02Worker
from filmdub.workers.audio_scene_analysis.m05_worker import M05Worker
from filmdub.workers.character_db.m04_worker import M04Worker
from filmdub.workers.voice_synthesis.m09_worker import M09Worker


class EndToEndTestPipeline:
    """端到端测试流水线"""

    def __init__(
        self,
        output_dir: Path,
        skip_missing_videos: bool = True
    ):
        """
        初始化端到端测试流水线

        Args:
            output_dir: 输出目录
            skip_missing_videos: 跳过缺失的测试视频
        """
        self.output_dir = output_dir
        self.skip_missing_videos = skip_missing_videos
        
        # 初始化各模块 Worker
        self.m02_worker = M02Worker(separation_backend="htdemucs")
        self.m05_worker = M05Worker(asr_backend="faster-whisper")
        self.m04_worker = M04Worker(voice_backend="qwen", voices_dir=output_dir / "voices")
        self.m09_worker = M09Worker(voice_backend="qwen")
        
        self.results: Dict[str, Any] = {}

    async def process_video(
        self,
        video_path: Path,
        extract_vocals_only: bool = True
    ) -> Dict[str, Any]:
        """
        处理单个视频

        Args:
            video_path: 视频文件路径
            extract_vocals_only: 是否只提取人声

        Returns:
            处理结果
        """
        if not video_path.exists():
            if self.skip_missing_videos:
                logger.warning(f"Video not found, skipping: {video_path}")
                return {"skipped": True, "reason": "file_not_found"}
            else:
                raise FileNotFoundError(f"Video not found: {video_path}")

        logger.info(f"Starting end-to-end test for: {video_path.name}")
        start_time = time.time()
        
        result = {
            "video_name": video_path.name,
            "video_path": str(video_path),
            "start_time": start_time,
            "stages": {},
            "success": False,
            "error": None
        }

        try:
            # Stage 1: M02 - 音频分离
            logger.info("Stage 1: Audio separation (M02)")
            stage_start = time.time()
            
            m02_output_dir = self.output_dir / video_path.stem / "stems"
            m02_result = await self.m02_worker.analyze_audio(
                audio_path=video_path,
                output_dir=m02_output_dir,
                extract_vocals_only=extract_vocals_only
            )
            
            result["stages"]["m02_separation"] = {
                "duration": time.time() - stage_start,
                "output": m02_result
            }
            logger.info(f"M02 completed in {result['stages']['m02_separation']['duration']:.2f}s")

            # Stage 2: M05 - 语音转写
            logger.info("Stage 2: Speech transcription (M05)")
            stage_start = time.time()
            
            # 获取分离出的人声
            vocals_path = Path(m02_result["stems"]["vocals"])
            
            m05_result = await self.m05_worker.analyze_dialogue(
                audio_path=vocals_path,
                with_speakers=True,
                language="zh"  # 假设是中文视频
            )
            
            result["stages"]["m05_transcription"] = {
                "duration": time.time() - stage_start,
                "output": m05_result
            }
            logger.info(f"M05 completed in {result['stages']['m05_transcription']['duration']:.2f}s")

            # Stage 3: M04 - 音色克隆
            logger.info("Stage 3: Voice cloning (M04)")
            stage_start = time.time()
            
            # 为每个说话人克隆音色
            speakers = m05_result.get("speakers", [])
            voice_mappings = {}
            
            for speaker in speakers:
                # 使用第一段音频作为参考
                speaker_segments = [
                    seg for seg in m05_result["segments"]
                    if seg.get("speaker") == speaker
                ]
                
                if speaker_segments:
                    # 使用分离的人声文件作为参考
                    voice_info = await self.m04_worker.clone_character_voice(
                        character_id=f"{video_path.stem}_{speaker}",
                        character_name=f"Speaker {speaker}",
                        reference_audio_path=vocals_path,
                        description=f"Voice for {speaker} in {video_path.name}"
                    )
                    voice_mappings[speaker] = voice_info
            
            result["stages"]["m04_cloning"] = {
                "duration": time.time() - stage_start,
                "voices_cloned": len(voice_mappings),
                "voice_mappings": voice_mappings
            }
            logger.info(f"M04 completed in {result['stages']['m04_cloning']['duration']:.2f}s")

            # Stage 4: M09 - 语音合成
            logger.info("Stage 4: Speech synthesis (M09)")
            stage_start = time.time()
            
            # 合成每个对话
            synthesis_items = []
            for seg in m05_result["segments"]:
                speaker = seg.get("speaker")
                if speaker in voice_mappings:
                    voice_id = voice_mappings[speaker]["voice_id"]
                    synthesis_items.append({
                        "text": seg["text"],
                        "voice_id": voice_id,
                        "output_filename": f"speech_{seg['start']:.2f}_{seg['end']:.2f}.wav"
                    })
            
            synthesis_output_dir = self.output_dir / video_path.stem / "synthesized"
            m09_result = await self.m09_worker.synthesize_batch(
                items=synthesis_items,
                output_dir=synthesis_output_dir
            )
            
            result["stages"]["m09_synthesis"] = {
                "duration": time.time() - stage_start,
                "output": m09_result,
                "synthesis_dir": str(synthesis_output_dir)
            }
            logger.info(f"M09 completed in {result['stages']['m09_synthesis']['duration']:.2f}s")

            # 计算总时长
            result["total_duration"] = time.time() - start_time
            result["success"] = True
            
            logger.info(f"End-to-end test completed successfully in {result['total_duration']:.2f}s")
            
        except Exception as e:
            result["total_duration"] = time.time() - start_time
            result["error"] = str(e)
            logger.error(f"End-to-end test failed: {e}")

        return result

    async def close(self):
        """清理资源"""
        await self.m02_worker.close()
        await self.m05_worker.close()
        await self.m04_worker.close()
        await self.m09_worker.close()


# 测试视频路径
TEST_VIDEOS_DIR = Path("测试视频")
LAOBAI_VIDEO = TEST_VIDEOS_DIR / "laobai.mp4"
PINGI_VIDEO = TEST_VIDEOS_DIR / "pingi.mp4"


@pytest.mark.asyncio
@pytest.mark.skipif(
    not LAOBAI_VIDEO.exists(),
    reason=f"Test video not found: {LAOBAI_VIDEO}"
)
@pytest.mark.skip(reason="Requires qwen-tts service and models to be running")
async def test_end_to_end_laobai(tmp_path):
    """端到端测试：laobai.mp4"""
    pipeline = EndToEndTestPipeline(
        output_dir=tmp_path / "laobai_output",
        skip_missing_videos=False
    )
    
    try:
        result = await pipeline.process_video(LAOBAI_VIDEO)
        
        assert result["success"], f"Pipeline failed: {result.get('error')}"
        assert "m02_separation" in result["stages"]
        assert "m05_transcription" in result["stages"]
        assert "m04_cloning" in result["stages"]
        assert "m09_synthesis" in result["stages"]
        
        # 验证输出
        assert result["stages"]["m02_separation"]["output"]["stems"]["vocals"]
        assert result["stages"]["m05_transcription"]["output"]["num_speakers"] > 0
        assert result["stages"]["m04_cloning"]["voices_cloned"] > 0
        
        # 检查合成结果
        m09_result = result["stages"]["m09_synthesis"]["output"]
        successful_syntheses = sum(1 for r in m09_result if r["success"])
        assert successful_syntheses > 0, "No successful syntheses"
        
    finally:
        await pipeline.close()


@pytest.mark.asyncio
@pytest.mark.skipif(
    not PINGI_VIDEO.exists(),
    reason=f"Test video not found: {PINGI_VIDEO}"
)
@pytest.mark.skip(reason="Requires qwen-tts service and models to be running")
async def test_end_to_end_pingi(tmp_path):
    """端到端测试：pingi.mp4"""
    pipeline = EndToEndTestPipeline(
        output_dir=tmp_path / "pingi_output",
        skip_missing_videos=False
    )
    
    try:
        result = await pipeline.process_video(PINGI_VIDEO)
        
        assert result["success"], f"Pipeline failed: {result.get('error')}"
        assert "m02_separation" in result["stages"]
        assert "m05_transcription" in result["stages"]
        assert "m04_cloning" in result["stages"]
        assert "m09_synthesis" in result["stages"]
        
    finally:
        await pipeline.close()


@pytest.mark.asyncio
async def test_end_to_end_skip_missing_videos(tmp_path):
    """端到端测试：跳过缺失的视频"""
    pipeline = EndToEndTestPipeline(
        output_dir=tmp_path / "test_output",
        skip_missing_videos=True
    )
    
    # 测试不存在的视频
    result = await pipeline.process_video(Path("/nonexistent/video.mp4"))
    assert result["skipped"] is True
    assert result["reason"] == "file_not_found"
    
    await pipeline.close()
