"""验证 OCR 路线 B（界面「提取文字」）。请在微信可见、未锁屏时，在你自己的终端运行。

    python verify_ocr.py

会自动：找当前聊天里的图片消息 -> 单击打开大图 -> 点「提取文字」-> 读结果。
全程只读图片、不发消息。请先切到一个有图片的聊天（如"文件传输助手"）。
"""
from wxconnector4 import WeChat, WxParam
from wxconnector4.utils import uiabase
from wxconnector4.msgs.types import ImageMessage


def main():
    if uiabase.is_locked():
        print('屏幕锁定中，请先解锁'); return
    wx = WeChat()
    imgs = [m for m in wx.GetAllMessage() if isinstance(m, ImageMessage)]
    print(f'当前聊天图片消息数: {len(imgs)}')
    if not imgs:
        print('没有图片消息，请切到有图片的聊天再试'); return

    print('\n=== 默认后端：微信界面「提取文字」===')
    res = imgs[-1].ocr(timeout=6)
    print('识别结果(前150字):', repr(str(res)[:150]))
    print('字数:', len(str(res)))
    print('✅ OCR 成功' if str(res) else '⚠️ 未识别到文字（可能该图无文字，或点击未生效）')

    # 演示可插拔后端：用户接入自己的高精度 OCR（这里只示意，不实际调用）
    print('\n=== 可插拔后端示例（不依赖本库）===')
    print('如需更高精度，用户可这样接入自己的 PaddleOCR：')
    print("    from wxconnector4 import WxParam")
    print("    WxParam.OCR_BACKEND = lambda path: my_paddle_ocr(path)  # (image_path)->str")
    print("    text = img_msg.ocr()  # 自动改走你的后端")


if __name__ == '__main__':
    main()
