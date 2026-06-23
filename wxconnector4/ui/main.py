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


def _find_wechat_exe() -> str:
    """通过注册表/常见安装目录定位微信 4.x 可执行文件 Weixin.exe。找不到返回 ''。"""
    import os
    # 1) 注册表
    try:
        import winreg
        for hive, sub in ((winreg.HKEY_CURRENT_USER, r'Software\Tencent\Weixin'),
                          (winreg.HKEY_CURRENT_USER, r'Software\Tencent\WeChat'),
                          (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Tencent\Weixin'),
                          (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Tencent\WeChat')):
            try:
                with winreg.OpenKey(hive, sub) as k:
                    for val in ('InstallPath', 'InstallDir'):
                        try:
                            base = winreg.QueryValueEx(k, val)[0]
                        except FileNotFoundError:
                            continue
                        for exe in ('Weixin.exe', 'WeChat.exe'):
                            p = os.path.join(base, exe)
                            if os.path.exists(p):
                                return p
            except OSError:
                continue
    except Exception:
        pass
    # 2) 常见安装目录
    for pf in (os.environ.get('ProgramFiles', r'C:\Program Files'),
               os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')):
        for sub in ('Tencent/Weixin/Weixin.exe', 'Tencent/WeChat/WeChat.exe'):
            p = os.path.join(pf, *sub.split('/'))
            if os.path.exists(p):
                return p
    return ''


class WeChatLoginWnd(BaseUIWnd):
    """登录窗口 mmui::LoginWindow（处理未登录 / 扫码登录场景）。"""
    _ui_cls_name = CTRL['login_window_cls']
    _main_cls = CTRL['main_window_cls']
    # 「进入微信」按钮候选文案（已记住账号时点它即可登录；扫码场景则等待扫码）
    _ENTER_NAMES = ('进入微信', '登录', '登 录', 'Log In', 'Login', 'Enter')

    def __init__(self):
        self.control = uiabase.find_window(classname=self._ui_cls_name, timeout=1.0)

    def _lang(self, text: str):
        return lang(text, WxParam.LANGUAGE)

    def exists(self, wait=0) -> bool:
        return self.control is not None and super().exists(wait)

    def _refresh(self, timeout: float = 1.0):
        self.control = uiabase.find_window(classname=self._ui_cls_name, timeout=timeout)
        return self.control

    def _wait_main(self, timeout: float = 60.0):
        """等待主窗口出现（视为登录成功）。"""
        import time
        deadline = time.time() + timeout
        while time.time() < deadline:
            w = uiabase.find_window(classname=self._main_cls, timeout=0)
            if w is not None:
                return w
            time.sleep(0.5)
        return None

    def open(self, timeout: float = 20.0):
        """打开登录窗口：已存在则置前；否则启动微信进程后等待登录窗口出现。

        返回 WxResponse（成功 data={'launched': bool}）。
        """
        from ..param import WxResponse
        if self._refresh(0.5) is not None:
            uiabase.force_foreground(self.control.NativeWindowHandle)
            return WxResponse.success('登录窗口已打开', data={'launched': False})
        # 主窗口已在 → 已登录，无需登录窗
        if uiabase.find_window(classname=self._main_cls, timeout=0) is not None:
            return WxResponse.success('已登录（主窗口已存在）', data={'launched': False})
        exe = _find_wechat_exe()
        if not exe:
            return WxResponse.failure('未找到微信可执行文件，无法启动；请手动打开微信')
        try:
            import subprocess
            subprocess.Popen([exe])
        except Exception as e:
            return WxResponse.error(f'启动微信失败: {e}')
        import time
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._refresh(0.5) is not None:
                uiabase.force_foreground(self.control.NativeWindowHandle)
                return WxResponse.success('已启动微信并打开登录窗口', data={'launched': True})
            if uiabase.find_window(classname=self._main_cls, timeout=0) is not None:
                return WxResponse.success('微信已直接进入主窗口', data={'launched': True})
            time.sleep(0.5)
        return WxResponse.failure('启动微信后未出现登录窗口')

    def login(self, timeout: float = 60.0):
        """登录：若有「进入微信」按钮（已记住账号）则点击；否则等待用户扫码。

        阻塞直至主窗口出现或超时。返回 WxResponse。
        """
        from ..param import WxResponse
        if self._refresh(1.0) is None:
            # 没有登录窗口：可能已登录
            if uiabase.find_window(classname=self._main_cls, timeout=0) is not None:
                return WxResponse.success('已登录')
            return WxResponse.failure('未找到登录窗口（先 open()）')
        uiabase.force_foreground(self.control.NativeWindowHandle)
        # 尝试点「进入微信」（已记住账号的快捷登录）
        btn = None
        for nm in self._ENTER_NAMES:
            btn = uiabase.find(self.control, name=nm, control_type='ButtonControl', maxdepth=16)
            if btn is not None:
                break
        if btn is not None:
            try:
                btn.Click(simulateMove=False)
            except Exception:
                pass
        else:
            wxlog.info('未发现「进入微信」按钮，请使用手机扫描登录窗口中的二维码…')
        main = self._wait_main(timeout)
        if main is not None:
            return WxResponse.success('登录成功')
        return WxResponse.failure(f'{int(timeout)}s 内未完成登录')

    def reopen(self, timeout: float = 60.0):
        """重新登录：在登录窗口点「切换账号/返回」回到二维码界面后再 login()。"""
        from ..param import WxResponse
        if self._refresh(1.0) is None:
            return self.open(timeout)
        for nm in ('切换账号', '返回', '重新登录'):
            b = uiabase.find(self.control, name=nm, control_type='ButtonControl', maxdepth=16)
            if b is not None:
                try:
                    b.Click(simulateMove=False)
                except Exception:
                    pass
                break
        return self.login(timeout)
