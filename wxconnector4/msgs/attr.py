"""按归属划分的消息类：系统 / 好友 / 自己。

注意：parse_message 实际返回的是按内容分型的类（TextMessage/ImageMessage…），
仅把 attr 设为字符串 'friend'/'self'；下面的 FriendMessage/SelfMessage 不会被
直接实例化，发送人识别等能力统一放在 HumanMessage 上（见 base.py.sender_info）。
"""
from .base import BaseMessage, HumanMessage


class SystemMessage(BaseMessage):
    """系统/时间分隔消息。"""
    attr = 'system'
    type = 'system'

    def __init__(self, control, parent=None):
        super().__init__(control, parent)
        self.sender = 'SYS'


class FriendMessage(HumanMessage):
    """好友发出的消息。sender_info 等能力继承自 HumanMessage。"""
    attr = 'friend'


class SelfMessage(HumanMessage):
    """自己发出的消息。"""
    attr = 'self'
