# Xone:K3 Ableton Live 12 Remote Script

[English guide](README_EN.md)

这是一个独立开发的 Allen & Heath Xone:K3 Ableton Live 12 MIDI Remote Script。它使用软件 Layer、4×4 Session Ring、Arrangement 设备导航、Push 2 参数 Bank，以及由 Live 控制的 RGB 状态灯。

> 本指南依据仓库中的 `Xone_K3/xonek3.py`、`Xone_K3/elements.py`、`Xone_K3/midi.py` 和 `Xone K3 Ableton.xml` 编写。

## 兼容性

- Allen & Heath Xone:K3
- Ableton Live 12（脚本使用 Ableton v3 Control Surface API）
- Xone Controller Editor；随附 XML 由 Editor `V1.0.1`、K3 Unit `V1.0.4` 保存
- MIDI Channel 16（XML 中为 16；Ableton Python API 内部表示为 15）

其他 Live、Editor 或固件版本尚未验证。

## 下载内容

```text
Xone_K3/
├── __init__.py
├── elements.py
├── midi.py
└── xonek3.py

Xone K3 Ableton.xml
README.md
README_EN.md
```

四个 Python 文件共同组成 Remote Script，缺少任何一个都无法正常加载。

可在 GitHub Releases 下载完整压缩包；解压后会同时得到 `Xone_K3` 脚本文件夹、K3 Editor XML 和中英文说明。

## 安装

### 1. 将硬件 Map 写入 K3

1. 连接 Xone:K3，打开 Xone Controller Editor。
2. 导入 `Xone K3 Ableton.xml`。
3. 将它保存到 K3 的 User Map 2、3 或 4，并加载该 Map。
4. 将 K3 的 **Latching Layers 设置为 OFF**。这个脚本只接收 Layer 1 的控制编号，并由 Ableton 在软件中切换三层；Layer 2/3 的 MIDI Note 用于多色 LED 反馈。
5. 完全关闭 Xone Controller Editor，避免它继续占用 MIDI 端口。

进入 K3 Power On Setup 的方法：断开电源，按住标有 `POWER ON SETUP` 的编码器并重新连接；选择第二项 Latching Layers，设为第一种状态 `OFF`，保存后按 SHIFT 退出。

### 2. 安装 Remote Script

在 Ableton User Library 中建立 `Remote Scripts` 文件夹，再把完整的 `Xone_K3` 文件夹放进去：

```text
macOS:
~/Music/Ableton/User Library/Remote Scripts/Xone_K3

Windows:
~/Documents/Ableton/User Library/Remote Scripts/Xone_K3
```

不要只复制 `xonek3.py`。`Xone_K3` 文件夹内必须同时包含四个 Python 文件。

### 3. 配置 Ableton Live

1. 完全退出并重新打开 Ableton Live。
2. 打开 `Settings/Preferences → Link, Tempo & MIDI`。
3. Control Surface 选择 `Xone_K3`。
4. Input 和 Output 都选择 `XONE:K3`。

K3 未连接或脚本尚未收到它的 MIDI 时，Session Ring 会隐藏；重新连接并发送任意控制消息后恢复。

## 控制逻辑

### 当前四轨

- Session View：Session Ring 中的四条轨道。
- Arrangement View：当前选中轨道作为第 1 列，后面三条可见轨道作为第 2–4 列。
- Arrangement 中右下编码器只负责选择轨道；受 Live Remote Script API 限制，它不会自动滚动 Arrangement 画面。

### 全局：最上方四个编码器

| 从左到右 | 旋转 |
|---|---|
| 1 | Tempo，20–999 BPM |
| 2 | 暂无功能 |
| 3 | Arrangement 播放位置走带；转得越快，移动跨度越大 |
| 4 | Master Volume |

### 最上方四个按键

| 从左到右 | Session View | Arrangement View |
|---|---|---|
| 1 | 停止第 1 条当前轨道上的 Clip | 跳到上一个 Locator |
| 2 | 停止第 2 条当前轨道上的 Clip | 跳到下一个 Locator |
| 3 | 停止第 3 条当前轨道上的 Clip | Set/Delete Locator |
| 4 | 停止第 4 条当前轨道上的 Clip | Back to Arrangement |

Arrangement 中只有 Back to Arrangement 可用时，第 4 个灯才会常亮。Session 中对应轨道有 Clip 正在播放时，上方按键灯常亮。

### 3×4 旋钮

按 `LAYER` 在三个软件 Layer 间循环。每次进入一个 Layer，该 Layer 都从 Bank 1 开始。

#### Layer 1：Track Sends

三排分别控制当前四轨的三个 Send：

- Bank 1：Send 1–3
- Bank 2：Send 4–6
- Bank 3：Send 7–9

按 `SHIFT` 切换 Bank。若工程中的 Return Track 数量不足，对应旋钮不映射。

#### Layer 2：Device Bank + Balance

- 上面 8 个旋钮：当前选中 Device 的 8 个参数。
- 最下面 4 个旋钮：当前四轨的 Balance/Pan。
- 按 `SHIFT` 在最多三个 Device Bank 间循环。

参数顺序来自 Ableton Live 内置的 `Push2.custom_bank_definitions`，因此会使用 Live 为设备设计的 Bank 名称与顺序，而不是简单取参数列表前八项。如果某个设备无法使用该 Bank 定义，脚本退回到原始参数列表，每 Bank 8 个参数。

选择新的 Device、重新进入 Layer 2，或切换到另一软件 Layer 后再回来时，Bank 会回到第 1 个。转动已映射的旋钮时，Live 状态栏会显示 Bank、Device、参数名和当前值。

#### Layer 3：Return-to-Return Sends

最多使用前四条 Return Track。每一列是一条 Return Track，三排控制它发送到另外三条 Return Track 的 Send；不会映射发送到自身的通道。

Layer 3 的 `SHIFT` 暂无切换功能。

### 旋钮下方三排按键

三个软件 Layer 和两种 Live View 中都保持一致：

| 按键排 | 功能 | 灯光 |
|---|---|---|
| HI | Track Activator / Mute | 轨道开启时橙色，关闭时灭 |
| MID | Solo | Solo 时蓝色 |
| LOW | Arm | 可录音轨道 Arm 时红色；Group/Return 等不可 Arm 轨道不亮 |

### 四根推子

控制当前四轨的 Volume。三个软件 Layer 和两种 Live View 中都保持一致。

## Session View

### 4×4 按键

按“从左到右、从上到下”对应 Session Ring 中 4 条轨道 × 4 个 Scene：

- 空 Clip Slot：灭
- 有 Clip、未播放：黄色
- 正在播放：绿色
- 正在录制或排队录制：红色

### 最下方编码器

| 控件 | 功能 |
|---|---|
| 左编码器旋转 | Session Ring 左右移动 |
| 按住左编码器并旋转 | Session Ring 上下移动 |
| 右编码器旋转 | 选择上/下一个 Scene；必要时 Ring 跟随 Scene |
| 按下右编码器 | 启动当前选中的整个 Scene |

## Arrangement View

### 4×4 Device 选择

16 个按键按“从左到右、从上到下”选择当前轨道上的 Device。设备顺序是：

1. 顶层 Device 从左到右；
2. 遇到 Rack 时，先计入 Rack 本体；
3. 再依次进入 Chain 1、Chain 2……，每条 Chain 内从左到右；
4. 嵌套 Rack 使用同样的深度优先顺序；
5. 最多映射前 16 个项目。

按下未选中的 Device：选中并把 Device Chain 视图聚焦到它。再次按下当前选中的 Device：切换 Device On/Bypass。

灯光：

- 空位置：灭
- 未选中的普通 Device：绿色（无论当前 On 或 Bypass）
- 未选中的 Rack：灭，用作设备组分隔
- 当前选中且 On：黄色
- 当前选中且 Bypass：红色

选中时，脚本会展开选中的普通 Device、折叠其他普通 Device；选中 Rack 内设备时会展开其 Rack 路径、显示 Macro/Device，并隐藏 Chains。

### 最下方编码器

| 控件 | 功能 |
|---|---|
| 左编码器旋转 | Arrangement 垂直缩放 |
| 按住左编码器并旋转 | Arrangement 水平缩放 |
| 右编码器旋转 | 选择上一条/下一条可见轨道 |
| 按下右编码器 | 切换 Ableton Arrangement Record |

## Layer 与 Bank 灯

随附 XML 中的实际颜色：

| 指示灯 | 状态颜色 |
|---|---|
| LAYER | Layer 1 红、Layer 2 黄、Layer 3 绿 |
| SHIFT | Bank 1 白、Bank 2 黄、Bank 3 绿 |

Latching Layers 必须关闭，三层 Note 才能被脚本分别用于 RGB 反馈。

## 故障排查

- **Live 完全没反应**：确认已加载 `Xone K3 Ableton` User Map、Latching Layers 为 OFF、Editor 已关闭、Live 的 Input/Output 都是 `XONE:K3`。
- **Control Surface 列表没有 Xone_K3**：确认文件夹层级是 `Remote Scripts/Xone_K3/__init__.py`，然后完全重启 Live。
- **有控制但没有灯**：确认 Live 的 MIDI Output 选择了 `XONE:K3`，XML 中 LED Mode 保持 Remote。
- **映射突然错乱**：先重新插拔 K3，并确认硬件仍加载正确 User Map。
- **更新脚本后没变化**：完全退出 Live，再替换文件并重新启动。Remote Script 不是所有改动都能热重载。
