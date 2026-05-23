"""
音频设备枚举模块

支持：
  - 普通麦克风（USB、3.5mm、蓝牙等）
  - 虚拟设备（VoiceMeeter、Virtual Cable 等）
  - 系统声音环回（录制电脑正在播放的声音，需 WASAPI）

数据结构 AudioDevice:
    index       : int   sounddevice 设备索引（输出设备环回时为其输出索引）
    name        : str   显示名称
    hostapi     : str   主机 API（WASAPI / MME / DirectSound 等）
    channels    : int   可用输入声道数（环回时取输出声道数）
    is_loopback : bool  True = 系统声音环回模式（WASAPI Loopback）
    is_default  : bool  True = 系统默认设备
"""

from dataclasses import dataclass, field
from typing import List, Optional
import sys
import sounddevice as sd

_IS_WINDOWS = sys.platform == "win32"


@dataclass
class AudioDevice:
    index: int
    name: str
    hostapi: str
    channels: int
    is_loopback: bool = False
    is_default: bool = False

    def display_name(self) -> str:
        """返回 UI 显示用的名称。"""
        tag = "🔊 系统声音" if self.is_loopback else "🎤"
        default = " ← 默认" if self.is_default else ""
        return f"{tag}  {self.name}{default}"

    def to_dict(self) -> dict:
        return {
            "index":       self.index,
            "name":        self.name,
            "hostapi":     self.hostapi,
            "channels":    self.channels,
            "is_loopback": self.is_loopback,
            "is_default":  self.is_default,
        }

    @staticmethod
    def from_dict(d: dict) -> "AudioDevice":
        return AudioDevice(**d)


def enumerate_devices() -> List[AudioDevice]:
    """
    枚举所有可用音频设备。

    返回列表包含：
      1. 所有输入设备（麦克风、虚拟输入如 VoiceMeeter Input）
      2. 所有输出设备的 WASAPI Loopback（用于录制系统声音）
         仅在 sounddevice 报告该平台支持 WASAPI 时添加。

    Returns:
        List[AudioDevice] — 按「输入设备在前，环回在后」排列。
    """
    result: List[AudioDevice] = []
    all_devices = sd.query_devices()
    hostapis = sd.query_hostapis()

    try:
        default_input_idx = sd.default.device[0]
    except Exception:
        default_input_idx = -1

    # ── 1. 普通输入设备 ──────────────────────────────────────
    for idx, dev in enumerate(all_devices):
        if dev["max_input_channels"] < 1:
            continue
        api_name = hostapis[dev["hostapi"]]["name"]
        result.append(AudioDevice(
            index=idx,
            name=dev["name"],
            hostapi=api_name,
            channels=min(dev["max_input_channels"], 2),
            is_loopback=False,
            is_default=(idx == default_input_idx),
        ))

    # ── 2. WASAPI 环回（系统声音）— 仅 Windows ─────────────────
    # macOS 用户可安装 BlackHole 等虚拟设备，它们会出现在输入设备列表
    if _IS_WINDOWS:
        wasapi_api_index = None
        for api_idx, api in enumerate(hostapis):
            if "wasapi" in api["name"].lower():
                wasapi_api_index = api_idx
                break

        if wasapi_api_index is not None:
            try:
                default_output_idx = sd.default.device[1]
            except Exception:
                default_output_idx = -1

            for idx, dev in enumerate(all_devices):
                if dev["max_output_channels"] < 1:
                    continue
                if dev["hostapi"] != wasapi_api_index:
                    continue
                result.append(AudioDevice(
                    index=idx,
                    name=dev["name"],
                    hostapi="WASAPI Loopback",
                    channels=min(dev["max_output_channels"], 2),
                    is_loopback=True,
                    is_default=(idx == default_output_idx),
                ))

    return result


def get_default_device() -> Optional[AudioDevice]:
    """返回系统默认输入设备，失败时返回 None。"""
    try:
        dev = sd.query_devices(kind="input")
        hostapis = sd.query_hostapis()
        return AudioDevice(
            index=sd.default.device[0],
            name=dev["name"],
            hostapi=hostapis[dev["hostapi"]]["name"],
            channels=min(dev["max_input_channels"], 2),
            is_loopback=False,
            is_default=True,
        )
    except Exception:
        return None
