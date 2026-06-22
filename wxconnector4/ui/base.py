"""UI 窗口基类。"""
from abc import ABC, abstractmethod

from ..param import PROJECT_NAME, WxParam
from ..utils import uiabase
from ..utils.lock import uilock


class BaseUIWnd(ABC):
    _ui_cls_name: str = None   # 目标窗口 ClassName
    _ui_name: str = None       # 目标窗口 Name
    control = None             # uiautomation 控件

    @abstractmethod
    def _lang(self, text: str):
        ...

    def __repr__(self):
        return f"<{PROJECT_NAME} - {self.__class__.__name__} at {hex(id(self))}>"

    def __eq__(self, other):
        try:
            return self.control == other.control
        except Exception:
            return False

    def __bool__(self):
        return self.exists()

    @property
    def HWND(self) -> int:
        if not hasattr(self, '_hwnd') or not self._hwnd:
            self._hwnd = uiabase.get_hwnd(self.control)
        return self._hwnd

    @property
    def pid(self):
        try:
            return self.control.ProcessId
        except Exception:
            return None

    def exists(self, wait=0) -> bool:
        try:
            return self.control.Exists(wait)
        except Exception:
            return False

    def _show(self):
        try:
            uiabase.show_window(self.HWND)
            self.control.SwitchToThisWindow()
        except Exception:
            pass

    @uilock
    def close(self):
        try:
            self.control.SendKeys('{Esc}')
        except Exception:
            pass

    def set_window_size(self, width, height, location=None):
        uiabase.set_window_size(self.HWND, width, height, location)

    def auto_resize(self):
        """放大窗口以加载更多控件（应对 4.x 虚拟列表）。"""
        try:
            self.set_window_size(*WxParam.CHAT_WINDOW_SIZE)
        except Exception:
            pass


class BaseUISubWnd(BaseUIWnd):
    root = None
    parent = None

    def _lang(self, text: str):
        if getattr(self, 'parent', None):
            return self.parent._lang(text)
        if getattr(self, 'root', None):
            return self.root._lang(text)
        return text
