# Xone:K3 Ableton Live 12 Remote Script

[中文说明](README.md)

This is an Ableton Live 12 MIDI Remote Script for the Allen & Heath Xone:K3. It provides a 4×4 Session Ring, Arrangement device navigation, three software layers, Push 2 device parameter banks, an internal Browser navigator, and multicolor LED feedback driven by Live.

This guide was rewritten from the current `Xone_K3/xonek3.py`, `elements.py`, `midi.py`, and `Xone K3 Ableton.xml` files. It does not reuse the obsolete control tables from earlier releases.

## Files and compatibility

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

Keep the complete `Xone_K3` folder when installing the Remote Script. `xonek3.py` does not work as a standalone file.

- Allen & Heath Xone:K3
- Ableton Live 12, using Live's v3 Control Surface API
- MIDI Channel 16 in the Editor; Live's zero-based Python API represents it as channel 15
- Included XML metadata: Xone Controller Editor `V1.0.1`, K3 Unit `V1.0.4`

Other Live, Editor, and K3 firmware versions have not been tested individually.

## Installation

### 1. Load the K3 map

1. Connect the K3 and open Xone Controller Editor.
2. Import `Xone K3 Ableton.xml`.
3. Save it to User Map slot 2, 3, or 4, then load that map on the K3.
4. Set hardware **Latching Layers to OFF**.
5. Keep the LEDs in **Remote** mode.
6. Quit Xone Controller Editor completely so it does not retain the MIDI port.

The map sends one set of control numbers. `LAYER` and `SHIFT` are managed by the script in software; the additional two note sets let Live request different colors from the same physical LEDs.

#### Set Latching Layers to OFF

This global hardware setting is not written by the XML and must be configured separately in K3 Power On Setup:

1. Disconnect power or USB from the K3.
2. Hold the bottom-right encoder labelled `POWER ON SETUP` while reconnecting the K3.
3. `SHIFT` flashes yellow and then remains yellow; the top-left matrix button lights to confirm Setup Mode.
4. Turn the bottom-right Setup encoder until the second button in the top matrix row lights. This is Latching Layers.
5. Press the Setup encoder to open the option.
6. Turn the encoder until **all option indicator LEDs are off**. This is **State 1: LATCHING LAYERS OFF**. States 2–5 are all ON, illuminate their corresponding range indicators, and must not be used.
7. Press the Setup encoder again to save and return to Setup Mode.
8. Press the yellow `SHIFT` button to exit. The K3 restarts.

After setup, the K3 does not display a hardware-layer color; all LEDs being off is normal. After Live starts, loads `Xone_K3`, and receives one K3 control message, the script takes over the LEDs. Each press of `LAYER` advances the software layer, with **Layer 1 red → Layer 2 yellow → Layer 3 green → Layer 1 red**. `SHIFT` shows the current bank: **Bank 1 white → Bank 2 yellow → Bank 3 green**. Entering another main layer resets its bank to 1, so `SHIFT` returns to white.

If `LAYER` must be pressed three times before Live reports one layer change, the hardware is still using State 2–5 instead of State 1.

### 2. Install the Remote Script

Create a `Remote Scripts` folder under the Ableton User Library and place the complete `Xone_K3` folder inside it:

```text
macOS:
~/Music/Ableton/User Library/Remote Scripts/Xone_K3

Windows (default User Library location):
%USERPROFILE%\Documents\Ableton\User Library\Remote Scripts\Xone_K3
```

If you moved the User Library, use the actual location shown in Live's settings.

### 3. Configure Live

1. Quit and relaunch Ableton Live completely.
2. Open `Settings/Preferences → Link, Tempo & MIDI`.
3. Select `Xone_K3` as the Control Surface.
4. Select `XONE:K3` for both Input and Output.

The Session Ring remains hidden while the K3 is disconnected or before the script has received K3 MIDI. After reconnecting, move or press any control to restore the Ring.

## How the four channel strips are chosen

- Session View: the four tracks inside the Session Ring.
- Arrangement View: the selected track is strip 1; the next three visible tracks are strips 2–4.
- If a Return Track is selected in Arrangement: that Return is strip 1; the next three Returns are strips 2–4.
- If the Master Track is selected in Arrangement: the four channel strips are unassigned; the top-right Master Volume encoder still works.

Arrangement track navigation only visits real tracks and Returns, never Automation Lanes. Live's public API does not guarantee that the Arrangement viewport will scroll to the newly selected track.

## Controls shared by all layers

### Four top encoders

| Left to right | Session View | Arrangement View |
|---|---|---|
| 1 | Tempo, 20–999 BPM | Tempo, 20–999 BPM |
| 2 | Unassigned | Layer 1: horizontal zoom; Layers 2/3: internal Browser navigation |
| 3 | Select through the current track's complete Device tree | Scroll the Arrangement viewport horizontally |
| 4 | Master Volume | Master Volume |

In Arrangement, encoder 3 calls Live's Arranger `scroll_view`. It moves the visible time range; it does not move the playhead or change `current_song_time`.

### Four top buttons

| Left to right | Session View | Arrangement View |
|---|---|---|
| 1 | Stop the playing Clip on channel strip 1 | Previous Locator |
| 2 | Stop the playing Clip on channel strip 2 | Layer 1: next Locator; Layers 2/3: open or load the current Browser item |
| 3 | Stop the playing Clip on channel strip 3 | Set/Delete Locator |
| 4 | Stop the playing Clip on channel strip 4 | Back to Arrangement |

In Session, a top-button LED remains lit while its track is playing a Session Clip. In Arrangement, button 4 remains lit while Back to Arrangement is available; the other actions flash briefly.

### Buttons below the three pot rows

Their behavior is the same in every layer and both Live views:

| Row | Action | Feedback |
|---|---|---|
| HI | Track Activator / Mute | Orange while the track is active; off while muted |
| MID | Solo | Blue while soloed |
| LOW | Arm | Red while an armable track is armed; off for tracks that cannot be armed |

### Four faders

They always control the Volume of the current four channel strips.

## Layers and the 3×4 pots

Press `LAYER` to cycle through Layers 1, 2, and 3. Entering a layer resets that layer to Bank 1.

### Layer 1: Sends

The three pot rows control three Sends across the current four channel strips:

- Bank 1: Sends 1–3
- Bank 2: Sends 4–6
- Bank 3: Sends 7–9

Press `SHIFT` to change banks. Pots beyond the available number of Returns are left unassigned.

When a Return Track is selected in Arrangement, the four strips become the selected Return plus the next three Returns. Disabled Sends, including self-sends, are skipped and the next available Sends move forward to fill the bank.

### Layer 2: Device banks + Pan

- Upper eight pots: eight parameters from the appointed Device.
- Bottom four pots: Pan for the current four channel strips.
- `SHIFT`: cycle through as many as three Device banks.

Parameter order comes from Live's built-in `Push2.custom_bank_definitions` whenever available. This reuses Push 2's named device banks instead of blindly taking the first eight raw parameters. Unsupported devices fall back to raw parameter order, eight parameters per bank. Turning a mapped pot shows the Layer, Bank, Device, parameter name, and value in Live's status bar.

In Arrangement, Layer 2 uses a compact 4×4 Device list: every top-level Device is shown, along with racks nested inside racks. Ordinary Devices inside racks do not consume pads, making racks easier to reach.

### Layer 3: Device banks + Pan

The 3×4 pots are the same as Layer 2 and have an independent set of up to three Device banks. The difference is the Arrangement 4×4 Device list: Layer 3 exposes the complete Device tree, including ordinary Devices inside racks.

Selecting a new appointed Device resets both Layer 2 and Layer 3 to their respective Bank 1.

## Session View

### 4×4 Clip pads

Pads map left to right, then top to bottom, over four tracks × four Scenes. Press a pad to fire its Clip Slot.

- Empty Slot: off
- Clip present and stopped: yellow
- Playing: green
- Recording or queued to record: red

### Two bottom encoders

| Control | Action |
|---|---|
| Turn left encoder | Select the previous/next visible track and make it the first Session Ring column |
| Press left encoder | Toggle Arrangement Record; this also works while Session View is open |
| Turn right encoder | Select the previous/next Scene; the Ring follows when required |
| Press right encoder | Re-enable Automation when automation can be restored |

The right encoder selects Scenes but does not launch a whole Scene. Individual Clips are launched with the 4×4 pads.

## Arrangement View

### 4×4 Device pads

Pads select Devices left to right, then top to bottom:

- Layers 1 and 3: top-level Devices from left to right; a rack itself comes first, followed recursively by its Chains in order; up to 16 entries.
- Layer 2: top-level Devices plus nested racks at any depth; ordinary Devices inside racks are hidden.

Press an unselected Device to select and focus it. Press the already selected Device again to toggle its first parameter, normally Device On/Bypass.

LED rules:

- Empty position: off
- Unselected ordinary Device: green, regardless of On/Bypass state
- Unselected rack: off, serving as a visual group separator
- Selected and enabled: yellow
- Selected and bypassed: red

When a Device is selected from the K3, the script opens Device Chain view, selects its containing Chain, expands the target path, hides the Chain List, and attempts to show the Device fully near the left edge. Among ordinary Devices, the target is unfolded and other ordinary Devices are folded; racks are excluded from that folding rule. Live still controls the final viewport position in complex or deeply nested racks.

Selecting a Device with the mouse updates the K3 pad LEDs and Layer 2/3 parameter banks. Mouse selection does not make the script rewrite the fold state of other Devices.

### Two bottom encoders

| Control | Action |
|---|---|
| Turn left encoder | Vertical Arrangement zoom |
| Press left encoder | Toggle Arrangement Record |
| Turn right encoder | Select real Tracks and Return Tracks, skipping Automation Lanes |
| Press right encoder | Re-enable Automation when automation can be restored |

## Internal Browser

Browser control is active only in **Arrangement View, Layers 2 and 3**:

- Turn top encoder 2 to move within the current level.
- Turn left past the first child to return to the parent level.
- Press top button 2 to enter an item with children or ask Live to load a loadable item at its current Browser insertion target, normally the selected track.
- A loadable selection is previewed after a short delay. Moving again, loading, leaving a Browser-enabled layer, or disconnecting stops the previous preview.

On first use, the root begins with Live's color-label items, followed by Sounds, Drums, Instruments, Audio Effects, MIDI Effects, Max for Live, Plug-ins, Clips, and Samples. The current path appears in Live's status bar. BrowserItem is the single source of truth: the script deliberately does not open Live's on-screen Browser or try to synchronize its visible highlight.

## Layer and Shift LEDs

| LED | Colors |
|---|---|
| LAYER | Layer 1 red, Layer 2 yellow, Layer 3 green |
| SHIFT | Bank 1 white, Bank 2 yellow, Bank 3 green |

`LAYER` is Note 12 in the XML; `SHIFT` is Note 15. Latching Layers must be off so the script can use the three feedback-note sets for stable color control.

## Known limitations

- Live's public Remote Script API has no complete command for “select a real track and guarantee that Arrangement scrolls it into view.” Track selection is correct, but the viewport may not follow.
- The API does not expose Arrangement's Zoom Hot Spot or precise visible time range. The script uses Live's horizontal scroll and zoom calls but cannot guarantee that the playhead remains on screen.
- Device left positioning is an approximation based on Device Chain selection and scrolling. Live decides the final position in complex racks.
- The internal Browser intentionally does not display or control Live's on-screen Browser. Use the status-bar path and the audible preview as feedback.

## Troubleshooting

- **Live does not react:** load the `Xone K3 Ableton` User Map, set Latching Layers to OFF, quit the Editor, and select `XONE:K3` for both Control Surface Input and Output.
- **Xone_K3 is missing from the Control Surface list:** verify `Remote Scripts/Xone_K3/__init__.py`, then relaunch Live completely.
- **Controls work but LEDs do not:** set Live's MIDI Output to `XONE:K3` and keep the XML LEDs in Remote mode.
- **The Session Ring is missing:** move or press any K3 control so the script can confirm the hardware connection. If necessary, reconnect the K3 and check its MIDI port.
- **Control numbers suddenly look wrong:** reconnect the K3, reload the correct User Map, and do not leave Xone Controller Editor open.
- **A script update appears to do nothing:** quit Live completely before replacing the `Xone_K3` folder, then relaunch it. Do not rely on hot reload for Remote Script changes.

## Getting updates

Download the latest code from the repository's `main` branch or use GitHub's **Code → Download ZIP**. Tagged Releases may lag behind `main`; use `main` when you need the current script.
