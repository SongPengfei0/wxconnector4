"""异常定义。"""


class WxautoOCRError(Exception):
    """OCR 相关错误。"""


class NetWorkError(Exception):
    """网络相关错误。"""


class WxautoUINotFoundError(Exception):
    """未找到目标 UI 控件。"""


class WxautoNoteLoadTimeoutError(Exception):
    """微信笔记加载超时。"""
