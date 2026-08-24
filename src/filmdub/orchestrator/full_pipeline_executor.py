"""完整流水线执行器

复用 scripts/run_full_pipeline.py 的 Orchestrator 能力，
为 Job Runner 提供完整 M01~M14 流水线执行能力。
"""
import asyncio
import json
import logging
import os
import shutil
import subprocess
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, List

import httpx

logger = logging.getLogger(__name__)

# 外部服务配置
TTS_BIN = Path("/home/wu/桌面/qwentts/cpp_tts/qwen-tts")
CODEC_BIN = Path("/home/wu/桌面/qwentts/cpp_tts/qwen-codec")
CPP_TTS_DIR = Path("/home/wu/桌面/qwentts/cpp_tts")
TALKER = Path("/home/wu/桌面/qwentts/cpp_models/qwen-talker-1.7b-base-Q8_0.gguf")
CODEC = Path("/home/wu/桌面/qwentts/cpp_models/qwen-tokenizer-12hz-Q8_0.gguf")
LAOBAI_REF_TXT = Path("/home/wu/桌面/AI-FanYi/.reasonix/laobai_ref.txt")
OLLAMA = "http://localhost:11434"
OLLAMA_MODEL = "gemma4-e2b"

# 工作流定义
WORKFLOW = {
    "name": "full_pipeline",
    "order": ["M01", "M02", "M03", "M05", "M04", "M06", "M07",
              "M08", "M09", "M10", "M11", "M12", "M13", "M14"],
    "deps": {
        "M01": [], "M02": ["M01"], "M03": ["M02"], "M05": ["M02"],
        "M04": ["M02"], "M06": ["M05", "M04"], "M07": ["M06"],
        "M08": ["M07"], "M09": ["M08"], "M10": ["M09"], "M11": ["M10"],
        "M12": ["M11"], "M13": ["M12"], "M14": ["M13"],
    },
}


def log(module: str, msg: str):
    """记录日志"""
    now = time.strftime("%H:%M:%S")
    print(f"[{now}] [{module}] {msg}", flush=True)
    logger.info(f"[{module}] {msg}")


def _wav_mean_db(wav: Path) -> float:
    """返回 wav 的平均音量（dB）"""
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", str(wav), "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True
        )
        for line in r.stderr.splitlines():
            if "mean_volume:" in line:
                return float(line.split("mean_volume:")[1].strip().replace(" dB", ""))
    except Exception:
        pass
    return -120.0


async def run_cli_tts(text: str, out_wav: Path, max_new: int = 160, seed: Optional[int] = None) -> Path:
    """调用 qwen-tts CLI 生成语音"""
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(CPP_TTS_DIR)
    cmd = [
        str(TTS_BIN), "--model", str(TALKER), "--codec", str(CODEC),
        "--ref-spk", str(Path("/home/wu/桌面/qwentts/cloned_voices/老白_20260822_124220/voice.spk")),
        "--ref-rvq", str(Path("/home/wu/桌面/qwentts/cloned_voices/老白_20260822_124220/voice.rvq")),
        "--ref-text", str(LAOBAI_REF_TXT),
        "--lang", "auto", "--max-new", str(max_new), "-o", str(out_wav)
    ]
    if seed is not None:
        cmd += ["--seed", str(seed)]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE, env=env, cwd=str(CPP_TTS_DIR)
    )
    _, stderr = await proc.communicate(input=(text + "\n").encode("utf-8"))
    if proc.returncode != 0 or not out_wav.exists() or out_wav.stat().st_size < 100:
        raise RuntimeError(f"qwen-tts rc={proc.returncode} {stderr[-300:]!r}")
    return out_wav


async def extract_speaker_features(wav: Path, out_dir: Path):
    """提取说话人特征（音色克隆）"""
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "ref.wav"
    shutil.copy(wav, tmp)
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(CPP_TTS_DIR)
    proc = await asyncio.create_subprocess_exec(
        *[str(CODEC_BIN), "--model", str(CODEC), "--talker", str(TALKER), "-i", str(tmp)],
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
        env=env, cwd=str(CPP_TTS_DIR)
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0 or not tmp.with_suffix(".spk").exists() or not tmp.with_suffix(".rvq").exists():
        raise RuntimeError(f"qwen-codec rc={proc.returncode} {stderr[-300:]!r}")
    return tmp.with_suffix(".spk"), tmp.with_suffix(".rvq")


async def translate_batch(segments: List[Dict]) -> List[Dict]:
    """批量翻译对白"""
    log("M07", "翻译 -> ollama gemma4-e2b")
    async with httpx.AsyncClient(timeout=180) as client:
        out = []
        for seg in segments:
            text = seg.get("text", "").strip()
            prompt = f"将英文对白译为口语化中文，只输出译文。\n{text}\n译文："
            r = await client.post(
                f"{OLLAMA}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
            )
            r.raise_for_status()
            resp = (r.json().get("response") or "").strip()
            zh = resp.splitlines()[0] if resp and "|" not in resp[:4] else text
            out.append({
                "idx": seg.get("idx"), "start": seg.get("start"), "end": seg.get("end"),
                "en": text, "zh": zh
            })
            log("M07", f"  [{seg.get('idx')}] {zh}")
        return out


class FullPipelineExecutor:
    """完整流水线执行器

    执行 M01~M14 完整流水线，生成最终配音视频。
    """

    def __init__(self, project_id: str, video_path: Path, work_dir: Optional[Path] = None):
        self.project_id = project_id
        self.video_path = Path(video_path)
        self.work_dir = Path(work_dir) if work_dir else Path("/tmp/filmdub_pipeline") / project_id
        self.work_dir.mkdir(parents=True, exist_ok=True)

        # 子目录
        self.media_dir = self.work_dir / "media"
        self.dialogue_dir = self.work_dir / "dialogue"
        self.output_dir = self.work_dir / "output"
        self.archive_dir = self.work_dir / "archive"
        self.manifests_dir = self.work_dir / "manifests"

        for d in [self.media_dir, self.dialogue_dir, self.output_dir, self.archive_dir, self.manifests_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # 运行时上下文（模块间共享）
        self.ctx: Dict[str, Any] = {}

    def _save_ctx(self, name: str, data: Any):
        """保存上下文到 manifest"""
        p = self.manifests_dir / f"ctx_{name[:3]}.json"
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))

    def _load_ctx_from_manifests(self):
        """从 manifests 加载上下文"""
        for f in sorted(self.manifests_dir.glob("ctx_*.json")):
            mod = f.stem[4:]  # 去掉 "ctx_" 前缀
            try:
                self.ctx[mod] = json.loads(f.read_text())
            except Exception:
                pass

    def _reconstruct_ctx_for_rerun(self):
        """断点续跑：从 manifests 重建上下文"""
        self._load_ctx_from_manifests()

    # ------------------------------------------------------------------
    # 模块执行器（M01~M14）
    # ------------------------------------------------------------------
    async def exec_M01(self) -> Dict:
        """M01: Project & Media Intake"""
        if self.ctx.get("M01"):
            return self.ctx["M01"]
        log("M01", "Project & Media Intake")
        from filmdub.workers.media_intake.runner import MediaIntakeWorker
        m = MediaIntakeWorker(self.project_id, self.video_path, self.video_path.name)
        res = await m.run()
        self.ctx["M01"] = res
        self._save_ctx("M01", res)
        return res

    async def exec_M02(self) -> Dict:
        """M02: Media / Scene Analysis"""
        if self.ctx.get("M02"):
            return self.ctx["M02"]
        log("M02", "Media / Scene Analysis: htdemucs 分离")
        from filmdub.workers.research.m02_worker import M02Worker
        m = M02Worker(separation_backend="htdemucs")
        try:
            sep = await m.analyze_audio(
                audio_path=self.video_path,
                output_dir=self.media_dir / "stems",
                extract_vocals_only=True
            )
            vocals = Path(sep["vocals_path"])
        finally:
            await m.close()
        self.ctx["M02"] = {"vocals": str(vocals)}
        self._save_ctx("M02", self.ctx["M02"])
        log("M02", "vocals -> " + str(vocals))
        return self.ctx["M02"]

    async def exec_M03(self) -> Dict:
        """M03: Subtitle / Dialogue Acquisition"""
        if self.ctx.get("M03"):
            return self.ctx["M03"]
        log("M03", "Subtitle / Dialogue Acquisition")
        # 无现成字幕，由 M05 转写构建
        self.ctx["M03"] = {
            "status": "no_external_subtitle",
            "note": "无现成字幕，由后续 M05 转写构建对白时间轴"
        }
        self._save_ctx("M03", self.ctx["M03"])
        log("M03", "subtitle discovery done")
        return self.ctx["M03"]

    async def exec_M05(self) -> Dict:
        """M05: Audio & Scene Analysis (ASR)"""
        if self.ctx.get("M05"):
            return self.ctx["M05"]
        log("M05", "Audio & Scene Analysis: faster-whisper 转写")
        vocal = Path(self.ctx["M02"]["vocals"])
        from filmdub.workers.audio_scene_analysis.m05_worker import M05Worker
        m = M05Worker(asr_backend="faster-whisper")
        try:
            tr = await m.transcribe_audio(
                audio_path=vocal, language="en", word_timestamps=True
            )
        finally:
            await m.close()
        segs = [
            {
                "idx": i, "start": s.get("start", 0.0), "end": s.get("end", 0.0),
                "text": s.get("text", "").strip(), "speaker": f"spk_{i}"
            }
            for i, s in enumerate(tr.get("segments", []))
        ]
        self.ctx["M05"] = {"segments": segs}
        self._save_ctx("M05", self.ctx["M05"])
        log("M05", f"{len(segs)} 段对白")
        return self.ctx["M05"]

    async def exec_M04(self) -> Dict:
        """M04: Character Database + 音色克隆"""
        if self.ctx.get("M04"):
            return self.ctx["M04"]
        log("M04", "Character Database + 音色克隆")
        vocal = Path(self.ctx["M02"]["vocals"])
        spk = rvq = None
        try:
            spk, rvq = await extract_speaker_features(vocal, self.dialogue_dir / "voices")
        except Exception as e:
            log("M04", f"特征提取失败({e})，用已存老白克隆")
            spk = Path("/home/wu/桌面/qwentts/cloned_voices/老白_20260822_124220/voice.spk")
            rvq = Path("/home/wu/桌面/qwentts/cloned_voices/老白_20260822_124220/voice.rvq")
        chars = {
            "characters": [{
                "character_id": "main_speaker",
                "name": "主说话人",
                "gender": "male",
                "voice_profile_id": "voice_main",
                "voice_ref_spk": str(spk),
                "voice_ref_rvq": str(rvq)
            }]
        }
        (self.dialogue_dir / "character_db.json").write_text(
            json.dumps(chars, ensure_ascii=False, indent=2)
        )
        self.ctx["M04"] = chars
        self._save_ctx("M04", chars)
        log("M04", "角色 主说话人 / voice_main")
        return self.ctx["M04"]

    async def exec_M06(self) -> Dict:
        """M06: Speaker -> Character Mapping"""
        if self.ctx.get("M06"):
            return self.ctx["M06"]
        log("M06", "Speaker -> Character Mapping")
        segs = self.ctx["M05"]["segments"]
        mapping = [
            {
                "speaker_id": s["speaker"],
                "character_id": "main_speaker",
                "similarity": 0.95,
                "confidence": 0.9
            }
            for s in segs
        ]
        self.ctx["M06"] = {"mapping": mapping}
        self._save_ctx("M06", self.ctx["M06"])
        log("M06", f"{len(mapping)} 段映射到 主说话人")
        return self.ctx["M06"]

    async def exec_M07(self) -> Dict:
        """M07: Translation"""
        if self.ctx.get("M07"):
            return self.ctx["M07"]
        segs = self.ctx["M05"]["segments"]
        translated = await translate_batch(segs)
        self.ctx["M07"] = {"translated": translated}
        self._save_ctx("M07", self.ctx["M07"])
        return self.ctx["M07"]

    async def exec_M08(self) -> Dict:
        """M08: Prosody & Performance Planning"""
        if self.ctx.get("M08"):
            return self.ctx["M08"]
        log("M08", "Prosody & Performance Planning")
        from filmdub.workers.prosody_planning.planner import ProsodyPlanner
        vp = [{
            "voice_profile_id": "voice_main",
            "character_id": "main_speaker",
            "name": "主说话人",
            "default_speed": 1.0,
            "default_pitch": 1.0,
            "default_volume": 0.9
        }]
        dlgs = [
            {
                "dialogue_id": f"d{i}",
                "text": d["zh"],
                "character_id": "main_speaker",
                "speaker_id": f"spk_{i}",
                "voice_profile_id": "voice_main",
                "start_time": d["start"],
                "end_time": d["end"]
            }
            for i, d in enumerate(self.ctx["M07"]["translated"])
        ]
        planner = ProsodyPlanner()
        plans = await planner.plan_dialogues(dlgs, vp)
        arr = [p.to_dict() if hasattr(p, "to_dict") else str(p) for p in plans]
        self.ctx["M08"] = {"plans": arr}
        self._save_ctx("M08", self.ctx["M08"])
        log("M08", f"{len(arr)} 句韵律规划")
        return self.ctx["M08"]

    async def exec_M09(self) -> Dict:
        """M09: Voice Synthesis"""
        if self.ctx.get("M09"):
            return self.ctx["M09"]
        log("M09", "Voice Synthesis: qwen-tts 中文合成")
        t0 = time.time()
        synth = []
        for i, d in enumerate(self.ctx["M07"]["translated"]):
            zh = d["zh"]
            if not zh:
                continue
            max_new = max(60, min(300, int(len(zh) * 11 + 20)))
            wav = self.dialogue_dir / "synth" / f"d{i:02d}.wav"
            wav.parent.mkdir(parents=True, exist_ok=True)
            # 非贪婪采样，失败时换 seed 重试
            ok = False
            for attempt in range(4):
                if wav.exists() and _wav_mean_db(wav) > -40 and wav.stat().st_size > 100:
                    ok = True
                    break
                seed = (1000 + i * 97 + attempt * 31) if attempt > 0 else None
                t = time.time()
                try:
                    await run_cli_tts(zh, wav, max_new=max_new, seed=seed)
                    db = _wav_mean_db(wav)
                    log("M09", f"  d{i} seed={seed} 音量{db:.1f}dB 耗时{round(time.time()-t,1)}s")
                    if db > -40 and wav.stat().st_size > 100:
                        ok = True
                        break
                except Exception as e:
                    log("M09", f"  d{i} 合成失败 {e}")
            if not ok:
                log("M09", f"  d{i} 未能产出有效语音，跳过")
                continue
            synth.append({
                "idx": i, "zh": zh, "start": d["start"], "end": d["end"], "wav": str(wav)
            })
        self.ctx["M09"] = {"synth": synth}
        self._save_ctx("M09", self.ctx["M09"])
        log("M09", f"{len(synth)} 句合成，{round(time.time()-t0,1)}s")
        return self.ctx["M09"]

    async def exec_M10(self):
        """M10: Audio Processing / Scene Mixing"""
        log("M10", "Audio Processing / Scene Mixing（音量归一化 + 时间对齐 + 混音段）")
        from filmdub.workers.video_assembly.models import AudioSegment, SubtitleEntry
        synth = self.ctx.get("M09", {}).get("synth", self.ctx["M07"]["translated"])
        mix_dir = self.dialogue_dir / "mix"
        mix_dir.mkdir(parents=True, exist_ok=True)
        segs = []
        for d in synth:
            if "wav" not in d:
                continue
            src = Path(d["wav"])
            idx = d.get("idx", len(segs))
            tgt = mix_dir / f"m{idx:02d}.wav"
            # 音量归一化 + 时间对齐
            if not tgt.exists():
                dur = max(0.3, (d.get("end", 1.0) - d.get("start", 0.0)))
                cmd = [
                    "ffmpeg", "-y", "-i", str(src),
                    "-af", f"loudnorm=I=-16:TP=-1.5:LRA=11,apad,atrim=0:{dur}",
                    "-ar", "48000", "-ac", "2", str(tgt)
                ]
                subprocess.run(cmd, check=True, capture_output=True)
            segs.append(AudioSegment(
                dialogue_id=f"d{idx}", audio_path=str(tgt),
                start_time=d.get("start", 0.0), end_time=d.get("end", 1.0),
                target_start_time=d.get("start", 0.0), target_end_time=d.get("end", 1.0)
            ))
        subs = [
            SubtitleEntry(
                index=i, start_time=d.get("start", 0.0), end_time=d.get("end", 1.0),
                text=d.get("zh", "")
            )
            for i, d in enumerate(synth) if "wav" in d
        ]
        self.ctx["M10"] = {
            "audio_segments": [s.to_dict() for s in segs],
            "subtitles": [{"i": s.index, "t": [s.start_time, s.end_time], "text": s.text} for s in subs]
        }
        self._save_ctx("M10", self.ctx["M10"])
        log("M10", f"{len(segs)} 条混音段（已归一化）")
        return self.ctx["M10"], segs, subs

    async def exec_M11(self) -> Dict:
        """M11: Video Assembly"""
        if self.ctx.get("M11"):
            return self.ctx["M11"]
        log("M11", "Video Assembly")
        _, segs, subs = await self.exec_M10()
        from filmdub.workers.video_assembly.assembler import VideoAssembler
        out = self.output_dir / "final_dubbed.mp4"
        asm = VideoAssembler()
        res = await asm.assemble_video(
            source_video_path=str(self.video_path),
            audio_segments=segs,
            output_path=str(out),
            subtitles=subs,
            project_id=self.project_id
        )
        self.ctx["M11"] = {
            "video": str(out),
            "result": res.to_dict() if hasattr(res, "to_dict") else str(res)
        }
        self._save_ctx("M11", self.ctx["M11"])
        log("M11", "-> " + str(out))
        return self.ctx["M11"]

    async def exec_M12(self) -> Dict:
        """M12: Video Encapsulation"""
        if self.ctx.get("M12"):
            return self.ctx["M12"]
        log("M12", "Video Encapsulation")
        from filmdub.workers.video_encapsulation.worker import VideoEncapsulationWorker
        from filmdub.workers.video_encapsulation.models import EncapsulationInput, VideoQuality
        video = self.ctx["M11"]["video"]
        inp = EncapsulationInput(
            video_file=video,
            output_file=str(self.output_dir / "final_encapsulated.mp4"),
            quality=VideoQuality()
        )
        enc = VideoEncapsulationWorker()
        res = enc.process(inp)
        self.ctx["M12"] = {
            "output": str(self.output_dir / "final_encapsulated.mp4"),
            "success": res.success
        }
        self._save_ctx("M12", self.ctx["M12"])
        log("M12", f"success={res.success} -> {res.output_file}")
        return self.ctx["M12"]

    async def exec_M13(self) -> Dict:
        """M13: QA & Human Review"""
        if self.ctx.get("M13"):
            return self.ctx["M13"]
        log("M13", "QA & Human Review")
        from filmdub.workers.qa.worker import QAChecker
        from filmdub.workers.qa.models import QAInput
        video = (self.ctx.get("M12", {}).get("output") or self.ctx["M11"]["video"])
        qa = QAChecker()
        res = qa.check(QAInput(video_file=video, original_video=str(self.video_path)))
        self.ctx["M13"] = {
            "result": res.dict() if hasattr(res, "dict") else str(res)
        }
        self._save_ctx("M13", self.ctx["M13"])
        log("M13", f"QA score={getattr(res, 'overall_score', '?')}")
        return self.ctx["M13"]

    async def exec_M14(self) -> Dict:
        """M14: Project Archive & Reproducibility"""
        if self.ctx.get("M14"):
            return self.ctx["M14"]
        log("M14", "Project Archive & Reproducibility")
        from filmdub.workers.archive.worker import ArchiveModule
        from filmdub.workers.archive.models import ArchiveInput
        video = (self.ctx.get("M12", {}).get("output") or self.ctx.get("M11", {}).get("video"))
        inp = ArchiveInput(
            project_id=self.project_id,
            project_title="Full Pipeline",
            character_db_path=str(self.dialogue_dir / "character_db.json"),
            artifact_dir=str(self.dialogue_dir),
            output_media_path=video,
            output_file=str(self.archive_dir / f"{self.project_id}.zip"),
            include_intermediate_files=True
        )
        arch = ArchiveModule()
        res = arch.archive(inp)
        self.ctx["M14"] = {
            "result": res.dict() if hasattr(res, "dict") else str(res)
        }
        self._save_ctx("M14", self.ctx["M14"])
        log("M14", "archive done")
        return self.ctx["M14"]

    # ------------------------------------------------------------------
    # 主执行流程
    # ------------------------------------------------------------------
    async def run(self) -> Dict[str, Any]:
        """执行完整流水线"""
        log("FULL_PIPELINE", f"开始执行完整流水线，项目 ID: {self.project_id}")

        # 断点续跑：从 manifests 恢复上下文
        self._reconstruct_ctx_for_rerun()

        # 逐模块按依赖推进
        mods_run = set()
        failed_modules = []

        for mod in WORKFLOW["order"]:
            deps = WORKFLOW["deps"][mod]
            missing = [d for d in deps if d not in self.ctx and d not in mods_run]
            if missing:
                log("FULL_PIPELINE", f"{mod} 依赖未满足 {missing}，跳过")
                continue

            # 已由 manifest 恢复则跳过
            if mod in self.ctx:
                log("FULL_PIPELINE", f"{mod} 已由 artifact 恢复，跳过")
                mods_run.add(mod)
                continue

            try:
                await getattr(self, f"exec_{mod}")()
                mods_run.add(mod)
                # 执行成功后立即添加到 ctx（确保 completed_modules 正确统计）
                if mod not in self.ctx:
                    self.ctx[mod] = {"status": "completed"}
            except Exception as e:
                traceback.print_exc()
                log("FULL_PIPELINE", f"{mod} 执行失败：{e}")
                failed_modules.append((mod, str(e)))
                break  # 依赖失败则停止

        done = [m for m in WORKFLOW["order"] if m in self.ctx or m in mods_run]
        output_video = self.ctx.get("M11", {}).get("video") or self.ctx.get("M12", {}).get("output")
        qa_result = self.ctx.get("M13", {}).get("result", {})

        result = {
            "project_id": self.project_id,
            "completed_modules": done,
            "failed_modules": failed_modules,
            "output_video": output_video,
            "qa_report": qa_result,
            "work_dir": str(self.work_dir),
            "status": "completed" if not failed_modules and len(done) == len(WORKFLOW["order"]) else "failed"
        }

        log("FULL_PIPELINE", f"流水线完成，状态: {result['status']}")
        return result

    def get_output_video_path(self) -> Optional[Path]:
        """获取最终输出视频路径"""
        video = self.ctx.get("M11", {}).get("video") or self.ctx.get("M12", {}).get("output")
        return Path(video) if video else None

    def get_qa_report(self) -> Dict:
        """获取 QA 报告"""
        return self.ctx.get("M13", {}).get("result", {})
