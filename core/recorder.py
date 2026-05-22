"""
录音模块 - 负责实时音频采集

支持：
  - 普通麦克风（默认或用户指定设备）
  - 虚拟声卡（VoiceMeeter Input 等）
  - WASAPI 环回（录制电脑正在播放的声音）

所有音频数据仅在内存中处理，不写入磁盘。
"""

import threading
import numpy as np
import sounddevice as sd

from core.audio_devices import AudioDevice


# 音频参数
SAMPLE_RATE = 16000   # Whisper 要求 16kHz
DTYPE = np.float32    # 浮点格式
BLOCK_SIZE = 1024     # 每次回调的样本数（约 64ms）


class AudioRecorder:
    """
    实时音频录制器。

    支持普通麦克风和 WASAPI 环回（系统声音）。
    通过回调函数实时传递音频数据给转录线程。
    """

    def __init__(self, on_audio_chunk=None, on_error=None,
                 device: AudioDevice = None):
        """
        初始化录音器。

        Args:
            on_audio_chunk : 收到音频数据时的回调，参数为 np.ndarray (float32, 1D)
            on_error       : 发生错误时的回调，参数为 Exception
            device         : AudioDevice 实例；None = 系统默认麦克风
        """
        self._on_audio_chunk = on_audio_chunk
        self._on_error = on_error
        self._device = device       # AudioDevice | None
        self._stream = None
        self._is_recording = False
        self._lock = threading.Lock()

    # ─────────────────────────────────────────
    # 公共接口
    # ─────────────────────────────────────────

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def set_device(self, device: AudioDevice | None):
        """切换录音设备（需在停止状态下调用）。"""
        if self._is_recording:
            return
        self._device = device

    def start(self):
        """开始录音。"""
        with self._lock:
            if self._is_recording:
                return
            try:
                self._stream = self._open_stream()
                self._stream.start()
                self._is_recording = True
            except Exception as e:
                if self._on_error:
                    self._on_error(e)

    def stop(self):
        """停止录音。"""
        with self._lock:
            if not self._is_recording:
                return
            self._is_recording = False
            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

    # ─────────────────────────────────────────
    # 流创建
    # ─────────────────────────────────────────

    def _open_stream(self) -> sd.InputStream:
        """
        根据设备配置创建 sounddevice InputStream。

        普通设备：直接传入 device index。
        WASAPI 环回：传入输出设备 index + WasapiSettings(loopback=True)。
        """
        dev = self._device

        if dev is None:
            # 系统默认麦克风
            return sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype=DTYPE,
                blocksize=BLOCK_SIZE,
                callback=self._audio_callback,
            )

        if dev.is_loopback:
            # WASAPI 环回：录制输出设备正在播放的声音
            try:
                wasapi_settings = sd.WasapiSettings(loopback=True)
            except AttributeError:
                # sounddevice 版本不支持 WasapiSettings → 降级到默认设备
                raise RuntimeError(
                    "当前 sounddevice 版本不支持 WASAPI 环回录制，"
                    "请升级：pip install sounddevice --upgrade"
                )

            # 环回流的声道数取输出设备的声道数（最多 2 声道）
            channels = max(1, min(dev.channels, 2))
            return sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=channels,
                dtype=DTYPE,
                blocksize=BLOCK_SIZE,
                device=dev.index,
                extra_settings=wasapi_settings,
                callback=self._audio_callback,
            )

        else:
            # 普通输入设备（麦克风 / 虚拟声卡）
            channels = max(1, min(dev.channels, 2))
            return sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=channels,
                dtype=DTYPE,
                blocksize=BLOCK_SIZE,
                device=dev.index,
                callback=self._audio_callback,
            )

    # ─────────────────────────────────────────
    # 音频回调
    # ─────────────────────────────────────────

    def _audio_callback(self, indata: np.ndarray, frames: int,
                        time_info, status):
        """
        sounddevice 音频回调（在独立线程中执行）。

        Args:
            indata: 形状为 (frames, channels) 的音频数据
        """
        if status:
            print(f"[录音] 状态: {status}")
        if self._on_audio_chunk and self._is_recording:
            # 混合多声道为单声道（取均值），传出 1D float32 数组
            if indata.shape[1] == 1:
                chunk = indata[:, 0].copy()
            else:
                chunk = indata.mean(axis=1).astype(np.float32)
            self._on_audio_chunk(chunk)

    # ─────────────────────────────────────────
    # 静态工具方法
    # ─────────────────────────────────────────

    @staticmethod
    def list_devices():
        """列出所有可用的音频输入设备（兼容旧接口）。"""
        from core.audio_devices import enumerate_devices
        return [
            {
                "index":   d.index,
                "name":    d.name,
                "channels": d.channels,
                "default_samplerate": 16000,
            }
            for d in enumerate_devices()
            if not d.is_loopback
        ]

    @staticmethod
    def get_default_input_device():
        """获取默认输入设备名称（兼容旧接口）。"""
        try:
            dev = sd.query_devices(kind="input")
            return dev["name"]
        except Exception:
            return "未知"
