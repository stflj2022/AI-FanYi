"""分析一段语音的频谱特征，判断是『人声』还是『噪声/静音』。

判据：
- 人声：频谱重心在低频(约 200-2000Hz)，且有较低的高频能量、语音段存在。
- 白噪声：频谱平坦，各频率能量接近。
- 静音：整体能量极低。
"""
import sys
import numpy as np
import soundfile as sf

path = sys.argv[1]
a, sr = sf.read(path)
if a.ndim > 1:
    a = a.mean(axis=1)
n = len(a)
rms = float(np.sqrt((a ** 2).mean())) if n else 0.0
peak = float(np.abs(a).max()) if n else 0.0

# 分帧做 FFT，取非静音帧计算频谱重心（人声应集中在低频）
frame = 1024
fft_sum = np.zeros(frame // 2)
count = 0
for start in range(0, n - frame, frame // 2):
    seg = a[start:start + frame]
    if np.sqrt((seg ** 2).mean()) > 0.001:
        mag = np.abs(np.fft.rfft(seg * np.hanning(frame)))
        fft_sum += mag[: frame // 2]
        count += 1
if count == 0:
    print(f"{path}: 静音(有效帧数=0)")
    sys.exit(0)

freqs = np.fft.rfftfreq(frame, 1 / sr)
fft_sum /= count
# 频谱重心
centroid = float((fft_sum * freqs[: len(fft_sum)]).sum() / fft_sum.sum()) if fft_sum.sum() > 0 else 0
# 低频(0-2kHz) 能量占比
lf = fft_sum[freqs[: len(fft_sum)] < 2000].sum()
hf = fft_sum[freqs[: len(fft_sum)] >= 2000].sum()
low_ratio = float(lf / (lf + hf)) if (lf + hf) > 0 else 0

verdict = "人声/语音" if 100 < centroid < 2500 and low_ratio > 0.5 else \
          ("白噪声" if low_ratio < 0.3 else "不确定")
print(f"{path}: rms={rms:.4f} peak={peak:.4f} 重心={centroid:.0f}Hz 低频占比={low_ratio:.2f} -> {verdict}")
