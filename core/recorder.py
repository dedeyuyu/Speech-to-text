"""
录音模块 - 负责实时音频采集

使用 sounddevice 进行麦克风录音，通过回调函数实时传递音频数据。
所有音频数据仅在内存中处理，不写入磁盘。
"""

import threading
import queue
import numpy as np
import sounddevice as sd


# 音频参数
SAMPLE_RATE = 16000   # Whisper 要求 16kHz
CHANNELS = 1          # 单声道
DTYPE = np.float32    # 浮点格式
BLOCK_SIZE = 1024     # 每次回调的样本数（约 64ms）


class AudioRecorder:
    """
    实时音频录制器。
    
    通过 sounddevice 流式采集麦克风音频，
    将音频块放入线程安全的队列，供转录线程消费。
    """

    def __init__(self, on_audio_chunk=None, on_error=None):
        """
        初始化录音器。

        Args:
            on_audio_chunk: 收到音频数据时的回调函数，参数为 np.ndarray
            on_error: 发生错误时的回调函数，参数为 Exception
        """
        self._on_audio_chunk = on_audio_chunk
        self._on_error = on_error
        self._stream = None
        self._is_recording = False
        self._lock = threading.Lock()

    @property
    def is_recording(self):
        return self._is_recording

    def start(self):
        """开始录音。"""
        with self._lock:
            if self._is_recording:
                return
            try:
                self._stream = sd.InputStream(
                    samplerate=SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype=DTYPE,
                    blocksize=BLOCK_SIZE,
                    callback=self._audio_callback,
                )
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
                self._stream.stop()
                self._stream.close()
                self._stream = None

    def _audio_callback(self, indata: np.ndarray, frames: int,
                        time_info, status):
        """
        sounddevice 音频回调（在独立线程中执行）。
        
        Args:
            indata: 形状为 (frames, channels) 的音频数据
            frames: 采样帧数
            time_info: 时间信息（未使用）
            status: 流状态标志
        """
        if status:
            print(f"[录音] 状态: {status}")
        if self._on_audio_chunk and self._is_recording:
            # 转为 1D 数组传出
            chunk = indata[:, 0].copy()
            self._on_audio_chunk(chunk)

    @staticmethod
    def list_devices():
        """列出所有可用的音频输入设备。"""
        devices = []
        for idx, dev in enumerate(sd.query_devices()):
            if dev["max_input_channels"] > 0:
                devices.append({
                    "index": idx,
                    "name": dev["name"],
                    "channels": dev["max_input_channels"],
                    "default_samplerate": dev["default_samplerate"],
                })
        return devices

    @staticmethod
    def get_default_input_device():
        """获取默认输入设备名称。"""
        try:
            dev = sd.query_devices(kind="input")
            return dev["name"]
        except Exception:
            return "未知"
