"""控件 → 消息对象 的分类器。

依据 ClassName + Name 标记判定消息类型；方向(自/他)用截图对齐判断(best-effort)。
"""
import re

from .attr import SystemMessage
from .types import (
    TextMessage, QuoteMessage, VoiceMessage, ImageMessage, VideoMessage,
    FileMessage, LocationMessage, LinkMessage, EmotionMessage, MergeMessage,
    PersonalCardMessage, NoteMessage, OtherMessage,
)
from ..languages import RE

# 内容标记 -> 类型类。4.x 气泡 Name = 裸词前缀 + 附加信息（'视频 0:04' / '文件\n名.pdf'
# / '聊天记录群聊...'），故按前缀匹配。注意「视频号」必须排在「视频」前（前缀包含）。
_TAG_MAP = [
    ('视频号', LinkMessage),
    ('图片', ImageMessage),
    ('视频', VideoMessage),
    ('语音', VoiceMessage),
    ('文件', FileMessage),
    ('链接', LinkMessage),
    ('位置', LocationMessage),
    ('名片', PersonalCardMessage),
    ('笔记', NoteMessage),
    ('动画表情', EmotionMessage),
    ('聊天记录', MergeMessage),
]

_RE_QUOTE = re.compile(RE['quote'], re.S)


def _detect_direction(control):
    """截图判断气泡左/右对齐：左=friend，右=self。失败返回 None。"""
    try:
        from PIL import ImageGrab
        r = control.BoundingRectangle
        left, top, right, bottom = r.left, r.top, r.right, r.bottom
        w, h = right - left, bottom - top
        if w <= 10 or h <= 10:
            return None
        img = ImageGrab.grab(bbox=(left, top, right, bottom)).convert('L')
        px = img.load()
        bg = px[w // 2, 1]  # 顶部中间通常是空白背景
        ys = list(range(max(1, h // 4), max(2, h * 3 // 4), max(1, h // 20)))
        left_c = right_c = 0
        for x in range(0, w, 3):
            for y in ys:
                if abs(px[x, y] - bg) > 25:
                    if x < w * 0.5:
                        left_c += 1
                    else:
                        right_c += 1
                    break
        if left_c == 0 and right_c == 0:
            return None
        return 'self' if right_c > left_c else 'friend'
    except Exception:
        return None


def _pick_type_cls(cls_name: str, name: str):
    # 语音有专属控件类，最稳，优先判定（4.x Name 形如 '语音7"秒'，无方括号）
    if cls_name.endswith('ChatVoiceItemView'):
        return VoiceMessage
    # 文本是独立控件类，不会与媒体标签混淆；先认引用再认纯文本
    if cls_name.endswith('ChatTextItemView'):
        return QuoteMessage if _RE_QUOTE.search(name) else TextMessage
    # 其余为气泡类（ChatBubbleItemView / ChatBubbleReferItemView 等），按 Name 前缀分流。
    # 文本已被上面拦截，故前缀匹配不会误伤正文。
    for tag, klass in _TAG_MAP:
        if name == tag or name.startswith(tag) or name.startswith(f'[{tag}]'):
            return klass
    # 无可辨标记：小程序/卡片等
    return OtherMessage


def parse_message(control, parent=None, detect_direction: bool = True):
    """把一个消息列表项控件解析为 Message 对象。"""
    try:
        cls_name = control.ClassName or ''
        name = control.Name or ''
    except Exception:
        return SystemMessage(control, parent)

    # 时间分隔 / 系统通知
    if cls_name.endswith('ChatItemView'):
        return SystemMessage(control, parent)

    klass = _pick_type_cls(cls_name, name)
    msg = klass(control, parent)

    # 方向 / 归属
    direction = _detect_direction(control) if detect_direction else None
    if direction:
        msg.direction = direction
        msg.attr = direction  # 'self' / 'friend'
    return msg
