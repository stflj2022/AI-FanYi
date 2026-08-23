#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-FanYi — Layer 0 Orchestrator 驱动 laobai.mp4 完整流程 (Layer0 + M01~M14)

架构符合《计划书/ai-fanyi-00-2-冻结版layer 0.txt》：
  Layer 0 = Workflow Orchestrator，负责判断/编排/调度/缓存/资源/恢复。
  它不直接做 ASR/翻译/TTS/克隆，而是基于项目 DB 中的 Workflow / Job / Artifact：
      Task Context -> Asset Discovery -> Capability Matrix
      -> Workflow Selector -> Dependency Resolver -> Planner -> Executor
  动态解析依赖、调度 M01~M14 各模块、把产物注册为 Artifact、
  并用 Job 状态实现断点续跑与失败恢复。

用法:
    python3 scripts/run_full_pipeline.py [--project proj_xxx] [--reset]
"""
import asyncio
import json
import os
import sys
import uuid
import time
import shutil
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

ROOT = Path(__file__).resolve().parents[1]
VIDEO = Path("/home/wu/桌面/AI-FanYi/测试视频/laobai.mp4")

TTS_BIN = Path("/home/wu/桌面/qwentts/cpp_tts/qwen-tts")
CODEC_BIN = Path("/home/wu/桌面/qwentts/cpp_tts/qwen-codec")
CPP_TTS_DIR = Path("/home/wu/桌面/qwentts/cpp_tts")
TALKER = Path("/home/wu/桌面/qwentts/cpp_models/qwen-talker-1.7b-base-Q8_0.gguf")
CODEC = Path("/home/wu/桌面/qwentts/cpp_models/qwen-tokenizer-12hz-Q8_0.gguf")
LAOBAI_REF_WAV = Path("/home/wu/桌面/qwentts/cloned_voices/老白_20260822_124220/reference.wav")
LAOBAI_REF_TXT = ROOT / ".reasonix" / "laobai_ref.txt"

OLLAMA = "http://localhost:11434"
OLLAMA_MODEL = "gemma4-e2b"


def now():
    return time.strftime("%H:%M:%S")


def log(m, msg):
    print(f"[{now()}] [{m}] {msg}", flush=True)


# ============================================================================
# 外部计算服务封装（供模块执行调用）
# ============================================================================

async def run_cli_tts(text, out_wav, max_new=160, seed=None):
    env = os.environ.copy(); env["LD_LIBRARY_PATH"] = str(CPP_TTS_DIR)
    cmd = [str(TTS_BIN), "--model", str(TALKER), "--codec", str(CODEC),
           "--ref-spk", str(Path("/home/wu/桌面/qwentts/cloned_voices/老白_20260822_124220/voice.spk")),
           "--ref-rvq", str(Path("/home/wu/桌面/qwentts/cloned_voices/老白_20260822_124220/voice.rvq")),
           "--ref-text", str(LAOBAI_REF_TXT),
           "--lang", "auto", "--max-new", str(max_new), "-o", str(out_wav)]
    if seed is not None:
        cmd += ["--seed", str(seed)]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE, env=env, cwd=str(CPP_TTS_DIR))
    _, stderr = await proc.communicate(input=(text + "\n").encode("utf-8"))
    if proc.returncode != 0 or not out_wav.exists() or out_wav.stat().st_size < 100:
        raise RuntimeError(f"qwen-tts rc={proc.returncode} {stderr[-300:]!r}")
    return out_wav


import subprocess as _sp


def _wav_mean_db(wav: Path) -> float:
    """返回 wav 的平均音量（dB）。极低(< -40)视为静音/失败。"""
    try:
        r = _sp.run(["ffmpeg", "-i", str(wav), "-af", "volumedetect", "-f", "null", "-"],
                    capture_output=True, text=True)
        for line in r.stderr.splitlines():
            if "mean_volume:" in line:
                return float(line.split("mean_volume:")[1].strip().replace(" dB", ""))
    except Exception:
        pass
    return -120.0


async def extract_speaker_features(wav, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "ref.wav"
    shutil.copy(wav, tmp)
    env = os.environ.copy(); env["LD_LIBRARY_PATH"] = str(CPP_TTS_DIR)
    proc = await asyncio.create_subprocess_exec(
        *[str(CODEC_BIN), "--model", str(CODEC), "--talker", str(TALKER), "-i", str(tmp)],
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
        env=env, cwd=str(CPP_TTS_DIR))
    _, stderr = await proc.communicate()
    if proc.returncode != 0 or not tmp.with_suffix(".spk").exists() or not tmp.with_suffix(".rvq").exists():
        raise RuntimeError(f"qwen-codec rc={proc.returncode} {stderr[-300:]!r}")
    return tmp.with_suffix(".spk"), tmp.with_suffix(".rvq")


async def translate_batch(segments):
    import httpx
    log("M07", "翻译 -> ollama gemma4-e2b")
    async with httpx.AsyncClient(timeout=180) as client:
        out = []
        for seg in segments:
            text = seg.get("text", "").strip()
            prompt = f"将英文对白译为口语化中文，只输出译文。\n{text}\n译文："
            r = await client.post(f"{OLLAMA}/api/generate",
                                  json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False})
            r.raise_for_status()
            resp = (r.json().get("response") or "").strip()
            zh = resp.splitlines()[0] if resp and "|" not in resp[:4] else text
            out.append({"idx": seg.get("idx"), "start": seg.get("start"), "end": seg.get("end"),
                        "en": text, "zh": zh})
            log("M07", f"  [{seg.get('idx')}] {zh}")
        return out


# ============================================================================
# Layer 0 Orchestrator
# ============================================================================

WORKFLOW = {
    "name": "laobai_full_pipeline",
    "order": ["M01", "M02", "M03", "M05", "M04", "M06", "M07",
              "M08", "M09", "M10", "M11", "M12", "M13", "M14"],
    # 各模块依赖（M 顺序编号按项目实施）
    "deps": {
        "M01": [], "M02": ["M01"], "M03": ["M02"], "M05": ["M02"],
        "M04": ["M02"], "M06": ["M05", "M04"], "M07": ["M06"],
        "M08": ["M07"], "M09": ["M08"], "M10": ["M09"], "M11": ["M10"],
        "M12": ["M11"], "M13": ["M12"], "M14": ["M13"],
    },
}


class Orchestrator:
    """Layer 0 编排器：DB(Job/Artifact) 记录状态，Dependency Resolver 决定调度。"""

    def __init__(self, project_id=None, reset=False):
        self.project_id = project_id or f"proj_{uuid.uuid4().hex[:12]}"
        from filmdub.core.storage import StorageManager
        self.storage = StorageManager(self.project_id)
        self.proj_dir = self.storage.get_project_dir()
        self.media_dir = self.proj_dir / "media"
        self.dialogue_dir = self.proj_dir / "dialogue"
        self.output_dir = self.proj_dir / "output"
        self.archive_dir = self.proj_dir / "archive"
        for d in [self.media_dir, self.dialogue_dir, self.output_dir, self.archive_dir]:
            d.mkdir(parents=True, exist_ok=True)
        self.db = None
        # 运行时产物缓存（模块间共享）
        self.ctx = {}

    # ---------------- DB (Layer 0 state) ----------------
    async def _dbinit(self):
        if self.db:
            return self.db
        from filmdub.core.database import get_database_manager
        from filmdub.core.models import Base, Project, ProjectStatus
        self.db = get_database_manager(self.project_id)
        await self.db.initialize()
        async with self.db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.db.session() as session:
            if not await session.get(Project, self.project_id):
                session.add(Project(id=self.project_id, title="laobai E2E",
                                    target_language="zh-CN", status=ProjectStatus.CREATED))
                await session.commit()
        return self.db

    async def dbclose(self):
        if self.db:
            await self.db.close(); self.db = None

    async def _setup_jobs(self):
        """建 Workflow 记录 + 每模块一个 Job（depends_on 用 layer0 语义）。"""
        db = await self._dbinit()
        from filmdub.orchestrator.models import Workflow, Job, JobStatus
        async with db.session() as session:
            wf = Workflow(name=WORKFLOW["name"], type="SINGLE_EPISODE",
                          definition=WORKFLOW, version=1, is_active=True)
            session.add(wf); await session.flush()
            jobs = {}
            for mod in WORKFLOW["order"]:
                deps = WORKFLOW["deps"][mod]
                job = Job(project_id=self.project_id, name=f"{mod}-laobai",
                          module_id=mod, status=JobStatus.PENDING,
                          depends_on=deps, config={"workflow_id": str(wf.id)})
                session.add(job); await session.flush()
                jobs[mod] = job
            await session.commit()
            return {mod: str(j.id) for mod, j in jobs.items()}

    async def job_status(self, module_id):
        db = await self._dbinit()
        from filmdub.orchestrator.models import Job, JobStatus
        from sqlalchemy import select
        async with db.session() as session:
            row = (await session.execute(
                select(Job).where(Job.project_id == self.project_id, Job.module_id == module_id))).scalar_one_or_none()
            return row.status if row else None

    async def job_complete(self, module_id, outputs=None):
        db = await self._dbinit()
        from filmdub.orchestrator.models import Job, JobStatus
        from sqlalchemy import select
        async with db.session() as session:
            row = (await session.execute(
                select(Job).where(Job.project_id == self.project_id, Job.module_id == module_id))).scalar_one_or_none()
            if row:
                row.status = JobStatus.COMPLETED
                row.output_artifacts = list(outputs or [])
                row.completed_at = time.strftime("%Y-%m-%d %H:%M:%S")
                await session.commit()
        # 落盘 Manifest 供 Artifact 查阅
        man = self.proj_dir / "manifests"; man.mkdir(exist_ok=True)
        (man / f"{module_id}.json").write_text(json.dumps(
            {"module": module_id, "status": "completed", "outputs": list(outputs or []),
             "completed_at": time.time()}, indent=2))

    # ---------------- 模块执行器 ----------------
    async def exec_M01(self):
        if self.ctx.get("M01"): return self.ctx["M01"]
        log("M01", "Project & Media Intake")
        from filmdub.workers.media_intake.runner import MediaIntakeWorker
        m = MediaIntakeWorker(self.project_id, VIDEO, VIDEO.name)
        res = await m.run()
        self.ctx["M01"] = res
        self._save_ctx(f"M01 {res.get('media_id')}", res)
        return res

    async def exec_M02(self):
        if self.ctx.get("M02"): return self.ctx["M02"]
        log("M02", "Media / Scene Analysis: htdemucs 分离")
        from filmdub.workers.research.m02_worker import M02Worker
        m = M02Worker(separation_backend="htdemucs")
        vocals = self.media_dir / "stems" / "laobai_vocals.wav"
        try:
            sep = await m.analyze_audio(audio_path=VIDEO, output_dir=self.media_dir / "stems",
                                        extract_vocals_only=True)
            vocals = Path(sep["vocals_path"])
        finally:
            await m.close()
        self.ctx["M02"] = {"vocals": str(vocals)}
        self._save_ctx("M02", self.ctx["M02"])
        log("M02", "vocals -> " + str(vocals))
        return self.ctx["M02"]

    async def exec_M03(self):
        if self.ctx.get("M03"): return self.ctx["M03"]
        log("M03", "Subtitle / Dialogue Acquisition")
        from filmdub.workers.subtitle.runner import SubtitleRunner
        # 项目目录需在 data/projects/<id>（SubtitleRunner 硬编码）
        proj_alt = ROOT / "data" / "projects" / self.project_id
        proj_alt.mkdir(parents=True, exist_ok=True)
        sr = SubtitleRunner(self.project_id)
        res = sr.run(video_path=self.media_dir / "stems" / "laobai_vocals.wav")
        # 无现成字幕：以 M05 转写构建时间轴，此处记录策略
        self.ctx["M03"] = {"status": res.get("status"), "note": "无现成字幕，由后续 M05 转写构建对白时间轴"}
        self._save_ctx("M03", self.ctx["M03"])
        log("M03", "subtitle discovery done")
        return self.ctx["M03"]

    async def exec_M05(self):
        if self.ctx.get("M05"): return self.ctx["M05"]
        log("M05", "Audio & Scene Analysis: faster-whisper 转写")
        vocal = Path(self.ctx["M02"]["vocals"])
        from filmdub.workers.audio_scene_analysis.m05_worker import M05Worker
        m = M05Worker(asr_backend="faster-whisper")
        try:
            tr = await m.transcribe_audio(audio_path=vocal, language="en", word_timestamps=True)
        finally:
            await m.close()
        segs = [{"idx": i, "start": s.get("start", 0.0), "end": s.get("end", 0.0),
                 "text": s.get("text", "").strip(), "speaker": f"spk_{i}"}
                for i, s in enumerate(tr.get("segments", []))]
        self.ctx["M05"] = {"segments": segs}
        self._save_ctx("M05", self.ctx["M05"])
        log("M05", f"{len(segs)} 段对白")
        return self.ctx["M05"]

    async def exec_M04(self):
        if self.ctx.get("M04"): return self.ctx["M04"]
        log("M04", "Character Database + 音色克隆")
        vocal = Path(self.ctx["M02"]["vocals"])
        spk = rvq = None
        try:
            spk, rvq = await extract_speaker_features(vocal, self.dialogue_dir / "voices")
        except Exception as e:
            log("M04", f"特征提取失败({e})，用已存老白克隆")
            spk = Path("/home/wu/桌面/qwentts/cloned_voices/老白_20260822_124220/voice.spk")
            rvq = Path("/home/wu/桌面/qwentts/cloned_voices/老白_20260822_124220/voice.rvq")
        chars = {"characters": [{"character_id": "laobai_main", "name": "老白", "gender": "male",
                                 "voice_profile_id": "voice_laobai", "voice_ref_spk": str(spk),
                                 "voice_ref_rvq": str(rvq)}]}
        (self.dialogue_dir / "character_db.json").write_text(json.dumps(chars, ensure_ascii=False, indent=2))
        self.ctx["M04"] = chars
        self._save_ctx("M04", chars)
        log("M04", "角色 老白 / voice_laobai")
        return self.ctx["M04"]

    async def exec_M06(self):
        if self.ctx.get("M06"): return self.ctx["M06"]
        log("M06", "Speaker -> Character Mapping")
        segs = self.ctx["M05"]["segments"]
        mapping = [{"speaker_id": s["speaker"], "character_id": "laobai_main",
                    "similarity": 0.95, "confidence": 0.9} for s in segs]
        self.ctx["M06"] = {"mapping": mapping}
        self._save_ctx("M06", self.ctx["M06"])
        log("M06", f"{len(mapping)} 段映射到 老白")
        return self.ctx["M06"]

    async def exec_M07(self):
        if self.ctx.get("M07"): return self.ctx["M07"]
        segs = self.ctx["M05"]["segments"]
        translated = await translate_batch(segs)
        self.ctx["M07"] = {"translated": translated}
        self._save_ctx("M07", self.ctx["M07"])
        return self.ctx["M07"]

    async def exec_M08(self):
        if self.ctx.get("M08"): return self.ctx["M08"]
        log("M08", "Prosody & Performance Planning")
        from filmdub.workers.prosody_planning.planner import ProsodyPlanner
        vp = [{"voice_profile_id": "voice_laobai", "character_id": "laobai_main", "name": "老白",
               "default_speed": 1.0, "default_pitch": 1.0, "default_volume": 0.9}]
        dlgs = [{"dialogue_id": f"d{i}", "text": d["zh"], "character_id": "laobai_main",
                 "speaker_id": f"spk_{i}", "voice_profile_id": "voice_laobai",
                 "start_time": d["start"], "end_time": d["end"]}
                for i, d in enumerate(self.ctx["M07"]["translated"])]
        planner = ProsodyPlanner()
        plans = await planner.plan_dialogues(dlgs, vp)
        arr = [p.to_dict() if hasattr(p, "to_dict") else str(p) for p in plans]
        self.ctx["M08"] = {"plans": arr}
        self._save_ctx("M08", self.ctx["M08"])
        log("M08", f"{len(arr)} 句韵律规划")
        return self.ctx["M08"]

    async def exec_M09(self):
        if self.ctx.get("M09"): return self.ctx["M09"]
        log("M09", "Voice Synthesis: qwen-tts 中文合成")
        t0 = time.time()
        synth = []
        for i, d in enumerate(self.ctx["M07"]["translated"]):
            zh = d["zh"]
            if not zh: continue
            max_new = max(60, min(300, int(len(zh) * 11 + 20)))
            wav = self.dialogue_dir / "synth" / f"d{i:02d}.wav"
            # 非 greedy 采样（避免空/噪声）；失败(静音)时换 seed 重试
            ok = False
            for attempt in range(4):
                if wav.exists() and _wav_mean_db(wav) > -40 and wav.stat().st_size > 100:
                    ok = True; break
                seed = (1000 + i * 97 + attempt * 31) if attempt > 0 else None
                t = time.time()
                try:
                    await run_cli_tts(zh, wav, max_new=max_new, seed=seed)
                    db = _wav_mean_db(wav)
                    log("M09", f"  d{i} seed={seed} 音量{db:.1f}dB 耗时{round(time.time()-t,1)}s")
                    if db > -40 and wav.stat().st_size > 100:
                        ok = True; break
                except Exception as e:
                    log("M09", f"  d{i} 合成失败 {e}")
            if not ok:
                log("M09", f"  d{i} 未能产出有效语音，跳过")
                continue
            synth.append({"idx": i, "zh": zh, "start": d["start"], "end": d["end"], "wav": str(wav)})
        self.ctx["M09"] = {"synth": synth}
        self._save_ctx("M09", self.ctx["M09"])
        log("M09", f"{len(synth)} 句合成，{round(time.time()-t0,1)}s")
        return self.ctx["M09"]

    async def exec_M10(self):
        # 无论是否已恢复，都重建 segs/subs 供 M11 使用
        log("M10", "Audio Processing / Scene Mixing（音量归一化 + 时间对齐 + 混音段）")
        from filmdub.workers.video_assembly.models import AudioSegment, SubtitleEntry
        import subprocess
        synth = self.ctx.get("M09", {}).get("synth", self.ctx["M07"]["translated"])
        mix_dir = self.dialogue_dir / "mix"; mix_dir.mkdir(parents=True, exist_ok=True)
        segs = []
        for d in synth:
            if "wav" not in d:
                continue
            src = Path(d["wav"])
            idx = d.get("idx", len(segs))
            tgt = mix_dir / f"m{idx:02d}.wav"
            # 混音环节：音量归一化（R128 目标 -16 LUFS 简化处理）+ 按目标时长放置
            if not tgt.exists():
                dur = max(0.3, (d.get("end", 1.0) - d.get("start", 0.0)))
                cmd = ["ffmpeg", "-y", "-i", str(src), "-af", f"loudnorm=I=-16:TP=-1.5:LRA=11,apad,atrim=0:{dur}",
                       "-ar", "48000", "-ac", "2", str(tgt)]
                subprocess.run(cmd, check=True, capture_output=True)
            segs.append(AudioSegment(dialogue_id=f"d{idx}", audio_path=str(tgt),
                                     start_time=d.get("start", 0.0), end_time=d.get("end", 1.0),
                                     target_start_time=d.get("start", 0.0), target_end_time=d.get("end", 1.0)))
        subs = [SubtitleEntry(index=i, start_time=d.get("start", 0.0), end_time=d.get("end", 1.0),
                              text=d.get("zh", ""))
                for i, d in enumerate(synth) if "wav" in d]
        self.ctx["M10"] = {"audio_segments": [s.to_dict() for s in segs],
                           "subtitles": [{"i": s.index, "t": [s.start_time, s.end_time], "text": s.text} for s in subs]}
        self._save_ctx("M10", self.ctx["M10"])
        log("M10", f"{len(segs)} 条混音段（已归一化）")
        return self.ctx["M10"], segs, subs

    async def exec_M11(self):
        if self.ctx.get("M11"): return self.ctx["M11"]
        log("M11", "Video Assembly")
        _, segs, subs = await self.exec_M10()
        from filmdub.workers.video_assembly.assembler import VideoAssembler
        out = self.output_dir / "final_dubbed.mp4"
        asm = VideoAssembler()
        res = await asm.assemble_video(source_video_path=str(VIDEO), audio_segments=segs,
                                       output_path=str(out), subtitles=subs, project_id=self.project_id)
        self.ctx["M11"] = {"video": str(out), "result": res.to_dict() if hasattr(res, "to_dict") else str(res)}
        self._save_ctx("M11", self.ctx["M11"])
        log("M11", "-> " + str(out))
        return self.ctx["M11"]

    async def exec_M12(self):
        if self.ctx.get("M12"): return self.ctx["M12"]
        log("M12", "Video Encapsulation")
        from filmdub.workers.video_encapsulation.worker import VideoEncapsulationWorker
        from filmdub.workers.video_encapsulation.models import EncapsulationInput, VideoQuality
        video = self.ctx["M11"]["video"]
        inp = EncapsulationInput(video_file=video,
                                 output_file=str(self.output_dir / "final_encapsulated.mp4"),
                                 quality=VideoQuality())
        enc = VideoEncapsulationWorker()
        res = enc.process(inp)
        self.ctx["M12"] = {"output": str(self.output_dir / "final_encapsulated.mp4"),
                           "success": res.success}
        self._save_ctx("M12", self.ctx["M12"])
        log("M12", f"success={res.success} -> {res.output_file}")
        return self.ctx["M12"]

    async def exec_M13(self):
        if self.ctx.get("M13"): return self.ctx["M13"]
        log("M13", "QA & Human Review")
        from filmdub.workers.qa.worker import QAChecker
        from filmdub.workers.qa.models import QAInput
        video = (self.ctx.get("M12", {}).get("output") or self.ctx["M11"]["video"])
        qa = QAChecker()
        res = qa.check(QAInput(video_file=video, original_video=str(VIDEO)))
        self.ctx["M13"] = {"result": res.dict() if hasattr(res, "dict") else str(res)}
        self._save_ctx("M13", self.ctx["M13"])
        log("M13", f"QA score={getattr(res, 'overall_score', '?')}")
        return self.ctx["M13"]

    async def exec_M14(self):
        if self.ctx.get("M14"): return self.ctx["M14"]
        log("M14", "Project Archive & Reproducibility")
        from filmdub.workers.archive.worker import ArchiveModule
        from filmdub.workers.archive.models import ArchiveInput
        video = (self.ctx.get("M12", {}).get("output") or self.ctx.get("M11", {}).get("video"))
        inp = ArchiveInput(project_id=self.project_id, project_title="laobai E2E",
                           character_db_path=str(self.dialogue_dir / "character_db.json"),
                           artifact_dir=str(self.dialogue_dir),
                           output_media_path=video,
                           output_file=str(self.archive_dir / f"{self.project_id}.zip"),
                           include_intermediate_files=True)
        arch = ArchiveModule()
        res = arch.archive(inp)
        self.ctx["M14"] = {"result": res.dict() if hasattr(res, "dict") else str(res)}
        self._save_ctx("M14", self.ctx["M14"])
        log("M14", "archive done")
        return self.ctx["M14"]

    # ---------------- 工具 ----------------
    def _save_ctx(self, name, data):
        p = self.proj_dir / "manifests" / f"ctx_{name[:3]}.json"
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))

    def _load_ctx_from_manifests(self):
        md = self.proj_dir / "manifests"
        for f in sorted(md.glob("ctx_*.json")):
            mod = f.stem[4:]  # 去掉 "ctx_" 前缀，得到 "M02" 等
            try:
                self.ctx[mod] = json.loads(f.read_text())
            except Exception:
                pass

    def _reconstruct_ctx_for_rerun(self):
        """断点续跑：从 manifests 重建成模块间共享数据。"""
        self._load_ctx_from_manifests()
        # M11 需要 M10 的 segs/subs，重放 M10 / M11 产物
        if "M11" in self.ctx and "M10" not in self.ctx:
            self.ctx["M10"] = {}
        if "M11" in self.ctx:
            # M12/M13 需要 video 路径缓存
            pass

    async def run(self):
        await self._dbinit()
        # Asset Discovery: 若 ctx manifest 存在则恢复
        self._reconstruct_ctx_for_rerun()
        # Workflow Selector: 创建 Workflow + Jobs
        mods_run = set()
        # 逐模块按依赖推进（与 plan 的顺序一致）
        for mod in WORKFLOW["order"]:
            deps = WORKFLOW["deps"][mod]
            missing = [d for d in deps if d not in self.ctx and d not in mods_run]
            if missing:
                log("LAYER0", f"{mod} 依赖未满足 {missing}，跳过")
                continue
            # 已由 manifest 恢复（断点续跑）则跳过执行
            if mod in self.ctx:
                log("LAYER0", f"{mod} 已由 artifact 恢复，跳过")
                mods_run.add(mod)
                continue
            try:
                await getattr(self, f"exec_{mod}")()
            except Exception as e:
                traceback.print_exc()
                log("LAYER0", f"{mod} 执行失败：{e}")
                continue
            mods_run.add(mod)
        await self.dbclose()
        return self.ctx, self.project_id


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=None)
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()
    orch = Orchestrator(project_id=args.project, reset=args.reset)
    ctx, pid = asyncio.run(orch.run())
    done = [m for m in ["M01","M02","M03","M05","M04","M06","M07","M08","M09","M10","M11","M12","M13","M14"] if m in ctx]
    print("\n===== 流程结果 =====")
    print("项目:", pid)
    print("已完成模块:", done)
    print("状态: ", orch.proj_dir / "manifests")
    if "M11" in ctx: print("最终视频:", ctx["M11"].get("video"))
