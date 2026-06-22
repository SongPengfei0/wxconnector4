"""AtAll 实测：@所有人 发一条测试消息到测试群（会通知成员）。"""
import time
from wxconnector4 import WeChat
from wxconnector4.utils import uiabase

GROUP = 'wxc测试备注'
MSG = 'wxconnector4 AtAll 自动化测试，可删除'


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
    r0 = wx.ChatWith(GROUP, exact=True)
    print('ChatWith:', r0.get('status'), '| 当前会话(标题):', wx.ChatInfo().get('chat_name'))
    r = wx.AtAll(MSG)  # 已在群，不传 who 避开备注名≠群真名的校验
    print('AtAll 返回:', r)
    time.sleep(1.2)
    msgs = wx.GetAllMessage()
    last = msgs[-1] if msgs else None
    if last is not None:
        print('最后一条消息:', last.__class__.__name__, '| name=', repr((last.content or '')[:70]))


if __name__ == '__main__':
    main()
