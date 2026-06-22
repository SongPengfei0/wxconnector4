"""按归属划分的消息类：系统 / 好友 / 自己。"""
from .base import BaseMessage, HumanMessage
from ..param import WxResponse
from ..utils.lock import uilock
from ..logger import wxlog


class SystemMessage(BaseMessage):
    """系统/时间分隔消息。"""
    attr = 'system'
    type = 'system'

    def __init__(self, control, parent=None):
        super().__init__(control, parent)
        self.sender = 'SYS'


class FriendMessage(HumanMessage):
    attr = 'friend'

    @uilock
    def sender_info(self) -> dict:
        wxlog.warning('FriendMessage.sender_info 尚未实现（Phase 3）')
        return {}


class SelfMessage(HumanMessage):
    attr = 'self'
