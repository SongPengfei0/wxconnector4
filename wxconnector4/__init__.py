"""wxconnector4 —— 独立、免授权的微信 4.x 自动化库。

基于公开的 Windows UI Automation 实现，无任何授权/许可校验。
"""
from .wx import WeChat, Chat, Listener
from .ui.main import WeChatLoginWnd as LoginWnd
from .param import WxParam, WxResponse
from .utils.auth import authenticate

__version__ = '0.1.0'

__all__ = [
    'WeChat',
    'Chat',
    'LoginWnd',
    'WxParam',
    'authenticate',
]
