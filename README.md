# Xone:K3 Ableton Live 12 Remote Script v2.0

[English guide](README_EN.md)

这是一个独立开发的 Allen & Heath Xone:K3 Ableton Live 12 MIDI Remote Script。它使用软件 Layer、4×4 Session Ring、Arrangement 设备导航、Push 2 参数 Bank，以及由 Live 控制的 RGB 状态灯。

> 本指南依据仓库中的 `Xone_K3/xonek3.py`、`Xone_K3/elements.py`、`Xone_K3/midi.py` 和 `Xone K3 Ableton.xml` 编写。

## v2.0 主要功能

- 三层软件映射及 Live RGB 灯光反馈
- Session Ring、Clip/Scene 启动与即时 Clip 状态灯
- Arrangement Device、Rack/Chain 与轨道导航
- Push 2 Device 参数 Bank、内部 BrowserItem 导航及自动 Preview
- Track/Return Sends 与四轨 EQ Eight Performance Layer

## 兼容性

- Allen & Heath Xone:K3
- Ableton Live 12.3 或更高版本（脚本使用 Ableton v3 Control Surface API；Layer 3 自动新建 EQ Eight 使用 Live 12.3 加入的 `Track.insert_device`）
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
%USERPROFILE%\Documents\Ableton\User Library\Remote Scripts\Xone_K3
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
- Arrangement 选中 Return Track 时：选中的 Return 作为第 1 列，后面三条 Return 作为第 2–4 列。
- Arrangement 中右下编码器通过 Live 的 Arranger 导航选择轨道；Live 不保证把新轨道自动滚动到可视区域。

### 全局：最上方四个编码器

| 从左到右 | Layer 1 | Layer 2 |
|---|---|---|
| 1 | Tempo，20–999 BPM | Tempo，20–999 BPM |
| 2 | Session：分层 Browser 导航；Arrangement：水平缩放 | Session/Arrangement：分层 Browser 导航 |
| 3 | Session：选择当前轨道的 Device 焦点；Arrangement：播放位置走带（支持加速值） | Session：选择当前轨道的 Device 焦点；Arrangement：播放位置走带（支持加速值） |
| 4 | Master Volume | Master Volume |

Layer 3 的 Arrangement View 中，四个顶部编码器分别控制当前四轨的 Bell Frequency。Layer 3 的 Session View 中，第 3 个编码器用于 Device 焦点选择，其余三个控制对应列的 Bell Frequency。

Browser 导航使用脚本内部的 BrowserItem 列表，不会打开或移动 Live 屏幕上的 Browser 高亮。一级列表首先包含 Live 的颜色标签并从 Favorites 开始，随后才是 Sounds、Drums 等类别；旋转选择同一级的相对项目，Live 底部状态栏显示当前完整路径；停在可预听项目上会短暂延迟后自动 Preview，继续旋转、加载项目、退出 Browser 控制层或断开脚本时会停止上一项预听。在子级第一个项目继续左转会返回上一级。按下顶部第 2 个编码器的按键时，分类项目进入下一级，可加载项目则插入当前选中轨道。底部提示、Preview 与实际加载项目使用同一个 BrowserItem，加载位置仍遵守 Live 当前轨道和 Device 插入规则。

### 最上方四个按键

| 从左到右 | Session View | Arrangement View |
|---|---|---|
| 1 | 停止第 1 条当前轨道上的 Clip | 跳到上一个 Locator |
| 2 | 停止第 2 条当前轨道上的 Clip | 跳到下一个 Locator |
| 3 | 停止第 3 条当前轨道上的 Clip | Set/Delete Locator |
| 4 | 停止第 4 条当前轨道上的 Clip | Back to Arrangement |

Arrangement 中只有 Back to Arrangement 可用时，第 4 个灯才会常亮。Session 中对应轨道有 Clip 正在播放时，上方按键灯常亮。

例外：Session Layer 1，以及 Session/Arrangement Layer 2 中，第 2 个按键由 Browser 接管，执行“进入下一级／加载当前项目”，不再执行表中的 Clip Stop 或下一个 Locator。

### 3×4 旋钮

按 `LAYER` 在三个软件 Layer 间循环。每次进入一个 Layer，该 Layer 都从 Bank 1 开始。

#### Layer 1：Track Sends

三排分别控制当前四轨的三个 Send：

- Bank 1：Send 1–3
- Bank 2：Send 4–6
- Bank 3：Send 7–9

按 `SHIFT` 切换 Bank。若工程中的 Return Track 数量不足，对应旋钮不映射。

Arrangement 选中 Return Track 时，Layer 1 改为控制“选中的 Return＋后面三条 Return”的可用 Send；被禁用的 Send（包括发送给自身）会被跳过，后面的可用 Send 自动顺位补上。

#### Layer 2：Device Bank + Balance

- 上面 8 个旋钮：当前选中 Device 的 8 个参数。
- 最下面 4 个旋钮：当前四轨的 Balance/Pan。
- 按 `SHIFT` 在最多三个 Device Bank 间循环。

参数顺序来自 Ableton Live 内置的 `Push2.custom_bank_definitions`，因此会使用 Live 为设备设计的 Bank 名称与顺序，而不是简单取参数列表前八项。如果某个设备无法使用该 Bank 定义，脚本退回到原始参数列表，每 Bank 8 个参数。

选择新的 Device、重新进入 Layer 2，或切换到另一软件 Layer 后再回来时，Bank 会回到第 1 个。转动已映射的旋钮时，Live 状态栏会显示 Bank、Device、参数名和当前值。

#### Layer 3：EQ Eight

四列对应当前四轨：

- HI 排：Low Cut Frequency
- MID 排：Bell Gain
- LOW 排：High Cut Frequency
- 顶部四个编码器：对应四轨的 Bell Frequency

Layer 3 本身不会修改工程。按下 `SHIFT` 时，只初始化当前选中的一条轨道；选中 Group Track 时只处理 Group 本身，不会处理组内轨道。

脚本先寻找具有启用 Low Cut、Bell、High Cut 且目标参数可直接控制的 EQ Eight。找到后会选中并展开该 EQ。若已有 EQ Eight 尚未形成这三个角色，则初始化 Band 1＝Low Cut、Band 4＝Bell、Band 8＝High Cut，并把 Low Cut Frequency 设为 10 Hz、High Cut Frequency 设为 22 kHz。若现有 EQ 的目标参数因 Rack Macro 映射而不可直接控制，脚本会在所选轨道末尾新建普通 EQ Eight，再执行相同初始化。

自动新建原生设备依赖 Ableton Live 12.3 或更高版本提供的 `Track.insert_device`。

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
| 左编码器旋转 | 选择上一条/下一条可见轨道，并让该轨道成为 Session Ring 的第 1 列 |
| 按下左编码器 | 开启/关闭 Arrangement Record（在 Session View 中同样有效） |
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

选中时，脚本会展开选中的普通 Device、折叠其他普通 Device；选中 Rack 或 Drum Rack 内设备时，会从外到内选择目标所属的每一层 Chain、展开完整 Rack 路径并显示当前 Chain Devices。嵌套 Rack 使用相同规则。

### 最下方编码器

| 控件 | 功能 |
|---|---|
| 左编码器旋转 | Arrangement 垂直缩放 |
| 按下左编码器 | 开启/关闭 Arrangement Record |
| 右编码器旋转 | 使用 Arranger 上/下导航选择轨道 |
| 按下右编码器 | Re-enable Automation（存在可恢复的 Automation 时） |

Arrangement 水平缩放位于 Layer 1 的顶部第 2 个编码器，不使用按压组合。

## Layer 与 Bank 灯

随附 XML 中的实际颜色：

| 指示灯 | 状态颜色 |
|---|---|
| LAYER | Layer 1 红、Layer 2 黄、Layer 3 绿 |
| SHIFT | Bank 1 白、Bank 2 黄、Bank 3 绿 |

Latching Layers 必须关闭，三层 Note 才能被脚本分别用于 RGB 反馈。

## 已知限制

- Live 的公开 Remote Script API 没有“让 Arrangement 滚动条精确跟随所选轨道”的直接接口。脚本使用与原生控制器相同类型的 `scroll_view` 方向导航，但 Live 可能只改变选择或焦点而不移动可视区域。
- API 也不公开 Arrangement 的 Zoom Hot Spot 和当前可视时间范围，因此播放位置走带无法保证始终停留在屏幕中央。
- Device 选中后会尝试把它完整显示并尽量靠左；Rack、嵌套 Rack 和不同 Detail 面板宽度下，最终位置仍由 Live 决定。
- 内部 BrowserItem 导航刻意不控制屏幕 Browser；请以 Live 底部状态栏显示的路径为准。

## 故障排查

- **Live 完全没反应**：确认已加载 `Xone K3 Ableton` User Map、Latching Layers 为 OFF、Editor 已关闭、Live 的 Input/Output 都是 `XONE:K3`。
- **Control Surface 列表没有 Xone_K3**：确认文件夹层级是 `Remote Scripts/Xone_K3/__init__.py`，然后完全重启 Live。
- **有控制但没有灯**：确认 Live 的 MIDI Output 选择了 `XONE:K3`，XML 中 LED Mode 保持 Remote。
- **映射突然错乱**：先重新插拔 K3，并确认硬件仍加载正确 User Map。
- **更新脚本后没变化**：完全退出 Live，再替换文件并重新启动。Remote Script 不是所有改动都能热重载。
