from .base import Message, BaseMessage, HumanMessage, NotExistsMessage
from .attr import SystemMessage, FriendMessage, SelfMessage
from .types import (
    TextMessage, QuoteMessage, VoiceMessage, ImageMessage, VideoMessage,
    FileMessage, LocationMessage, LinkMessage, EmotionMessage, MergeMessage,
    PersonalCardMessage, NoteMessage, OtherMessage,
)
from .parse import parse_message
