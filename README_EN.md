# Xone:K3 Ableton Live 12 Remote Script v2.0

[中文说明](README.md)

An independently developed Ableton Live 12 MIDI Remote Script for the Allen & Heath Xone:K3. It provides software-controlled layers, a 4×4 Session Ring, Arrangement device navigation, Push 2 parameter banks, and RGB feedback driven by Live.

> This guide was written from the actual `Xone_K3/xonek3.py`, `Xone_K3/elements.py`, `Xone_K3/midi.py`, and `Xone K3 Ableton.xml` files in this repository.

## v2.0 Highlights

- Three software layers with RGB feedback driven by Live
- Session Ring, Clip/Scene launching, and immediate Clip-state LEDs
- Arrangement Device, Rack/Chain, and track navigation
- Push 2 Device parameter banks, internal BrowserItem navigation, and automatic Preview
- Track/Return Sends and a four-track EQ Eight performance layer

## Compatibility

- Allen & Heath Xone:K3
- Ableton Live 12.3 or later (the script uses Ableton's v3 Control Surface API; Layer 3 automatic EQ Eight insertion uses `Track.insert_device`, introduced in Live 12.3)
- Xone Controller Editor; the included XML was saved by Editor `V1.0.1` for K3 Unit `V1.0.4`
- MIDI Channel 16 in the Editor XML (represented internally as channel 15 by Ableton's zero-based Python API)

Other Live, Editor, and firmware versions have not been verified.

## Package Contents

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

All four Python files are required. `xonek3.py` is not a standalone installation.

The complete package is available from GitHub Releases. After extraction it contains the `Xone_K3` script folder, the K3 Editor XML, and both guides.

## Installation

### 1. Load the hardware map into the K3

1. Connect the Xone:K3 and open Xone Controller Editor.
2. Import `Xone K3 Ableton.xml`.
3. Save it to User Map slot 2, 3, or 4 on the K3, then load that map.
4. Set the K3's **Latching Layers to OFF**. The script listens to the Layer 1 control numbers and switches its three layers in software; Layer 2/3 note numbers are used for multicolor LED feedback.
5. Quit Xone Controller Editor completely so it does not retain the MIDI port.

To enter Power On Setup, disconnect power, hold the encoder labelled `POWER ON SETUP`, then reconnect it. Select the second setup item, Latching Layers; choose the first state, `OFF`; save and press SHIFT to exit.

### 2. Install the Remote Script

Create a `Remote Scripts` folder inside the Ableton User Library, then place the complete `Xone_K3` folder inside it:

```text
macOS:
~/Music/Ableton/User Library/Remote Scripts/Xone_K3

Windows:
%USERPROFILE%\Documents\Ableton\User Library\Remote Scripts\Xone_K3
```

Do not copy only `xonek3.py`. The `Xone_K3` folder must contain all four Python files.

### 3. Configure Ableton Live

1. Quit and relaunch Ableton Live completely.
2. Open `Settings/Preferences → Link, Tempo & MIDI`.
3. Select `Xone_K3` as the Control Surface.
4. Select `XONE:K3` for both Input and Output.

The Session Ring is hidden while the K3 is disconnected or before the script receives MIDI from it. It returns after reconnection and the next control message.

## Control Model

### Current four tracks

- Session View: the four tracks inside the Session Ring.
- Arrangement View: the selected track is column 1; the next three visible tracks are columns 2–4.
- When a Return Track is selected in Arrangement: that Return is column 1 and the next three Returns are columns 2–4.
- The lower-right encoder selects tracks through Live's Arranger navigation. Live does not guarantee that the newly selected track will be scrolled into the visible viewport.

### Global top encoders

| Left to right | Layer 1 | Layer 2 |
|---|---|---|
| 1 | Tempo, 20–999 BPM | Tempo, 20–999 BPM |
| 2 | Session: hierarchical Browser navigation; Arrangement: horizontal zoom | Session/Arrangement: hierarchical Browser navigation |
| 3 | Session: select Device focus on the current track; Arrangement: accelerated play-position scrub | Session: select Device focus on the current track; Arrangement: accelerated play-position scrub |
| 4 | Master Volume | Master Volume |

In Layer 3 Arrangement View, all four top encoders control Bell Frequency for the corresponding tracks. In Layer 3 Session View, encoder 3 is assigned to Device-focus selection while the other three control Bell Frequency for their corresponding columns.

Browser navigation uses the script's internal BrowserItem list and does not open or move the highlighted item in Live's on-screen Browser. The top level begins with Live's color labels, starting at Favorites, followed by categories such as Sounds and Drums. Turning selects a relative item at the current level and Live's status bar shows the full current path. After a short delay, a previewable selected item is previewed automatically; turning again, loading the item, leaving a Browser-enabled layer, or disconnecting the script stops the previous preview. Turning left beyond the first child returns to the parent level. Pressing top encoder button 2 enters a folder or loads a loadable item into the selected track. The status message, preview, and loaded item use the same BrowserItem. The final insertion position follows Live's current track and Device insertion rules.

### Top encoder buttons

| Left to right | Session View | Arrangement View |
|---|---|---|
| 1 | Stop clips on current track 1 | Previous Locator |
| 2 | Stop clips on current track 2 | Next Locator |
| 3 | Stop clips on current track 3 | Set/Delete Locator |
| 4 | Stop clips on current track 4 | Back to Arrangement |

In Arrangement, button 4 stays lit while Back to Arrangement is available. In Session, each button stays lit while its track is playing a Session clip.

Exception: in Session Layer 1 and in Layer 2 in either view, button 2 is claimed by the Browser for Enter/Load instead of Clip Stop or Next Locator.

### 3×4 pots

Press `LAYER` to cycle through the three software layers. Entering any layer resets that layer to Bank 1.

#### Layer 1: Track Sends

The three rows control three Sends for the current four tracks:

- Bank 1: Sends 1–3
- Bank 2: Sends 4–6
- Bank 3: Sends 7–9

Press `SHIFT` to change bank. Pots with no corresponding Return Track remain unassigned.

When a Return Track is selected in Arrangement, Layer 1 controls the available Sends on the selected Return and the next three Returns. Disabled Sends, including self-sends, are skipped and later available Sends move forward.

#### Layer 2: Device Bank + Balance

- Upper eight pots: eight parameters from the appointed Device.
- Bottom four pots: Balance/Pan for the current four tracks.
- Press `SHIFT` to cycle through up to three Device banks.

Parameter order comes from Live's built-in `Push2.custom_bank_definitions`, including Live's designed bank names and ordering. If a Device cannot use that bank definition, the script falls back to raw Device parameters in groups of eight.

Selecting a new Device, re-entering Layer 2, or leaving and returning to the software layer resets it to the first bank. Turning a mapped pot displays the bank, Device, parameter name, and current value in Live's status bar.

#### Layer 3: EQ Eight

The four columns correspond to the current four tracks:

- HI row: Low Cut Frequency
- MID row: Bell Gain
- LOW row: High Cut Frequency
- Four top encoders: Bell Frequency for the corresponding tracks

Entering Layer 3 never edits the Set. Pressing `SHIFT` initializes only the currently selected track. Selecting a Group Track processes the Group itself, not its child tracks.

The script first looks for an EQ Eight with enabled Low Cut, Bell, and High Cut roles whose target parameters can be controlled directly. If found, that EQ is selected and unfolded. If an existing EQ Eight does not yet provide all three roles, Band 1 is initialized as Low Cut, Band 4 as Bell, and Band 8 as High Cut; Low Cut Frequency is set to 10 Hz and High Cut Frequency to 22 kHz. If an existing EQ is inaccessible because its target parameters are mapped to Rack Macros, the script inserts a normal EQ Eight at the end of the selected track and applies the same initialization.

Automatic native-device insertion requires `Track.insert_device`, available in Ableton Live 12.3 and later.

### Three button rows below the pots

These functions do not change with the software layer or Live view:

| Row | Function | LED |
|---|---|---|
| HI | Track Activator / Mute | Orange while the track is active; off while muted |
| MID | Solo | Blue while soloed |
| LOW | Arm | Red while an armable track is armed; unavailable on Group/Return tracks |

### Four faders

Volume for the current four tracks in every software layer and both Live views.

## Session View

### 4×4 buttons

The grid maps left-to-right, then top-to-bottom, to four tracks × four scenes inside the Session Ring:

- Empty slot: off
- Clip present and stopped: yellow
- Playing: green
- Recording or queued to record: red

### Bottom encoders

| Control | Function |
|---|---|
| Turn left encoder | Select the previous/next visible track and make it the first column of the Session Ring |
| Press left encoder | Toggle Arrangement Record; this also works from Session View |
| Turn right encoder | Select the previous/next Scene; the Ring follows when needed |
| Press right encoder | Fire the selected Scene |

## Arrangement View

### 4×4 Device selection

The 16 buttons select Devices on the current track, assigned left-to-right and then top-to-bottom. Device order is:

1. top-level Devices from left to right;
2. a Rack itself is counted first;
3. then Chain 1, Chain 2, and so on, with Devices left-to-right inside each Chain;
4. nested Racks use the same depth-first traversal;
5. only the first 16 items are mapped.

Press an unselected Device to select and focus it. Press the currently selected Device again to toggle Device On/Bypass.

LED states:

- Empty position: off
- Unselected normal Device: green, whether on or bypassed
- Unselected Rack: off, acting as a visual group separator
- Selected and on: yellow
- Selected and bypassed: red

When a Device is selected, the script expands the selected normal Device and collapses the other normal Devices. For a Device inside a Rack or Drum Rack, it selects every containing Chain from outermost to innermost, expands the full Rack path, and shows the current Chain Devices. Nested Racks follow the same rule.

### Bottom encoders

| Control | Function |
|---|---|
| Turn left encoder | Vertical Arrangement zoom |
| Press left encoder | Toggle Arrangement Record |
| Turn right encoder | Select a track through Arranger up/down navigation |
| Press right encoder | Re-enable Automation when automation can be restored |

Horizontal Arrangement zoom is assigned to top encoder 2 in Layer 1; it does not use a press-and-turn gesture.

## Layer and Bank LEDs

Actual colors in the included XML:

| Indicator | Colors |
|---|---|
| LAYER | Layer 1 red, Layer 2 yellow, Layer 3 green |
| SHIFT | Bank 1 white, Bank 2 yellow, Bank 3 green |

Latching Layers must be off so the script can use the three layer note numbers as independent RGB feedback channels.

## Known Limitations

- Live's public Remote Script API has no direct command to make the Arrangement scrollbar precisely follow the selected track. The script uses the same kind of directional `scroll_view` navigation used by native control surfaces, but Live may change selection or focus without moving the visible viewport.
- The API does not expose the Arrangement Zoom Hot Spot or visible time range, so play-position scrubbing cannot guarantee that the position remains centered on screen.
- Device selection attempts to show the complete Device and place it as far left as possible. Live still decides the final position for Racks, nested Racks, and different Detail panel widths.
- Internal BrowserItem navigation intentionally does not control the on-screen Browser. Use the path shown in Live's status bar.

## Troubleshooting

- **Live does not react:** verify that the `Xone K3 Ableton` User Map is loaded, Latching Layers is OFF, the Editor is closed, and both Live ports are set to `XONE:K3`.
- **Xone_K3 is missing from Control Surfaces:** verify the path is `Remote Scripts/Xone_K3/__init__.py`, then restart Live completely.
- **Controls work but LEDs do not:** set the Control Surface Output to `XONE:K3` and keep the XML LEDs in Remote mode.
- **Mappings suddenly become incorrect:** reconnect the K3 and verify that the correct User Map is still active.
- **A script update has no effect:** quit Live completely before replacing the files, then relaunch it. Not every Remote Script change can be hot-reloaded.
