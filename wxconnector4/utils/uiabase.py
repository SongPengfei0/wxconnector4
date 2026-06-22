"""对开源 uiautomation(Apache-2.0) 的薄封装。

只暴露 wxconnector4 需要的能力：控件查找、点击、剪贴板、粘贴、键入、窗口尺寸。
uiautomation 在 import 时已 comtypes.CoInitialize()，主线程可直接用；
子线程需先调用 ensure_com()。
"""
import struct
import time

import uiautomation as auto
import win32gui
import win32con
import win32clipboard

Control = auto.Control  # 类型别名


def ensure_com():
    """在新线程中使用 UIA 前确保 COM 已初始化。"""
    try:
        import comtypes
        comtypes.CoInitialize()
    except Exception:
        pass


def get_root() -> Control:
    return auto.GetRootControl()


# ---------------- 控件查找 ----------------

def _match(ctrl: Control, classname=None, automation_id=None, name=None,
           control_type=None, name_contains=None, aid_suffix=None) -> bool:
    try:
        if classname is not None and ctrl.ClassName != classname:
            return False
        if automation_id is not None and ctrl.AutomationId != automation_id:
            return False
        if aid_suffix is not None and not (ctrl.AutomationId or '').endswith(aid_suffix):
            return False
        if name is not None and ctrl.Name != name:
            return False
        if name_contains is not None and name_contains not in (ctrl.Name or ''):
            return False
        if control_type is not None and ctrl.ControlTypeName != control_type:
            return False
        return True
    except Exception:
        return False


def find(parent: Control, classname=None, automation_id=None, name=None,
         control_type=None, name_contains=None, aid_suffix=None, maxdepth=40, timeout=0,
         interval=0.2):
    """深度优先查找首个匹配的后代控件；timeout>0 时在超时内重试。返回控件或 None。"""
    deadline = time.time() + timeout

    def _search(ctrl, depth):
        if depth > maxdepth:
            return None
        try:
            children = ctrl.GetChildren()
        except Exception:
            return None
        for c in children:
            if _match(c, classname, automation_id, name, control_type, name_contains, aid_suffix):
                return c
            hit = _search(c, depth + 1)
            if hit is not None:
                return hit
        return None

    while True:
        result = _search(parent, 0)
        if result is not None or time.time() >= deadline:
            return result
        time.sleep(interval)


def find_all(parent: Control, classname=None, automation_id=None, name=None,
             control_type=None, name_contains=None, aid_suffix=None, maxdepth=40):
    """查找所有匹配的后代控件。"""
    out = []

    def _search(ctrl, depth):
        if depth > maxdepth:
            return
        try:
            children = ctrl.GetChildren()
        except Exception:
            return
        for c in children:
            if _match(c, classname, automation_id, name, control_type, name_contains, aid_suffix):
                out.append(c)
            _search(c, depth + 1)

    _search(parent, 0)
    return out


def find_window(classname=None, name=None, timeout=2.0, interval=0.3):
    """在顶层窗口中查找首个匹配窗口。返回控件或 None。"""
    deadline = time.time() + timeout
    while True:
        for w in get_root().GetChildren():
            if _match(w, classname=classname, name=name):
                return w
        if time.time() >= deadline:
            return None
        time.sleep(interval)


def find_windows(classname=None, name=None):
    """返回所有匹配的顶层窗口。"""
    return [w for w in get_root().GetChildren() if _match(w, classname=classname, name=name)]


# ---------------- 取值 ----------------

def content_point(control):
    """消息控件是满宽行、气泡靠边对齐。截图定位真正的气泡块，返回屏幕点击点 (x,y)。

    用于点击/右键消息气泡（行中心常是空白，直接点会落空）。失败返回 None。
    """
    try:
        from PIL import ImageGrab
        import win32api
        r = control.BoundingRectangle
        sw, sh = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
        left, top, right, bottom = max(0, r.left), max(0, r.top), min(sw, r.right), min(sh, r.bottom)
        w, h = right - left, bottom - top
        if w <= 20 or h <= 20:
            return None
        img = ImageGrab.grab(bbox=(left, top, right, bottom)).convert('L')
        px = img.load()
        bg = px[2, 2]
        cols = []
        for x in range(0, w, 2):
            cnt = sum(1 for y in range(0, h, 3) if abs(px[x, y] - bg) > 25)
            cols.append((x, cnt > (h / 3) / 3))
        best = (0, 0, 0)
        start = None
        for x, has in cols + [(w, False)]:
            if has and start is None:
                start = x
            elif not has and start is not None:
                if x - start > best[2]:
                    best = (start, x, x - start)
                start = None
        if best[2] <= 0:
            return None
        return (left + (best[0] + best[1]) // 2, (top + bottom) // 2)
    except Exception:
        return None


def right_click_at(x, y):
    import uiautomation as auto
    auto.RightClick(x, y)


def click_at(x, y):
    import uiautomation as auto
    auto.Click(x, y)


def get_value(ctrl: Control) -> str:
    """读取控件文本：优先 ValuePattern，否则回退 Name。"""
    try:
        vp = ctrl.GetValuePattern()
        if vp is not None:
            return vp.Value
    except Exception:
        pass
    try:
        return ctrl.Name or ''
    except Exception:
        return ''


# ---------------- 输入 / 剪贴板 ----------------

def set_clipboard_text(text: str):
    auto.SetClipboardText(text)


def get_clipboard_text() -> str:
    try:
        return auto.GetClipboardText()
    except Exception:
        return ''


def set_clipboard_files(paths):
    """把文件路径写入剪贴板（CF_HDROP），用于"粘贴文件"发送。"""
    if isinstance(paths, str):
        paths = [paths]
    files = '\0'.join(paths) + '\0\0'
    # DROPFILES: pFiles=20, pt(0,0), fNC=0, fWide=1
    header = struct.pack('<IiiII', 20, 0, 0, 0, 1)
    data = header + files.encode('utf-16-le')
    for _ in range(3):
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_HDROP, data)
            win32clipboard.CloseClipboard()
            return True
        except Exception:
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                pass
            time.sleep(0.1)
    return False


def click(ctrl: Control):
    ctrl.Click(simulateMove=False)


def set_focus(ctrl: Control):
    try:
        ctrl.SetFocus()
    except Exception:
        ctrl.Click(simulateMove=False)


def send_keys(ctrl: Control, keys: str, interval=0.01):
    """向控件发送按键。modifier 语法：'{Ctrl}v'、'{Ctrl}a'、'{Enter}'、'{Delete}'。"""
    ctrl.SendKeys(keys, interval=interval)


def paste(ctrl: Control):
    ctrl.SendKeys('{Ctrl}v')


def clear_edit(ctrl: Control):
    ctrl.SendKeys('{Ctrl}a{Delete}')


def press_enter(ctrl: Control):
    ctrl.SendKeys('{Enter}')


# ---------------- 窗口尺寸 ----------------

def get_hwnd(ctrl: Control) -> int:
    return ctrl.NativeWindowHandle


def set_window_size(hwnd: int, width: int, height: int, location=None):
    if location:
        x, y = location
        win32gui.MoveWindow(hwnd, x, y, width, height, True)
    else:
        # SWP_NOZORDER(4) | SWP_NOMOVE(2) = 6
        win32gui.SetWindowPos(hwnd, 0, 0, 0, width, height, 6)


def show_window(hwnd: int):
    win32gui.ShowWindow(hwnd, win32con.SW_SHOWNORMAL)


def handle_file_dialog(path: str, title: str = None, timeout: float = 6.0) -> bool:
    """用 win32 消息操作系统文件选择框(#32770)：填路径并点「打开」。

    不走 UIA（模态对话框会阻塞 UIA），稳定不卡。title 不指定则取首个可见 #32770。
    用于朋友圈选图、发送文件等需要系统文件框的场景。
    """
    import time
    deadline = time.time() + timeout
    h = 0
    while time.time() < deadline:
        found = {}

        def cb(hh, _):
            try:
                if win32gui.GetClassName(hh) == '#32770' and win32gui.IsWindowVisible(hh):
                    found[win32gui.GetWindowText(hh)] = hh
            except Exception:
                pass

        win32gui.EnumWindows(cb, None)
        if title and title in found:
            h = found[title]
        elif found:
            h = next(iter(found.values()))
        if h:
            break
        time.sleep(0.2)
    if not h:
        return False
    # 文件名 Edit: dlg -> ComboBoxEx32 -> ComboBox -> Edit
    combo = win32gui.FindWindowEx(h, 0, 'ComboBoxEx32', None)
    cbx = win32gui.FindWindowEx(combo, 0, 'ComboBox', None) if combo else 0
    edit = win32gui.FindWindowEx(cbx, 0, 'Edit', None) if cbx else 0
    if not edit:
        edit = win32gui.FindWindowEx(h, 0, 'Edit', None)
    if not edit:
        return False
    win32gui.SendMessage(edit, win32con.WM_SETTEXT, 0, path)
    time.sleep(0.3)
    win32gui.PostMessage(h, win32con.WM_COMMAND, 1, 0)  # IDOK = 打开
    return True


def save_file_dialog(dir_path: str, filename: str = None, timeout: float = 6.0):
    """操作系统「另存为」框(#32770)：把保存目标设为 dir_path/filename 并点「保存」。

    filename=None 时沿用对话框自带的默认文件名（适合视频等 Name 不含文件名的场景）。
    返回最终保存路径(str)，失败返回 None。
    """
    import os
    import time
    deadline = time.time() + timeout
    h = 0
    while time.time() < deadline:
        found = []

        def cb(hh, _):
            try:
                if win32gui.GetClassName(hh) == '#32770' and win32gui.IsWindowVisible(hh):
                    found.append(hh)
            except Exception:
                pass

        win32gui.EnumWindows(cb, None)
        if found:
            h = found[0]
            break
        time.sleep(0.2)
    if not h:
        return None
    # Win11 文件名 Edit 嵌在 AppControlHost(ComboBox) 里，固定层级 FindWindowEx 找不到，
    # 改用 EnumChildWindows 递归找，优先文件名框的控件 id 1001。
    edits = []

    def _collect_edit(hh, _):
        try:
            if win32gui.GetClassName(hh) == 'Edit':
                if win32gui.GetDlgCtrlID(hh) == 1001:
                    edits.insert(0, hh)
                else:
                    edits.append(hh)
        except Exception:
            pass
    try:
        win32gui.EnumChildWindows(h, _collect_edit, None)
    except Exception:
        pass
    edit = edits[0] if edits else 0
    if not edit:
        return None
    # GetWindowText 跨进程读不到外部控件文本，用 WM_GETTEXT。
    import ctypes
    _n = ctypes.windll.user32.SendMessageW(edit, win32con.WM_GETTEXTLENGTH, 0, 0)
    _buf = ctypes.create_unicode_buffer(_n + 1)
    ctypes.windll.user32.SendMessageW(edit, win32con.WM_GETTEXT, _n + 1, _buf)
    default_name = os.path.basename(_buf.value or '')
    fname = filename or default_name or 'wechat_file'
    os.makedirs(dir_path, exist_ok=True)
    target = os.path.join(dir_path, fname)
    win32gui.SendMessage(edit, win32con.WM_SETTEXT, 0, target)
    time.sleep(0.3)
    win32gui.PostMessage(h, win32con.WM_COMMAND, 1, 0)  # IDOK = 保存
    return target


def force_foreground(hwnd: int) -> bool:
    """强制把窗口提到前台。

    关键：先把 Windows「前台锁超时」设为 0，否则后台进程的 SetForegroundWindow 会被
    系统静默忽略（只闪任务栏）。再配合 Alt 键技巧 + AttachThreadInput 兜底。
    """
    import ctypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    if not hwnd:
        return False
    # 关闭前台锁超时（最关键的一步）
    try:
        user32.SystemParametersInfoW(0x2001, 0, 0, 0)  # SPI_SETFOREGROUNDLOCKTIMEOUT
    except Exception:
        pass
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    else:
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWNORMAL)
    if user32.GetForegroundWindow() == hwnd:
        return True
    # Alt 键技巧解锁 SetForegroundWindow
    try:
        import win32api
        win32api.keybd_event(0x12, 0, 0, 0)
        win32api.keybd_event(0x12, 0, win32con.KEYEVENTF_KEYUP, 0)
    except Exception:
        pass
    user32.SetForegroundWindow(hwnd)
    user32.SetActiveWindow(hwnd)
    time.sleep(0.05)
    if user32.GetForegroundWindow() == hwnd:
        return True
    # AttachThreadInput 兜底
    cur = kernel32.GetCurrentThreadId()
    fg = user32.GetForegroundWindow()
    fg_thread = user32.GetWindowThreadProcessId(fg, 0)
    tgt_thread = user32.GetWindowThreadProcessId(hwnd, 0)
    a1 = user32.AttachThreadInput(cur, fg_thread, True)
    a2 = user32.AttachThreadInput(cur, tgt_thread, True)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    user32.SetActiveWindow(hwnd)
    if a2:
        user32.AttachThreadInput(cur, tgt_thread, False)
    if a1:
        user32.AttachThreadInput(cur, fg_thread, False)
    return user32.GetForegroundWindow() == hwnd


def is_locked() -> bool:
    """工作站是否锁屏。锁屏时物理点击/键入无法送达应用。

    两种检测：
    1) 安全桌面（Winlogon）—— 经典锁屏；
    2) LockScreenBackstopFrame 覆盖窗口 —— Win10/11 锁屏 UI 宿主（运行在 default 桌面）。
    """
    import ctypes
    user32 = ctypes.windll.user32
    # 1) 输入桌面名
    hdesk = user32.OpenInputDesktop(0, False, 0x0001)
    if not hdesk:
        return True
    try:
        buf = ctypes.create_unicode_buffer(256)
        needed = ctypes.c_ulong()
        user32.GetUserObjectInformationW(hdesk, 2, buf, 256, ctypes.byref(needed))
        if buf.value.lower() != 'default':
            return True
    finally:
        user32.CloseDesktop(hdesk)
    # 2) 锁屏覆盖窗口
    try:
        import win32api
        cx = win32api.GetSystemMetrics(0) // 2
        cy = win32api.GetSystemMetrics(1) // 2
        wp = win32gui.WindowFromPoint((cx, cy))
        root_hwnd = user32.GetAncestor(wp, 2)  # GA_ROOT
        if win32gui.GetClassName(root_hwnd) == 'LockScreenBackstopFrame':
            return True
    except Exception:
        pass
    return False


def activate_window(window_ctrl):
    """把窗口带到前台，确保后续物理点击/粘贴落到正确窗口。"""
    try:
        hwnd = window_ctrl.NativeWindowHandle
        ok = force_foreground(hwnd)
        if not ok:
            try:
                window_ctrl.SwitchToThisWindow()
            except Exception:
                pass
        time.sleep(0.12)
    except Exception:
        pass
