"""会话列表组件：列举会话、搜索、切换会话。"""
import time

from ..param import WxParam, WxResponse
from ..languages import CTRL
from ..utils import uiabase
from ..logger import wxlog


class SessionElement:
    """单个会话项（mmui::ChatSessionCell）。"""

    def __init__(self, control, parent=None):
        self.control = control
        self.parent = parent
        raw = (control.Name or '')
        lines = [x for x in raw.split('\n')]
        self.name = lines[0] if lines else ''
        self.content = lines[1] if len(lines) > 1 else ''
        self.time = lines[2] if len(lines) > 2 else ''
        self.mute = '消息免打扰' in raw
        self.raw = raw

    def __repr__(self):
        return f"<SessionElement {self.name!r}>"

    def click(self):
        self.control.Click(simulateMove=False)

    def double_click(self):
        self.control.DoubleClick(simulateMove=False)

    def right_click(self):
        self.control.RightClick(simulateMove=False)

    def roll_into_view(self):
        try:
            self.control.GetScrollItemPattern().ScrollIntoView()
        except Exception:
            pass


class SessionBox:
    def __init__(self, root_control, parent=None):
        self.root_control = root_control
        self.parent = parent

    def _list(self):
        return uiabase.find(self.root_control, automation_id=CTRL['session_list_aid'], maxdepth=30)

    def _search_edit(self):
        # 搜索框：XSearchField 内的 XValidatorTextEdit(Name=搜索)
        return uiabase.find(self.root_control, classname=CTRL['search_edit_cls'], maxdepth=20)

    def get_session(self):
        lst = self._list()
        if lst is None:
            return []
        cells = uiabase.find_all(lst, classname=CTRL['session_cell_cls'], maxdepth=6)
        return [SessionElement(c, self.parent) for c in cells]

    def _find_cell(self, who: str, exact: bool):
        lst = self._list()
        if lst is None:
            return None
        cells = uiabase.find_all(lst, classname=CTRL['session_cell_cls'], maxdepth=6)
        for c in cells:
            name = (c.Name or '').split('\n')[0]
            if (exact and name == who) or (not exact and who in name):
                return c
        return None

    def search(self, keyword: str, interval: float = 0.05):
        edit = self._search_edit()
        if edit is None:
            return False
        uiabase.set_focus(edit)
        uiabase.clear_edit(edit)
        time.sleep(0.1)
        edit.SendKeys(keyword, interval=interval)
        return True

    def _find_sub_window(self, who: str):
        from ..languages import CTRL as C
        for w in uiabase.find_windows(classname=C['sub_window_cls']):
            lbl = uiabase.find(w, aid_suffix=C['chat_name_label_aid_suffix'], maxdepth=40)
            if lbl and lbl.Name == who:
                return w
        return None

    def open_separate_window(self, who: str, exact: bool = True, timeout: float = 3.0):
        """把会话以独立窗口(mmui::ChatSingleWindow)打开；已存在则直接复用。返回窗口控件或 None。"""
        existing = self._find_sub_window(who)
        if existing is not None:
            return existing
        if uiabase.is_locked():
            return None
        uiabase.activate_window(self.root_control)
        cell = self._find_cell(who, exact)
        if cell is None:
            # 不在可见列表则先搜索切换，再从主窗口当前会话双击打开
            self.switch_chat(who, exact=exact)
            time.sleep(0.3)
            cell = self._find_cell(who, exact)
            if cell is None:
                return None
        try:
            cell.DoubleClick(simulateMove=False)
        except Exception:
            return None
        deadline = time.time() + timeout
        while time.time() < deadline:
            w = self._find_sub_window(who)
            if w is not None:
                return w
            time.sleep(0.2)
        return None

    def switch_chat(self, who: str, exact: bool = True, force: bool = False,
                    force_wait: float = 0.5) -> WxResponse:
        if uiabase.is_locked():
            return WxResponse.error('工作站已锁屏，无法操作微信；请先解锁屏幕')
        uiabase.activate_window(self.root_control)
        # 1) 优先直接点击可见会话项
        cell = self._find_cell(who, exact)
        if cell is not None:
            try:
                cell.Click(simulateMove=False)
                time.sleep(0.2)
                return WxResponse.success('已切换会话', data={'who': who})
            except Exception as e:
                wxlog.debug(f'点击会话项失败: {e}')

        # 2) 回退到搜索
        if not self.search(who):
            return WxResponse.failure('未找到搜索框')
        time.sleep(WxParam.SEARCH_CHAT_TIMEOUT if not force else force_wait)
        edit = self._search_edit()
        try:
            edit.SendKeys('{Enter}')  # 进入首个结果
            time.sleep(0.3)
            return WxResponse.success('已切换会话(搜索)', data={'who': who})
        except Exception as e:
            return WxResponse.error(f'切换会话失败: {e}')
