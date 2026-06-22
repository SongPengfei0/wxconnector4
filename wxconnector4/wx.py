"""公开门面：WeChat / Chat / Listener。

微信 4.x 自动化主接口。Phase 0：连接/账号；Phase 1：收发/切换会话。
"""
import time
import threading
from abc import ABC
from concurrent.futures import ThreadPoolExecutor

from .param import WxParam, WxResponse
from .logger import wxlog
from .ui.main import WeChatMainWnd, WeChatSubWnd, WeChatLoginWnd
from .ui.chatbox import ChatBox
from .ui.sessionbox import SessionBox
from .utils import uiabase
from .utils.lock import uilock


class Listener(ABC):
    """监听能力基类（Phase 2 实现）。"""
    pass


class Chat:
    """单个聊天窗口的操作门面。"""

    def __init__(self, core=None):
        self.core = core
        self.ChatBox = ChatBox(core.control, self) if core is not None else None
        self.who = getattr(core, 'nickname', None)

    def __repr__(self):
        return f"<wxconnector4 Chat: {self.who}>"

    def __add__(self, other):
        return str(self) + str(other)

    def __radd__(self, other):
        return str(other) + str(self)

    def Show(self) -> None:
        if self.core is not None:
            self.core._show()

    def ChatInfo(self) -> dict:
        return self.ChatBox.get_info() if self.ChatBox else {}

    def EditFriendInfo(self, add_tags=None, remove_tags=None, remark: str = None,
                       tag_wait: float = 0.2) -> WxResponse:
        wxlog.warning('EditFriendInfo 代码实装待真机微调（好友资料→设置备注和标签）')
        return WxResponse.failure('待真机微调')

    def GetDialog(self, wait: int = 3):
        from .ui.component import WeChatDialog
        return WeChatDialog(getattr(self.core, 'control', None), wait=wait)

    @uilock
    def SendMsg(self, msg: str, who: str = None, clear: bool = True,
                at=None, exact: bool = False) -> WxResponse:
        if at:
            wxlog.warning('@ 功能尚未实现（Phase 1.5），将仅发送文本')
        return self.ChatBox.send_text(msg, clear=clear)

    @uilock
    def SendFiles(self, filepath, who: str = None, exact: bool = False) -> WxResponse:
        return self.ChatBox.send_file(filepath)

    @uilock
    def AtAll(self, msg: str, who: str = None, exact: bool = False) -> WxResponse:
        """群内 @所有人 并发送 msg（独立窗口场景，不切换会话）。"""
        return self.ChatBox.at_all(msg)

    @uilock
    def SendAudio(self, filepath: str, duration: int = None, start: int = 0,
                  who: str = None, exact: bool = False) -> WxResponse:
        wxlog.warning('SendAudio 暂未实现：需安装 VB-CABLE 虚拟声卡并将微信麦克风设为 CABLE Output')
        return WxResponse.failure('SendAudio 暂未实现（需 VB-CABLE 虚拟声卡）')

    def GetAllMessage(self):
        return self.ChatBox.get_msgs() if self.ChatBox else []

    def GetNewMessage(self):
        return self.ChatBox.get_new_msgs() if self.ChatBox else []

    def Close(self) -> None:
        if self.core is not None:
            self.core.close()


class WeChat(Chat, Listener):
    """微信主入口。"""

    def __init__(self, nickname: str = None, start_listener: bool = False,
                 debug: bool = False, resize: bool = True,
                 version: str = '微信', **kwargs):
        wxlog.set_debug(debug)
        self.core = WeChatMainWnd(nickname)
        self.ChatBox = ChatBox(self.core.control, self)
        self.SessionBox = SessionBox(self.core.control, self)
        self.NavigationBox = None  # Phase 3

        if resize:
            try:
                self.core._show()
            except Exception:
                pass

        self.myinfo = self.GetMyInfo()
        self.nickname = self.myinfo.get('nickname') or nickname
        self.who = self.ChatBox.who

        # 监听状态
        self.listen = {}                       # nickname -> Chat(子窗口)
        self._listener_stop = threading.Event()
        self._listener_thread = None
        self._executor = None

        wxlog.info(f'已连接微信主窗口（PID={self.core.pid}，当前会话={self.who}）')

        if start_listener:
            self.StartListening()

    # ---------- 账号 / 状态 ----------
    def GetMyInfo(self) -> dict:
        return self.core.get_my_info()

    def IsOnline(self) -> bool:
        return self.core.is_online()

    @property
    def path(self):
        return self.core.path

    @property
    def dir(self):
        return self.core.dir

    def KeepRunning(self) -> None:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            wxlog.info('KeepRunning 已退出')

    def ShutDown(self):
        try:
            import psutil
            psutil.Process(self.core.pid).terminate()
            return WxResponse.success('已结束微信进程')
        except Exception as e:
            return WxResponse.error(f'结束进程失败: {e}')

    # ---------- 会话切换 ----------
    @uilock
    def ChatWith(self, who: str, exact: bool = True, force: bool = False,
                 force_wait=0.5) -> WxResponse:
        if uiabase.is_locked():
            return WxResponse.error('工作站已锁屏，无法切换会话；请先解锁屏幕')
        if force:
            res = self.SessionBox.switch_chat(who, exact=exact, force=True, force_wait=force_wait)
            time.sleep(0.2)
            self.who = self.ChatBox.who
            return res
        # 带校验重试，避免前台时序导致切换落空
        ok = self._ensure_chat(who, exact, max_retries=3)
        self.who = self.ChatBox.who
        return WxResponse.success('已切换会话', data={'who': who}) if ok \
            else WxResponse.failure(f'切换到「{who}」失败')

    def GetSession(self):
        return self.SessionBox.get_session()

    def ChatInfo(self) -> dict:
        return self.ChatBox.get_info()

    # ---------- 发送（主窗口支持 who 切换 + 重试防发错） ----------
    @uilock
    def SendMsg(self, msg: str, who: str = None, clear: bool = True,
                at=None, exact: bool = False, max_retries: int = 3) -> WxResponse:
        if who and not self._ensure_chat(who, exact, max_retries):
            return WxResponse.failure(f'切换到「{who}」失败，未发送')
        if at:
            wxlog.warning('@ 功能尚未实现（Phase 1.5），将仅发送文本')
        return self.ChatBox.send_text(msg, clear=clear)

    @uilock
    def SendFiles(self, filepath, who: str = None, exact: bool = False,
                  max_retries: int = 3) -> WxResponse:
        if who and not self._ensure_chat(who, exact, max_retries):
            return WxResponse.failure(f'切换到「{who}」失败，未发送')
        return self.ChatBox.send_file(filepath)

    @uilock
    def AtAll(self, msg: str, who: str = None, exact: bool = False,
              max_retries: int = 3) -> WxResponse:
        """群内 @所有人 并发送 msg。who 指定则先切到该群（会通知全体成员）。"""
        if who and not self._ensure_chat(who, exact, max_retries):
            return WxResponse.failure(f'切换到「{who}」失败，未发送')
        return self.ChatBox.at_all(msg)

    def _ensure_chat(self, who: str, exact: bool, max_retries: int) -> bool:
        """切换到目标会话并校验当前会话名，避免发错对象。"""
        for _ in range(max_retries):
            self.SessionBox.switch_chat(who, exact=exact)
            time.sleep(0.2)
            cur = self.ChatBox.who or ''
            if (exact and cur == who) or (not exact and who in cur):
                self.who = cur
                return True
        return False

    # ---------- 群管理 ----------
    @uilock
    def CreateGroup(self, contacts) -> WxResponse:
        """发起群聊。contacts 为联系人名列表（至少 2 个）。会通知被拉入的联系人。"""
        if uiabase.is_locked():
            return WxResponse.error('已锁屏')
        if not contacts or len(contacts) < 2:
            return WxResponse.failure('建群至少需要 2 个联系人')
        root = self.core.control
        uiabase.force_foreground(root.NativeWindowHandle)
        chat = uiabase.find(root, name='微信', control_type='ButtonControl', maxdepth=10)
        if chat is not None:
            chat.Click(simulateMove=False)
            time.sleep(0.6)
        # 快捷操作 → 发起群聊（带重试）
        item = None
        for _ in range(4):
            qa = uiabase.find(root, name='快捷操作', control_type='ButtonControl', maxdepth=12)
            if qa is None:
                break
            qa.Click(simulateMove=False)
            time.sleep(0.9)
            item = uiabase.find(root, name='发起群聊', maxdepth=20)
            if item is not None:
                break
        if item is None:
            return WxResponse.failure('未找到「发起群聊」入口')
        item.Click(simulateMove=False)
        time.sleep(1.5)
        # 逐个搜索并勾选联系人
        chosen = []
        for c in contacts:
            se = uiabase.find(root, classname='mmui::XValidatorTextEdit', name='搜索', maxdepth=24)
            if se is None:
                se = uiabase.find(root, classname='mmui::XValidatorTextEdit', maxdepth=24)
            if se is not None:
                uiabase.set_focus(se)
                uiabase.clear_edit(se)
                time.sleep(0.1)
                se.SendKeys(c, interval=0.03)
                time.sleep(0.8)
            cell = None
            for cand in uiabase.find_all(root, classname='mmui::SearchContactCellView', maxdepth=24):
                if c in (cand.Name or ''):
                    cell = cand
                    break
            if cell is not None:
                try:
                    cell.Click(simulateMove=False)
                    chosen.append(c)
                    time.sleep(0.2)
                except Exception:
                    pass
        if len(chosen) < 2:
            return WxResponse.failure(f'仅勾选到 {chosen}，不足 2 人，未建群')
        done = uiabase.find(root, name='完成', control_type='ButtonControl',
                            classname='mmui::XOutlineButton', maxdepth=24)
        if done is None:
            return WxResponse.failure('未找到「完成」按钮')
        done.Click(simulateMove=False)
        time.sleep(2.0)
        return WxResponse.success('已发起群聊', data={'members': chosen})

    def GetAllRecentGroups(self, speed: int = 1, interval: float = 0.1):
        """从会话列表筛出群聊（名称含「群」标志的会话）。"""
        return [(s.name, s.content) for s in self.GetSession() if '群' in (s.name or '')]

    # ---------- 好友管理 ----------
    @uilock
    def AddNewFriend(self, keywords: str, addmsg: str = None, remark: str = None,
                     tags=None, permission: str = '朋友圈') -> WxResponse:
        """搜索并添加好友。keywords 可为手机号/微信号/QQ号。

        流程：主搜索框搜 → 「网络查找手机/QQ号」→ AddFriendWindow「添加到通讯录」
        → VerifyFriendWindow 填申请语/备注/权限 → 「确定」发送。
        """
        if uiabase.is_locked():
            return WxResponse.error('已锁屏')
        root = self.core.control
        uiabase.force_foreground(root.NativeWindowHandle)
        # 1) 搜索
        edit = uiabase.find(root, classname='mmui::XValidatorTextEdit', maxdepth=20)
        if edit is None:
            return WxResponse.failure('未找到搜索框')
        uiabase.set_focus(edit)
        uiabase.clear_edit(edit)
        time.sleep(0.2)
        edit.SendKeys(keywords, interval=0.03)
        time.sleep(1.5)
        # 2) 点「网络查找手机/QQ号」
        cell = uiabase.find(root, name_contains='网络查找', maxdepth=22)
        if cell is None:
            return WxResponse.failure('未出现「网络查找」结果，检查关键词')
        cell.Click(simulateMove=False)
        time.sleep(2.5)
        # 3) AddFriendWindow → 添加到通讯录
        afw = uiabase.find_window(classname='mmui::AddFriendWindow', timeout=3)
        if afw is None:
            return WxResponse.failure('未找到该账号')
        uiabase.force_foreground(afw.NativeWindowHandle)
        addbtn = uiabase.find(afw, name='添加到通讯录', control_type='ButtonControl', maxdepth=16)
        if addbtn is None:
            return WxResponse.failure('该账号无「添加到通讯录」（可能已是好友/被限制）')
        addbtn.Click(simulateMove=False)
        time.sleep(2.0)
        # 4) VerifyFriendWindow → 填表单
        vfw = uiabase.find_window(classname='mmui::VerifyFriendWindow', timeout=3)
        if vfw is None:
            return WxResponse.failure('未弹出申请表单')
        uiabase.force_foreground(vfw.NativeWindowHandle)
        if addmsg:
            me = uiabase.find(vfw, classname='mmui::XValidatorTextEdit', maxdepth=16)
            if me is not None:
                uiabase.set_focus(me); uiabase.clear_edit(me)
                uiabase.set_clipboard_text(addmsg); time.sleep(0.1); uiabase.paste(me)
                time.sleep(0.2)
        if remark:
            re = uiabase.find(vfw, classname='mmui::XLineEdit', maxdepth=16)
            if re is not None:
                uiabase.set_focus(re); uiabase.clear_edit(re)
                uiabase.set_clipboard_text(remark); time.sleep(0.1); uiabase.paste(re)
                time.sleep(0.2)
        if permission == '仅聊天':
            opt = uiabase.find(vfw, name='仅聊天', maxdepth=16)
            if opt is not None:
                try:
                    opt.Click(simulateMove=False)
                except Exception:
                    pass
        if tags:
            wxlog.warning('好友标签选择待真机微调，本次忽略')
        # 5) 确定 发送
        ok = uiabase.find(vfw, name='确定', control_type='ButtonControl', maxdepth=16)
        if ok is None:
            return WxResponse.failure('未找到「确定」按钮')
        ok.Click(simulateMove=False)
        time.sleep(1.5)
        return WxResponse.success('已发送好友申请', data={'keywords': keywords})

    def _open_contact_profile(self, friend: str) -> bool:
        """切到通讯录，用搜索框定位好友并打开资料区。

        通讯录是虚拟列表、滚动定位不稳定，改走：通讯录搜索框输入好友名 →
        点搜索结果浮层里精确匹配的 mmui::XTableCell → 直接进资料页(ContactProfileView)。
        注意：好友若设过备注，搜索结果显示名是备注，friend 需传当前显示名。
        """
        root = self.core.control
        uiabase.force_foreground(root.NativeWindowHandle)
        tab = uiabase.find(root, name='通讯录', control_type='ButtonControl', maxdepth=10)
        if tab is not None:
            tab.Click(simulateMove=False)
            time.sleep(1.0)
        se = uiabase.find(root, classname='mmui::XValidatorTextEdit', name='搜索', maxdepth=24)
        if se is None:
            return False
        uiabase.set_focus(se)
        uiabase.clear_edit(se)
        uiabase.set_clipboard_text(friend)
        time.sleep(0.1)
        se.SendKeys('{Ctrl}v')
        time.sleep(1.0)
        target = None
        for c in uiabase.find_all(root, classname='mmui::XTableCell', maxdepth=30):
            if (c.Name or '') == friend:
                target = c
                break
        if target is None:
            return False
        for _ in range(3):
            target.Click(simulateMove=False)
            time.sleep(1.0)
            if uiabase.find(root, name_contains='微信号', maxdepth=24):
                return True
        return False

    @uilock
    def EditFriendInfo(self, add_tags=None, remove_tags=None, remark: str = None,
                       tag_wait: float = 0.2) -> WxResponse:
        """修改好友备注（作用于当前会话好友 self.who）。

        路径：通讯录搜索定位好友 → 资料区「更多」→「设置备注和标签」→
        ProfileFormEditorView 备注框 → 完成。

        add_tags/remove_tags 参数保留以兼容接口，但**不实现**——4.x 资料
        面板的标签编辑入口定位极不稳定（同群属性方法），传入会被忽略并告警。
        """
        if remark is None:
            if add_tags or remove_tags:
                return WxResponse.failure('标签编辑在微信4.x 不稳定，wxconnector4 不支持；本方法仅改 remark')
            return WxResponse.failure('remark 不能为 None')
        if add_tags or remove_tags:
            wxlog.warning('add_tags/remove_tags 在微信4.x 资料面板定位不稳定，已忽略；仅处理 remark')
        if uiabase.is_locked():
            return WxResponse.error('已锁屏')
        friend = self.who or (self.ChatBox.who if self.ChatBox else None)
        if not friend:
            return WxResponse.failure('未确定要修改的好友（先 ChatWith 该好友）')
        if not self._open_contact_profile(friend):
            return WxResponse.failure(f'通讯录中未找到/未打开好友「{friend}」资料')
        root = self.core.control
        prof = uiabase.find(root, classname='mmui::ContactProfileView', maxdepth=30) or root
        more = uiabase.find(prof, name='更多', control_type='ButtonControl', maxdepth=16)
        if more is None:
            return WxResponse.failure('未找到资料区「更多」按钮')
        more.Click(simulateMove=False)
        time.sleep(0.8)
        item = uiabase.find(uiabase.get_root(), name='设置备注和标签', maxdepth=20)
        if item is None:
            return WxResponse.failure('菜单中无「设置备注和标签」')
        item.Click(simulateMove=False)
        time.sleep(1.0)
        panel = uiabase.find(root, classname='mmui::ProfileFormEditorView', maxdepth=24)
        if panel is None:
            return WxResponse.failure('未弹出设置备注和标签面板')
        rm = uiabase.find(panel, classname='mmui::XLineEdit', maxdepth=14)
        if rm is not None:
            uiabase.set_focus(rm)
            rm.SendKeys('{Ctrl}a{Delete}')
            if remark:
                uiabase.set_clipboard_text(remark)
                time.sleep(0.1)
                rm.SendKeys('{Ctrl}v')
            time.sleep(0.2)
        # 完成（按钮在面板外层，扩大到整窗搜索 XOutlineButton）
        done = (uiabase.find(panel, name='完成', control_type='ButtonControl', maxdepth=16)
                or uiabase.find(root, name='完成', control_type='ButtonControl', maxdepth=30))
        if done is None:
            return WxResponse.failure('未找到「完成」按钮')
        done.Click(simulateMove=False)
        time.sleep(0.8)
        return WxResponse.success('已修改好友备注', data={'friend': friend, 'remark': remark})

    def _read_contact_profile(self) -> dict:
        """读取当前联系人资料区（通讯录点开后右侧 ContactProfileView）。"""
        root = self.core.control
        prof = uiabase.find(root, classname='mmui::ContactProfileView', maxdepth=30) or root
        texts = uiabase.find_all(prof, control_type='TextControl', maxdepth=20)
        info = {}
        head = uiabase.find(prof, classname='mmui::ContactHeadView', maxdepth=14)
        if head is not None:
            info['nickname'] = head.Name
        values = [(t.BoundingRectangle.top, (t.Name or '').strip())
                  for t in texts if t.ClassName == 'mmui::ContactProfileTextView' and (t.Name or '').strip()]
        LABELMAP = {'微信号': 'wxid', '地区': 'region', '个性签名': 'signature',
                    '来源': 'source', '备注': 'remark', '昵称': 'nickname'}
        for t in texts:
            if t.ClassName == 'mmui::XTextView':
                lname = (t.Name or '').strip().rstrip('：')
                if lname in LABELMAP:
                    ly = t.BoundingRectangle.top
                    near = min(values, key=lambda v: abs(v[0] - ly)) if values else None
                    if near and abs(near[0] - ly) < 12:
                        info[LABELMAP[lname]] = near[1]
        return info

    def GetFriendDetails(self, n: int = None, timeout: int = 0xFFFFF, save_head_image: bool = False,
                         save_head_wait: int = 0, interval: int = 0, callback=None,
                         speed: int = 3, max_repeat: int = 10):
        """遍历通讯录读取好友详情（昵称/微信号/地区/个性签名/来源/备注）。只读。"""
        if uiabase.is_locked():
            return []
        root = self.core.control
        uiabase.force_foreground(root.NativeWindowHandle)
        tab = uiabase.find(root, name='通讯录', control_type='ButtonControl', maxdepth=10)
        if tab is not None:
            tab.Click(simulateMove=False)
            time.sleep(1.0)
        SKIP = ['新的朋友', '群聊', '公众号', '企业号', '通讯录管理', '标签', '文件传输助手', '服务号']
        cells = uiabase.find_all(root, classname='mmui::ContactsCellItemView', maxdepth=30)
        friends = [c for c in cells if (c.Name or '') and not any(k in c.Name for k in SKIP)]
        if n:
            friends = friends[:n]
        results = []
        for c in friends:
            try:
                c.Click(simulateMove=False)
                time.sleep(0.3 + interval)
                d = self._read_contact_profile()
                d.setdefault('nickname', c.Name)
                results.append(d)
                if callback is not None:
                    try:
                        if callback(d) is False:
                            break
                    except Exception as e:
                        wxlog.error(f'GetFriendDetails 回调异常: {e}')
            except Exception as e:
                wxlog.debug(f'读取好友 {c.Name} 详情失败: {e}')
        return results

    def SendUrlCard(self, url: str, friends, message: str = None, timeout: int = 10) -> WxResponse:
        """发送链接。最简实现：直接发 URL（微信会自动渲染为链接）；卡片分享流程待真机微调。"""
        if isinstance(friends, str):
            friends = [friends]
        results = {}
        for f in friends:
            r = self.SendMsg(url if not message else f'{message}\n{url}', who=f)
            results[f] = r['status']
        return WxResponse.success('已发送链接', data=results)

    # ---------- 朋友圈 ----------
    def Moments(self, timeout: int = 3):
        """进入朋友圈，返回 MomentsWnd。"""
        from .ui.moment import MomentsWnd
        if uiabase.is_locked():
            return None
        wnd = MomentsWnd(self.core.control, timeout=timeout)
        return wnd if wnd else None

    @uilock
    def PublishMoment(self, text: str = None, media_files=None, privacy_config=None) -> WxResponse:
        """发布朋友圈（4.x 图片优先，需 media_files）。

        privacy_config 示例: {'privacy': '仅自己可见'} 或 {'privacy': '白名单', 'tags': [...]}
        """
        from .ui.moment import MomentsWnd
        if uiabase.is_locked():
            return WxResponse.error('已锁屏')
        wnd = MomentsWnd(self.core.control)
        if not wnd:
            return WxResponse.failure('未能打开朋友圈')
        return wnd.Publish(text=text, media_files=media_files, privacy_config=privacy_config)

    # ---------- 子窗口 ----------
    def GetSubWindow(self, nickname: str):
        win = self.SessionBox._find_sub_window(nickname)
        if win is None:
            return None
        return Chat(core=WeChatSubWnd(control=win, root=self.core, nickname=nickname))

    def GetAllSubWindow(self):
        from .languages import CTRL
        out = []
        for w in uiabase.find_windows(classname=CTRL['sub_window_cls']):
            lbl = uiabase.find(w, aid_suffix=CTRL['chat_name_label_aid_suffix'], maxdepth=40)
            nick = lbl.Name if lbl else None
            out.append(Chat(core=WeChatSubWnd(control=w, root=self.core, nickname=nick)))
        return out

    # ---------- 监听 ----------
    @uilock
    def AddListenChat(self, nickname: str, callback) -> WxResponse:
        """把某会话独立成子窗口并加入监听；新消息触发 callback(msg, chat)。"""
        if uiabase.is_locked():
            return WxResponse.error('工作站已锁屏，无法添加监听；请先解锁屏幕')
        if nickname in self.listen:
            return WxResponse.success('已在监听', data={'nickname': nickname})
        win = self.SessionBox.open_separate_window(nickname)
        if win is None:
            return WxResponse.failure(f'无法打开「{nickname}」独立窗口')
        sub = WeChatSubWnd(control=win, root=self.core, nickname=nickname)
        chat = Chat(core=sub)
        chat._callback = callback
        # 设定基线：把当前已有消息标记为已读，之后只回调新消息
        chat.ChatBox.get_new_msgs()
        self.listen[nickname] = chat
        wxlog.info(f'已添加监听：{nickname}')
        if self._listener_thread is None or not self._listener_thread.is_alive():
            self.StartListening()
        return WxResponse.success('添加监听成功', data={'nickname': nickname})

    @uilock
    def RemoveListenChat(self, nickname: str, close_window: bool = True) -> WxResponse:
        chat = self.listen.pop(nickname, None)
        if chat is None:
            return WxResponse.failure(f'「{nickname}」未在监听')
        if close_window:
            try:
                chat.core.close()
            except Exception:
                pass
        wxlog.info(f'已移除监听：{nickname}')
        return WxResponse.success('移除监听成功')

    def StartListening(self) -> None:
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=WxParam.LISTENER_EXCUTOR_WORKERS)
        self._listener_stop.clear()
        if self._listener_thread is None or not self._listener_thread.is_alive():
            self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._listener_thread.start()
            wxlog.info('监听线程已启动')

    def StopListening(self, remove: bool = True) -> None:
        self._listener_stop.set()
        if self._listener_thread is not None:
            self._listener_thread.join(timeout=WxParam.LISTEN_INTERVAL + 2)
        if remove:
            for nick in list(self.listen):
                self.RemoveListenChat(nick, close_window=False)
        wxlog.info('监听已停止')

    def _listen_loop(self):
        uiabase.ensure_com()  # 子线程使用 UIA 前初始化 COM
        while not self._listener_stop.is_set():
            if uiabase.is_locked():
                self._listener_stop.wait(WxParam.LISTEN_INTERVAL)
                continue
            for nickname, chat in list(self.listen.items()):
                try:
                    new = chat.GetNewMessage()
                    for m in new:
                        self._executor.submit(self._safe_callback, chat._callback, m, chat)
                except Exception as e:
                    wxlog.debug(f'监听 {nickname} 取新消息失败: {e}')
            self._listener_stop.wait(WxParam.LISTEN_INTERVAL)

    @staticmethod
    def _safe_callback(callback, msg, chat):
        try:
            callback(msg, chat)
        except Exception as e:
            wxlog.error(f'监听回调异常: {e}')

    # ---------- 其它（Phase 3 完善） ----------
    def GetNextNewMessage(self, filter_mute: bool = False, callback=None) -> dict:
        """扫会话列表，取第一个有未读（预览行 [N条]）的会话的新消息。

        返回 {'chat_name','chat_type','msg':[...]}，无未读返回 {}。注意切入会话会
        清除其未读（符合逐个消费语义）。filter_mute=True 跳过免打扰会话。
        """
        import re
        from .languages import RE
        rc = re.compile(RE['session_count'])
        for s in self.GetSession():
            if filter_mute and getattr(s, 'mute', False):
                continue
            m = rc.search(s.content or '')
            if not m:
                continue
            cnt = int(m.group(1))
            self.ChatWith(s.name, exact=True)
            time.sleep(0.3)
            msgs = self.GetAllMessage()
            human = [x for x in msgs if getattr(x, 'attr', None) != 'system']
            new = human[-cnt:] if cnt else []
            if callback:
                for x in new:
                    try:
                        callback(x)
                    except Exception as e:
                        wxlog.error(f'GetNextNewMessage 回调异常: {e}')
            return {'chat_name': s.name,
                    'chat_type': 'group' if '群' in s.name else 'friend',
                    'msg': new}
        return {}

    def GetHistoryMessage(self, n: int = None, callback=None, interval: float = 0.2,
                          speed: int = 1, goback: bool = True):
        """向上滚动加载并收集历史消息（按 id 去重）。

        Args:
            n: 目标数量，None 表示尽量多取直到滚不动
            callback: 每条新读到的消息回调
            interval: 每次滚动后的等待
            speed: 每次上滚的滚轮格数
            goback: 结束后是否回到最新位置
        """
        if uiabase.is_locked():
            wxlog.warning('工作站已锁屏，无法滚动加载历史')
            return []
        cb = self.ChatBox
        uiabase.activate_window(self.core.control)
        seen = {}
        order = []
        stagnant = 0
        max_rounds = (n or WxParam.GET_NEXT_MAX_QUANTITY * 5) + 20
        rounds = 0
        while (n is None or len(order) < n) and stagnant < 6 and rounds < max_rounds:
            rounds += 1
            before = len(order)
            for m in cb.get_msgs(detect_direction=False):
                if m.id and m.id not in seen:
                    seen[m.id] = m
                    order.append(m)
                    if callback:
                        try:
                            callback(m)
                        except Exception as e:
                            wxlog.error(f'历史消息回调异常: {e}')
            stagnant = stagnant + 1 if len(order) == before else 0
            cb.scroll_up(max(1, speed))
            time.sleep(interval)
        if goback:
            cb.scroll_to_bottom()
        return order[:n] if n else order
