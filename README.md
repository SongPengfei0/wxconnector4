# wxconnector4

> 免费、开源的微信 4.x（Windows 桌面版）自动化库

基于公开的 **Windows UI Automation** 实现的微信自动化工具库，纯 Python，**无任何授权/许可校验**，开箱即用。面向消息收发、监听、媒体处理、好友与群管理等自动化场景，可作为 RPA / 客服 / 消息中转等系统的确定性执行层。

- ✅ **完全免费、开源**，无激活、无序列号、无联网校验
- ✅ **纯界面自动化**，基于公开的 Windows UIA + 物理鼠键，不注入、不 hook、不逆向私有协议
- ✅ **零第三方 OCR 依赖**：默认走微信内置「提取文字」，需要高精度时可一行接入自己的 OCR 引擎
- ✅ **低耦合、轻量**，依赖均为宽松许可，可商用分发

> ⚠️ 自动化操作微信可能违反其用户协议、存在账号风险。请仅在**本机、自有账号**上用于学习与测试，风险自负。

---

## 环境要求

| 项 | 要求 |
|---|---|
| 操作系统 | Windows 10 / 11 |
| 微信版本 | 微信 4.x（Windows 桌面版），需已登录 |
| Python | 3.9+ |

## 安装

```bash
git clone <your-repo-url>
cd wxconnector4
pip install -e .
```

主要依赖：`uiautomation`、`pywin32`、`pillow`、`pyperclip`（均为宽松开源许可）。

## 快速开始

```python
from wxconnector4 import WeChat

wx = WeChat()                         # 连接已登录的微信主窗口
print(wx.IsOnline(), wx.GetMyInfo())

wx.ChatWith('文件传输助手')            # 切换会话
wx.SendMsg('Hello from wxconnector4')  # 发送文本
wx.SendFiles(r'D:\path\to\file.pdf')   # 发送文件

for msg in wx.GetAllMessage():         # 读取当前会话消息
    print(msg.type, msg.content)
```

### 监听消息

```python
def on_message(msg, chat):
    print(f'[{chat}] {msg.type}: {msg.content}')
    if msg.type == 'voice':
        print('  语音转文字 →', msg.to_text())

wx.AddListenChat('某个会话', on_message)
wx.StartListening()
wx.KeepRunning()        # 阻塞保持运行
```

### 媒体消息处理

```python
for msg in wx.GetAllMessage():
    if msg.type == 'image':
        msg.download()                 # 保存图片
        print(msg.ocr())               # 提取图片文字
    elif msg.type == 'voice':
        print(msg.to_text())           # 语音转文字
    elif msg.type in ('file', 'video'):
        path = msg.download(dir_path='downloads')
    elif msg.type == 'merge':
        print(msg.get_content())       # 读取合并转发（聊天记录）内容
```

### OCR 可插拔

```python
from wxconnector4 import WxParam

# 默认：OCR_BACKEND = None → 走微信内置「提取文字」，零额外依赖
# 需要更高精度时，接入自己的 OCR（签名： (image_path: str) -> str）：
WxParam.OCR_BACKEND = lambda image_path: my_ocr_engine(image_path)
```

---

## 功能清单

### ✅ 已实现

**连接 / 账号**
- `WeChat()` 连接主窗口、`IsOnline()`、`GetMyInfo()`
- `Show()` / `Close()` 窗口显示与关闭

**会话**
- `ChatWith(who)` 切换会话（带会话名校验，防发错对象）
- `GetSession()` 会话列表、`ChatInfo()` 当前会话信息
- `GetAllRecentGroups()` 最近群聊
- `GetDialog()` 读取对话框

**发送**
- `SendMsg(msg, who)` 发送文本（粘贴 + 相似度校验）
- `SendFiles(filepath, who)` 发送文件 / 图片
- `AtAll(msg, who)` 群内 @所有人 并发送（需群主 / 管理员权限）
- `SendUrlCard(url, friends)` 发送链接卡片（粘贴 URL 等微信渲染卡片后发送）
- `SendAudio(filepath, who)` 发送语音条（需 VB-CABLE 虚拟声卡，见下）

**读取**
- `GetAllMessage()` / `GetNewMessage()` 当前会话消息
- `GetHistoryMessage(n)` 向上滚动加载历史消息
- `GetNextNewMessage()` 扫描会话列表逐个取未读

**消息动作**（消息对象方法）
- `select_option(option)` 右键菜单操作（复制 / 收藏 / 提醒 …）
- `quote(text)` 引用回复、`forward(targets)` 转发、`delete()` 删除
- `click_head(right=False)` 点击头像打开发送者资料、`tickle()` 拍一拍（双击头像）
- `sender_info()` 读取发送人信息（群里识别"谁发的"，点头像取资料卡）

**媒体**（按消息类型）
- 图片 `image`：`download()` 保存、`ocr()` 提取文字
- 语音 `voice`：`to_text()` 语音转文字
- 文件 `file` / 视频 `video`：`download(dir_path)` 另存为
- 合并转发 `merge`：`get_messages()` / `get_content()` 读取聊天记录
- 笔记 `note`：`get_content()` 读正文、`save_files()` 存附件、`to_markdown()` 导出

**监听**
- `AddListenChat(nickname, callback)` / `RemoveListenChat()`
- `StartListening()` / `StopListening()` / `KeepRunning()`
- `GetSubWindow()` / `GetAllSubWindow()`

**好友**
- `AddNewFriend(keywords, addmsg, remark)` 搜索并添加好友
- `GetFriendDetails()` 读取好友资料
- `EditFriendInfo(remark=..., add_tags=..., remove_tags=...)` 修改好友备注与标签

**登录**
- `LoginWnd.open() / login() / reopen()` 启动微信并处理（扫码 / 已记住账号快捷）登录

**群**
- `CreateGroup(contacts)` 发起群聊

**朋友圈**
- `Moments()` 获取朋友圈、`PublishMoment(text, media_files, privacy_config)` 发表

### 🧪 已实现但需真机校验

下列原「待实现」清单中的接口现已按本库既有的控件定位约定实现，但**作者无真机环境逐一验证**，
其依赖的界面控件名/位置在微信 4.x 中可能随版本变化。建议首次使用在自有账号上验证，必要时按下表微调：

| 接口 | 实现路线 | 真机校验点 |
|---|---|---|
| `<msg>.click_head()` / `tickle()` | 按消息方向算头像坐标，单击开资料卡 / 双击触发拍一拍 | `WxParam.HEAD_INSET_X/Y` 头像内缩偏移 |
| `<msg>.sender_info()` | 点头像 → 读 `mmui::ContactProfileView` 资料卡 | 资料卡浮层 ClassName |
| `Note` 笔记 `get_content`/`save_files`/`to_markdown` | 点气泡开笔记详情窗 → 读文本/存图 → 导出 md | `NoteMessage.WND_CLS_CANDIDATES` 笔记窗类名 |
| `SendAudio(filepath)` | 音频灌入虚拟声卡 + 「按住说话」录制发送 | 见下方「发送语音条」前置条件 |
| `LoginWnd.open/login/reopen` | 注册表定位 Weixin.exe 启动 → 点「进入微信」或等扫码 | 登录按钮文案、安装路径 |
| `EditFriendInfo` 标签 `add_tags`/`remove_tags` | 设置备注和标签面板 → 点「标签」行 → 增删 | 标签编辑器控件（4.x 定位不稳定） |
| `SendUrlCard` 链接卡片 | 粘贴 URL，等微信抓取渲染卡片后发送 | 卡片渲染等待 `wait_render` |

> 标签编辑、笔记窗等控件在 4.x 中定位较不稳定；如失效，优先检查并更新对应 ClassName / 文案。

### ⏳ 仍未实现

| 接口 | 说明 |
|---|---|
| 群资料修改 `SetGroupName` / `SetGroupAnnouncement` 等 | 群管理写操作（控件定位不稳定） |
| `GetNewFriends` / 通过好友申请 | 好友申请列表读取与同意 |
| 朋友圈点赞 / 评论 `Like` / `Comment` | 仅实现了发布与读取 |

### 发送语音条（`SendAudio`）前置条件

`SendAudio` 本质是把音频「播放给微信听」，故需：

1. 安装 [VB-CABLE](https://vb-audio.com/Cable/) 虚拟声卡；
2. 微信「设置 → 音视频 → 麦克风」选 **CABLE Output**；
3. 安装可选依赖：`pip install sounddevice soundfile numpy`；
4. 非 wav 音频（mp3/m4a 等）需 `ffmpeg`（在 PATH 或设 `WxParam.AUDIO_PARAM['ffmpeg_path']`）。

缺少任一前置条件时 `SendAudio` 会返回明确的失败原因，不影响其它功能。

---

## 配置（`WxParam`）

常用配置项（完整见 `wxconnector4/param.py`）：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `OCR_BACKEND` | `None` | OCR 后端，`None` 走微信内置「提取文字」；可设为 `(image_path)->str` 接入自定义引擎 |
| `DEFAULT_SAVE_PATH` | `./wxconnector文件下载` | 文件 / 图片默认保存目录 |
| `LISTEN_INTERVAL` | `1` | 监听轮询间隔（秒） |
| `LISTENER_EXCUTOR_WORKERS` | `4` | 监听回调线程池大小 |
| `SEARCH_CHAT_TIMEOUT` | `2` | 搜索会话超时（秒） |
| `SEND_CONTENT_RATIO` | `0.9` | 发送前输入框内容相似度校验阈值 |
| `GET_NEXT_MAX_QUANTITY` | `30` | `GetNextNewMessage` 单次最大获取数量 |
| `MESSAGE_HASH` | `False` | 是否启用消息哈希辅助去重 |

所有接口统一返回 `WxResponse`（`status` / `message` / `data` 三态，可直接当 `bool` 判断成功与否）。

---

## 已知限制

- **版本脆性**：微信客户端为自研渲染框架，控件随版本变化，升级后可能需要适配（控件标识集中在 `wxconnector4/languages.py` 便于维护）。
- **虚拟列表**：读取历史 / 监听前会自动放大窗口以加载更多控件；超长列表需滚动加载。
- **前台要求**：写操作（点击 / 输入）需要微信窗口可被提到前台；锁屏状态下会拒绝操作。
- **发错对象防护**：发送前会校验当前会话名与输入内容相似度，降低误发风险。

## 贡献

欢迎提交 Issue 与 PR，尤其是上文「待实现」清单中的接口。适配新版本微信时，请优先更新 `languages.py` 中的控件标识。

## 许可证

本项目以 MIT 许可证开源（如需可改为 Apache-2.0）。所依赖的第三方库均为宽松开源许可，可商用分发。
