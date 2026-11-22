# Xone:K3 Ableton Live 12 Remote Script

[English guide](README_EN.md)

为 Allen & Heath Xone:K3 编写的 Ableton Live 12 Remote Script，包含 Session Clip 控制、Arrangement 设备导航、Push 设备参数分组、Browser 浏览和多色灯光反馈。

三个 Layer 分别用于 Send、设备参数和现场演出：

| Layer | 用途 |
|---|---|
| 1 | 调整四条轨道的 Send |
| 2 | 调整设备参数和四轨 Pan |
| 3（Session） | Performance 演出界面：启动 Clip、静音、选择设备和调整十二个参数，并控制 Arrangement 录制 |

演出时，可以选择另一条轨道、Return 或 Main 调整设备，同时让 Clip、Mute 和推子继续控制当前四条轨道。

## 文件与要求

- Ableton Live 12；Allen & Heath Xone:K3。无需安装额外的 API 或开发工具。
- MIDI Channel 16；Latching Layers **OFF**；LED Mode **Remote**。
- 安装完整 `Xone_K3` 文件夹（四个 Python 文件），并将本仓库的 `Xone K3 Ableton.xml` 写入硬件。只更新脚本不会更新硬件灯色。
- XML 元数据：Editor V1.0.1、K3 V1.0.4。其他组合未逐一验证。

## 安装

### 1. 写入 K3 Map

1. 连接 K3，打开 Xone Controller Editor。
2. 导入 `Xone K3 Ableton.xml`。
3. 保存到 K3 的 User Map 2、3 或 4，并加载该 Map。
4. 将硬件的 **Latching Layers 设为 OFF**。
5. 确认 LED Mode 保持 **Remote**。
6. 完全关闭 Xone Controller Editor，避免它占用 MIDI 端口。

这个 Map 的控制消息全部使用第一组 MIDI 编号；`LAYER` 和 `SHIFT` 由脚本在软件中管理。额外两组 Note 只用于让 Live 指定同一盏灯的不同颜色。

#### 将 Latching Layers 设为 OFF

这项设置不会随 XML 一起写入，必须在 K3 的 Power On Setup 中单独完成：

1. 断开 K3 电源或 USB。
2. 按住右下角标有 `POWER ON SETUP` 的编码器，同时重新连接 K3。
3. `SHIFT` 会先闪黄色再保持黄色，上方矩阵最左上按键亮起，表示已进入 Setup Mode。
4. 旋转右下角 Setup 编码器，直到上方矩阵第一排第 2 个按键亮起；这一项是 Latching Layers。
5. 按下 Setup 编码器进入选项。
6. 旋转编码器，直到这一组选项的指示灯**全部熄灭**；这就是 **State 1：LATCHING LAYERS OFF**。State 2–5 都属于 ON，会有对应的范围指示灯亮起，不能使用。
7. 再按一下 Setup 编码器保存并返回 Setup Mode。
8. 按保持黄色的 `SHIFT` 退出；K3 会重新启动。

设置完成后，K3 自身不会显示硬件 Layer 颜色，灯全部熄灭是正常状态。启动 Live、加载 `Xone_K3` 并操作一次 K3 后，灯光才由脚本接管：每按一次 `LAYER`，软件 Layer 依次切换，灯色为 **Layer 1 黄 → Layer 2 绿 → Layer 3 红 → Layer 1 黄**。`SHIFT` 显示当前 Bank：**Bank 1 白 → Bank 2 黄 → Bank 3 绿**；每次切换主 Layer 后 Bank 回到 1，因此 `SHIFT` 回到白色。

如果必须按三次 `LAYER`，Live 才显示一次 Layer 变化，说明硬件仍在 State 2–5，而不是 State 1。

### 2. 安装 Remote Script

在 Ableton User Library 下建立 `Remote Scripts` 文件夹，再放入完整的 `Xone_K3` 文件夹：

```text
macOS:
~/Music/Ableton/User Library/Remote Scripts/Xone_K3

Windows（默认 User Library 位置）:
%USERPROFILE%\Documents\Ableton\User Library\Remote Scripts\Xone_K3
```

如果自定义过 User Library 位置，以 Live 设置里显示的实际路径为准。

### 3. 配置 Live

1. 完全退出并重新打开 Ableton Live。
2. 打开 `Settings/Preferences → Link, Tempo & MIDI`。
3. Control Surface 选择 `Xone_K3`。
4. Input 和 Output 都选择 `XONE:K3`。

K3 未连接，或脚本还没收到 K3 MIDI 时，Session Ring 会隐藏；重新连接后操作任意控件，Ring 会恢复。

## Layer 与灯光

`LAYER` 循环切换软件 Layer：**1 黄 → 2 绿 → 3 红**。硬件 Latching Layers 必须关闭。切换 Layer 时恢复该层 Bank 1。

Session Layer 1/2 和 Arrangement 中，`SHIFT` 切参数／Send Bank，指示色为白、黄、红。**Session Layer 3 中 SHIFT 改为 Arrangement Record：录制红色常亮，未录制灭**，同步鼠标和其他控制器的录制操作。

## Session View：选轨与 Clip 控制

- 顶部编码器 2 在三个 Layer 中均选择：可见普通轨道 → Return → Main；反转可返回。
- 选轨会显示 Device Chain；有选中设备时聚焦该设备。不会改变 Session Ring 或四个推子的绑定范围。
- 四个推子与 Clip 列始终对应 Session Ring 内的四条普通轨道。选中 Return／Main 后可以控制其设备，但不会把 Return／Main 换到这些推子上。
- Clip Pad 为四轨 × 四场景，不用于启动整个 Scene。

### Session 共用顶部控件

| 控件 | 功能 |
|---|---|
| 顶部 1 旋转 | Tempo，20–999 BPM，每步 0.2 BPM |
| 顶部 2 旋转 | 只选择轨道，范围不跟随 |
| 顶部 3 旋转 | Layer 1/2：在完整设备树中选设备；Layer 3：只选顶层设备 |
| 顶部 4 旋转 | Main 音量 |
| 顶部四个按下 | 停止当前四列对应轨道的 Clip |
| 四根推子 | Session Ring 内四轨 Volume |
| 4×4 Pad | 四轨 × 四场景 Clip Launch |

Clip 灯：空位灭、有 Clip 未播放黄、播放绿、录制或等待录制红。硬件未连接／未收到 MIDI 时 Ring 隐藏，操作后恢复。

### Layer 1：Sends

三排旋钮分别控制当前四轨的三个 Send。SHIFT 循环 Send 1–3、4–6、7–9；不足的位置留空。

### Layer 2：Device Bank＋Pan

前八个旋钮控制当前 Appointed Device 的一个 Push Bank，第三排四个旋钮控制当前四轨 Pan。SHIFT 循环最多三个 Bank。优先使用 Live 的 Push2 Bank 定义，无可用定义时回退原始参数顺序。

Layer 1/2 的三排按钮从上到下为 Mute、Solo、Arm：轨道开启黄、Solo 蓝、Arm 红。底部左旋转选普通轨道并移动四轨范围；右旋转选 Scene，超出四行时范围跟随。左下按下切换 Arrangement Record，右下按下 Re-enable Automation。

## Session Layer 3：Performance 演出界面

### 设备控制

| 控件 | 功能 |
|---|---|
| 顶部 3 旋转 | 选择当前轨道的顶层设备，不进入 Rack 内部 |
| 第二、三排八个按钮 | 对应设备窗口中的八个设备；按未选设备选择并聚焦，再按已选设备切换 Device On/Bypass |
| 三排十二个旋钮 | 按 Push Bank 顺序展开，每页十二个参数槽 |
| 按住左下编码器并旋转 | 前后切换参数页；无循环，首尾停止 |

八设备窗口保持位置：在窗口内选设备不会重排；选到第九个才向后移动一位，反向越界同理。**设备按钮本身不会移动窗口。** 换轨时窗口与参数页回到起点，换设备时参数页回到第一页。

第一页是 Push Bank 1 的八项＋Bank 2 的前四项；第二页从 Bank 2 的后四项继续。缺项留空，不压缩顺序；无可用 Bank 定义时，回退到设备原始参数列表并跳过 Device On。旋钮使用接管机制，避免设备或页面变化导致参数跳变。Macro 顺序以实际 Push Bank 为准，不保证所有设备都对应界面上的连续旋钮。

### 现场混音与录制

| 控件 | 功能 |
|---|---|
| 第一排四个按钮 | 当前四列轨道的 Mute |
| 左下旋转 | 每步移动一轨，Clip／Mute／推子范围一起移动，不改变选中轨道 |
| 右下旋转 | 每步移动一场景，不改变选中 Scene |
| 底部两个单独按下 | 不执行操作；左下按住旋转用于参数翻页 |
| SHIFT | Arrangement Record 开关，录制红色常亮、未录制灭 |
| LAYER | 保持切换 Layer |

### 八个设备按钮的灯光

Device 和 Rack 使用相同规则：

| 状态 | 灯色 |
|---|---|
| 空位／未选中且关闭 | 灭 |
| 未选中且开启 | 蓝 |
| 选中且开启 | 黄 |
| 选中且关闭 | 红 |

灯色表示设备当前的选择与开关状态。如果显示不符，确认硬件已载入本仓库随附的 XML。

## Arrangement View

在 Live 中切换到 Arrangement View 后，控件按下表工作。

| 控件 | 功能 |
|---|---|
| 顶部 1 旋转／按下 | Tempo／上一个 Locator |
| 顶部 2 旋转／按下，Layer 1 | 水平缩放／下一个 Locator |
| 顶部 2 旋转／按下，Layer 2/3 | Browser 导航／进入目录或加载项目 |
| 顶部 3 旋转／按下 | 水平滚动画面／设置或删除 Locator |
| 顶部 4 旋转／按下 | Main 音量／Back to Arrangement |
| 左下旋转／按下 | 垂直缩放／Arrangement Record |
| 右下旋转／按下 | 选择普通轨道及 Return／Re-enable Automation |

四轨混音范围从当前选中轨道开始；选中 Return 时使用 Return 范围，选中 Main 时四轨控件不映射。三排按钮为 Mute／Solo／Arm。旋钮 Layer 1 为 Sends，Layer 2/3 为八个设备参数＋四轨 Pan，SHIFT 切 Bank。

4×4 Pad 选择设备，再按已选设备切换开关。Layer 2 列出顶层设备和嵌套 Rack；Layer 1/3 展开完整设备树。Arrangement Pad 灯色：未选普通设备绿（不反映开关）、未选 Rack 灭、选中开启黄、选中关闭红。

Browser 只在 Arrangement Layer 2/3 生效：顶部 2 旋转浏览，子目录第一项继续往回转可返回；按下进入或加载。可预听项目短暂延迟后预听，移动、加载或离开时停止。路径显示在状态栏，不同步屏幕 Browser 高亮。

## 使用限制与故障排查

- Live 的设备面板聚焦、折叠与近似定位受公开 API 和 Rack 布局限制，不保证设备始终靠左或轨道自动滚入画面。
- Arrangement 水平滚动移动可视区域，不移动播放光标。
- 替换脚本后须完全重启 Live；XML 要另行在 Editor 中保存到硬件，并关闭 Editor 避免占用端口。
- 灯色错误先核对是否写入随附 XML、Latching Layers OFF、LED Remote，以及 Live 的 MIDI Output。

从仓库 `main` 下载当前脚本；Tagged Release 可能落后于 `main`。
