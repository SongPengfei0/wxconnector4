"""消息模型基类。

4.x 现实：消息气泡是 Skia 渲染的叶子控件，无子控件，内容全在 Name。
故 content 取自 Name；发送人/方向靠截图等辅助手段（best-effort）。
"""
import hashlib

from ..param import WxParam, WxResponse
from ..utils.lock import uilock


class Message:
    """消息标记基类。"""


class BaseMessage(Message):
    type: str = 'base'
    attr: str = 'base'

    def __init__(self, control, parent=None):
        self.control = control
        self.parent = parent
        self.root = getattr(parent, 'root', None)
        self.content = self._read_content()
        self.sender = None
        self.sender_remark = None
        self.direction = None
        self.chat_info = getattr(parent, 'chat_info', {}) if parent else {}
        self.id = self._read_id()
        self.hash_text = f'{self.type}:{self.attr}:{self.content}'
        self.hash = hashlib.md5(self.hash_text.encode('utf-8', 'ignore')).hexdigest() \
            if WxParam.MESSAGE_HASH else self.id

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.attr}/{self.type}: {(self.content or '')[:20]!r}>"

    def _read_content(self) -> str:
        try:
            return self.control.Name or ''
        except Exception:
            return ''

    def _read_id(self):
        try:
            return ''.join(str(i) for i in self.control.GetRuntimeId())
        except Exception:
            return None

    @property
    def raw(self):
        """便于打印：[归属, 内容]。"""
        return [self.sender or self.attr, self.content]

    def roll_into_view(self):
        try:
            self.control.GetScrollItemPattern().ScrollIntoView()
        except Exception:
            try:
                self.control.MoveCursorToMyCenter()
            except Exception:
                pass

    def exists(self) -> bool:
        try:
            return self.control.Exists(0)
        except Exception:
            return False


class HumanMessage(BaseMessage):
    """人发出的消息（好友/自己），可点击/转发/引用等。"""
    attr = 'human'

    # ---------- 基础操作 ----------
    def _window(self):
        return getattr(self.parent, 'root_control', None)

    def _activate(self):
        import time
        from ..utils import uiabase
        win = self._window()
        if win is not None:
            uiabase.activate_window(win)
        try:
            self.roll_into_view()
        except Exception:
            pass
        time.sleep(0.05)

    def _point(self):
        from ..utils import uiabase
        return uiabase.content_point(self.control)

    def click(self) -> None:
        from ..utils import uiabase
        self._activate()
        pt = self._point()
        if pt:
            uiabase.click_at(*pt)
        else:
            try:
                self.control.Click(simulateMove=False)
            except Exception:
                pass

    def right_click(self) -> None:
        from ..utils import uiabase
        self._activate()
        pt = self._point()
        if pt:
            uiabase.right_click_at(*pt)
        else:
            try:
                self.control.RightClick(simulateMove=False)
            except Exception:
                pass

    def _open_menu(self, timeout: float = 2.0):
        """右键消息并返回菜单。满宽行气泡靠边对齐，content_point 截图算法对
        文件/视频卡片可能失败，故多候选点重试：content_point → 靠右(self) →
        靠左(friend) → 中心，命中菜单即停。"""
        import time
        from ..ui.component import Menu
        from ..utils import uiabase
        self._activate()
        cands = []
        pt = self._point()
        if pt:
            cands.append(pt)
        try:
            r = self.control.BoundingRectangle
            cy = (r.top + r.bottom) // 2
            w = r.right - r.left
            cands += [(r.left + int(w * 0.80), cy),
                      (r.left + int(w * 0.20), cy),
                      (r.left + w // 2, cy)]
        except Exception:
            pass
        for i, (x, y) in enumerate(cands):
            uiabase.right_click_at(x, y)
            time.sleep(0.35)
            menu = Menu(timeout=timeout if i == 0 else 0.8)
            if menu:
                return menu
        return Menu(timeout=0.1)

    def _save_as(self, dir_path=None, filename=None, timeout: int = 30, menu_kw: str = '另存为'):
        """右键→「另存为...」→系统文件框保存到 dir_path（默认 WxParam.DEFAULT_SAVE_PATH）。

        filename=None 时沿用对话框自带文件名。成功返回保存后的 Path，失败返回 WxResponse。
        File/Video 下载共用此逻辑。
        """
        import os
        import time
        from pathlib import Path
        from ..utils import uiabase
        if uiabase.is_locked():
            return WxResponse.failure('已锁屏，无法下载')
        target_dir = str(dir_path) if dir_path else WxParam.DEFAULT_SAVE_PATH
        os.makedirs(target_dir, exist_ok=True)
        before = set(os.listdir(target_dir))
        menu = self._open_menu(2)
        if not menu:
            return WxResponse.failure('未弹出右键菜单')
        if not menu.select(menu_kw):
            menu.close()
            return WxResponse.failure(f'菜单无「{menu_kw}」项')
        time.sleep(0.8)
        saved = uiabase.save_file_dialog(target_dir, filename=filename, timeout=8)
        if not saved:
            return WxResponse.failure('未能操作「另存为」对话框')
        # 目录扫描确认落地（对话框可能自动补扩展名，不能精确匹配 saved）
        deadline = time.time() + timeout
        while time.time() < deadline:
            new = [f for f in os.listdir(target_dir)
                   if f not in before and not f.endswith(('.tmp', '.crdownload', '.download', '.part'))]
            if new:
                new.sort(key=lambda f: os.path.getsize(os.path.join(target_dir, f)))
                return Path(target_dir) / new[-1]
            time.sleep(0.4)
        return WxResponse.failure(f'保存超时，目录无新文件: {target_dir}')

    def click_head(self, right: bool = False) -> None:
        from ..logger import wxlog
        wxlog.warning('click_head 尚未完整实现（Phase 3）')

    # ---------- 菜单动作 ----------
    @uilock
    def select_option(self, option: str, timeout: int = 2) -> WxResponse:
        """右键消息并选择指定菜单项（复制/收藏/提醒/翻译/搜一搜...）。"""
        menu = self._open_menu(timeout)
        if not menu:
            return WxResponse.failure('未弹出右键菜单')
        ok = menu.select(option)
        if not ok:
            menu.close()
            return WxResponse.failure(f'菜单中无「{option}」项，可选: {menu.option_names}')
        return WxResponse.success(f'已选择「{option}」')

    @uilock
    def quote(self, text: str, at=None, timeout: int = 3) -> WxResponse:
        """引用本条消息并回复 text。"""
        import time
        from ..utils import uiabase
        from ..param import WxParam
        menu = self._open_menu(timeout)
        if not menu:
            return WxResponse.failure('未弹出右键菜单')
        if not menu.select('引用'):
            menu.close()
            return WxResponse.failure('菜单中无「引用」项')
        time.sleep(0.3)
        win = self._window()
        inp = uiabase.find(win, automation_id='chat_input_field', maxdepth=40, timeout=2)
        if inp is None:
            return WxResponse.failure('未找到输入框')
        uiabase.set_focus(inp)
        uiabase.set_clipboard_text(text)
        time.sleep(0.1)
        uiabase.paste(inp)
        time.sleep(0.15)
        uiabase.press_enter(inp)
        return WxResponse.success('引用回复成功')

    @uilock
    def forward(self, targets, message: str = None, timeout: int = 3, interval: float = 0.1) -> WxResponse:
        """转发本条消息给 targets（单个或列表）。"""
        from ..ui.component import SelectContactWnd
        menu = self._open_menu(timeout)
        if not menu:
            return WxResponse.failure('未弹出右键菜单')
        if not menu.select('转发'):
            menu.close()
            return WxResponse.failure('菜单中无「转发」项')
        picker = SelectContactWnd(timeout=timeout)
        if not picker:
            return WxResponse.failure('未弹出联系人选择窗')
        return picker.send(targets, message=message, interval=interval)

    @uilock
    def delete(self) -> WxResponse:
        """删除本条消息（仅本地）。"""
        import time
        from ..ui.component import WeChatDialog
        menu = self._open_menu()
        if not menu:
            return WxResponse.failure('未弹出右键菜单')
        if not menu.select('删除'):
            menu.close()
            return WxResponse.failure('菜单中无「删除」项')
        time.sleep(0.3)
        dlg = WeChatDialog(self._window(), wait=2)
        if dlg:
            dlg.click_button('删除') or dlg.click_button('确定')
        return WxResponse.success('已删除')

    @uilock
    def tickle(self):
        from ..logger import wxlog
        wxlog.warning('tickle 尚未实现（Phase 3，需群聊好友头像双击）')
        return WxResponse.failure('未实现')


class NotExistsMessage(BaseMessage):
    type = 'notexists'
    attr = 'notexists'
