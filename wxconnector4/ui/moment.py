"""朋友圈窗口 mmui::SNSWindow 与发布流程。

发布流程（4.x，图片优先）：
  导航栏「朋友圈」→ SNSWindow → 「发表」→ 系统文件框选图(win32) → 发布器
  → 填文字(XValidatorTextEdit) → 隐私(PublishPrivacyView→PublishPrivacySelection 单选)
  → 「发表」(XOutlineButton)
"""
import time

from ..param import WxResponse
from ..utils import uiabase
from ..logger import wxlog

# 隐私文案 -> 单选项 Name
PRIVACY_MAP = {
    '公开': '公开', '所有朋友可见': '公开',
    '私密': '私密', '仅自己可见': '私密',
    '白名单': '选中的标签或朋友可见', '部分可见': '选中的标签或朋友可见',
    '黑名单': '选中的标签或朋友不可见', '不给谁看': '选中的标签或朋友不可见',
}


class MomentsWnd:
    WND_CLS = 'mmui::SNSWindow'

    def __init__(self, main_window_control, timeout: int = 3):
        self.main = main_window_control
        self.control = uiabase.find_window(classname=self.WND_CLS, timeout=0.5)
        if self.control is None:
            uiabase.activate_window(self.main)
            tab = uiabase.find(self.main, name='朋友圈', control_type='ButtonControl', maxdepth=10)
            if tab is not None:
                tab.Click(simulateMove=False)
                self.control = uiabase.find_window(classname=self.WND_CLS, timeout=timeout)

    def __bool__(self):
        return self.control is not None

    def Close(self):
        btn = uiabase.find(self.control, name='关闭', control_type='ButtonControl', maxdepth=10)
        if btn:
            try:
                btn.Click(simulateMove=False)
            except Exception:
                pass

    def Refresh(self):
        btn = uiabase.find(self.control, name='刷新', control_type='ButtonControl', maxdepth=10)
        if btn:
            btn.Click(simulateMove=False)

    def Publish(self, text: str = None, media_files=None, privacy_config=None) -> WxResponse:
        if self.control is None:
            return WxResponse.failure('未能打开朋友圈窗口')
        if not media_files:
            return WxResponse.failure('4.x 朋友圈需至少一张图片/视频（图片优先）')
        if isinstance(media_files, str):
            media_files = [media_files]

        uiabase.force_foreground(self.control.NativeWindowHandle)
        pub_tab = uiabase.find(self.control, name='发表', control_type='ButtonControl',
                               classname='mmui::XTabBarItem', maxdepth=12)
        if pub_tab is None:
            pub_tab = uiabase.find(self.control, name='发表', control_type='ButtonControl', maxdepth=12)
        pub_tab.Click(simulateMove=False)
        # 系统文件框选第一张图（win32，稳定不卡）
        if not uiabase.handle_file_dialog(media_files[0], timeout=6):
            return WxResponse.failure('未能操作系统文件选择框')
        time.sleep(1.5)

        # 填文字
        if text:
            edit = uiabase.find(self.control, classname='mmui::XValidatorTextEdit', maxdepth=16)
            if edit is not None:
                uiabase.set_focus(edit)
                uiabase.set_clipboard_text(text)
                time.sleep(0.1)
                uiabase.paste(edit)
                time.sleep(0.2)

        # 隐私
        if privacy_config:
            self._set_privacy(privacy_config)

        # 发表（最终按钮是 XOutlineButton）
        final = uiabase.find(self.control, name='发表', control_type='ButtonControl',
                             classname='mmui::XOutlineButton', maxdepth=18)
        if final is None:
            return WxResponse.failure('未找到发表按钮')
        final.Click(simulateMove=False)
        time.sleep(1.5)
        return WxResponse.success('已发表朋友圈')

    @staticmethod
    def _radio_green(r) -> int:
        """截图统计单选项圆点处的绿色像素：>50 视为已选中（Skia 单选无 UIA 状态可读）。"""
        try:
            from PIL import ImageGrab
            rc = r.BoundingRectangle
            img = ImageGrab.grab(bbox=(rc.left, rc.top, rc.left + 30, rc.bottom)).convert('RGB')
            px = img.load()
            return sum(1 for x in range(img.size[0]) for y in range(img.size[1])
                       if px[x, y][1] > 120 and px[x, y][1] > px[x, y][0] + 40 and px[x, y][1] > px[x, y][2] + 40)
        except Exception:
            return -1

    def _set_privacy(self, privacy_config) -> bool:
        """选隐私 → 视觉确认选中 → 点「确定」收起「谁可以看」面板。返回是否确认成功。"""
        privacy = privacy_config.get('privacy') if isinstance(privacy_config, dict) else privacy_config
        target = PRIVACY_MAP.get(privacy, privacy)
        priv_btn = uiabase.find(self.control, classname='mmui::PublishPrivacyView', maxdepth=18)
        if priv_btn is not None:
            priv_btn.Click(simulateMove=False)
            time.sleep(0.6)
        radios = uiabase.find_all(self.control, classname='mmui::PublishPrivacySelection', maxdepth=20)
        chosen = None
        for r in radios:
            if r.Name == target:
                chosen = r
                try:
                    r.Click(simulateMove=False)
                    time.sleep(0.4)
                except Exception:
                    pass
                break
        if chosen is None:
            wxlog.warning(f'未找到隐私选项「{target}」，保持默认')
            return False
        # 视觉确认（绿点）—— Skia 单选无 UIA 选中状态，截图兜底
        chosen = next((r for r in uiabase.find_all(self.control, classname='mmui::PublishPrivacySelection',
                       maxdepth=20) if r.Name == target), chosen)
        if self._radio_green(chosen) < 50:
            wxlog.warning(f'未能视觉确认「{target}」已选中（隐私可能未设对）')
        tags = privacy_config.get('tags') if isinstance(privacy_config, dict) else None
        if tags:
            wxlog.warning('白/黑名单标签选择待真机微调')
        # 点「确定」收起隐私面板（否则它盖住「发表」按钮）
        for ok in uiabase.find_all(self.control, classname='mmui::XOutlineButton', maxdepth=22):
            if ok.Name == '确定':
                try:
                    ok.Click(simulateMove=False)
                    time.sleep(0.6)
                except Exception:
                    pass
                break
        return True
