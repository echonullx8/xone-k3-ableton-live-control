import Live
import time

from ableton.v3.control_surface import ControlSurface, ControlSurfaceSpecification
from ableton.v3.control_surface.banking_util import BankingInfo, create_parameter_bank
from ableton.v3.control_surface.components import SessionComponent
from Push2.custom_bank_definitions import BANK_DEFINITIONS

from .elements import Elements, CHANNEL
from .midi import (
    FEEDBACK_LAYER_NOTE_OFFSET,
    L1_BUTTONS,
    L1_HI_POTENT_BTNS,
    L1_LAYER,
    L1_LOW_POTENT_BTNS,
    L1_MID_POTENT_BTNS,
    L1_SHFT,
    L1_TOP_ENCODER_BTNS,
    L2_LAYER,
    L2_SHFT,
    L3_LAYER,
    L3_SHFT,
)


class Specification(ControlSurfaceSpecification):
    elements_type = Elements
    num_tracks = 4
    num_scenes = 4


class XoneK3(ControlSurface):
    """Xone:K3 workflow for software-controlled layers and RGB feedback."""

    _PAD_NOTES = tuple(tuple(row) for row in L1_BUTTONS)
    _MUTE_NOTES = tuple(L1_HI_POTENT_BTNS[0])
    _SOLO_NOTES = tuple(L1_MID_POTENT_BTNS[0])
    _ARM_NOTES = tuple(L1_LOW_POTENT_BTNS[0])
    _TOP_BUTTON_NOTES = tuple(L1_TOP_ENCODER_BTNS[0])
    _LAYER_NOTES = (L1_LAYER, L2_LAYER, L3_LAYER)
    _SHIFT_NOTES = (L1_SHFT, L2_SHFT, L3_SHFT)

    def __init__(self, c_instance=None):
        self._active_layer = 0
        self._layer_banks = [0, 0, 0]
        self._session_track_offset = 0
        self._session_scene_offset = 0
        self._bottom_left_pressed = False
        self._last_cursor_turn = None
        self._led_states = {}
        self._session_pad_signature = None
        self._push_banking_info = BankingInfo(BANK_DEFINITIONS)
        self._push_parameter_bank = None
        self._push_bank_device = None
        self._push_bank_failed_device = None
        self._bound_pot_infos = [None] * 12
        self._value_listeners = []
        self._track_transport_listeners = []
        self._listened_transport_tracks = ()
        self._hardware_connected = False
        self._disconnected = False
        super().__init__(Specification(), c_instance=c_instance)

    def setup(self):
        super().setup()

        with self.component_guard():
            self._session = SessionComponent(name='Session', is_enabled=False)
            if self._session_ring:
                self._session_ring.set_enabled(self._hardware_connected)

        self._add_matrix_listeners(self.elements.top_encoders_raw, self._on_top_encoder)
        self._add_matrix_listeners(self.elements.top_buttons_raw, self._on_top_button)
        self._add_matrix_listeners(self.elements.mute_buttons_raw, self._on_mute)
        self._add_matrix_listeners(self.elements.solo_buttons_raw, self._on_solo)
        self._add_matrix_listeners(self.elements.arm_buttons_raw, self._on_arm)
        self._add_matrix_listeners(self.elements.pot_controls_raw, self._on_pot)
        self._add_matrix_listeners(self.elements.pad_buttons_raw, self._on_pad)
        self._add_matrix_listeners(self.elements.bottom_encoders_raw, self._on_bottom_encoder)
        self._add_matrix_listeners(self.elements.bottom_buttons_raw, self._on_bottom_button)

        self._add_value_listener(self.elements.shift_button, self._on_shift)
        self._add_value_listener(self.elements.layer_button, self._on_layer)

        self.application.view.add_focused_document_view_listener(self._on_view_changed)
        self.song.view.add_selected_track_listener(self._on_selected_track_changed)
        self.song.add_visible_tracks_listener(self._on_visible_tracks_changed)
        self.song.add_is_playing_listener(self._on_transport_state_changed)
        if hasattr(self.song, 'add_appointed_device_listener'):
            self.song.add_appointed_device_listener(self._on_appointed_device_changed)

        self._on_view_changed()
        self._refresh_leds()
        self.schedule_message(1, self._scheduled_session_refresh)
        self.schedule_message(5, self._scheduled_refresh)

    def port_settings_changed(self):
        self._set_hardware_connected(False)
        super().port_settings_changed()

    def receive_midi(self, midi_bytes):
        self._set_hardware_connected(True)
        super().receive_midi(midi_bytes)

    def receive_midi_chunk(self, midi_chunk):
        if midi_chunk:
            self._set_hardware_connected(True)
        super().receive_midi_chunk(midi_chunk)

    def _set_hardware_connected(self, connected):
        connected = bool(connected)
        if connected == self._hardware_connected:
            return
        self._hardware_connected = connected
        self._led_states.clear()
        self._session_pad_signature = None
        session_ring = getattr(self, '_session_ring', None)
        if session_ring:
            session_ring.set_enabled(connected)
        if connected:
            self.schedule_message(1, self._refresh_after_reconnect)

    def _refresh_after_reconnect(self):
        if self._hardware_connected and not self._disconnected:
            self._refresh_leds_safely(force=True)

    # ------------------------------------------------------------------
    # Listener setup
    # ------------------------------------------------------------------

    def _add_matrix_listeners(self, controls, handler):
        for index, control in enumerate(controls):
            callback = lambda value, i=index: handler(i, value)
            self._add_value_listener(control, callback)

    def _add_value_listener(self, control, callback):
        control.add_value_listener(callback)
        self._value_listeners.append((control, callback))

    # ------------------------------------------------------------------
    # Global top encoders and buttons
    # ------------------------------------------------------------------

    def _on_top_encoder(self, index, value):
        delta = self._relative_delta(value)
        if index == 0:
            self.song.tempo = max(20.0, min(999.0, self.song.tempo + delta * 0.2))
        elif index == 2 and self._is_arranger():
            multiplier = self._cursor_speed_multiplier()
            self.song.current_song_time = max(
                0.0,
                self.song.current_song_time + delta * multiplier,
            )
        elif index == 3:
            volume = self.song.master_track.mixer_device.volume
            volume.value = max(volume.min, min(volume.max, volume.value + delta * 0.005))

    def _on_top_button(self, index, value):
        if not value:
            self.schedule_message(1, lambda: self._refresh_top_leds(force=True))
            return

        if self._is_arranger():
            if index == 0 and self.song.can_jump_to_prev_cue:
                self.song.jump_to_prev_cue()
            elif index == 1 and self.song.can_jump_to_next_cue:
                self.song.jump_to_next_cue()
            elif index == 2:
                self.song.set_or_delete_cue()
            elif index == 3 and self.song.back_to_arranger:
                self.song.back_to_arranger = False
        else:
            tracks = self._controlled_tracks()
            if index < len(tracks):
                tracks[index].stop_all_clips()

        self._flash_top_button(index)

    # ------------------------------------------------------------------
    # Mixer controls
    # ------------------------------------------------------------------

    def _on_mute(self, index, value):
        if value:
            track = self._track_at(index)
            if track:
                track.mute = not track.mute
        self.schedule_message(1, lambda: self._refresh_mixer_leds(force=True))

    def _on_solo(self, index, value):
        if value:
            track = self._track_at(index)
            if track:
                track.solo = not track.solo
        self.schedule_message(1, lambda: self._refresh_mixer_leds(force=True))

    def _on_arm(self, index, value):
        if value:
            track = self._track_at(index)
            if track and track.can_be_armed:
                track.arm = not track.arm
        self.schedule_message(1, lambda: self._refresh_mixer_leds(force=True))

    # ------------------------------------------------------------------
    # 4x4 matrix
    # ------------------------------------------------------------------

    def _on_pad(self, index, value):
        if not value:
            self.schedule_message(1, lambda: self._refresh_pad_leds(force=True))
            return

        if self._is_arranger():
            devices = self._flatten_selected_track_devices()
            device_index = self._device_index_for_pad(index)
            if device_index < len(devices):
                device = devices[device_index]
                previous_device = self.song.appointed_device
                was_selected = device == previous_device
                if was_selected:
                    self._toggle_device(device)
                self._focus_device(device)
                self._bind_pots()
        else:
            row, column = divmod(index, 4)
            tracks = self._controlled_tracks()
            scene_index = self._session_ring.scene_offset + row
            if column < len(tracks) and scene_index < len(self.song.scenes):
                tracks[column].clip_slots[scene_index].fire()

        self.schedule_message(1, lambda: self._refresh_pad_leds(force=True))

    # ------------------------------------------------------------------
    # Bottom encoders
    # ------------------------------------------------------------------

    def _on_bottom_encoder(self, index, value):
        delta = self._relative_delta(value)
        if not delta:
            return

        if self._is_arranger():
            if index == 0:
                if self._bottom_left_pressed:
                    self._zoom_arranger(delta)
                else:
                    self._zoom_arranger_vertical(delta)
            else:
                self._select_relative_track(delta)
        else:
            if index == 0:
                if self._bottom_left_pressed:
                    self._move_session_ring(0, delta)
                else:
                    self._move_session_ring(delta, 0)
            else:
                self._select_relative_scene(delta)

    def _on_bottom_button(self, index, value):
        if index == 0:
            self._bottom_left_pressed = bool(value)
        elif value:
            if self._is_arranger():
                self.song.record_mode = not self.song.record_mode
            else:
                self.song.view.selected_scene.fire()

    def _on_shift(self, value):
        if not value:
            self.schedule_message(1, lambda: self._refresh_shift_led(force=True))
            return

        if self._active_layer == 0:
            self._layer_banks[0] = (self._layer_banks[0] + 1) % 3
            self._bind_pots()
            start = self._layer_banks[0] * 3 + 1
            self.show_message(
                'Xone K3 Layer 1 · Sends {}–{}'.format(start, start + 2)
            )
        elif self._active_layer == 1:
            self._cycle_push_bank()

        self._refresh_shift_led()

    # ------------------------------------------------------------------
    # Software layers
    # ------------------------------------------------------------------

    def _on_layer(self, value):
        if value:
            self._active_layer = (self._active_layer + 1) % 3
            self._reset_active_bank()
            self._bind_pots()
            self._refresh_layer_led()
            self._refresh_shift_led()
            self.show_message('Xone K3 Layer {}'.format(self._active_layer + 1))
        else:
            self.schedule_message(1, lambda: self._refresh_layer_led(force=True))

    def _reset_active_bank(self):
        self._layer_banks[self._active_layer] = 0
        if (
            self._active_layer == 1
            and self._push_parameter_bank is not None
            and self._push_bank_device == self.song.appointed_device
        ):
            self._push_parameter_bank.index = 0

    def _on_pot(self, index, value):
        if index >= len(self._bound_pot_infos):
            return
        info = self._bound_pot_infos[index]
        if info is not None:
            label, parameter = info
            self._show_parameter(label, parameter)

    def _show_parameter(self, label, parameter):
        try:
            value = parameter.str_for_value(parameter.value)
        except AttributeError:
            value = str(parameter.value)
        self.show_message('{}: {}'.format(label, value))

    def _bind_pots(self):
        pots = self.elements.pot_controls_raw
        self._bound_pot_infos = [None] * 12
        for control in pots:
            control.release_parameter()

        if self._active_layer == 0:
            self._bind_track_sends(pots)
        elif self._active_layer == 1:
            self._bind_device_and_balance(pots)
        else:
            self._bind_return_sends(pots)

    def _bind_track_sends(self, pots):
        tracks = self._controlled_tracks()
        first_send = self._layer_banks[0] * 3
        for row in range(3):
            for column in range(4):
                if column < len(tracks):
                    sends = tracks[column].mixer_device.sends
                    send_index = first_send + row
                    if send_index < len(sends):
                        pot_index = row * 4 + column
                        parameter = sends[send_index]
                        pots[pot_index].connect_to(parameter)
                        self._bound_pot_infos[pot_index] = (
                            'K3 L1 · {} · {}'.format(
                                tracks[column].name,
                                parameter.name,
                            ),
                            parameter,
                        )

    def _bind_device_and_balance(self, pots):
        device = self.song.appointed_device
        parameter_infos = self._push_bank_parameter_infos()
        bank_name = self._push_bank_name()
        for index, (parameter, display_name) in enumerate(
            parameter_infos[:8]
        ):
            if parameter is not None:
                pots[index].connect_to(parameter)
                self._bound_pot_infos[index] = (
                    'K3 L2 · {} · {} · {}'.format(
                        bank_name,
                        device.name,
                        display_name,
                    ),
                    parameter,
                )

        for column, track in enumerate(self._controlled_tracks()):
            parameter = track.mixer_device.panning
            pot_index = 8 + column
            pots[pot_index].connect_to(parameter)
            self._bound_pot_infos[pot_index] = (
                'K3 L2 · {} · {}'.format(track.name, parameter.name),
                parameter,
            )

    def _push_bank_parameter_infos(self):
        device = self.song.appointed_device
        if device is None:
            self._disconnect_push_parameter_bank()
            return ()
        self._ensure_push_parameter_bank(device)
        if self._push_parameter_bank is None:
            return self._fallback_device_parameter_infos(device)

        result = []
        for slot in self._push_parameter_bank.parameters:
            if isinstance(slot, tuple):
                parameter = slot[0] if slot else None
                display_name = slot[1] if len(slot) > 1 else None
            else:
                parameter = slot
                display_name = None
            if parameter is not None and not self._is_mappable_parameter(parameter):
                return self._fallback_device_parameter_infos(device)
            result.append(
                (
                    parameter,
                    display_name or (parameter.name if parameter is not None else ''),
                )
            )
        return tuple(result)

    def _ensure_push_parameter_bank(self, device):
        if (
            device == self._push_bank_device
            or device == self._push_bank_failed_device
        ):
            return
        self._disconnect_push_parameter_bank()
        self._push_bank_failed_device = None
        bank = None
        try:
            bank = create_parameter_bank(
                device,
                self._push_banking_info,
            )
            bank_count = max(1, min(3, bank.bank_count))
            self._layer_banks[1] %= bank_count
            bank.index = self._layer_banks[1]
            bank.add_parameters_listener(
                self._on_push_bank_parameters_changed
            )
            self._push_parameter_bank = bank
            self._push_bank_device = device
        except (AttributeError, IndexError, RuntimeError, TypeError):
            self._push_bank_failed_device = device
            if bank is not None:
                try:
                    bank.disconnect()
                except (AttributeError, RuntimeError, TypeError):
                    pass

    def _disconnect_push_parameter_bank(self):
        bank = self._push_parameter_bank
        self._push_parameter_bank = None
        self._push_bank_device = None
        if bank is None:
            return
        try:
            if bank.parameters_has_listener(self._on_push_bank_parameters_changed):
                bank.remove_parameters_listener(self._on_push_bank_parameters_changed)
            bank.disconnect()
        except (AttributeError, RuntimeError, TypeError):
            pass

    def _on_push_bank_parameters_changed(self):
        if self._active_layer == 1 and not self._disconnected:
            self.schedule_message(1, self._rebind_push_bank)

    def _rebind_push_bank(self):
        if self._active_layer == 1 and not self._disconnected:
            self._bind_pots()

    def _cycle_push_bank(self):
        device = self.song.appointed_device
        if device is None:
            self._layer_banks[1] = (self._layer_banks[1] + 1) % 3
            self.show_message(
                'Xone K3 Layer 2 · Bank {}'.format(self._layer_banks[1] + 1)
            )
            return

        self._ensure_push_parameter_bank(device)
        bank = self._push_parameter_bank
        if bank is None:
            self._layer_banks[1] = (self._layer_banks[1] + 1) % 3
        else:
            bank_count = max(1, min(3, bank.bank_count))
            self._layer_banks[1] = (self._layer_banks[1] + 1) % bank_count
            bank.index = self._layer_banks[1]
        self._bind_pots()
        self.show_message(
            'Xone K3 Layer 2 · {}'.format(self._push_bank_name())
        )

    def _push_bank_name(self):
        bank = self._push_parameter_bank
        if bank is not None:
            name = getattr(bank, 'name', '')
            if name:
                return 'Bank {} ({})'.format(bank.index + 1, name)
            return 'Bank {}'.format(bank.index + 1)
        return 'Bank {}'.format(self._layer_banks[1] + 1)

    @staticmethod
    def _is_mappable_parameter(parameter):
        return (
            not isinstance(parameter, tuple)
            and hasattr(parameter, 'name')
            and hasattr(parameter, 'value')
        )

    def _fallback_device_parameter_infos(self, device):
        start = 1 + self._layer_banks[1] * 8
        return tuple(
            (parameter, parameter.name)
            for parameter in list(device.parameters)[start:start + 8]
        )

    def _bind_return_sends(self, pots):
        returns = list(self.song.return_tracks)[:4]
        for source_index, source in enumerate(returns):
            destinations = [index for index in range(len(returns)) if index != source_index]
            sends = source.mixer_device.sends
            for row, destination_index in enumerate(destinations[:3]):
                if destination_index < len(sends):
                    pot_index = row * 4 + source_index
                    parameter = sends[destination_index]
                    pots[pot_index].connect_to(parameter)
                    self._bound_pot_infos[pot_index] = (
                        'K3 L3 · {} → {} · {}'.format(
                            source.name,
                            returns[destination_index].name,
                            parameter.name,
                        ),
                        parameter,
                    )

    # ------------------------------------------------------------------
    # Session and Arrangement navigation
    # ------------------------------------------------------------------

    def _on_view_changed(self):
        self._apply_session_ring_offsets()
        self.schedule_message(1, self._refresh_bindings_and_leds)

    def _on_selected_track_changed(self):
        self.schedule_message(1, self._refresh_bindings_and_leds)

    def _on_visible_tracks_changed(self):
        self.schedule_message(1, self._refresh_bindings_and_leds)

    def _refresh_bindings_and_leds(self):
        if self._disconnected:
            return
        try:
            self._bind_all_parameters()
            self._refresh_leds()
        except (RuntimeError, TypeError):
            pass

    def _on_appointed_device_changed(self):
        self._layer_banks[1] = 0
        if (
            self._push_parameter_bank is not None
            and self._push_bank_device == self.song.appointed_device
        ):
            self._push_parameter_bank.index = 0
        self._bind_pots()
        self.schedule_message(1, lambda: self._refresh_pad_leds(force=True))

    def _on_transport_state_changed(self):
        try:
            self._refresh_top_leds(force=True)
            if not self._is_arranger():
                self._refresh_pad_leds(force=True)
        except (RuntimeError, TypeError):
            pass

    def _move_session_ring(self, track_delta, scene_delta):
        max_track = max(0, len(self.song.visible_tracks) - 4)
        max_scene = max(0, len(self.song.scenes) - 4)
        self._session_track_offset = max(
            0,
            min(max_track, self._session_ring.track_offset + track_delta),
        )
        self._session_scene_offset = max(
            0,
            min(max_scene, self._session_ring.scene_offset + scene_delta),
        )
        self._apply_session_ring_offsets()
        self._bind_all_parameters()
        self._refresh_leds()

    def _select_relative_scene(self, delta):
        scenes = list(self.song.scenes)
        if not scenes:
            return
        selected = self.song.view.selected_scene
        index = scenes.index(selected) if selected in scenes else 0
        index = max(0, min(len(scenes) - 1, index + delta))
        self.song.view.selected_scene = scenes[index]
        self._session_scene_offset = self._session_ring.scene_offset
        if index < self._session_ring.scene_offset:
            self._session_scene_offset = index
        elif index >= self._session_ring.scene_offset + 4:
            self._session_scene_offset = index - 3
        self._apply_session_ring_offsets()
        self._refresh_pad_leds()

    def _select_relative_track(self, delta):
        tracks = list(self.song.visible_tracks)
        if not tracks:
            return
        selected = self.song.view.selected_track
        old_index = tracks.index(selected) if selected in tracks else 0
        new_index = max(0, min(len(tracks) - 1, old_index + delta))
        if new_index != old_index:
            self.song.view.selected_track = tracks[new_index]

    def _zoom_arranger(self, delta):
        if self.application.view.focused_document_view != 'Arranger':
            self.application.view.focus_view('Arranger')
        direction = (
            Live.Application.Application.View.NavDirection.right
            if delta > 0
            else Live.Application.Application.View.NavDirection.left
        )
        for _ in range(min(abs(delta), 6)):
            self.application.view.zoom_view(direction, 'Arranger', False)

    def _zoom_arranger_vertical(self, delta):
        if self.application.view.focused_document_view != 'Arranger':
            self.application.view.focus_view('Arranger')
        direction = (
            Live.Application.Application.View.NavDirection.up
            if delta > 0
            else Live.Application.Application.View.NavDirection.down
        )
        for _ in range(min(abs(delta), 6)):
            self.application.view.zoom_view(direction, 'Arranger', False)

    def _apply_session_ring_offsets(self):
        if self._session_ring:
            self._session_ring.set_offsets(
                self._session_track_offset,
                self._session_scene_offset,
            )

    # ------------------------------------------------------------------
    # Parameter and device helpers
    # ------------------------------------------------------------------

    def _bind_all_parameters(self):
        for control in self.elements.volume_faders_raw:
            control.release_parameter()
        for control, track in zip(self.elements.volume_faders_raw, self._controlled_tracks()):
            control.connect_to(track.mixer_device.volume)
        self._bind_pots()
        self._rebind_track_transport_listeners()

    def _rebind_track_transport_listeners(self):
        tracks = tuple(self._controlled_tracks())
        if tracks == self._listened_transport_tracks:
            return

        self._remove_track_transport_listeners()
        self._listened_transport_tracks = tracks
        for track in tracks:
            for property_name in ('playing_slot_index', 'fired_slot_index'):
                add_listener = getattr(track, 'add_{}_listener'.format(property_name), None)
                if add_listener is not None:
                    callback = lambda: self._on_transport_state_changed()
                    try:
                        add_listener(callback)
                        self._track_transport_listeners.append(
                            (track, property_name, callback)
                        )
                    except (RuntimeError, TypeError):
                        pass

    def _remove_track_transport_listeners(self):
        listeners = self._track_transport_listeners
        self._track_transport_listeners = []
        self._listened_transport_tracks = ()
        for track, property_name, callback in listeners:
            has_listener = getattr(
                track,
                '{}_has_listener'.format(property_name),
                None,
            )
            remove_listener = getattr(
                track,
                'remove_{}_listener'.format(property_name),
                None,
            )
            try:
                if remove_listener is not None and (
                    has_listener is None or has_listener(callback)
                ):
                    remove_listener(callback)
            except (RuntimeError, TypeError):
                pass

    def _controlled_tracks(self):
        tracks = list(self.song.visible_tracks)
        if self._is_arranger():
            selected = self.song.view.selected_track
            if selected not in tracks:
                return []
            offset = tracks.index(selected)
            return tracks[offset:offset + 4]
        offset = self._session_ring.track_offset
        return tracks[offset:offset + 4]

    def _track_at(self, index):
        tracks = self._controlled_tracks()
        return tracks[index] if index < len(tracks) else None

    def _flatten_selected_track_devices(self):
        track = self.song.view.selected_track
        devices = []
        for device in getattr(track, 'devices', ()):
            self._append_device_tree(device, devices)
        return devices

    @staticmethod
    def _device_index_for_pad(pad_index):
        return pad_index

    def _append_device_tree(self, device, result):
        result.append(device)
        if getattr(device, 'can_have_chains', False):
            for chain in device.chains:
                for nested_device in chain.devices:
                    self._append_device_tree(nested_device, result)

    def _focus_device(self, device):
        self.application.view.show_view('Detail/DeviceChain')
        self.application.view.focus_view('Detail/DeviceChain')
        self.song.view.select_device(device, True)
        self.song.appointed_device = device
        self._set_device_folding(device)
        self.schedule_message(
            1,
            lambda selected_device=device: self._finalize_rack_view(
                selected_device
            ),
        )

    def _set_device_folding(self, selected_device):
        for device in self._flatten_selected_track_devices():
            view = getattr(device, 'view', None)
            if view is None:
                continue
            if (
                not getattr(device, 'can_have_chains', False)
                and hasattr(view, 'is_collapsed')
            ):
                view.is_collapsed = device != selected_device

    def _finalize_rack_view(self, selected_device):
        if self._disconnected:
            return
        for device in self._device_path(selected_device):
            if not getattr(device, 'can_have_chains', False):
                continue
            view = getattr(device, 'view', None)
            if view is None:
                continue
            if hasattr(view, 'is_collapsed'):
                view.is_collapsed = False
            if hasattr(view, 'is_showing_chains'):
                view.is_showing_chains = False
            if hasattr(view, 'is_showing_chain_devices'):
                view.is_showing_chain_devices = True

    def _device_path(self, selected_device):
        track = self.song.view.selected_track
        for device in getattr(track, 'devices', ()):
            path = self._find_device_path(device, selected_device)
            if path:
                return path
        return ()

    def _find_device_path(self, device, selected_device):
        if device == selected_device:
            return (device,)
        if getattr(device, 'can_have_chains', False):
            for chain in device.chains:
                for nested_device in chain.devices:
                    nested_path = self._find_device_path(
                        nested_device,
                        selected_device,
                    )
                    if nested_path:
                        return (device,) + nested_path
        return ()

    # ------------------------------------------------------------------
    # LED feedback
    # ------------------------------------------------------------------

    def _refresh_leds(self, force=False):
        self._refresh_layer_led(force=force)
        self._refresh_shift_led(force=force)
        self._refresh_mixer_leds(force=force)
        self._refresh_pad_leds(force=force)
        self._refresh_top_leds(force=force)

    def _refresh_leds_safely(self, force=False):
        try:
            self._refresh_leds(force=force)
        except (RuntimeError, TypeError):
            pass

    def _refresh_layer_led(self, force=False):
        self._set_multicolor_led(self._LAYER_NOTES, self._active_layer, True, force=force)

    def _refresh_shift_led(self, force=False):
        bank_index = self._layer_banks[self._active_layer]
        self._set_multicolor_led(self._SHIFT_NOTES, bank_index, True, force=force)

    def _refresh_mixer_leds(self, force=False):
        tracks = self._controlled_tracks()
        for index in range(4):
            track = tracks[index] if index < len(tracks) else None
            self._set_single_color_led(self._MUTE_NOTES[index], bool(track and not track.mute), force=force)
            self._set_single_color_led(self._SOLO_NOTES[index], bool(track and track.solo), force=force)
            self._set_single_color_led(
                self._ARM_NOTES[index],
                bool(track and track.can_be_armed and track.arm),
                force=force,
            )

    def _refresh_pad_leds(self, force=False):
        notes = [note for row in self._PAD_NOTES for note in row]
        if self._is_arranger():
            self._session_pad_signature = None
            devices = self._flatten_selected_track_devices()
            selected = self.song.appointed_device
            for index, note in enumerate(notes):
                device_index = self._device_index_for_pad(index)
                if device_index >= len(devices):
                    self._set_multicolor_led(self._feedback_notes(note), 0, False, force=force)
                else:
                    device = devices[device_index]
                    if device != selected:
                        color = 0
                        is_on = not getattr(device, 'can_have_chains', False)
                    elif self._device_is_enabled(device):
                        color = 1
                        is_on = True
                    else:
                        color = 2
                        is_on = True
                    self._set_multicolor_led(self._feedback_notes(note), color, is_on, force=force)
        else:
            tracks = self._controlled_tracks()
            pad_states = []
            for index, note in enumerate(notes):
                row, column = divmod(index, 4)
                scene_index = self._session_ring.scene_offset + row
                color = 0
                is_on = False
                is_triggered = False
                if column < len(tracks) and scene_index < len(self.song.scenes):
                    track = tracks[column]
                    slot = track.clip_slots[scene_index]
                    is_triggered = bool(getattr(slot, 'is_triggered', False))
                    will_record = bool(getattr(slot, 'will_record_on_start', False))
                    if is_triggered and will_record:
                        is_on = True
                        color = 2
                    elif slot.has_clip:
                        is_on = True
                        clip = slot.clip
                        is_recording = bool(getattr(slot, 'is_recording', False)) or bool(
                            getattr(clip, 'is_recording', False)
                        )
                        is_playing = (
                            self.song.is_playing
                            and track.playing_slot_index == scene_index
                        )
                        color = 2 if is_recording else 0 if is_playing else 1
                pad_states.append((color, is_on, is_triggered))

            signature = tuple(pad_states)
            force = force or signature != self._session_pad_signature
            self._session_pad_signature = signature
            for note, (color, is_on, _) in zip(notes, pad_states):
                self._set_multicolor_led(self._feedback_notes(note), color, is_on, force=force)

    def _refresh_top_leds(self, force=False):
        if self._is_arranger():
            for index, note in enumerate(self._TOP_BUTTON_NOTES):
                is_on = index == 3 and bool(self.song.back_to_arranger)
                self._set_single_color_led(note, is_on, force=force)
        else:
            tracks = self._controlled_tracks()
            for index, note in enumerate(self._TOP_BUTTON_NOTES):
                playing = (
                    self.song.is_playing
                    and index < len(tracks)
                    and tracks[index].playing_slot_index >= 0
                )
                self._set_single_color_led(note, playing, force=force)

    def _flash_top_button(self, index):
        note = self._TOP_BUTTON_NOTES[index]
        self._set_single_color_led(note, True)
        self.schedule_message(3, lambda: self._refresh_top_leds())

    def _set_single_color_led(self, note, is_on, force=False):
        if not self._hardware_connected:
            return
        key = ('single', note)
        state = bool(is_on)
        if force or key not in self._led_states or self._led_states[key] != state:
            self._send_note(note, 127 if state else 0)
            self._led_states[key] = state

    def _set_multicolor_led(self, notes, color, is_on, force=False):
        if not self._hardware_connected:
            return
        notes = tuple(notes)
        key = ('multi', notes)
        target = notes[color] if is_on else None
        if force:
            previous = self._led_states.get(key)
            if key not in self._led_states:
                for note in notes:
                    self._send_note(note, 0)
            elif previous is not None and previous != target:
                self._send_note(previous, 0)
            if target is not None:
                self._send_note(target, 127)
            self._led_states[key] = target
            return
        if key in self._led_states and self._led_states[key] == target:
            return

        if key not in self._led_states:
            for note in notes:
                self._send_note(note, 0)
        else:
            previous = self._led_states[key]
            if previous is not None:
                self._send_note(previous, 0)

        if target is not None:
            self._send_note(target, 127)
        self._led_states[key] = target

    def _send_note(self, note, value):
        if self._hardware_connected:
            self._send_midi((0x90 | CHANNEL, note, value))

    @staticmethod
    def _feedback_notes(layer_one_note):
        return (
            layer_one_note,
            layer_one_note + FEEDBACK_LAYER_NOTE_OFFSET,
            layer_one_note + FEEDBACK_LAYER_NOTE_OFFSET * 2,
        )

    @staticmethod
    def _device_on_parameter(device):
        parameters = list(getattr(device, 'parameters', ()))
        return parameters[0] if parameters else None

    def _device_is_enabled(self, device):
        parameter = self._device_on_parameter(device)
        if parameter is None:
            return True
        return parameter.value > (parameter.min + parameter.max) / 2.0

    def _toggle_device(self, device):
        parameter = self._device_on_parameter(device)
        if parameter is not None:
            parameter.value = parameter.min if self._device_is_enabled(device) else parameter.max

    # ------------------------------------------------------------------
    # General helpers
    # ------------------------------------------------------------------

    def _scheduled_session_refresh(self):
        if not self._disconnected:
            if self._hardware_connected and not self._is_arranger():
                try:
                    self._refresh_pad_leds()
                    self._refresh_top_leds()
                except (RuntimeError, TypeError):
                    pass
            self.schedule_message(1, self._scheduled_session_refresh)

    def _scheduled_refresh(self):
        if not self._disconnected:
            if self._hardware_connected:
                self._refresh_leds_safely()
            self.schedule_message(5, self._scheduled_refresh)

    def _is_arranger(self):
        return self.application.view.is_view_visible('Arranger')

    def _cursor_speed_multiplier(self):
        now = time.monotonic()
        elapsed = None if self._last_cursor_turn is None else now - self._last_cursor_turn
        self._last_cursor_turn = now
        if elapsed is not None and elapsed < 0.04:
            return 12
        if elapsed is not None and elapsed < 0.09:
            return 4
        return 1

    @staticmethod
    def _relative_delta(value):
        return value if value < 64 else value - 128

    def disconnect(self):
        self._disconnected = True
        self._disconnect_push_parameter_bank()
        if self.application.view.focused_document_view_has_listener(self._on_view_changed):
            self.application.view.remove_focused_document_view_listener(self._on_view_changed)
        if self.song.view.selected_track_has_listener(self._on_selected_track_changed):
            self.song.view.remove_selected_track_listener(self._on_selected_track_changed)
        if self.song.visible_tracks_has_listener(self._on_visible_tracks_changed):
            self.song.remove_visible_tracks_listener(self._on_visible_tracks_changed)
        if self.song.is_playing_has_listener(self._on_transport_state_changed):
            self.song.remove_is_playing_listener(self._on_transport_state_changed)
        if hasattr(self.song, 'appointed_device_has_listener') and self.song.appointed_device_has_listener(self._on_appointed_device_changed):
            self.song.remove_appointed_device_listener(self._on_appointed_device_changed)
        self._remove_track_transport_listeners()
        for control, callback in self._value_listeners:
            if control.value_has_listener(callback):
                control.remove_value_listener(callback)
        super().disconnect()
