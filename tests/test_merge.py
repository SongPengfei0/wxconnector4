"""测 MergeMessage.get_content / get_messages。"""
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
    cleanup()
    wx = WeChat()
    wx.ChatWith('文件传输助手', exact=True)
    uiabase.force_foreground(wx.core.control.NativeWindowHandle)
    time.sleep(0.4)
    msgs = wx.GetAllMessage()
    merge = [m for m in msgs if getattr(m, 'type', None) == 'merge']
    print('merge 样本:', len(merge))
    if not merge:
        return
    m = merge[-1]
    msgs2 = m.get_messages()
    print(f'\nget_messages（{len(msgs2)} 条，含类型）:')
    for x in msgs2:
        print(f'   {x.__class__.__name__:16} {repr((x.content or "")[:54])}')
    contents = [mm.content for mm in msgs2
                if (getattr(mm, "content", "") or "").strip() and getattr(mm, "type", None) != "system"]
    print(f'\nget_content 文本（{len(contents)} 条）:')
    for c in contents:
        print('   ', repr(c[:60]))


if __name__ == '__main__':
    main()
