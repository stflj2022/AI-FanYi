# Layer 0 — qwentts Adapter 接口设计
**版本**: V1.0 | **日期**: 2026-08-23 | **状态**: 实现依据（无人值守按此实现）

---

## 1. 设计目标与原则

把 qwentts 封装为 Layer 0 可调度的**能力提供者**，供 M02/M04/M05/M09/M10 使用。

**遵循 Layer 0 三条铁律**：
1. **模块间禁止直接调用**：worker（如 M09）不直接调 qwentts，而是 `worker → Artifact → Layer 0 → adapter → qwentts`。
2. **Capability Matrix 状态机**：adapter 对外暴露能力状态 `NONE/PARTIAL/COMPLETE/INVALID/OUTDATED`，供 Layer 0 决策。
3. **可替换性**：adapter 是统一接口，将来换 TTS 引擎（如换回 CosyVoice）只改 adapter 实现，不影响 worker。

**adapter 层位置**：
```
worker(M02/M04/M05/M09/M10)
   │  只依赖 adapter 接口 + schemas
   ▼
src/filmdub/adapters/   ← 本设计
   │
   ├── voice.py      → qwentts tts-server + cloned_voices/ + qwen-codec
   ├── asr.py        → Faster-Whisper large-v3
   ├── separate.py   → HTDemucs
   └── registry.py   → Capability Matrix 状态查询
```

---

## 2. 统一抽象（src/filmdub/adapters/base.py）

所有 adapter 实现同一基类，暴露**能力状态**与**初始化**：

```python
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel

class Capability(Enum):
    NONE = "none"        # 不可用（模型缺失/未初始化）
    PARTIAL = "partial"  # 部分可用
    COMPLETE = "complete"# 完全可用
    INVALID = "invalid"  # 存在但配置/模型错误
    OUTDATED = "outdated"# 可用但版本过期

class AdapterResult(BaseModel):
    ok: bool
    error: Optional[str] = None
    data: Any = None

class BaseAdapter:
    name: str  # "voice" / "asr" / "separate"

    def health(self) -> Capability:
        """返回能力状态，供 Capability Matrix 查询。"""
        raise NotImplementedError

    def ensure_ready(self) -> None:
        """初始化/加载模型；失败抛 AdapterNotReady（含手动下载指引）。"""
        raise NotImplementedError

    def close(self) -> None:
        """释放资源（GPU/VRAM）。"""
        raise NotImplementedError
```

---

## 3. 数据模型（src/filmdub/adapters/schemas.py）

```python
# ---- 声音库 M04 ----
class VoiceProfile(BaseModel):
    """一个克隆音色（M04 声音库条目）"""
    id: str                 # 音色唯一 id（= cloned_voices/ 子目录名）
    name: str               # 用户可读名
    ref_text: str           # 参考音频对应文本
    spk_path: str           # .spk 特征文件绝对路径
    rvq_path: str           # .rvq 特征文件绝对路径
    reference_audio: str    # 参考音频路径
    created_at: str         # ISO 时间
    registered: bool        # 是否已注册到 tts-server

# ---- ASR M05 ----
class TranscriptSegment(BaseModel):
    text: str
    start: float            # 秒
    end: float
    speaker: Optional[str] = None  # 说话人标签（可选，由上游聚类）

class TranscriptionResult(BaseModel):
    language: str
    segments: list[TranscriptSegment]
    full_text: str

# ---- 分离 M02 ----
class SeparationResult(BaseModel):
    vocals_path: str        # 人声
    accompaniment_path: str # 伴奏（背景音乐+环境+音效）
    drums_path: Optional[str]
    bass_path: Optional[str]
    other_path: Optional[str]

# ---- 语音生成 M09 ----
class TTSSegment(BaseModel):
    text: str
    voice_id: str
    language: str = "zh-CN"
    speed: Optional[float] = None   # 弱整合 M10：语速
    pause_ms: Optional[int] = None  # 弱整合 M10：句间停顿

class TTSResult(BaseModel):
    output_path: str        # 生成的音频文件（wav/opus）
    voice_id: str
    duration_sec: Optional[float]
```

---

## 4. VoiceAdapter（强替换 M04 + M09）

**文件**: `src/filmdub/adapters/voice.py`
**对接**: qwentts tts-server（HTTP）+ `cloned_voices/`（文件系统）+ `qwen-codec`（CLI）

### 4.1 接口

```python
class VoiceAdapter(BaseAdapter):
    name = "voice"

    # ---- M04 声音库 ----
    async def clone_voice(self, name: str, ref_audio: str,
                          ref_text: str) -> VoiceProfile:
        """克隆音色并注册到 tts-server、保存到 cloned_voices/。
        内部：qwen-codec 提取特征 → register_voice → 写 meta.json"""
        ...

    async def list_voices(self) -> list[VoiceProfile]:
        """列出所有已保存/已注册音色。"""
        ...

    async def register_local_voice(self, voice_name: str) -> VoiceProfile:
        """把本地 cloned_voices/ 里的音色注册到 tts-server。"""
        ...

    async def delete_voice(self, voice_id: str) -> bool:
        """删除音色（含 cleanup）。"""
        ...

    # ---- M09 语音生成 ----
    async def synthesize(self, text: str, voice_id: str,
                         language: str = "zh-CN",
                         speed: float | None = None,
                         pause_ms: int | None = None) -> TTSResult:
        """单条文本合成。speed/pause_ms 为弱整合 M10。"""
        ...

    async def batch_synthesize(self, segments: list[TTSSegment],
                               output_dir: str,
                               output_format: str = "wav") -> list[TTSResult]:
        """批量合成（影视长对白）。断点续传：已生成的跳过。"""
        ...
```

### 4.2 qwentts 对接映射

| VoiceAdapter 方法 | qwentts 实现 | 返回 |
|---|---|---|
| `clone_voice` | `cpp_manager.cloner.extract_voice_features()` + `register_voice()` + 写 `cloned_voices/{name}_{ts}/meta.json` | VoiceProfile |
| `list_voices` | 读 `cloned_voices/` 各 `meta.json` | list[VoiceProfile] |
| `synthesize` | `cpp_manager.generate_speech(text, voice, language)` | (path, msg) → TTSResult |
| `batch_synthesize` | `batch_generate(text, voice, language, fmt, prefix)`（按行） | list[TTSResult] |

### 4.3 关键实现细节
- **voice_id ↔ qwentts 音色名**：VoiceProfile.id = 目录名（`{safe_name}_{ts}`），qwentts server 注册名 = `name`。需映射。
- **HTTP vs CLI**：合成走 tts-server HTTP（`generate_speech`）；克隆特征走 `qwen-codec` CLI。
- **tts-server 地址**：从 config 读（见 §8），默认 `http://127.0.0.1:xxxx`（由 `qwen-tts.service` 提供，systemd 已自启）。
- **models 检查**：`ensure_ready()` 检查 `cpp_models/qwen-talker-*.gguf`、`qwen-tokenizer-*.gguf` 存在。

---

## 5. ASRAdapter（辅助替换 M05）

**文件**: `src/filmdub/adapters/asr.py`
**对接**: Faster-Whisper large-v3

```python
class ASRAdapter(BaseAdapter):
    name = "asr"

    async def transcribe(self, audio_path: str,
                         language: str | None = None,
                         word_timestamps: bool = True) -> TranscriptionResult:
        """转写音频→带时间戳的分段文本。
        Faster-Whisper large-v3, compute_type=int8, device 由 config 定。"""
        ...
```

**实现**：`faster_whisper.WhisperModel("large-v3", device=..., compute_type="int8")`，
遍历 `segments` 收集 `(text, start, end)`。模型首次加载下载大文件（见 §8 下载策略）。

---

## 6. SeparateAdapter（辅助替换 M02）

**文件**: `src/filmdub/adapters/separate.py`
**对接**: HTDemucs

```python
class SeparateAdapter(BaseAdapter):
    name = "separate"

    async def separate(self, audio_path: str,
                       output_dir: str | None = None) -> SeparationResult:
        """人声/背景分离（HTDemucs）。输出 24kHz 单声道人声 + 伴奏。"""
        ...
```

**实现**：`demucs.separate` 或 `pretrained.get_model('htdemucs')` + `apply_model`。
输出按 §9 的 SeparationResult 落盘。

---

## 7. 能力注册表（src/filmdub/adapters/registry.py）

供 Layer 0 的 Capability Matrix 查询所有适配器状态：

```python
class AdapterRegistry:
    def __init__(self):
        self._adapters: dict[str, BaseAdapter] = {}

    def register(self, adapter: BaseAdapter) -> None: ...
    def get(self, name: str) -> BaseAdapter: ...
    def capability_matrix(self) -> dict[str, Capability]:
        """返回 {adapter: Capability}，供 Layer 0 决策。
        例如 {"voice": "complete", "asr": "partial", "separate": "none"}"""
        return {n: a.health() for n, a in self._adapters.items()}
```

**Capability 判定规则**：
| 资源 | COMPLETE 条件 | 常见 INVALID/OUTDATED 情形 |
|---|---|---|
| voice | tts-server 通 + 模型 gguf 在 + cloned_voices 可写 | server 挂、模型缺、voices 目录只读 |
| asr | faster_whisper 可导入 + 模型可加载 | 模型未下载（转 NONE）、显存不足 |
| separate | demucs 可导入 + 模型可加载 | 模型未下载 |

---

## 8. 配置（src/filmdub/core/config/adapters.py 或 .env）

```env
# qwentts 路径与 server
QWENTTS_BASE_DIR=~/桌面/qwentts
QWENTTS_CPP_TTS_DIR=${QWENTTS_BASE_DIR}/cpp_tts
QWENTTS_MODELS_DIR=${QWENTTS_BASE_DIR}/cpp_models
QWENTTS_CLONED_VOICES_DIR=${QWENTTS_BASE_DIR}/cloned_voices
QWENTTS_TTS_SERVER_URL=http://127.0.0.1:xxxx   # 由 qwen-tts.service 提供

# 模型设备
ADAPTER_DEVICE=cpu        # cpu / cuda / vulkan
ADAPTER_COMPUTE_TYPE=int8

# 下载/重试
ADAPTER_DOWNLOAD_RETRIES=5
ADAPTER_TIMEOUT_SEC=180
```

---

## 9. 错误处理与手动下载

统一异常：`AdapterNotReady(msg, manual_url=None)`、`AdapterError(msg)`。

`ensure_ready()` 失败时（模型缺失）：
1. 自动下载尝试 **5 次**（`ADAPTER_DOWNLOAD_RETRIES`）
2. 5 次后抛 `AdapterNotReady`，`manual_url` 指向：
   - HTDemucs: https://github.com/facebookresearch/demucs
   - Faster-Whisper large-v3: https://huggingface.co/Systran/faster-whisper-large-v3
   - qwen-tts GGUF: https://github.com/ServeurpersoCom/qwentts.cpp
3. Layer 0 捕获后：Capability Matrix 标 `NONE`，在 `docs/MANUAL_DOWNLOAD.md` 追加提示，跳过该模块并记日志，**不阻塞整条流水线**。

---

## 10. 测试策略

1. **单元测试**（`tests/adapters/`）：mock qwentts/Faster-Whisper/demucs，测接口契约与错误路径。
2. **adapter 冒烟**：真实调用（若模型在），对 `测试视频/laobai.mp4` 跑 `separate→asr`。
3. **实例测试**：`clone_voice`（用一段人声）→ `synthesize` 中文 → 断言输出 wav 存在且非空。
4. **M09 worker 集成**：`batch_synthesize` 对多行对白 → 断点续传验证（中断后跳过已完成）。

---

## 11. 实现顺序建议（无人值守按序）

1. `schemas.py` + `base.py`（契约）
2. `VoiceAdapter`（M04+M09，优先级最高）
3. `SeparateAdapter`（M02）
4. `ASRAdapter`（M05）
5. `registry.py`（Capability Matrix）
6. 各 adapter 单元测试 → 实例测试
7. worker 改为经 Layer 0 调 adapter（不直接耦合 qwentts）
