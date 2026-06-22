"""测 VoiceMessage.to_text。"""
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
    msgs = wx.GetAllMessage()
    voice = [m for m in msgs if getattr(m, 'type', None) == 'voice']
    print('语音样本数:', len(voice))
    if voice:
        v = voice[-1]
        print('气泡原始 name:', repr(v.content))
        txt = v.to_text()
        print('to_text() 返回:', repr(txt))


if __name__ == '__main__':
    main()
