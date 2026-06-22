"""日志：控制台彩色 + 可选文件日志。"""
from .param import WxParam, PROJECT_NAME, VERSION

import logging
from pathlib import Path
from datetime import datetime

try:
    import colorama
    colorama.init()
    _COLORS = {
        'DEBUG': colorama.Fore.CYAN,
        'INFO': colorama.Fore.GREEN,
        'WARNING': colorama.Fore.YELLOW,
        'ERROR': colorama.Fore.RED,
        'CRITICAL': colorama.Fore.MAGENTA,
    }
    _RESET = colorama.Style.RESET_ALL
except Exception:  # colorama 缺失时降级为无色
    _COLORS = {}
    _RESET = ''


_FMT = '%(asctime)s [%(name)s] [%(levelname)s] [%(filename)s:%(lineno)d]  %(message)s'
_DATEFMT = "%Y-%m-%d %H:%M:%S"


class _ColoredFormatter(logging.Formatter):
    def format(self, record):
        message = super().format(record)
        color = _COLORS.get(record.levelname, '')
        return f"{color}{message}{_RESET}" if color else message


class WxautoLogger:
    name: str = f'{PROJECT_NAME}({VERSION})'

    def __init__(self):
        self.file_handler = None
        self.logger = self._setup()
        self.set_debug(False)

    def _setup(self) -> logging.Logger:
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        for noisy in ('comtypes', 'urllib3', 'requests', 'PIL', 'asyncio'):
            logging.getLogger(noisy).setLevel(logging.WARNING)
        root.handlers.clear()

        self.console_handler = logging.StreamHandler()
        self.console_handler.setFormatter(_ColoredFormatter(fmt=_FMT, datefmt=_DATEFMT))
        self.console_handler.setLevel(logging.DEBUG)
        root.addHandler(self.console_handler)
        return logging.getLogger(self.name)

    def setup_file_logger(self):
        if not WxParam.ENABLE_FILE_LOGGER or self.file_handler is not None:
            return
        log_dir = Path("wxconnector_logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        self.file_handler = logging.FileHandler(log_file, encoding='utf-8')
        self.file_handler.setFormatter(logging.Formatter(_FMT, datefmt=_DATEFMT))
        self.file_handler.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(self.file_handler)

    def set_debug(self, debug=False):
        self.console_handler.setLevel(logging.DEBUG if debug else logging.INFO)

    def _ensure_file(self):
        if WxParam.ENABLE_FILE_LOGGER and self.file_handler is None:
            self.setup_file_logger()

    def debug(self, msg, stacklevel=2, *a, **k):
        self._ensure_file(); self.logger.debug(msg, *a, stacklevel=stacklevel, **k)

    def info(self, msg, stacklevel=2, *a, **k):
        self._ensure_file(); self.logger.info(msg, *a, stacklevel=stacklevel, **k)

    def warning(self, msg, stacklevel=2, *a, **k):
        self._ensure_file(); self.logger.warning(msg, *a, stacklevel=stacklevel, **k)

    def error(self, msg, stacklevel=2, *a, **k):
        self._ensure_file(); self.logger.error(msg, *a, stacklevel=stacklevel, **k)

    def critical(self, msg, stacklevel=2, *a, **k):
        self._ensure_file(); self.logger.critical(msg, *a, stacklevel=stacklevel, **k)


wxlog = WxautoLogger()
