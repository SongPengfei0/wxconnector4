"""wxconnector4 端到端验证脚本（只操作"文件传输助手"，安全）。

运行前请确保：微信已登录打开，且屏幕未锁定。
    python verify_wxconnector4.py
"""
from wxconnector4 import WeChat
from wxconnector4.utils import uiabase

TARGET = '文件传输助手'


def main():
    if uiabase.is_locked():
        print('❌ 工作站已锁屏，无法进行点击/发送验证。请解锁屏幕后重试。')
        return

    print('=== 连接 ===')
    wx = WeChat()
    print('IsOnline:', wx.IsOnline())
    print('GetMyInfo:', wx.GetMyInfo())
    print('安装路径:', wx.path)

    print('\n=== 读会话列表 ===')
    sessions = wx.GetSession()
    print(f'共 {len(sessions)} 个会话，前 5：')
    for s in sessions[:5]:
        print('  ', repr(s.name), '| mute=', s.mute)

    print(f'\n=== 切换到「{TARGET}」 ===')
    r = wx.ChatWith(TARGET, exact=True)
    print('切换结果:', r)
    info = wx.ChatInfo()
    print('当前会话:', info)
    ok_switch = info.get('chat_name') == TARGET
    print('✅ 切换成功' if ok_switch else '❌ 切换失败（当前不是目标会话）')

    print('\n=== 读取当前消息（后 5 条）===')
    for m in wx.GetAllMessage()[-5:]:
        print('  ', m.__class__.__name__, '| attr=', m.attr, '| type=', m.type,
              '|', repr((m.content or '')[:30]))

    if ok_switch:
        print('\n=== 发送测试消息 ===')
        text = 'wxconnector4 自检消息 ✅'
        r = wx.SendMsg(text, who=TARGET, exact=True)
        print('发送结果:', r)

        print('\n=== 回读确认 ===')
        last = wx.GetAllMessage()[-1]
        print('最后一条:', repr(last.content), '| attr=', last.attr)
        print('✅ 发送并回读成功' if text in (last.content or '') else '⚠️ 未在末尾读到刚发送内容')

    print('\n=== 完成 ===')


if __name__ == '__main__':
    main()
