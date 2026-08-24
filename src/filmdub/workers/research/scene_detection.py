"""
M02 场景/镜头/黑屏检测（ticket-034）

基于 PyAV 逐帧分析视频，输出 Scene Timeline：

- **场景切割**：帧间视觉差异超过 `scene_threshold` 判定为场景切换
- **镜头变化**：帧间差异超过 `shot_threshold`（比场景更灵敏）判定为镜头切换
- **黑屏检测**：帧平均亮度低于 `black_luma_threshold` 判定为黑帧，连续黑帧合并为黑屏段

检测结果与视频时间轴对齐（start/end 均为秒）。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import av
import numpy as np

logger = logging.getLogger(__name__)

# 默认 8-bit 亮度
MAX_LUMA = 255.0


def frame_diff_score(prev: np.ndarray, curr: np.ndarray) -> float:
    """
    计算两帧之间的归一化差异分数（0.0 ~ 1.0）

    基于缩小后的 RGB 帧逐像素绝对差均值。

    Args:
        prev: 前一帧 RGB ndarray
        curr: 当前帧 RGB ndarray

    Returns:
        差异分数，0.0 表示完全相同，越大差异越明显
    """
    if prev is None or curr is None:
        return 0.0
    prev = prev.astype(np.float32)
    curr = curr.astype(np.float32)
    return float(np.mean(np.abs(prev - curr)) / MAX_LUMA)


def frame_luma_mean(frame: np.ndarray) -> float:
    """
    计算帧的平均亮度（0.0 ~ 255.0）

    Args:
        frame: RGB ndarray

    Returns:
        平均亮度
    """
    rgb = frame.astype(np.float32)
    # 亮度近似：0.299R + 0.587G + 0.114B（BT.601）
    luma = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    return float(np.mean(luma))


class SceneDetector:
    """
    场景/镜头/黑屏检测器

    Args:
        scene_threshold: 场景切换差异阈值（0-1），值越大越难触发
        shot_threshold: 镜头切换差异阈值（0-1），须小于 scene_threshold
        black_luma_threshold: 黑屏判定亮度阈值（0-255）
        min_black_duration: 最短黑屏持续时长（秒），小于此值的黑帧忽略
        sample_every_n: 抽样帧间隔（1=全量），用于加速长视频
    """

    def __init__(
        self,
        scene_threshold: float = 0.30,
        shot_threshold: float = 0.15,
        black_luma_threshold: float = 16.0,
        min_black_duration: float = 0.3,
        sample_every_n: int = 1,
    ):
        if shot_threshold >= scene_threshold:
            raise ValueError("shot_threshold 必须小于 scene_threshold")
        self.scene_threshold = scene_threshold
        self.shot_threshold = shot_threshold
        self.black_luma_threshold = black_luma_threshold
        self.min_black_duration = min_black_duration
        self.sample_every_n = max(1, int(sample_every_n))

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------
    def detect(self, video_path: str | Path) -> Dict[str, Any]:
        """
        检测视频的场景/镜头/黑屏时间线

        Args:
            video_path: 视频文件路径

        Returns:
            Scene Timeline 字典：
            {
                "video_file": str,
                "duration": float,
                "width": int,
                "height": int,
                "fps": float,
                "total_frames": int,
                "scenes": [{"index", "start", "end"}, ...],
                "shots": [{"index", "start", "end", "scene_index"}, ...],
                "black_frames": [{"start", "end", "duration"}, ...],
                "detection": {...},
            }
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        # 逐帧采样：diff 序列、亮度序列、真实时间戳
        diffs: List[float] = []
        luma: List[float] = []
        times: List[float] = []

        fps = None
        width = height = 0

        with av.open(str(video_path)) as container:
            if not container.streams.video:
                raise ValueError(f"视频无视频流: {video_path}")
            stream = container.streams.video[0]
            fps = float(stream.average_rate) if stream.average_rate else 30.0
            width = stream.width or 0
            height = stream.height or 0
            duration = float(stream.duration * stream.time_base) if stream.duration else 0.0

            prev = None
            index = -1
            for frame in container.decode(stream):
                index += 1
                if index % self.sample_every_n != 0:
                    continue
                rgb = frame.to_ndarray(format="rgb24")
                # 缩小后计算，兼顾速度与鲁棒性
                small = self._resize(rgb)
                t = float(frame.pts * frame.time_base) if frame.pts is not None else index / fps
                d = frame_diff_score(prev, small) if prev is not None else 0.0
                diffs.append(d)
                luma.append(frame_luma_mean(small))
                times.append(t)
                prev = small

        total_frames = len(diffs)
        if total_frames == 0:
            # 无有效帧：返回空时间线而非崩溃
            logger.warning(f"未解码到任何视频帧: {video_path}")
            return {
                "video_file": str(video_path),
                "duration": round(duration, 3),
                "width": width,
                "height": height,
                "fps": round(fps, 4),
                "total_frames": 0,
                "scenes": [],
                "shots": [],
                "black_frames": [],
                "detection": self._detection_meta(),
            }

        # 检测场景/镜头切点（帧索引 → 时间）
        scene_cuts = self._find_cuts(diffs, self.scene_threshold)
        shot_cuts = self._find_cuts(diffs, self.shot_threshold)

        # 黑屏段
        black_segments = self._find_black_segments(
            luma,
            times,
            total_frames,
            luma_threshold=self.black_luma_threshold,
            min_duration=self.min_black_duration,
            fps=fps,
        )

        # 组装时间线
        scenes = self._build_segments(scene_cuts, times, total_frames, duration)
        shots = self._build_segments(shot_cuts, times, total_frames, duration)
        shots = self._map_shots_to_scenes(shots, scenes)

        return {
            "video_file": str(video_path),
            "duration": round(duration, 3),
            "width": width,
            "height": height,
            "fps": round(fps, 4),
            "total_frames": total_frames,
            "scenes": scenes,
            "shots": shots,
            "black_frames": black_segments,
            "detection": self._detection_meta(),
        }

    def _detection_meta(self) -> Dict[str, Any]:
        """返回检测参数元数据"""
        return {
            "scene_threshold": self.scene_threshold,
            "shot_threshold": self.shot_threshold,
            "black_luma_threshold": self.black_luma_threshold,
            "min_black_duration": self.min_black_duration,
            "sample_every_n": self.sample_every_n,
        }

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------
    @staticmethod
    def _resize(frame: np.ndarray, max_w: int = 96, max_h: int = 54) -> np.ndarray:
        """等比缩小帧，降低计算量"""
        h, w = frame.shape[:2]
        scale = min(max_w / w, max_h / h, 1.0)
        if scale >= 1.0:
            return frame
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        # 简单的最近邻/平均降采样（numpy 切片 + reshape 平均）
        if new_w * 2 <= w and new_h * 2 <= h:
            pooled = frame[: new_h * 2, : new_w * 2].reshape(
                new_h, 2, new_w, 2, frame.shape[2]
            ).mean(axis=(1, 3))
            return pooled.astype(frame.dtype)
        return frame[:: max(1, h // new_h), :: max(1, w // new_w)]

    @staticmethod
    def _find_cuts(diffs: List[float], threshold: float) -> List[int]:
        """
        查找差异超过阈值的切点（帧索引）

        连续超过阈值的帧只取第一帧作为切点，避免一次切换重复计数。

        Args:
            diffs: 帧间差异序列
            threshold: 切点阈值

        Returns:
            切点帧索引列表（不含首帧 0）
        """
        cuts: List[int] = []
        i = 1
        n = len(diffs)
        while i < n:
            if diffs[i] >= threshold:
                cuts.append(i)
                # 跳过紧接着的连续高差异帧
                while i + 1 < n and diffs[i + 1] >= threshold * 0.5:
                    i += 1
            i += 1
        return cuts

    @staticmethod
    def _find_black_segments(
        luma: List[float],
        times: List[float],
        total_frames: int,
        luma_threshold: float = 16.0,
        min_duration: float = 0.3,
        fps: float = 30.0,
    ) -> List[Dict[str, Any]]:
        """
        查找连续黑帧并合并为黑屏段

        Args:
            luma: 每帧平均亮度
            times: 每帧时间戳（秒）
            total_frames: 总帧数
            luma_threshold: 黑屏亮度阈值
            min_duration: 最短黑屏时长（秒）
            fps: 帧率（用于推算时长）

        Returns:
            黑屏段列表
        """
        segments: List[Dict[str, Any]] = []
        black = [i for i, v in enumerate(luma) if v <= luma_threshold]

        if not black:
            return segments

        start = black[0]
        prev_i = black[0]
        for i in black[1:]:
            if i != prev_i + 1:
                # 段结束
                segments.append((start, prev_i))
                start = i
            prev_i = i
        segments.append((start, prev_i))

        result = []
        for s, e in segments:
            start_t = times[s]
            if e + 1 < total_frames:
                end_t = times[e + 1]
            else:
                end_t = start_t + (e - s + 1) / fps
            duration = end_t - start_t
            if duration >= min_duration:
                result.append({
                    "start": round(start_t, 3),
                    "end": round(end_t, 3),
                    "duration": round(duration, 3),
                })
        return result

    @staticmethod
    def _build_segments(
        cuts: List[int],
        times: List[float],
        total_frames: int,
        duration: float,
    ) -> List[Dict[str, Any]]:
        """
        根据切点构建连续时间区间

        Args:
            cuts: 切点帧索引（不含首帧）
            times: 每帧时间戳
            total_frames: 总帧数
            duration: 视频总时长（秒）

        Returns:
            区间列表 [{"index", "start", "end"}, ...]
        """
        boundaries = [0] + cuts + [total_frames - 1]
        segments = []
        for i in range(len(boundaries) - 1):
            s_frame = boundaries[i]
            e_frame = boundaries[i + 1]
            start_t = times[s_frame]
            if e_frame == total_frames - 1:
                # 最后一段：取视频总时长（更准确）
                end_t = duration if duration > start_t else times[e_frame]
            else:
                # 切点帧属于下一个段，所以当前段结束于切点帧的时间
                end_t = times[e_frame]
            segments.append({
                "index": i,
                "start": round(start_t, 3),
                "end": round(end_t, 3),
            })
        return segments

    @staticmethod
    def _map_shots_to_scenes(
        shots: List[Dict[str, Any]],
        scenes: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """将镜头映射到所属场景（scene_index）"""
        result = []
        for shot in shots:
            scene_index = None
            for scene in scenes:
                if shot["start"] >= scene["start"] - 1e-6 and shot["start"] < scene["end"]:
                    scene_index = scene["index"]
                    break
            result.append({**shot, "scene_index": scene_index})
        return result
