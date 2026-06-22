"""通用 UI 组件：右键菜单、联系人选择窗、对话框等。"""
import time

from ..utils import uiabase
from ..logger import wxlog


class Menu:
    """右键弹出菜单。菜单项 MenuItemControl，ClassName mmui::XMenuView。

    注意：菜单窗口 mmui::XMenu 不是桌面根的直接子窗（嵌套在更深层），
    所以用整树深搜定位菜单项，而非 find_window。
    """

    ITEM_CLS = 'mmui::XMenuView'
    MENU_WINDOW_CLS = 'mmui::XMenu'

    def __init__(self, timeout: float = 2.0):
        self._items = []
        deadline = time.time() + timeout
        while True:
            items = uiabase.find_all(uiabase.get_root(), classname=self.ITEM_CLS, maxdepth=20)
            self._items = [i for i in items if i.ControlTypeName == 'MenuItemControl']
            if self._items or time.time() >= deadline:
                break
            time.sleep(0.1)

    def __bool__(self):
        return bool(self._items)

    @property
    def items(self):
        return self._items

    @property
    def option_names(self):
        return [i.Name for i in self._items]

    def select(self, name: str, exact: bool = False) -> bool:
        """按名称点击菜单项。'转发...' 这类带省略号的也能用 '转发' 命中。"""
        for it in self._items:
            n = (it.Name or '')
            if (exact and n == name) or (not exact and (n == name or n.rstrip('.…') == name or name in n)):
                try:
                    it.Click(simulateMove=False)
                    return True
                except Exception as e:
                    wxlog.debug(f'点击菜单项失败: {e}')
                    return False
        return False

    def close(self):
        # 深搜 XMenu 窗口并 Esc 它（只关菜单，不误伤主窗口）
        for m in uiabase.find_all(uiabase.get_root(), classname=self.MENU_WINDOW_CLS, maxdepth=20):
            try:
                m.SendKeys('{Esc}')
            except Exception:
                pass


class SelectContactWnd:
    """转发/分享时的联系人选择窗 mmui::SessionPickerWindow。

    结构：搜索框 mmui::XValidatorTextEdit(Name=搜索)、联系人行 mmui::SPSelectionContactRow、
    附加消息框 mmui::ChatInputField、发送/取消按钮。
    """

    WND_CLS = 'mmui::SessionPickerWindow'
    ROW_CLS = 'mmui::SPSelectionContactRow'

    def __init__(self, timeout: float = 3.0):
        self.control = uiabase.find(uiabase.get_root(), classname=self.WND_CLS, maxdepth=12, timeout=timeout)

    def __bool__(self):
        return self.control is not None

    def _search_edit(self):
        return uiabase.find(self.control, classname='mmui::XValidatorTextEdit', maxdepth=16)

    def _msg_edit(self):
        return uiabase.find(self.control, classname='mmui::ChatInputField', maxdepth=16)

    def search(self, keyword, interval: float = 0.05):
        edit = self._search_edit()
        if edit is not None:
            uiabase.set_focus(edit)
            uiabase.clear_edit(edit)
            edit.SendKeys(keyword, interval=interval)

    def _select_row(self, name: str) -> bool:
        """点击联系人。搜索结果是 CheckBox(cls mmui::SearchContactCellView)，
        最近联系人行是 mmui::SPSelectionContactRow。"""
        import time
        # 1) 按精确名匹配（搜索结果勾选框 / 最近联系人行）
        cands = [c for c in uiabase.find_all(self.control, name=name, maxdepth=18)
                 if 'Contact' in (c.ClassName or '')
                 or c.ControlTypeName in ('CheckBoxControl', 'ListItemControl')]
        # 2) 兜底：搜索结果单元里按包含匹配
        if not cands:
            cells = uiabase.find_all(self.control, classname='mmui::SearchContactCellView', maxdepth=18)
            cands = [c for c in cells if name in (c.Name or '')]
        for c in cands:
            try:
                c.Click(simulateMove=False)
                time.sleep(0.15)
                return True
            except Exception:
                continue
        return False

    def add_message(self, content: str):
        import time
        edit = self._msg_edit()
        if edit is not None:
            uiabase.set_focus(edit)
            uiabase.set_clipboard_text(content)
            time.sleep(0.1)
            uiabase.paste(edit)

    def confirm(self) -> bool:
        btn = uiabase.find(self.control, name='发送', control_type='ButtonControl', maxdepth=16)
        if btn is None:
            return False
        try:
            btn.Click(simulateMove=False)
            return True
        except Exception:
            return False

    def send(self, targets, message: str = None, interval: float = 0.1):
        import time
        from ..param import WxResponse
        if self.control is None:
            return WxResponse.failure('未弹出联系人选择窗')
        if isinstance(targets, str):
            targets = [targets]
        chosen = []
        for t in targets:
            self.search(t)
            time.sleep(max(0.3, interval))
            if self._select_row(t):
                chosen.append(t)
        if not chosen:
            return WxResponse.failure('未能选中任何转发目标')
        if message:
            self.add_message(message)
            time.sleep(0.2)
        if self.confirm():
            return WxResponse.success('转发成功', data={'targets': chosen})
        return WxResponse.failure('未找到发送按钮')


class WeChatDialog:
    """确认/提示对话框 mmui::XDialog。"""

    DIALOG_CLS = 'mmui::XDialog'

    def __init__(self, parent_window=None, wait: float = 3.0):
        self._win = parent_window
        self.control = uiabase.find_window(classname=self.DIALOG_CLS, timeout=wait)
        if self.control is None and parent_window is not None:
            self.control = uiabase.find(parent_window, classname=self.DIALOG_CLS, maxdepth=20, timeout=wait)

    def __bool__(self):
        return self.control is not None

    def get_all_text(self) -> str:
        if self.control is None:
            return ''
        texts = uiabase.find_all(self.control, control_type='TextControl', maxdepth=14)
        return '\n'.join(t.Name for t in texts if (t.Name or '').strip())

    def click_button(self, text: str, move: bool = True) -> bool:
        if self.control is None:
            return False
        btn = uiabase.find(self.control, name=text, control_type='ButtonControl', maxdepth=14)
        if btn is None:
            return False
        try:
            btn.Click(simulateMove=False)
            return True
        except Exception:
            return False
