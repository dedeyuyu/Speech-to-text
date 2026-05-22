"""
本地存储模块 - 管理转录记录的持久化

所有数据均存储在用户本地目录，不进行任何网络传输。
存储格式：
  - data/transcripts/YYYY-MM-DD.json  每日记录文件
  - data/transcripts/YYYY-MM-DD.txt   纯文本导出文件
"""

import json
import os
from datetime import datetime
from pathlib import Path


# 默认数据目录（相对于项目根目录）
DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data" / "transcripts"


class TranscriptStorage:
    """
    转录记录本地存储管理器。
    
    每天自动创建一个 JSON 文件保存当天的所有转录记录，
    包含时间戳、文本内容等元信息。
    """

    def __init__(self, data_dir: Path = None):
        """
        初始化存储管理器。

        Args:
            data_dir: 数据目录路径，默认为项目 data/transcripts/
        """
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────────────────
    # 写入
    # ─────────────────────────────────────────

    def save_entry(self, text: str, language: str = None) -> dict:
        """
        保存一条转录记录。

        Args:
            text: 转录文本
            language: 检测到的语言代码（可选）

        Returns:
            保存的记录字典
        """
        now = datetime.now()
        entry = {
            "id": now.strftime("%Y%m%d_%H%M%S_%f"),
            "timestamp": now.isoformat(),
            "text": text,
            "language": language,
        }

        # 追加到当日 JSON 文件
        json_path = self._get_daily_json_path(now)
        records = self._load_json(json_path)
        records.append(entry)
        self._save_json(json_path, records)

        return entry

    def export_txt(self, date: datetime = None) -> Path:
        """
        将指定日期的记录导出为纯文本文件。

        Args:
            date: 要导出的日期，默认为今天

        Returns:
            导出文件的路径
        """
        date = date or datetime.now()
        records = self.get_records_for_date(date)

        txt_path = self.data_dir / f"{date.strftime('%Y-%m-%d')}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"转录记录 - {date.strftime('%Y年%m月%d日')}\n")
            f.write("=" * 50 + "\n\n")
            for rec in records:
                ts = datetime.fromisoformat(rec["timestamp"])
                f.write(f"[{ts.strftime('%H:%M:%S')}] {rec['text']}\n\n")

        return txt_path

    # ─────────────────────────────────────────
    # 读取
    # ─────────────────────────────────────────

    def get_records_for_date(self, date: datetime = None) -> list:
        """
        获取指定日期的所有转录记录。

        Args:
            date: 日期，默认为今天

        Returns:
            记录列表，按时间排序
        """
        date = date or datetime.now()
        json_path = self._get_daily_json_path(date)
        return self._load_json(json_path)

    def get_all_dates(self) -> list:
        """
        获取所有有记录的日期列表。

        Returns:
            日期字符串列表（YYYY-MM-DD格式），倒序
        """
        dates = []
        for f in self.data_dir.glob("*.json"):
            try:
                datetime.strptime(f.stem, "%Y-%m-%d")
                dates.append(f.stem)
            except ValueError:
                pass
        return sorted(dates, reverse=True)

    def get_today_records(self) -> list:
        """获取今天的所有转录记录。"""
        return self.get_records_for_date(datetime.now())

    def get_total_count(self) -> int:
        """获取今日转录总条数。"""
        return len(self.get_today_records())

    # ─────────────────────────────────────────
    # 内部辅助
    # ─────────────────────────────────────────

    def _get_daily_json_path(self, date: datetime) -> Path:
        return self.data_dir / f"{date.strftime('%Y-%m-%d')}.json"

    def _load_json(self, path: Path) -> list:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save_json(self, path: Path, records: list):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
