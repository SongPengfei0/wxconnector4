"""测 SendFiles：建临时文件 → 发到文件传输助手 → 读回确认最后一条是 file。"""
import os
import time
from wxconnector4 import WeChat
from wxconnector4.utils import uiabase


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
    p = os.path.abspath('wxconnector4_sendfiles_test.txt')
    with open(p, 'w', encoding='utf-8') as f:
        f.write('wxconnector4 SendFiles 自检文件，可删除。\n')

    cleanup()
    wx = WeChat()
    print('chatwith:', wx.ChatWith('文件传输助手', exact=True)['status'])
    r = wx.SendFiles(p)
    print('SendFiles 返回:', r)
    time.sleep(1.8)
    msgs = wx.GetAllMessage()
    last = msgs[-1] if msgs else None
    if last is not None:
        print('最后一条消息:', last.__class__.__name__,
              '| type=', getattr(last, 'type', None),
              '| name=', repr((getattr(last, 'content', '') or '')[:60]))


if __name__ == '__main__':
    main()
