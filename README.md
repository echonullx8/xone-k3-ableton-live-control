# Xone:K3 Ableton Live 12 Remote Script

[English guide](README_EN.md)

这是一个为 Allen & Heath Xone:K3 编写的 Ableton Live 12 MIDI Remote Script。它提供 4×4 Session Ring、Arrangement 设备导航、三层软件映射、Push 2 设备参数 Bank、脚本内 Browser 导航，以及由 Live 驱动的多色 LED 反馈。

本说明按仓库当前的 `Xone_K3/xonek3.py`、`elements.py`、`midi.py` 和 `Xone K3 Ableton.xml` 重新编写，不沿用旧版功能表。

## 文件与兼容性

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

安装 Remote Script 时必须保留完整的 `Xone_K3` 文件夹，不能只复制 `xonek3.py`。

- Allen & Heath Xone:K3
- Ableton Live 12，使用 Live 的 v3 Control Surface API
- MIDI Channel 16（Live 的 Python API 内部以从 0 开始的 Channel 15 表示）
- 随附 XML 的元数据：Xone Controller Editor `V1.0.1`、K3 Unit `V1.0.4`

其他 Live、Editor 或 K3 固件版本没有逐一验证。

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

设置完成后，K3 自身不会显示硬件 Layer 颜色，灯全部熄灭是正常状态。启动 Live、加载 `Xone_K3` 并操作一次 K3 后，灯光才由脚本接管：每按一次 `LAYER`，软件 Layer 依次切换，灯色为 **Layer 1 红 → Layer 2 黄 → Layer 3 绿 → Layer 1 红**。`SHIFT` 显示当前 Bank：**Bank 1 白 → Bank 2 黄 → Bank 3 绿**；每次切换主 Layer 后 Bank 回到 1，因此 `SHIFT` 回到白色。

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

## 四列轨道如何确定

- Session View：Session Ring 内的四条轨道。
- Arrangement View：当前选中轨道是第 1 列，后面三条可见轨道是第 2–4 列。
- Arrangement 选中 Return Track：所选 Return 是第 1 列，后面三条 Return 是第 2–4 列。
- Arrangement 选中 Master Track：四列轨道控件不映射；顶部最右 Master Volume 仍然有效。

Arrangement 的选轨只遍历真实轨道和 Return，不会选择 Automation Lane。Live 的公开接口不保证让 Arrangement 画面自动滚到新轨道。

## 所有 Layer 共用的控件

### 最上方四个旋钮

| 从左到右 | Session View | Arrangement View |
|---|---|---|
| 1 | Tempo，20–999 BPM | Tempo，20–999 BPM |
| 2 | 空置 | Layer 1：水平缩放；Layer 2/3：脚本内 Browser 导航 |
| 3 | 在当前轨道的完整 Device 树中前后选择 | 水平滚动 Arrangement 画面 |
| 4 | Master Volume | Master Volume |

第 3 个旋钮在 Arrangement 中调用 Live 的 Arranger `scroll_view`，移动的是时间轴可视区域，不是播放光标，也不会改变 `current_song_time`。

### 最上方四个按键

| 从左到右 | Session View | Arrangement View |
|---|---|---|
| 1 | 停止第 1 列轨道正在播放的 Clip | 上一个 Locator |
| 2 | 停止第 2 列轨道正在播放的 Clip | Layer 1：下一个 Locator；Layer 2/3：打开 Browser 项目或加载项目 |
| 3 | 停止第 3 列轨道正在播放的 Clip | Set/Delete Locator |
| 4 | 停止第 4 列轨道正在播放的 Clip | Back to Arrangement |

Session 中，对应轨道正在播放 Session Clip 时，上方按键灯常亮。Arrangement 中，第 4 个灯在 Back to Arrangement 可用时常亮；其他操作会短暂闪灯。

### 三排旋钮下方的按键

三个 Layer、两种 View 中功能不变：

| 按键排 | 功能 | 反馈 |
|---|---|---|
| HI | Track Activator / Mute | 轨道开启时橙色，Mute 时灭 |
| MID | Solo | Solo 时蓝色 |
| LOW | Arm | 可录音轨道 Arm 时红色；不可 Arm 的轨道不亮 |

### 四根推子

始终控制当前四列轨道的 Volume。

## Layer 与 3×4 旋钮

按 `LAYER` 循环 Layer 1、2、3。每次切入一个 Layer，该 Layer 都回到 Bank 1。

### Layer 1：Sends

三排旋钮控制当前四列轨道的三个 Send：

- Bank 1：Send 1–3
- Bank 2：Send 4–6
- Bank 3：Send 7–9

按 `SHIFT` 切换 Bank。Return 数量不足时，多出的旋钮不映射。

Arrangement 选中 Return Track 时，四列改为“所选 Return＋后面三条 Return”；脚本会跳过被禁用的 Send（包括不能发送给自身的 Send），并让后面的可用 Send 顺位补上。

### Layer 2：Device Bank + Pan

- 上面 8 个旋钮：当前 Appointed Device 的 8 个参数。
- 最下面 4 个旋钮：当前四列轨道的 Pan。
- `SHIFT`：在最多三个 Device Bank 中循环。

参数顺序优先读取 Live 内置的 `Push2.custom_bank_definitions`，也就是 Push 2 的设备 Bank 定义，而不是机械地取参数列表前八项。没有可用定义时，脚本才回退为原始参数列表，每 Bank 8 个参数。转动旋钮时，Live 状态栏显示 Layer、Bank、Device、参数名和当前值。

Arrangement 的 4×4 Device 列表在 Layer 2 使用精简模式：显示所有顶层 Device，并递归显示 Rack 里的 Rack；普通的 Rack 内部 Device 不占 Pad，因此更容易找到 Rack。

### Layer 3：Device Bank + Pan

Layer 3 的 3×4 旋钮与 Layer 2 相同，也有独立的三个 Device Bank。区别在 4×4 Device 列表：Layer 3 显示完整 Device 树，包括 Rack 内的普通 Device。

选择新的 Appointed Device 时，Layer 2 和 Layer 3 都回到各自的 Bank 1。

## Session View

### 4×4 Clip Pads

Pad 按“从左到右、从上到下”对应 4 条轨道 × 4 个 Scene；按下启动对应 Clip Slot。

- 空 Slot：灭
- 有 Clip、未播放：黄色
- 正在播放：绿色
- 正在录制，或排队录制：红色

### 最下方两个旋钮

| 控件 | 功能 |
|---|---|
| 左旋钮旋转 | 选择上一条/下一条可见轨道，并让它成为 Session Ring 第 1 列 |
| 左旋钮按下 | 开启/关闭 Arrangement Record；在 Session View 同样有效 |
| 右旋钮旋转 | 选择上一个/下一个 Scene，Ring 必要时跟随 |
| 右旋钮按下 | Re-enable Automation；只有存在可恢复的 Automation 时生效 |

右旋钮只选择 Scene，不会启动整个 Scene；Clip 仍由 4×4 Pad 启动。

## Arrangement View

### 4×4 Device Pads

Pad 按“从左到右、从上到下”选择当前轨道的 Device：

- Layer 1 / Layer 3：顶层 Device 从左到右；Rack 本体先计入，再按 Chain 顺序递归进入；最多 16 个。
- Layer 2：只显示顶层 Device 和任意深度的嵌套 Rack，不显示 Rack 内的普通 Device。

按下未选中的 Device 会选中并聚焦它；再次按下当前选中的 Device，会切换它的第一个参数，通常就是 Device On/Bypass。

灯光规则：

- 空位置：灭
- 未选中的普通 Device：绿色，不用颜色区分 On/Bypass
- 未选中的 Rack：灭，作为设备组的视觉分隔
- 选中且启用：黄色
- 选中且 Bypass：红色

从 K3 选中 Device 时，脚本会显示 Device Chain、选择其所属 Chain、展开目标路径、隐藏 Chain List，并尝试把 Device 完整显示且靠左。普通 Device 中，目标展开，其他普通 Device 折叠；Rack 不参加这条折叠规则。Rack、嵌套 Rack 和面板宽度不同，最终可视位置仍由 Live 决定。

用鼠标在 Live 中选 Device 时，K3 的 Pad 灯和 Layer 2/3 参数 Bank 会同步；脚本不会因为鼠标选择而自动改写其他 Device 的折叠状态。

### 最下方两个旋钮

| 控件 | 功能 |
|---|---|
| 左旋钮旋转 | Arrangement 垂直缩放 |
| 左旋钮按下 | 开启/关闭 Arrangement Record |
| 右旋钮旋转 | 在真实 Track 和 Return Track 中选择，不进入 Automation Lane |
| 右旋钮按下 | Re-enable Automation；只有存在可恢复的 Automation 时生效 |

## 脚本内 Browser

Browser 只在 **Arrangement View 的 Layer 2/3** 生效：

- 顶部第 2 个旋钮旋转：在当前层级移动选择。
- 在子级第一项继续向左：返回上一级。
- 顶部第 2 个按键按下：有子项时进入下一级；可加载时交给 Live 的当前 Browser 插入目标加载（通常是当前选中轨道）。
- 停在可预听项目上：短暂延迟后 Preview；继续移动、加载、离开 Browser Layer 或断开脚本时停止上一项 Preview。

第一次使用时，根列表从 Live 的颜色标签开始，然后是 Sounds、Drums、Instruments、Audio Effects、MIDI Effects、Max for Live、Plug-ins、Clips 和 Samples。选择路径显示在 Live 状态栏。这个功能使用 BrowserItem 作为唯一状态，不打开 Live 屏幕 Browser，也不尝试同步屏幕高亮。

## Layer / Shift 灯

| 灯 | 颜色 |
|---|---|
| LAYER | Layer 1 红、Layer 2 黄、Layer 3 绿 |
| SHIFT | Bank 1 白、Bank 2 黄、Bank 3 绿 |

`LAYER` 在 XML 中是 Note 12，`SHIFT` 是 Note 15。Latching Layers 必须关闭，脚本才能用三组反馈 Note 稳定控制颜色。

## 已知限制

- Live 的公开 Remote Script API 没有“选择真实轨道并保证 Arrangement 自动滚到该轨道”的完整命令；脚本能正确选轨，但画面可能不跟随。
- API 不公开 Arrangement 的 Zoom Hot Spot 或精确可视时间范围。本脚本只调用 Live 的水平滚动与缩放接口，不承诺让播放光标始终留在屏幕内。
- Device 左对齐是基于 Device Chain 选择和滚动的近似定位；复杂 Rack 中最终位置由 Live 决定。
- Browser 刻意不显示或控制屏幕 Browser，请以 Live 状态栏路径和听到的 Preview 为准。

## 故障排查

- **Live 没反应**：确认加载了 `Xone K3 Ableton` User Map、Latching Layers 为 OFF、Editor 已关闭，且 Control Surface 的 Input/Output 都是 `XONE:K3`。
- **列表中没有 Xone_K3**：确认路径是 `Remote Scripts/Xone_K3/__init__.py`，并完全重启 Live。
- **控制正常但不亮灯**：确认 Live MIDI Output 是 `XONE:K3`，XML 的 LED Mode 是 Remote。
- **Session Ring 没出现**：操作任意 K3 控件让脚本确认硬件已连接；仍无效时重新插拔 K3，并检查 MIDI 端口。
- **映射编号突然错乱**：重新插拔 K3，重新加载正确的 User Map；不要同时运行 Xone Controller Editor。
- **更新脚本后没变化**：完全退出 Live 后再替换 `Xone_K3` 文件夹，然后重新启动。Remote Script 改动不能依赖热重载。

## 获取更新

从仓库 `main` 分支下载最新代码，或使用 GitHub 的 **Code → Download ZIP**。Tagged Release 可能晚于 `main`，需要最新脚本时以 `main` 为准。
