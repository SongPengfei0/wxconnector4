"""聊天区组件：输入/发送、读取消息、会话信息。

操作对象是一个窗口控件（主窗口或独立子窗口）的聊天区。
"""
import os
import time
from difflib import SequenceMatcher

from ..param import WxParam, WxResponse
from ..languages import CTRL
from ..utils import uiabase
from ..logger import wxlog
from ..msgs.parse import parse_message


class ChatBox:
    def __init__(self, root_control, parent=None):
        self.root_control = root_control
        self.parent = parent
        self.root = getattr(parent, 'core', None) or parent
        self.chat_info = {}

    # ---------- 控件定位 ----------
    def _input(self):
        return uiabase.find(self.root_control, automation_id=CTRL['input_field_aid'], maxdepth=40) \
            or uiabase.find(self.root_control, classname=CTRL['input_field_cls'], maxdepth=40)

    def _msg_list(self):
        return uiabase.find(self.root_control, automation_id=CTRL['message_list_aid'], maxdepth=40)

    def _chat_name_label(self):
        return uiabase.find(self.root_control, aid_suffix=CTRL['chat_name_label_aid_suffix'],
                            maxdepth=40, timeout=1.5)

    def _send_button(self):
        return uiabase.find(self.root_control, name=CTRL['send_button_name'],
                            control_type='ButtonControl', maxdepth=40)

    # ---------- 会话信息 ----------
    @property
    def who(self):
        # 切换/重渲染瞬间 Name 可能短暂为空，重试读取直到拿到非空
        deadline = time.time() + 1.5
        while True:
            lbl = self._chat_name_label()
            name = lbl.Name if lbl else None
            if name or time.time() >= deadline:
                return name or None
            time.sleep(0.1)

    def get_info(self) -> dict:
        name = self.who
        self.chat_info = {'chat_name': name}
        return self.chat_info

    # ---------- 发送 ----------
    def clear_edit(self):
        inp = self._input()
        if inp:
            uiabase.set_focus(inp)
            uiabase.clear_edit(inp)

    def send_text(self, text: str, clear: bool = True) -> WxResponse:
        if uiabase.is_locked():
            return WxResponse.error('工作站已锁屏，无法发送；请先解锁屏幕')
        inp = self._input()
        if inp is None:
            return WxResponse.failure('未找到输入框')
        uiabase.activate_window(self.root_control)
        uiabase.set_focus(inp)
        time.sleep(0.05)
        if clear:
            uiabase.clear_edit(inp)
            time.sleep(0.05)
        uiabase.set_clipboard_text(text)
        time.sleep(0.08)
        uiabase.paste(inp)
        time.sleep(0.15)
        # 发送前内容相似度校验，避免发错
        actual = uiabase.get_value(inp)
        ratio = SequenceMatcher(None, actual.strip(), text.strip()).ratio() if actual else 0
        if ratio < WxParam.SEND_CONTENT_RATIO:
            wxlog.warning(f'输入框内容校验未通过(相似度{ratio:.2f})，实际={actual!r}')
            # 再尝试一次：清空重贴
            uiabase.clear_edit(inp)
            uiabase.set_clipboard_text(text)
            time.sleep(0.1)
            uiabase.paste(inp)
            time.sleep(0.15)
            actual = uiabase.get_value(inp)
            ratio = SequenceMatcher(None, actual.strip(), text.strip()).ratio() if actual else 0
            if ratio < WxParam.SEND_CONTENT_RATIO:
                return WxResponse.failure(f'内容校验失败(相似度{ratio:.2f})，未发送')
        uiabase.press_enter(inp)
        return WxResponse.success('发送成功')

    def send_file(self, filepath) -> WxResponse:
        if uiabase.is_locked():
            return WxResponse.error('工作站已锁屏，无法发送；请先解锁屏幕')
        if isinstance(filepath, str):
            filepath = [filepath]
        for p in filepath:
            if not os.path.exists(p):
                return WxResponse.failure(f'文件不存在: {p}')
        filepath = [os.path.abspath(p) for p in filepath]
        inp = self._input()
        if inp is None:
            return WxResponse.failure('未找到输入框')
        uiabase.activate_window(self.root_control)
        uiabase.set_focus(inp)
        uiabase.clear_edit(inp)
        if not uiabase.set_clipboard_files(filepath):
            return WxResponse.failure('写入剪贴板失败')
        time.sleep(0.2)
        uiabase.paste(inp)
        time.sleep(0.6)  # 等待文件加载进编辑框
        uiabase.press_enter(inp)
        return WxResponse.success('发送成功', data={'files': filepath})

    def at_all(self, msg: str = None) -> WxResponse:
        """群内 @所有人 并发送 msg。

        输入框打 @ → 弹出 mmui::ChatMentionList → 点其中 mmui::XTableCell「所有人」→
        输入正文 → 回车。需在群聊、且你是群主/管理员才有「所有人」选项。
        """
        if uiabase.is_locked():
            return WxResponse.error('工作站已锁屏，无法发送；请先解锁屏幕')
        inp = self._input()
        if inp is None:
            return WxResponse.failure('未找到输入框')
        uiabase.activate_window(self.root_control)
        uiabase.set_focus(inp)
        uiabase.clear_edit(inp)
        inp.SendKeys('@')
        time.sleep(1.0)
        mention = uiabase.find(uiabase.get_root(), classname='mmui::ChatMentionList',
                               maxdepth=22, timeout=2)
        if mention is None:
            uiabase.clear_edit(inp)
            return WxResponse.failure('未弹出 @ 成员列表（需在群聊中）')
        allcell = uiabase.find(mention, name='所有人', maxdepth=8)
        if allcell is None:
            uiabase.clear_edit(inp)
            return WxResponse.failure('@ 列表中无「所有人」（需群主/管理员权限）')
        allcell.Click(simulateMove=False)
        time.sleep(0.3)
        if msg:
            uiabase.set_clipboard_text(msg)
            time.sleep(0.1)
            uiabase.paste(inp)
            time.sleep(0.2)
        uiabase.press_enter(inp)
        return WxResponse.success('已 @所有人 并发送', data={'msg': msg})

    # ---------- 读取消息 ----------
    def get_msgs(self, detect_direction: bool = True):
        mlist = self._msg_list()
        if mlist is None:
            return []
        try:
            items = mlist.GetChildren()
        except Exception:
            return []
        msgs = []
        for it in items:
            try:
                msgs.append(parse_message(it, self, detect_direction=detect_direction))
            except Exception as e:
                wxlog.debug(f'解析消息失败: {e}')
        return msgs

    # ---------- 滚动 ----------
    def scroll_up(self, times: int = 3):
        mlist = self._msg_list()
        if mlist is not None:
            try:
                mlist.WheelUp(wheelTimes=max(1, times), waitTime=0.05)
            except Exception:
                pass

    def scroll_to_bottom(self):
        mlist = self._msg_list()
        if mlist is not None:
            for _ in range(8):
                try:
                    mlist.WheelDown(wheelTimes=10, waitTime=0.02)
                except Exception:
                    break

    def get_new_msgs(self, detect_direction: bool = True):
        """返回自上次调用以来的新消息（按 id 去重）。"""
        if not hasattr(self, '_seen_ids'):
            self._seen_ids = set()
            # 首次调用：记录现有消息为已读，返回空
            for m in self.get_msgs(detect_direction=False):
                if m.id:
                    self._seen_ids.add(m.id)
            return []
        new = []
        for m in self.get_msgs(detect_direction=detect_direction):
            if m.id and m.id not in self._seen_ids:
                self._seen_ids.add(m.id)
                new.append(m)
        return new
