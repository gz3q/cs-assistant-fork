import json
import logging
import os
from typing import Any

# ANSI escape codes for colors
LOG_COLORS = {
    "DEBUG": "\033[94m",
    "INFO": "\033[92m",
    "WARNING": "\033[93m",
    "ERROR": "\033[91m",
    "RESET": "\033[0m",
}


class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        level_color = LOG_COLORS.get(record.levelname, "")
        reset = LOG_COLORS["RESET"]
        record.msg = f"{level_color}{record.msg}{reset}"
        return super().format(record)


class SemanticLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.propagate = False

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = ColorFormatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

    def info(self, event: str, **data: Any):
        self.logger.info(self._format(event, data))

    def warning(self, event: str, **data: Any):
        self.logger.warning(self._format(event, data))

    def error(self, event: str, **data: Any):
        self.logger.error(self._format(event, data))

    def debug(self, event: str, **data: Any):
        self.logger.debug(self._format(event, data))

    def _format(self, event: str, data: dict[str, Any]) -> str:
        structured = {"event": event, **data}
        return json.dumps(structured, default=str)


def get_logger(name: str) -> SemanticLogger:
    return SemanticLogger(name)
