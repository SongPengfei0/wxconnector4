"""控件文案 / 正则表。

把界面文字、ClassName、AutomationId、正则集中于此，便于微信改版时统一维护。
内容来自我们自行 UIA 检查的结果（自行整理，非复制他处）。
"""

# 关键控件标识（ClassName / AutomationId）—— 4.x mmui 系
CTRL = {
    'main_window_cls': 'mmui::MainWindow',
    'sub_window_cls': 'mmui::ChatSingleWindow',
    'login_window_cls': 'mmui::LoginWindow',
    'main_tabbar_aid': 'MainView.main_tabbar',
    'search_field_cls': 'mmui::XSearchField',
    'search_edit_cls': 'mmui::XValidatorTextEdit',
    'session_list_aid': 'session_list',
    'session_cell_cls': 'mmui::ChatSessionCell',
    'session_item_aid_prefix': 'session_item_',
    'chat_message_page_aid': 'chat_message_page',
    'chat_name_label_aid_suffix': 'current_chat_name_label',
    'message_list_aid': 'chat_message_list',
    'input_field_aid': 'chat_input_field',
    'input_field_cls': 'mmui::ChatInputField',
    'send_button_name': '发送',
}

# 多语言文案表：key -> {语言: 文案}
_TEXTS = {
    '微信': {'cn': '微信', 'cn_t': '', 'en': 'WeChat'},
    '通讯录': {'cn': '通讯录', 'cn_t': '', 'en': 'Contacts'},
    '收藏': {'cn': '收藏', 'cn_t': '', 'en': 'Favorites'},
    '朋友圈': {'cn': '朋友圈', 'cn_t': '', 'en': 'Moments'},
    '搜索': {'cn': '搜索', 'cn_t': '', 'en': 'Search'},
    '会话': {'cn': '会话', 'cn_t': '', 'en': 'Sessions'},
    '消息': {'cn': '消息', 'cn_t': '', 'en': 'Messages'},
    '发送': {'cn': '发送', 'cn_t': '', 'en': 'Send'},
    '发送文件': {'cn': '发送文件', 'cn_t': '', 'en': 'Send File'},
    '文件传输助手': {'cn': '文件传输助手', 'cn_t': '', 'en': 'File Transfer'},
    '置顶': {'cn': '置顶', 'cn_t': '', 'en': 'Pin'},
    '最小化': {'cn': '最小化', 'cn_t': '', 'en': 'Minimize'},
    '最大化': {'cn': '最大化', 'cn_t': '', 'en': 'Maximize'},
    '关闭': {'cn': '关闭', 'cn_t': '', 'en': 'Close'},
}

# 消息内容标记
MESSAGE_TAGS = {
    'image': '[图片]', 'video': '[视频]', 'voice': '[语音]', 'music': '[音乐]',
    'location': '[位置]', 'link': '[链接]', 'file': '[文件]', 'card': '[名片]',
    'note': '[笔记]', 'channel': '[视频号]', 'emotion': '[动画表情]', 'merge': '[聊天记录]',
}

# 正则
RE = {
    'voice': r'^\[语音\]\d+秒(,未播放)?$',
    'quote': r'(^.+)\n引用.*?的消息 : (.+$)',
    'tickle': r'^.+拍了拍.+$',
    'session_count': r'\[(\d+)条\]',
}


def lang(key: str, language: str = 'cn') -> str:
    """取某 key 在指定语言下的文案；缺省回退 key 本身。"""
    entry = _TEXTS.get(key)
    if not entry:
        return key
    return entry.get(language) or entry.get('cn') or key
