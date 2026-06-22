"""按内容类型划分的消息类。

内容类消息继承 HumanMessage 以具备点击/转发/引用等能力；
媒体下载/OCR/语音转文字等在 Phase 3 完善，这里先留接口。
"""
import re
from pathlib import Path

from .base import BaseMessage, HumanMessage
from ..param import WxResponse
from ..utils.lock import uilock
from ..logger import wxlog


class TextMessage(HumanMessage):
    type = 'text'


class QuoteMessage(HumanMessage):
    type = 'quote'


class VoiceMessage(HumanMessage):
    type = 'voice'

    # 语音气泡 Name 形如 '语音7"秒'；点「语音转文字」后就地追加为 '语音7"秒<转换文本>'。
    # 时长可能是 'N"秒' 或 'M分S秒'，用非贪婪锚定避免误剥转换文本里的「秒」字。
    _PREFIX_RE = re.compile(r'^语音(?:\d+分)?\d+["\'″]?秒')

    def _cur_name(self) -> str:
        try:
            return self.control.Name or ''
        except Exception:
            return ''

    def _strip_prefix(self, name: str) -> str:
        return self._PREFIX_RE.sub('', name or '').strip()

    @uilock
    def to_text(self, timeout: int = 8) -> str:
        """语音转文字：右键→「语音转文字」，转换文本追加到气泡 Name，剥掉时长前缀返回。

        已转换过的语音直接返回缓存文本；失败返回空串。
        """
        import time
        from ..utils import uiabase
        if uiabase.is_locked():
            wxlog.warning('已锁屏，无法语音转文字')
            return ''
        existing = self._strip_prefix(self._cur_name())
        if existing:
            return existing
        menu = self._open_menu(2)
        if not menu:
            wxlog.warning('语音转文字：未弹出右键菜单')
            return ''
        if not menu.select('语音转文字'):
            menu.close()
            wxlog.warning('语音转文字：菜单无「语音转文字」项')
            return ''
        deadline = time.time() + timeout
        while time.time() < deadline:
            txt = self._strip_prefix(self._cur_name())
            if txt:
                return txt
            time.sleep(0.3)
        wxlog.warning('语音转文字：超时未获得转换文本')
        return ''


class ImageMessage(HumanMessage):
    type = 'image'

    @uilock
    def download(self):
        """打开大图查看器并点「保存」（4.x 保存到微信默认下载目录）。"""
        import time
        import uiautomation as auto
        from ..utils import uiabase
        if uiabase.is_locked():
            return WxResponse.failure('已锁屏')
        self._activate()
        pt = self._point()
        if pt:
            auto.Click(pt[0], pt[1])
        time.sleep(1.0)
        viewer = uiabase.find_window(classname='mmui::PreviewWindow', timeout=2)
        if viewer is None:
            return WxResponse.failure('未能打开图片查看器')
        uiabase.activate_window(viewer)
        save = uiabase.find(viewer, classname='mmui::XButton', name='保存', maxdepth=16)
        if save is None:
            return WxResponse.failure('未找到保存按钮')
        try:
            save.Click(simulateMove=False)
            time.sleep(0.6)
        finally:
            try:
                viewer.SendKeys('{Esc}')  # 关查看器（独立窗口，安全）
            except Exception:
                pass
        return WxResponse.success('已保存图片到微信默认下载目录')

    @uilock
    def ocr(self, timeout: int = 3):
        """提取图片中的文字。

        默认走微信界面「提取文字」（路线 B）；若用户设置了 WxParam.OCR_BACKEND，
        则下载图片后交给用户后端（如 PaddleOCR）。本库不依赖任何第三方 OCR。
        """
        from ..param import WxParam
        from ..ocr import OcrResult, ocr_via_wechat
        if WxParam.OCR_BACKEND:
            path = self.download()
            try:
                return OcrResult(WxParam.OCR_BACKEND(str(path)))
            except Exception as e:
                wxlog.error(f'OCR_BACKEND 调用失败: {e}')
                return OcrResult('')
        return ocr_via_wechat(self, timeout)


class VideoMessage(HumanMessage):
    type = 'video'

    @uilock
    def download(self, dir_path=None, timeout: int = 30):
        """下载视频：右键→「另存为...」。Name 不含文件名，沿用对话框默认名。"""
        return self._save_as(dir_path=dir_path, timeout=timeout)


class FileMessage(HumanMessage):
    type = 'file'

    @uilock
    def download(self, dir_path=None, force_click: bool = False, timeout: int = 30):
        """下载文件：右键→「另存为...」→系统文件框保存到 dir_path。"""
        return self._save_as(dir_path=dir_path, timeout=timeout)


class LocationMessage(HumanMessage):
    type = 'location'


class LinkMessage(HumanMessage):
    type = 'link'


class EmotionMessage(HumanMessage):
    type = 'emotion'


class MergeMessage(HumanMessage):
    type = 'merge'

    WND_CLS = 'mmui::RecordDetailWindow'

    def _open_record_window(self):
        """多候选点击气泡，打开「聊天记录」独立窗 mmui::RecordDetailWindow。"""
        import time
        from ..utils import uiabase
        win = uiabase.find_window(classname=self.WND_CLS, timeout=0.2)
        if win:
            return win
        self._activate()
        time.sleep(0.2)
        r = self.control.BoundingRectangle
        cy = (r.top + r.bottom) // 2
        w = r.right - r.left
        for frac in (0.5, 0.3, 0.7, 0.85):
            uiabase.click_at(r.left + int(w * frac), cy)
            time.sleep(0.9)
            win = uiabase.find_window(classname=self.WND_CLS, timeout=0.5)
            if win:
                return win
        return None

    @uilock
    def get_messages(self, close: bool = True):
        """打开合并转发记录窗，读取其中消息列表（复用主聊天的解析器，返回 Message 列表）。"""
        from ..utils import uiabase
        from .parse import parse_message
        if uiabase.is_locked():
            wxlog.warning('已锁屏，无法读取合并转发')
            return []
        win = self._open_record_window()
        if win is None:
            wxlog.warning('合并转发：未能打开聊天记录窗')
            return []
        try:
            lst = uiabase.find(win, classname='mmui::RecyclerListView', maxdepth=20, timeout=2)
            if lst is None:
                return []
            out = []
            for item in lst.GetChildren():
                try:
                    out.append(parse_message(item, parent=None, detect_direction=False))
                except Exception:
                    continue
            return out
        finally:
            if close:
                try:
                    btn = uiabase.find(win, classname='mmui::XButton', name='关闭', maxdepth=12)
                    if btn:
                        btn.Click(simulateMove=False)
                except Exception:
                    pass

    @uilock
    def get_content(self, close: bool = True):
        """返回合并转发里每条消息的文本列表（剔除空/系统项）。"""
        msgs = self.get_messages(close=close)
        return [m.content for m in msgs if (getattr(m, 'content', '') or '').strip()
                and getattr(m, 'type', None) != 'system']


class PersonalCardMessage(HumanMessage):
    type = 'personalcard'


class NoteMessage(HumanMessage):
    type = 'note'

    @uilock
    def get_content(self, wait: int = 0):
        wxlog.warning('NoteMessage.get_content 尚未实现（Phase 3）')
        return []

    @uilock
    def save_files(self, dir_path=None, wait: int = 3):
        wxlog.warning('NoteMessage.save_files 尚未实现（Phase 3）')
        return WxResponse.failure('未实现')

    @uilock
    def to_markdown(self, dir_path=None, wait: int = 3):
        wxlog.warning('NoteMessage.to_markdown 尚未实现（Phase 3）')
        return WxResponse.failure('未实现')


class OtherMessage(HumanMessage):
    type = 'other'
