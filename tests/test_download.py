"""测 FileMessage.download / VideoMessage.download（右键另存为到本地临时目录）。"""
import os
import shutil
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


def close_saveas():
    import win32gui

    def cb(h, _):
        try:
            if win32gui.GetClassName(h) == '#32770' and win32gui.IsWindowVisible(h):
                win32gui.PostMessage(h, 0x0010, 0, 0)  # WM_CLOSE
        except Exception:
            pass
    win32gui.EnumWindows(cb, None)


def main():
    dest = os.path.abspath('_dl_test')
    shutil.rmtree(dest, ignore_errors=True)

    close_saveas()
    cleanup()
    wx = WeChat()
    wx.ChatWith('文件传输助手', exact=True)
    msgs = wx.GetAllMessage()
    files = [m for m in msgs if getattr(m, 'type', None) == 'file']
    videos = [m for m in msgs if getattr(m, 'type', None) == 'video']
    print('file 样本:', len(files), '| video 样本:', len(videos))

    if files:
        r = files[0].download(dir_path=dest)  # 用较靠上的文件，避开最新消息被输入框遮挡
        print('File.download ->', r)
    time.sleep(1.0)
    cleanup()
    if videos:
        r2 = videos[0].download(dir_path=dest)
        print('Video.download ->', r2)

    listing = os.listdir(dest) if os.path.exists(dest) else []
    print('目标目录内容:', listing)
    for f in listing:
        p = os.path.join(dest, f)
        print(f'   {f}  ({os.path.getsize(p)} bytes)')


if __name__ == '__main__':
    main()
