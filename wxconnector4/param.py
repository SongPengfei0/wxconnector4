"""全局参数 WxParam 与统一返回结构 WxResponse。

集中管理所有可调参数与默认值。
"""
from typing import Literal
import os

PROJECT_NAME = 'wxconnector4'
VERSION = '0.1.0'

# 微信默认表情名（公开符号，用于文本里识别 [xxx] 表情）
DEFAULT_STICKERS = [
    '[微笑]', '[撇嘴]', '[色]', '[发呆]', '[得意]', '[流泪]', '[害羞]', '[闭嘴]', '[睡]', '[大哭]',
    '[尴尬]', '[发怒]', '[调皮]', '[呲牙]', '[惊讶]', '[难过]', '[囧]', '[抓狂]', '[吐]', '[偷笑]',
    '[愉快]', '[白眼]', '[傲慢]', '[困]', '[惊恐]', '[憨笑]', '[悠闲]', '[咒骂]', '[疑问]', '[嘘]',
    '[晕]', '[衰]', '[骷髅]', '[敲打]', '[再见]', '[擦汗]', '[抠鼻]', '[鼓掌]', '[坏笑]', '[右哼哼]',
    '[捂脸]', '[奸笑]', '[机智]', '[皱眉]', '[耶]', '[吃瓜]', '[加油]', '[汗]', '[天啊]', '[社会社会]',
    '[旺柴]', '[好的]', '[打脸]', '[哇]', '[翻白眼]', '[666]', '[让我看看]', '[叹气]', '[苦涩]', '[裂开]',
    '[爱心]', '[强]', '[弱]', '[握手]', '[胜利]', '[抱拳]', '[OK]', '[合十]', '[玫瑰]', '[庆祝]',
    '[红包]', '[发]', '[福]',
]


class WxParam:
    # 语言设置
    LANGUAGE: Literal['cn', 'cn_t', 'en'] = 'cn'

    # 是否启用日志文件
    ENABLE_FILE_LOGGER: bool = True

    # 下载文件/图片默认保存路径
    DEFAULT_SAVE_PATH: str = os.path.join(os.getcwd(), 'wxconnector文件下载')

    # 是否启用消息哈希值用于辅助判断消息
    MESSAGE_HASH: bool = False

    # 头像到消息 X/Y 偏移量，用于消息定位、点击等
    DEFAULT_MESSAGE_XBIAS: int = 51
    DEFAULT_MESSAGE_YBIAS: int = 30

    # 是否每次启动强制重新自动获取 X 偏移量
    FORCE_MESSAGE_XBIAS: bool = False

    # 监听消息时间间隔，单位秒
    LISTEN_INTERVAL: int = 1

    # 监听执行器线程池大小
    LISTENER_EXCUTOR_WORKERS: int = 4

    # 搜索聊天对象超时时间，单位秒
    SEARCH_CHAT_TIMEOUT: int = 2

    # 微信笔记加载超时时间，单位秒
    NOTE_LOAD_TIMEOUT: int = 30

    # 发送文件超时时间，单位秒
    SEND_FILE_TIMEOUT: int = 10

    # 监听/读取窗口尺寸，越大越好（4.x 虚拟列表，可见才注册控件）
    CHAT_WINDOW_SIZE = (1200, 6000)

    # 输入内容相似度阈值，达到即通过校验才触发发送
    SEND_CONTENT_RATIO: float = 0.9

    # GetNextNewMessage 最大获取数量
    GET_NEXT_MAX_QUANTITY: int = 30

    # GetNextNewMessage 最长获取时间，单位秒
    GET_NEXT_MAX_RUNTIME: int = 10

    # 特殊聊天会话名
    SPECIAL_SESSION_NAME = ['公众号', '折叠的聊天', 'QQ邮箱提醒', '服务号']

    # 默认聊天表情
    DEFAULT_STICKERS = DEFAULT_STICKERS

    # OCR 后端（可插拔）：
    #   None  -> 默认走微信界面「提取文字」(零依赖、不逆向)
    #   可调用 -> 签名 (image_path: str) -> str，用户可接入自己的 PaddleOCR 等高精度引擎
    # 本库本身不依赖任何第三方 OCR，保持轻量低耦合。
    OCR_BACKEND = None

    # 回调函数结束标识
    CALLBACK_STOP_SIGN = 'stop'

    # @成员输入间隔时间，单位秒
    INPUT_AT_INTERVAL: float = 0.5

    # 音频输入配置（SendAudio 用，需虚拟声卡）
    AUDIO_PARAM = {
        "device_keyword": "CABLE Input",
        "device_id": None,
        "samplerate": None,
        "channels": None,
        "block_frames": 1024,
        "latency": "high",
        "ffmpeg_path": None,
        "ffprobe_path": None,
    }


class WxResponse(dict):
    """统一返回结构：成功/失败/错误三态，可直接当 bool 判断。"""

    def __init__(self, status: str, message: str, data: dict = None):
        super().__init__(status=status, message=message, data=data)

    def __str__(self):
        return str(self.to_dict())

    def __repr__(self):
        return str(self.to_dict())

    def to_dict(self):
        return {
            'status': self['status'],
            'message': self['message'],
            'data': self['data'],
        }

    def __bool__(self):
        return self.is_success

    @property
    def is_success(self):
        return self['status'] == '成功'

    @classmethod
    def success(cls, message=None, data: dict = None):
        return cls(status="成功", message=message, data=data)

    @classmethod
    def failure(cls, message: str, data: dict = None):
        return cls(status="失败", message=message, data=data)

    @classmethod
    def error(cls, message: str, data: dict = None):
        return cls(status="错误", message=message, data=data)
