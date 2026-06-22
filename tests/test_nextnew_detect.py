"""只读验证 GetNextNewMessage 的未读检测逻辑（不切入、不清除真实未读）。"""
import re
from wxconnector4 import WeChat
from wxconnector4.languages import RE


def main():
    wx = WeChat()
    rc = re.compile(RE['session_count'])
    print('会话未读检测：')
    any_unread = False
    for s in wx.GetSession():
        m = rc.search(s.content or '')
        if m:
            any_unread = True
            print(f'   未读 {m.group(1):>2} 条 | mute={s.mute} | {s.name!r}  预览={s.content[:30]!r}')
    if not any_unread:
        print('   （当前无未读会话）')


if __name__ == '__main__':
    main()
