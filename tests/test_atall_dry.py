"""AtAll dry-run：走到点「所有人」插入 @，验证后清空，不发送（不打扰成员）。"""
import time
from wxconnector4 import WeChat
from wxconnector4.utils import uiabase

GROUP = 'wxc测试备注'


def cleanup():
    for _ in range(6):
        s = uiabase.find_all(uiabase.get_root(), classname='mmui::XMenu', maxdepth=20)
        if not s:
            return
        for w in s:
            try:
                w.SendKeys('{Esc}')
            except Exception:
                pass
        time.sleep(0.3)


def main():
    cleanup()
    wx = WeChat()
    root = wx.core.control
    uiabase.force_foreground(root.NativeWindowHandle)
    tab = uiabase.find(root, name='微信', control_type='ButtonControl', maxdepth=10)
    if tab:
        tab.Click(simulateMove=False)
        time.sleep(1.0)
    wx.ChatWith(GROUP, exact=True)
    print('当前会话:', wx.ChatInfo().get('chat_name'))
    inp = uiabase.find(root, automation_id='chat_input_field', maxdepth=40)
    if inp is None:
        print('无输入框')
        return
    uiabase.set_focus(inp)
    uiabase.clear_edit(inp)
    inp.SendKeys('@')
    time.sleep(1.0)
    mention = uiabase.find(uiabase.get_root(), classname='mmui::ChatMentionList', maxdepth=22, timeout=2)
    print('弹出@列表:', mention is not None)
    allcell = uiabase.find(mention, name='所有人', maxdepth=8) if mention else None
    print('「所有人」项:', allcell is not None)
    if allcell:
        allcell.Click(simulateMove=False)
        time.sleep(0.4)
        print('点「所有人」后输入框内容:', repr(uiabase.get_value(inp)))
    uiabase.clear_edit(inp)
    print('已清空输入框，未发送（dry-run）')


if __name__ == '__main__':
    main()
