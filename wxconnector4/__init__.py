"""wxconnector4 —— 独立、免授权的微信 4.x 自动化库。

基于公开的 Windows UI Automation 实现，无任何授权/许可校验。
"""
from .wx import WeChat, Chat, Listener
from .ui.main import WeChatLoginWnd as LoginWnd
from .ui.sessionbox import SessionElement
from .param import WxParam, WxResponse
from .utils.auth import authenticate
from .msgs import (
    Message, BaseMessage, HumanMessage, NotExistsMessage,
    SystemMessage, FriendMessage, SelfMessage,
    TextMessage, QuoteMessage, VoiceMessage, ImageMessage, VideoMessage,
    FileMessage, LocationMessage, LinkMessage, EmotionMessage, MergeMessage,
    PersonalCardMessage, NoteMessage, OtherMessage,
)

__version__ = '0.1.0'

__all__ = [
    # ---- 入口 ----
    'WeChat',
    'Chat',
    'LoginWnd',
    # ---- 参数 / 统一返回结构 ----
    'WxParam',
    'WxResponse',
    'authenticate',
    # ---- 会话 ----
    'SessionElement',
    # ---- 消息类型（isinstance 判别后调用各自的专属方法/属性）----
    'Message',
    'BaseMessage',
    'HumanMessage',
    'NotExistsMessage',
    'SystemMessage',
    'FriendMessage',
    'SelfMessage',
    'TextMessage',
    'QuoteMessage',
    'VoiceMessage',
    'ImageMessage',
    'VideoMessage',
    'FileMessage',
    'LocationMessage',
    'LinkMessage',
    'EmotionMessage',
    'MergeMessage',
    'PersonalCardMessage',
    'NoteMessage',
    'OtherMessage',
]
