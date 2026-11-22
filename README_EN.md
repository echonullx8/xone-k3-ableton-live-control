# Xone:K3 Ableton Live 12 Remote Script

[中文说明](README.md)

A Live 12 Remote Script for Allen & Heath Xone:K3, with Session clip launching, Arrangement device navigation, Push parameter banks, Browser navigation and multicolor feedback.

The three layers provide Send, device and live-performance controls:

| Layer | Use |
|---|---|
| 1 | Adjust Sends for four tracks |
| 2 | Adjust device parameters and four track pans |
| 3 (Session) | Performance layout for live shows: launch clips, mute tracks, select devices, adjust twelve parameters and control Arrangement recording |

During a performance, select another track, Return or Main to adjust its devices while the clips, mute buttons and faders continue to control the current four-track window.

## Requirements and installation

- Ableton Live 12; Allen & Heath Xone:K3. No additional API or developer tools need to be installed.
- MIDI channel 16; hardware **Latching Layers OFF**; LED mode **Remote**.
- XML metadata: Controller Editor V1.0.1 and K3 V1.0.4. Other combinations have not been individually verified.

1. Import `Xone K3 Ableton.xml` into Xone Controller Editor, save it to User Map 2, 3 or 4 and activate that map. **Updating Python alone does not update hardware LED colors.**
2. Set Latching Layers OFF in the hardware Power On Setup; this setting is not stored by the XML. Disconnect the K3, hold the bottom-right POWER ON SETUP encoder and reconnect it. Rotate to the second button in the top grid row (Latching Layers), press the encoder, then rotate until all option indicator LEDs are off: **State 1, OFF**. Press to save and press SHIFT to exit. States 2–5 are ON and must not be used.
3. Keep LED mode Remote and close the Editor to release its MIDI ports.
4. Install the entire `Xone_K3` folder, including `__init__.py`, `elements.py`, `midi.py` and `xonek3.py`, under your User Library's `Remote Scripts` folder:

```text
macOS default:
~/Music/Ableton/User Library/Remote Scripts/Xone_K3

Windows default:
%USERPROFILE%\Documents\Ableton\User Library\Remote Scripts\Xone_K3
```

Use the actual User Library location shown in Live if customized. An existing installation inside Live's application resources must also be updated; avoid leaving different copies of the same surface installed.

5. Fully quit and reopen Live. In Settings/Preferences → Link, Tempo & MIDI, select `Xone_K3` as the Control Surface and `XONE:K3` for both Input and Output.

Before Live takes over, dark hardware LEDs are expected with Latching Layers OFF. Operate a control after connecting: the Session Ring appears once the script receives MIDI. If three LAYER presses produce only one software layer change, hardware Latching Layers are still enabled.

## Layers and indicators

LAYER cycles software layers: **1 yellow → 2 green → 3 red**. Entering a layer resets its bank to 1.

In Session Layers 1/2 and Arrangement, SHIFT cycles Send/parameter banks, with white/yellow/red bank feedback. **In Session Layer 3, SHIFT instead toggles Arrangement Record: steady red while recording, dark otherwise.** Changes made with the mouse or other controllers are reflected too.

## Session View: track selection and clip controls

Top encoder 2 selects visible normal tracks, then Returns, then Main; reverse rotation goes back. This applies to **all three Session layers**. It displays the Device Chain and focuses the track's selected device when available, without changing the Session Ring or fader assignments.

The four faders and clip columns continue to address the four normal tracks inside the Session Ring. Selecting Return/Main lets you control their devices but does not assign them to those faders. Clip pads launch individual slots, not entire scenes.

### Shared Session controls

| Control | Function |
|---|---|
| Top encoder 1 turn | Tempo, 20–999 BPM, 0.2 BPM per step |
| Top encoder 2 turn | Select a track without moving the control window |
| Top encoder 3 turn | Layers 1/2: select within the full device tree; Layer 3: top-level devices only |
| Top encoder 4 turn | Main volume |
| Four top encoder presses | Stop clips on the corresponding four controlled tracks |
| Four faders | Volume of the four tracks in the Session Ring |
| 4×4 pads | Launch slots across four tracks and four scenes |

Clip feedback: empty dark; stopped clip yellow; playing green; recording or queued recording red. The Ring hides while disconnected or before incoming hardware MIDI is detected.

### Layer 1: Sends

The three pot rows control three Sends for the four controlled tracks. SHIFT cycles Sends 1–3, 4–6 and 7–9. Unavailable sends remain unmapped.

### Layer 2: Device Bank + Pan

The first eight pots control one bank of the Appointed Device; the last four control panning for the four controlled tracks. SHIFT cycles up to three banks. Live's Push2 bank definitions take priority; unavailable definitions fall back to raw device parameter order.

In Layers 1/2, button rows are Mute, Solo and Arm: active tracks yellow, Solo blue, Arm red. Bottom-left rotation selects a normal track and moves the track window; bottom-right rotation selects a scene and scrolls the four-row window when needed. Bottom-left press toggles Arrangement Record; bottom-right press re-enables automation.

## Session Layer 3: Performance for live shows

### Devices and parameters

| Control | Function |
|---|---|
| Top encoder 3 turn | Select top-level devices on the selected track; do not enter racks |
| Middle and bottom button rows | Select one of eight displayed devices and focus it in Live; press the selected device again to toggle Device On/Bypass |
| Twelve pots | Twelve parameter slots per page, following Push bank order |
| Hold bottom-left encoder and turn | Change parameter pages; stop at the first/last page |

The eight-device window stays fixed while selection remains inside it. Selecting device 9 shifts it forward by one; reverse navigation scrolls only when selection leaves the window. **Device-button presses never rearrange the window.** Changing tracks resets the device window and parameter page; changing devices resets the parameter page.

Page 1 contains eight slots from Push bank 1 and four from bank 2. Page 2 continues with the remaining four from bank 2. Missing slots stay empty rather than compressing the order. If banking is unavailable, raw parameters are used after skipping Device On. Parameter takeover remains enabled across device/page changes. Actual Macro order depends on Push definitions; it is not guaranteed to match every device's visual knob order.

### Mixing and recording

| Control | Function |
|---|---|
| Top button row beneath the pots | Mute the four controlled tracks |
| Bottom-left turn | Move the track window one track per step; clips, mutes and faders move together; selected track stays unchanged |
| Bottom-right turn | Move the scene window one scene per step without changing scene selection |
| Bottom encoder presses alone | No action; holding the left encoder while turning changes parameter pages |
| SHIFT | Toggle Arrangement Record; steady red while recording, dark otherwise |
| LAYER | Continue cycling layers |

### Eight device-button LEDs

Devices and racks share the same rules:

| State | Color |
|---|---|
| Empty / unselected and bypassed | Dark |
| Unselected and enabled | Blue |
| Selected and enabled | Yellow |
| Selected and bypassed | Red |

LEDs show the current selection and enabled state. If the colors do not match, check that the supplied XML is loaded on the hardware.

## Arrangement View

Switch Live to Arrangement View to use the following controls.

| Control | Function |
|---|---|
| Top encoder 1 turn / press | Tempo / previous locator |
| Top encoder 2 turn / press, Layer 1 | Horizontal zoom / next locator |
| Top encoder 2 turn / press, Layers 2/3 | Browser navigation / enter folder or load item |
| Top encoder 3 turn / press | Horizontal view scrolling / set or delete locator |
| Top encoder 4 turn / press | Main volume / Back to Arrangement |
| Bottom-left turn / press | Vertical zoom / Arrangement Record |
| Bottom-right turn / press | Select normal and Return tracks / re-enable automation |

The mixer window begins at the selected track, or selected Return when applicable. Selecting Main leaves the four-track controls unmapped. Button rows are Mute/Solo/Arm. Layer 1 pots control Sends; Layer 2/3 pots control eight device parameters and four pans. SHIFT cycles banks.

The 4×4 pads select devices; pressing the selected device toggles it. Layer 2 lists top-level devices and nested racks; Layers 1/3 list the full device tree. Arrangement pad colors: unselected ordinary devices green regardless of enabled state; unselected racks dark; selected enabled yellow; selected bypassed red.

Browser navigation operates only in Arrangement Layers 2/3: turn top encoder 2 to navigate, turn backward past the first child to return to the parent, and press to enter or load. Previewable items play after a short delay; moving, loading or leaving stops the previous preview. The path appears in Live's status bar; the on-screen Browser selection is not synchronized.

## Limits and troubleshooting

- Device focusing, folding and approximate positioning depend on Live's public API and rack layout. Left alignment and automatic scrolling to a selected track are not guaranteed.
- Arrangement horizontal scrolling changes the visible region, not the playback position.
- Fully restart Live after replacing Python files. Write XML separately to the hardware and close the Editor.
- Wrong colors: check the current XML, Latching Layers OFF, LED Remote, and Live's MIDI Output.

Download the current version from `main`. Tagged releases may be older than `main`.
