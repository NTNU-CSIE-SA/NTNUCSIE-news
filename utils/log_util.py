from __future__ import annotations

import logging
import sys
from logging.handlers import TimedRotatingFileHandler

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[1;90m",     # 灰
        logging.INFO: "\033[1;36m",      # 青
        logging.WARNING: "\033[1;33m",   # 黃
        logging.ERROR: "\033[1;31m",     # 紅
        logging.CRITICAL: "\033[1;41m",  # 紅底
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        # 先存原本的 levelname（避免污染其他 handler）
        original_levelname = record.levelname

        # 固定寬度 + 上色
        color = self.COLORS.get(record.levelno, "")
        record.levelname = f"{color}{original_levelname:<8}{self.RESET}"

        try:
            return super().format(record)
        finally:
            # 還原，避免影響 file handler 或其他 formatter
            record.levelname = original_levelname

def setup_logging(console_level: int = logging.INFO) -> None:
    # 1) root logger = 你全專案共用的 logger
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # 避免重複加 handler（熱重載或多次執行時會重複印）
    if root.handlers:
        return

    # 2) console handler（直觀）
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(console_level)
    console.setFormatter(ColorFormatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    ))

    # 3) file handler（完整，按天切檔）
    file_handler = TimedRotatingFileHandler(
        filename="logs/app.log",
        when="midnight",
        backupCount=14,
        encoding="utf-8",
        utc=False,
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    root.addHandler(console)
    root.addHandler(file_handler)

    # 4) discord.py 自己的 logger：讓它走 root handler，但你可以降噪
    logging.getLogger("discord").setLevel(logging.INFO)
    logging.getLogger("discord.http").setLevel(logging.WARNING)