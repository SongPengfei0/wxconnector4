"""验证消息动作（复制/引用/删除）。只操作文件传输助手，安全。"""
import time
import uiautomation as auto
from wxconnector4 import WeChat
from wxconnector4.utils import uiabase
from wxconnector4.languages import CTRL
from wxconnector4.msgs.types import TextMessage


def cleanup_popups():
    """深搜关掉残留菜单/查看器浮层（XMenu 嵌套较深，非 root 直接子窗）。"""
    for _ in range(8):
        stray = (uiabase.find_all(uiabase.get_root(), classname='mmui::XMenu', maxdepth=20)
                 + uiabase.find_all(uiabase.get_root(), classname='mmui::PreviewWindow', maxdepth=4))
        if not stray:
            return
        for w in stray:
            try:
                w.SendKeys('{Esc}')
            except Exception:
                pass
        time.sleep(0.3)


def main():
    if uiabase.is_locked():
        print('屏幕锁定中，请先解锁'); return
    cleanup_popups()
    wx = WeChat()
    wx.ChatWith('文件传输助手', exact=True)
    # 等会话切换 + 消息加载
    texts = []
    for _ in range(8):
        time.sleep(0.4)
        if wx.ChatInfo().get('chat_name') != '文件传输助手':
            continue
        texts = [m for m in wx.GetAllMessage() if isinstance(m, TextMessage)]
        if texts:
            break
    print('文字消息数:', len(texts))
    if not texts:
        print('无文字消息，退出'); return
    msg = texts[-1]
    print('目标消息:', repr(msg.content[:20]))

    # 1) select_option('复制') -> 剪贴板应含消息内容
    uiabase.set_clipboard_text('___占位___')
    r = msg.select_option('复制')
    time.sleep(0.4)
    clip = uiabase.get_clipboard_text()
    ok = msg.content[:8] in clip
    print(f'select_option(复制): {r["status"]} | 剪贴板={clip[:24]!r} | {"✅" if ok else "❌"}')
    cleanup_popups()

    # 2) quote -> 引用回复，末尾应出现回复文本
    time.sleep(0.5)
    qtext = '引用回复自检'
    r2 = msg.quote(qtext)
    time.sleep(1.0)
    allm = wx.GetAllMessage()
    last = allm[-1] if allm else None
    last_txt = (last.content or '')[:24] if last else None
    ok2 = last is not None and qtext in (last.content or '')
    print(f'quote: {r2["status"]} | 末条={last_txt!r} | {"✅" if ok2 else "❌"}')
    cleanup_popups()
    print('完成')


if __name__ == '__main__':
    main()
