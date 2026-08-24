"""测试完整流水线执行器"""
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from filmdub.orchestrator.full_pipeline_executor import FullPipelineExecutor


@pytest.fixture
def mock_video_path(tmp_path):
    """创建模拟视频文件"""
    video = tmp_path / "test_video.mp4"
    video.write_bytes(b"fake video content")
    return video


@pytest.fixture
def temp_work_dir(tmp_path):
    """临时工作目录"""
    work_dir = tmp_path / "pipeline_work"
    work_dir.mkdir()
    return work_dir


class TestFullPipelineExecutor:
    """测试完整流水线执行器"""

    def test_init(self, mock_video_path, temp_work_dir):
        """测试初始化"""
        executor = FullPipelineExecutor(
            project_id="test_project",
            video_path=mock_video_path,
            work_dir=temp_work_dir
        )

        assert executor.project_id == "test_project"
        assert executor.video_path == mock_video_path
        assert executor.work_dir == temp_work_dir
        assert executor.media_dir.exists()
        assert executor.dialogue_dir.exists()
        assert executor.output_dir.exists()

    def test_save_and_load_ctx(self, mock_video_path, temp_work_dir):
        """测试上下文保存和加载"""
        executor = FullPipelineExecutor(
            project_id="test_project",
            video_path=mock_video_path,
            work_dir=temp_work_dir
        )

        test_data = {"key": "value", "number": 42}
        executor.ctx["M01"] = test_data
        executor._save_ctx("M01", test_data)

        # 新建执行器，从 manifests 加载
        executor2 = FullPipelineExecutor(
            project_id="test_project",
            video_path=mock_video_path,
            work_dir=temp_work_dir
        )
        executor2._load_ctx_from_manifests()

        assert "M01" in executor2.ctx
        assert executor2.ctx["M01"]["key"] == "value"
        assert executor2.ctx["M01"]["number"] == 42

    @pytest.mark.asyncio
    async def test_reconstruct_ctx_for_rerun(self, mock_video_path, temp_work_dir):
        """测试断点续跑的上下文重建"""
        executor = FullPipelineExecutor(
            project_id="test_project",
            video_path=mock_video_path,
            work_dir=temp_work_dir
        )

        # 模拟已有的 manifests
        m02_data = {"vocals": "/path/to/vocals.wav"}
        (temp_work_dir / "manifests").mkdir(exist_ok=True)
        (temp_work_dir / "manifests" / "ctx_M02.json").write_text(
            json.dumps(m02_data, ensure_ascii=False)
        )

        executor._reconstruct_ctx_for_rerun()

        assert "M02" in executor.ctx
        assert executor.ctx["M02"]["vocals"] == "/path/to/vocals.wav"


class TestFullPipelineExecutorModules:
    """测试各模块执行（带 mock）"""

    @pytest.mark.asyncio
    @patch("filmdub.workers.media_intake.runner.MediaIntakeWorker")
    async def test_exec_M01(self, mock_worker_class, mock_video_path, temp_work_dir):
        """测试 M01 执行"""
        # 设置 mock
        mock_worker = AsyncMock()
        mock_worker.run.return_value = {"media_id": "media_123", "filename": "test.mp4"}
        mock_worker_class.return_value = mock_worker

        executor = FullPipelineExecutor(
            project_id="test_project",
            video_path=mock_video_path,
            work_dir=temp_work_dir
        )

        result = await executor.exec_M01()

        assert result["media_id"] == "media_123"
        assert "M01" in executor.ctx
        assert executor.ctx["M01"]["media_id"] == "media_123"

        # 验证已保存到 manifest
        manifest_file = temp_work_dir / "manifests" / "ctx_M01.json"
        assert manifest_file.exists()

        # 测试从 ctx 缓存返回（不重复执行）
        result2 = await executor.exec_M01()
        assert result2 == result
        mock_worker.run.assert_called_once()

    @pytest.mark.asyncio
    @patch("filmdub.orchestrator.full_pipeline_executor.run_cli_tts")
    @patch("filmdub.orchestrator.full_pipeline_executor.extract_speaker_features")
    async def test_exec_M04(self, mock_extract, mock_tts, mock_video_path, temp_work_dir):
        """测试 M04 执行"""
        # 设置 mocks
        mock_extract.return_value = (
            Path("/path/to/voice.spk"),
            Path("/path/to/voice.rvq")
        )

        # 模拟 M02 上下文
        executor = FullPipelineExecutor(
            project_id="test_project",
            video_path=mock_video_path,
            work_dir=temp_work_dir
        )
        executor.ctx["M02"] = {"vocals": str(mock_video_path)}

        result = await executor.exec_M04()

        assert "M04" in executor.ctx
        assert "characters" in result
        assert len(result["characters"]) > 0
        assert result["characters"][0]["character_id"] == "main_speaker"

    @pytest.mark.asyncio
    @patch("filmdub.orchestrator.full_pipeline_executor.translate_batch")
    async def test_exec_M07(self, mock_translate, mock_video_path, temp_work_dir):
        """测试 M07 执行"""
        # 设置 mock
        mock_translate.return_value = [
            {"idx": 0, "start": 0.0, "end": 1.0, "en": "Hello", "zh": "你好"},
            {"idx": 1, "start": 1.0, "end": 2.0, "en": "World", "zh": "世界"},
        ]

        # 模拟 M05 上下文
        executor = FullPipelineExecutor(
            project_id="test_project",
            video_path=mock_video_path,
            work_dir=temp_work_dir
        )
        executor.ctx["M05"] = {
            "segments": [
                {"idx": 0, "start": 0.0, "end": 1.0, "text": "Hello"},
                {"idx": 1, "start": 1.0, "end": 2.0, "text": "World"},
            ]
        }

        result = await executor.exec_M07()

        assert "M07" in executor.ctx
        assert "translated" in result
        assert len(result["translated"]) == 2
        assert result["translated"][0]["zh"] == "你好"

        # 验证从 ctx 缓存返回
        result2 = await executor.exec_M07()
        assert result2 == result


class TestFullPipelineRun:
    """测试完整流水线运行"""

    @pytest.mark.asyncio
    async def test_full_pipeline_success(self, mock_video_path, temp_work_dir):
        """测试完整流水线成功执行"""
        executor = FullPipelineExecutor(
            project_id="test_project",
            video_path=mock_video_path,
            work_dir=temp_work_dir
        )

        # 手动 mock 所有模块执行方法
        async def mock_m01(self):
            self.ctx["M01"] = {"media_id": "media_123"}
            return self.ctx["M01"]

        async def mock_m02(self):
            self.ctx["M02"] = {"vocals": "/path/to/vocals.wav"}
            return self.ctx["M02"]

        async def mock_m03(self):
            self.ctx["M03"] = {"status": "no_subtitle"}
            return self.ctx["M03"]

        async def mock_m05(self):
            self.ctx["M05"] = {"segments": [{"idx": 0, "text": "Hello"}]}
            return self.ctx["M05"]

        async def mock_m04(self):
            self.ctx["M04"] = {"characters": [{"character_id": "main"}]}
            return self.ctx["M04"]

        async def mock_m06(self):
            self.ctx["M06"] = {"mapping": []}
            return self.ctx["M06"]

        async def mock_m07(self):
            self.ctx["M07"] = {"translated": []}
            return self.ctx["M07"]

        async def mock_m08(self):
            self.ctx["M08"] = {"plans": []}
            return self.ctx["M08"]

        async def mock_m09(self):
            self.ctx["M09"] = {"synth": []}
            return self.ctx["M09"]

        async def mock_m10(self):
            self.ctx["M10"] = {"audio_segments": [], "subtitles": []}
            return self.ctx["M10"]

        async def mock_m11(self):
            self.ctx["M11"] = {"video": "/output/final.mp4"}
            return self.ctx["M11"]

        async def mock_m12(self):
            self.ctx["M12"] = {"output": "/output/final_encapsulated.mp4", "success": True}
            return self.ctx["M12"]

        async def mock_m13(self):
            self.ctx["M13"] = {"result": {"overall_score": 90}}
            return self.ctx["M13"]

        async def mock_m14(self):
            self.ctx["M14"] = {"result": {"archive_file": "/archive.zip"}}
            return self.ctx["M14"]

        # 替换方法
        executor.exec_M01 = mock_m01.__get__(executor, type(executor))
        executor.exec_M02 = mock_m02.__get__(executor, type(executor))
        executor.exec_M03 = mock_m03.__get__(executor, type(executor))
        executor.exec_M05 = mock_m05.__get__(executor, type(executor))
        executor.exec_M04 = mock_m04.__get__(executor, type(executor))
        executor.exec_M06 = mock_m06.__get__(executor, type(executor))
        executor.exec_M07 = mock_m07.__get__(executor, type(executor))
        executor.exec_M08 = mock_m08.__get__(executor, type(executor))
        executor.exec_M09 = mock_m09.__get__(executor, type(executor))
        executor.exec_M10 = mock_m10.__get__(executor, type(executor))
        executor.exec_M11 = mock_m11.__get__(executor, type(executor))
        executor.exec_M12 = mock_m12.__get__(executor, type(executor))
        executor.exec_M13 = mock_m13.__get__(executor, type(executor))
        executor.exec_M14 = mock_m14.__get__(executor, type(executor))

        result = await executor.run()

        assert result["status"] == "completed"
        assert result["project_id"] == "test_project"
        assert len(result["completed_modules"]) == 14
        assert len(result["failed_modules"]) == 0
        assert result["output_video"] == "/output/final.mp4"

    @pytest.mark.asyncio
    @patch.object(FullPipelineExecutor, "exec_M01")
    @patch.object(FullPipelineExecutor, "exec_M02")
    async def test_full_pipeline_failure(
        self, mock_m02, mock_m01, mock_video_path, temp_work_dir
    ):
        """测试流水线失败处理"""
        mock_m01.return_value = {"media_id": "media_123"}
        mock_m02.side_effect = Exception("M02 failed")

        executor = FullPipelineExecutor(
            project_id="test_project",
            video_path=mock_video_path,
            work_dir=temp_work_dir
        )

        result = await executor.run()

        assert result["status"] == "failed"
        assert len(result["completed_modules"]) == 1  # 只有 M01 成功
        assert len(result["failed_modules"]) == 1
        assert result["failed_modules"][0][0] == "M02"

    @pytest.mark.asyncio
    @patch.object(FullPipelineExecutor, "exec_M01")
    @patch.object(FullPipelineExecutor, "exec_M02")
    async def test_full_pipeline_checkpoint_resume(
        self, mock_m02, mock_m01, mock_video_path, temp_work_dir
    ):
        """测试断点续跑"""
        # 模拟已有 M02 的 manifest
        (temp_work_dir / "manifests").mkdir(exist_ok=True)
        (temp_work_dir / "manifests" / "ctx_M02.json").write_text(
            json.dumps({"vocals": "/cached/vocals.wav"}, ensure_ascii=False)
        )

        mock_m01.return_value = {"media_id": "media_123"}

        executor = FullPipelineExecutor(
            project_id="test_project",
            video_path=mock_video_path,
            work_dir=temp_work_dir
        )

        result = await executor.run()

        # M01 应该执行，M02 应该从 manifest 恢复（不执行）
        mock_m01.assert_called_once()
        mock_m02.assert_not_called()

        # 验证 M02 在已完成模块中
        assert "M02" in result["completed_modules"]


class TestWavMeanDb:
    """测试 WAV 音量计算"""

    def test_wav_mean_db_valid(self, tmp_path):
        """测试有效 WAV 文件"""
        from filmdub.orchestrator.full_pipeline_executor import _wav_mean_db

        # 创建一个假的 WAV 文件（实际测试需要真实文件）
        fake_wav = tmp_path / "test.wav"
        fake_wav.write_bytes(b"RIFF" + b"\x00" * 100)

        # 由于是假文件，预期返回静音值
        result = _wav_mean_db(fake_wav)
        assert result == -120.0  # 解析失败返回默认值

    def test_wav_mean_db_nonexistent(self, tmp_path):
        """测试不存在的文件"""
        from filmdub.orchestrator.full_pipeline_executor import _wav_mean_db

        result = _wav_mean_db(tmp_path / "nonexistent.wav")
        assert result == -120.0
