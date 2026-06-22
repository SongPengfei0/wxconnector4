"""OCR 能力（可插拔）。

设计原则：本库**不**自带任何第三方 OCR 引擎，保持轻量低耦合。
- 默认：走微信界面「提取文字」（路线 B，纯 UIA，不逆向、不驱动 WeChatOCR.exe）。
- 高精度：用户自行设置 WxParam.OCR_BACKEND = my_ocr，签名 (image_path:str)->str。

ImageMessage.ocr() 的调度逻辑：
    if WxParam.OCR_BACKEND:  下载图片 -> 调用用户后端
    else:                    走微信「提取文字」
"""
from .logger import wxlog


class OcrResult:
    """OCR 结果。text 为整段文字；regions 预留（路线 B 一般只拿到整段文本）。"""

    def __init__(self, text: str = '', regions: list = None):
        self.text = text or ''
        self.regions = regions or []

    def __str__(self):
        return self.text

    def __repr__(self):
        return f"<OcrResult {self.text[:30]!r}>"

    def __bool__(self):
        return bool(self.text)


import time

# 4.x 图片查看器控件标识
_PREVIEW_WINDOW_CLS = 'mmui::PreviewWindow'
_OCR_BUTTON_CLS = 'mmui::XButton'
_OCR_BUTTON_NAME = '提取文字'
_RESULT_TEXT_CLS = 'mmui::XTextView'


def read_extracted_text(viewer) -> str:
    """从已打开、且已点过「提取文字」的查看器窗口里读取识别结果。

    识别文字显示在工具栏下方、图片右侧的面板里（XTextView）。
    """
    from .utils import uiabase
    try:
        vr = viewer.BoundingRectangle
        mid_x = (vr.left + vr.right) // 2
    except Exception:
        mid_x = 700
    tvs = uiabase.find_all(viewer, classname=_RESULT_TEXT_CLS, maxdepth=24)
    cand = []
    for tv in tvs:
        try:
            name = (tv.Name or '').strip()
            r = tv.BoundingRectangle
            if name and r.left > mid_x:  # 图片右侧的结果面板（工具栏内无 XTextView）
                cand.append(name)
        except Exception:
            continue
    return max(cand, key=len) if cand else ''


def image_click_point(control):
    """图片缩略图点击点（复用通用气泡定位）。"""
    from .utils import uiabase
    return uiabase.content_point(control)


def ocr_via_wechat(image_message, timeout: int = 3) -> OcrResult:
    """路线 B：单击图片→查看器→点「提取文字」→读结果（纯 UIA，不逆向）。"""
    from .utils import uiabase
    msg = image_message
    if uiabase.is_locked():
        wxlog.warning('工作站已锁屏，无法 OCR；请先解锁屏幕')
        return OcrResult('')

    win = getattr(msg.parent, 'root_control', None)  # 消息所在窗口
    try:
        msg.roll_into_view()
    except Exception:
        pass
    if win is not None:
        uiabase.activate_window(win)

    # 1) 单击图片缩略图打开查看器（满宽行需截图定位真实缩略图位置）
    try:
        pt = image_click_point(msg.control)
        if pt:
            import uiautomation as auto
            auto.Click(pt[0], pt[1])
        else:
            msg.control.Click(simulateMove=False)
    except Exception as e:
        wxlog.warning(f'点击图片失败: {e}')
        return OcrResult('')

    # 2) 等待 PreviewWindow 出现
    viewer = None
    deadline = time.time() + max(timeout, 3)
    while time.time() < deadline:
        viewer = uiabase.find_window(classname=_PREVIEW_WINDOW_CLS, timeout=0)
        if viewer is not None:
            break
        time.sleep(0.2)
    if viewer is None:
        wxlog.warning('未能打开图片查看器(PreviewWindow)')
        return OcrResult('')

    # 3) 点「提取文字」按钮
    uiabase.activate_window(viewer)
    btn = uiabase.find(viewer, classname=_OCR_BUTTON_CLS, name=_OCR_BUTTON_NAME, maxdepth=16)
    if btn is None:
        wxlog.warning('查看器中未找到「提取文字」按钮')
        _close_viewer(viewer)
        return OcrResult('')
    try:
        btn.Click(simulateMove=False)
    except Exception as e:
        wxlog.warning(f'点击「提取文字」失败: {e}')
        _close_viewer(viewer)
        return OcrResult('')

    # 4) 等待并读取右侧识别结果
    text = ''
    deadline = time.time() + max(timeout, 3)
    while time.time() < deadline:
        text = read_extracted_text(viewer)
        if text:
            break
        time.sleep(0.3)

    _close_viewer(viewer)
    return OcrResult(text)


def _close_viewer(viewer):
    """关闭图片查看器（独立窗口，Esc 只作用于它，不影响主窗口）。"""
    from .utils import uiabase
    try:
        if not uiabase.is_locked():
            viewer.SendKeys('{Esc}')
    except Exception:
        pass
