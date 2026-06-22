"""微信顶层窗口：主窗口 / 独立聊天子窗口 / 登录窗口。"""
import os

from .base import BaseUIWnd, BaseUISubWnd
from ..param import WxParam
from ..languages import CTRL, lang
from ..utils import uiabase
from ..logger import wxlog


class WeChatMainWnd(BaseUIWnd):
    """微信主窗口 mmui::MainWindow。"""
    _ui_cls_name = CTRL['main_window_cls']
    _ui_name = lang('微信')

    def __init__(self, nickname: str = None, timeout: float = 5.0):
        self.control = uiabase.find_window(
            classname=self._ui_cls_name, name=nickname, timeout=timeout
        )
        if self.control is None and nickname:
            # 指定昵称找不到时退回任意主窗口
            self.control = uiabase.find_window(classname=self._ui_cls_name, timeout=timeout)
        if self.control is None:
            raise RuntimeError('未找到微信主窗口，请确认微信已打开并登录')
        self.language = WxParam.LANGUAGE

    def _lang(self, text: str):
        return lang(text, self.language)

    # ---------- 状态 ----------
    def is_online(self) -> bool:
        """主窗口存在且能找到导航栏/会话列表即视为已登录在线。"""
        if not self.exists():
            return False
        tabbar = uiabase.find(self.control, automation_id=CTRL['main_tabbar_aid'], maxdepth=8)
        session = uiabase.find(self.control, automation_id=CTRL['session_list_aid'], maxdepth=20)
        return tabbar is not None or session is not None

    # ---------- 账号信息 ----------
    @property
    def path(self) -> str:
        """微信可执行文件路径（通过进程 PID 反查）。"""
        try:
            import psutil
            return psutil.Process(self.pid).exe()
        except Exception:
            return ''

    @property
    def dir(self) -> str:
        p = self.path
        return os.path.dirname(p) if p else ''

    def get_my_info(self) -> dict:
        """获取我的信息（Phase 0 为最小实现：昵称占位，后续阶段补全）。"""
        info = {'nickname': getattr(self, 'nickname', None), 'pid': self.pid}
        return info

    def close(self):
        """主窗口不走 Esc（4.x 会最小化到托盘并销毁窗口）。如需结束请用 ShutDown()。"""
        wxlog.warning('已忽略对主窗口的 close()，避免误最小化到托盘；结束进程请用 wx.ShutDown()')


class WeChatSubWnd(BaseUISubWnd):
    """独立聊天子窗口 mmui::ChatSingleWindow（监听用）。"""
    _ui_cls_name = CTRL['sub_window_cls']

    def __init__(self, control=None, root=None, nickname: str = None):
        self.root = root
        self.nickname = nickname
        self.control = control
        if self.control is None:
            self.control = uiabase.find_window(classname=self._ui_cls_name, name=nickname, timeout=2.0)

    def _lang(self, text: str):
        if self.root is not None:
            return self.root._lang(text)
        return lang(text, WxParam.LANGUAGE)


class WeChatLoginWnd(BaseUIWnd):
    """登录窗口 mmui::LoginWindow（占位，Phase 3 完善扫码登录）。"""
    _ui_cls_name = CTRL['login_window_cls']

    def __init__(self):
        self.control = uiabase.find_window(classname=self._ui_cls_name, timeout=1.0)

    def _lang(self, text: str):
        return lang(text, WxParam.LANGUAGE)

    def exists(self, wait=0) -> bool:
        return self.control is not None and super().exists(wait)

    def open(self):
        wxlog.warning('WeChatLoginWnd.open 尚未实现（Phase 3）')

    def login(self):
        wxlog.warning('WeChatLoginWnd.login 尚未实现（Phase 3）')

    def reopen(self):
        wxlog.warning('WeChatLoginWnd.reopen 尚未实现（Phase 3）')
