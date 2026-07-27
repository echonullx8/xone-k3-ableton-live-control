import math

import Live

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
        self._selected_device_track = None
        self._positioning_device = False
        self._scroll_generations = [0, 0]
        self._scroll_directions = [None, None]
        self._led_states = {}
        self._session_pad_signature = None
        self._push_banking_info = BankingInfo(BANK_DEFINITIONS)
        self._push_parameter_bank = None
        self._push_bank_device = None
        self._push_bank_failed_device = None
        self._browser_levels = []
        self._browser_preview_generation = 0
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
        self._update_selected_device_listener()

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
        if index == 1 and self._browser_navigation_active():
            self._navigate_browser(delta)
            return
        if index == 2 and not self._is_arranger():
            self._select_relative_device(delta)
            return
        if self._active_layer == 2:
            self._adjust_layer3_bell_frequency(index, delta)
            return
        if index == 0:
            self.song.tempo = max(20.0, min(999.0, self.song.tempo + delta * 0.2))
        elif index == 1 and self._is_arranger():
            self._zoom_arranger(delta)
        elif index == 2 and self._is_arranger():
            if not delta:
                return
            direction = (
                Live.Application.Application.View.NavDirection.right
                if delta > 0
                else Live.Application.Application.View.NavDirection.left
            )
            self._mackie_scroll(0, direction, abs(delta))
        elif index == 3:
            volume = self.song.master_track.mixer_device.volume
            volume.value = max(volume.min, min(volume.max, volume.value + delta * 0.005))

    def _on_top_button(self, index, value):
        if not value:
            self.schedule_message(1, lambda: self._refresh_top_leds(force=True))
            return

        if index == 1 and self._browser_navigation_active():
            self._activate_browser_item()
            self._flash_top_button(index)
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
                self._zoom_arranger_vertical(delta)
            else:
                direction = (
                    Live.Application.Application.View.NavDirection.down
                    if delta > 0
                    else Live.Application.Application.View.NavDirection.up
                )
                self._mackie_scroll(1, direction, abs(delta))
        else:
            if index == 0:
                self._select_session_track(delta)
            else:
                self._select_relative_scene(delta)

    def _on_bottom_button(self, index, value):
        if not value:
            return
        if index == 0:
            self.song.record_mode = not self.song.record_mode
        elif self._is_arranger():
            if self.song.re_enable_automation_enabled:
                self.song.re_enable_automation()
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
        else:
            self._initialize_layer3_eqs()

        self._refresh_shift_led()

    # ------------------------------------------------------------------
    # Software layers
    # ------------------------------------------------------------------

    def _on_layer(self, value):
        if value:
            self._active_layer = (self._active_layer + 1) % 3
            if not self._browser_navigation_active():
                self._stop_browser_preview()
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
            if self._selected_track_is_return():
                self._bind_return_sends(pots)
            else:
                self._bind_track_sends(pots)
        elif self._active_layer == 1:
            self._bind_device_and_balance(pots)
        else:
            self._bind_track_eqs(pots)

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
        first_send = self._layer_banks[0] * 3
        for column, source in enumerate(self._controlled_tracks()):
            enabled_sends = [
                parameter
                for parameter in source.mixer_device.sends
                if getattr(parameter, 'is_enabled', True)
            ]
            for row, parameter in enumerate(
                enabled_sends[first_send:first_send + 3]
            ):
                pot_index = row * 4 + column
                pots[pot_index].connect_to(parameter)
                self._bound_pot_infos[pot_index] = (
                    'K3 L1 · {} · {}'.format(source.name, parameter.name),
                    parameter,
                )

    def _bind_track_eqs(self, pots):
        for column, track in enumerate(self._controlled_tracks()):
            role_parameters = self._find_ready_eq8_roles(track)
            if role_parameters is None:
                continue
            parameters = (
                role_parameters['low_frequency'],
                role_parameters['bell_gain'],
                role_parameters['high_frequency'],
            )
            labels = ('Low Cut Frequency', 'Bell Gain', 'High Cut Frequency')
            for row, (parameter, label) in enumerate(zip(parameters, labels)):
                pot_index = row * 4 + column
                pots[pot_index].connect_to(parameter)
                self._bound_pot_infos[pot_index] = (
                    'K3 L3 · {} · {}'.format(track.name, label),
                    parameter,
                )

    def _adjust_layer3_bell_frequency(self, column, delta):
        if not delta:
            return
        track = self._track_at(column)
        role_parameters = (
            self._find_ready_eq8_roles(track) if track is not None else None
        )
        if role_parameters is None:
            return
        parameter = role_parameters['bell_frequency']
        minimum = float(parameter.min)
        maximum = float(parameter.max)
        current = float(parameter.value)
        if minimum > 0.0 and maximum > minimum:
            log_min = math.log(minimum)
            log_max = math.log(maximum)
            normalized = (
                math.log(max(minimum, current)) - log_min
            ) / (log_max - log_min)
            normalized = max(0.0, min(1.0, normalized + delta * 0.01))
            parameter.value = math.exp(
                log_min + normalized * (log_max - log_min)
            )
        else:
            parameter.value = max(
                minimum,
                min(maximum, current + (maximum - minimum) * delta * 0.01),
            )
        self._show_parameter(
            'K3 L3 · {} · Bell Frequency'.format(track.name),
            parameter,
        )

    def _initialize_layer3_eqs(self):
        track = self.song.view.selected_track
        if track is None:
            self.show_message('K3 L3 EQ Eight · no selected track')
            return

        device = self._find_ready_eq8(track)
        state = 'ready'
        if device is not None:
            self._set_standard_eq8_frequency_endpoints(device)
        else:
            device = self._find_initializable_eq8(track)
            state = 'configured'
            if device is None:
                device = self._insert_eq8(track)
                state = 'created'
            if device is None or not self._configure_standard_eq8(device):
                self.show_message(
                    'K3 L3 EQ Eight · failed: {}'.format(track.name)
                )
                return

        self._focus_device(device)
        self._bind_pots()
        self.show_message(
            'K3 L3 EQ Eight · {} · {}'.format(track.name, state)
        )

    def _find_ready_eq8(self, track):
        for device in self._eq8_devices(track):
            if self._eq8_roles(device) is not None:
                return device
        return None

    def _find_ready_eq8_roles(self, track):
        device = self._find_ready_eq8(track)
        return self._eq8_roles(device) if device is not None else None

    def _find_initializable_eq8(self, track):
        for device in self._eq8_devices(track):
            parameters = []
            for band in (1, 4, 8):
                band_parameters = self._eq8_band_parameters(device, band)
                names = ('on', 'type', 'frequency')
                if band == 4:
                    names += ('gain',)
                parameters.extend(
                    band_parameters.get(name) for name in names
                )
            if all(
                parameter is not None
                and getattr(parameter, 'is_enabled', True)
                for parameter in parameters
            ):
                return device
        return None

    def _insert_eq8(self, track):
        insert_device = getattr(track, 'insert_device', None)
        if insert_device is None:
            return None
        before = tuple(self._eq8_devices(track))
        try:
            inserted = insert_device('EQ Eight')
        except (AttributeError, RuntimeError, TypeError):
            return None
        if getattr(inserted, 'class_name', '') == 'Eq8':
            return inserted
        for device in reversed(self._eq8_devices(track)):
            if device not in before:
                return device
        return None

    def _configure_standard_eq8(self, device):
        configuration = (
            (1, 'low_cut'),
            (4, 'bell'),
            (8, 'high_cut'),
        )
        for band, role in configuration:
            parameters = self._eq8_band_parameters(device, band)
            on_parameter = parameters.get('on')
            type_parameter = parameters.get('type')
            frequency_parameter = parameters.get('frequency')
            gain_parameter = parameters.get('gain')
            if (
                on_parameter is None
                or type_parameter is None
                or frequency_parameter is None
                or (band == 4 and gain_parameter is None)
                or not getattr(on_parameter, 'is_enabled', True)
                or not getattr(type_parameter, 'is_enabled', True)
                or not getattr(frequency_parameter, 'is_enabled', True)
                or (
                    band == 4
                    and not getattr(gain_parameter, 'is_enabled', True)
                )
                or not self._set_eq8_filter_type(type_parameter, role)
            ):
                return False
            on_parameter.value = on_parameter.max
        self._set_standard_eq8_frequency_endpoints(device)
        return self._eq8_roles(device) is not None

    def _set_standard_eq8_frequency_endpoints(self, device):
        low_frequency = self._eq8_band_parameters(
            device,
            1,
        ).get('frequency')
        high_frequency = self._eq8_band_parameters(
            device,
            8,
        ).get('frequency')
        if low_frequency is not None:
            low_frequency.value = low_frequency.min
        if high_frequency is not None:
            high_frequency.value = high_frequency.max

    def _eq8_roles(self, device):
        roles = {}
        for band in range(1, 9):
            parameters = self._eq8_band_parameters(device, band)
            on_parameter = parameters.get('on')
            type_parameter = parameters.get('type')
            frequency = parameters.get('frequency')
            gain = parameters.get('gain')
            if (
                on_parameter is None
                or type_parameter is None
                or frequency is None
                or on_parameter.value
                <= (on_parameter.min + on_parameter.max) / 2.0
            ):
                continue
            role = self._eq8_filter_role(type_parameter)
            if role == 'low_cut' and 'low_frequency' not in roles:
                if getattr(frequency, 'is_enabled', True):
                    roles['low_frequency'] = frequency
            elif role == 'bell' and 'bell_frequency' not in roles:
                if (
                    gain is not None
                    and getattr(frequency, 'is_enabled', True)
                    and getattr(gain, 'is_enabled', True)
                ):
                    roles['bell_frequency'] = frequency
                    roles['bell_gain'] = gain
            elif role == 'high_cut' and getattr(
                frequency,
                'is_enabled',
                True,
            ):
                roles['high_frequency'] = frequency
        required = (
            'low_frequency',
            'bell_frequency',
            'bell_gain',
            'high_frequency',
        )
        return roles if all(name in roles for name in required) else None

    def _eq8_devices(self, track):
        devices = []
        for device in getattr(track, 'devices', ()):
            self._append_device_tree(device, devices)
        return [
            device
            for device in devices
            if getattr(device, 'class_name', '') == 'Eq8'
        ]

    def _eq8_band_parameters(self, device, band):
        return {
            'on': self._parameter_by_original_name(
                device,
                '{} Filter On A'.format(band),
            ),
            'type': self._parameter_by_original_name(
                device,
                '{} Filter Type A'.format(band),
            ),
            'frequency': self._parameter_by_original_name(
                device,
                '{} Frequency A'.format(band),
            ),
            'gain': self._parameter_by_original_name(
                device,
                '{} Gain A'.format(band),
            ),
        }

    @staticmethod
    def _parameter_by_original_name(device, wanted_name):
        for parameter in getattr(device, 'parameters', ()):
            if getattr(parameter, 'original_name', '') == wanted_name:
                return parameter
            if getattr(parameter, 'name', '') == wanted_name:
                return parameter
        return None

    def _eq8_filter_role(self, parameter):
        try:
            display = parameter.str_for_value(parameter.value)
        except (AttributeError, RuntimeError, TypeError):
            display = ''
        normalized = ' '.join(str(display).lower().split())
        if 'low' in normalized and 'cut' in normalized:
            return 'low_cut'
        if 'high' in normalized and 'cut' in normalized:
            return 'high_cut'
        if 'bell' in normalized:
            return 'bell'
        fallback_roles = {
            0: 'low_cut',
            1: 'low_cut',
            3: 'bell',
            6: 'high_cut',
            7: 'high_cut',
        }
        return fallback_roles.get(
            int(round(parameter.value - parameter.min))
        )

    def _set_eq8_filter_type(self, parameter, role):
        items = tuple(getattr(parameter, 'value_items', ()))
        matches = []
        for index, item in enumerate(items):
            normalized = ' '.join(str(item).lower().split())
            if role == 'low_cut' and 'low' in normalized and 'cut' in normalized:
                matches.append((index, normalized))
            elif role == 'high_cut' and 'high' in normalized and 'cut' in normalized:
                matches.append((index, normalized))
            elif role == 'bell' and 'bell' in normalized:
                matches.append((index, normalized))
        if matches:
            preferred = next(
                (index for index, name in matches if '12' in name),
                matches[0][0],
            )
            if len(items) > 1:
                parameter.value = parameter.min + (
                    parameter.max - parameter.min
                ) * preferred / (len(items) - 1)
            else:
                parameter.value = parameter.min
            return True

        fallback_indices = {'low_cut': 1, 'bell': 3, 'high_cut': 6}
        index = fallback_indices.get(role)
        if index is None or parameter.max - parameter.min < index:
            return False
        parameter.value = parameter.min + index
        return True

    # ------------------------------------------------------------------
    # Session and Arrangement navigation
    # ------------------------------------------------------------------

    def _on_view_changed(self):
        if not self._browser_navigation_active():
            self._stop_browser_preview()
        self._apply_session_ring_offsets()
        self.schedule_message(1, self._refresh_bindings_and_leds)

    def _on_selected_track_changed(self):
        self._update_selected_device_listener()
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
        if self._positioning_device:
            return
        self._layer_banks[1] = 0
        if (
            self._push_parameter_bank is not None
            and self._push_bank_device == self.song.appointed_device
        ):
            self._push_parameter_bank.index = 0
        self._bind_pots()
        self.schedule_message(1, lambda: self._refresh_pad_leds(force=True))

    def _update_selected_device_listener(self):
        previous_track = self._selected_device_track
        if previous_track is not None:
            view = previous_track.view
            if view.selected_device_has_listener(self._on_selected_device_changed):
                view.remove_selected_device_listener(self._on_selected_device_changed)

        track = self.song.view.selected_track
        self._selected_device_track = track
        if track is not None:
            view = track.view
            if not view.selected_device_has_listener(self._on_selected_device_changed):
                view.add_selected_device_listener(self._on_selected_device_changed)
        self._on_selected_device_changed()

    def _on_selected_device_changed(self):
        if self._positioning_device:
            return
        track = self._selected_device_track
        device = track.view.selected_device if track is not None else None
        if device is not None and device != self.song.appointed_device:
            self.song.appointed_device = device
        self._bind_pots()
        self.schedule_message(1, lambda: self._refresh_pad_leds(force=True))

    def _on_transport_state_changed(self):
        try:
            self._refresh_top_leds(force=True)
            if not self._is_arranger():
                self._refresh_pad_leds(force=True)
        except (RuntimeError, TypeError):
            pass

    def _select_session_track(self, delta):
        tracks = list(self.song.visible_tracks)
        if not tracks:
            return
        selected = self.song.view.selected_track
        old_index = (
            tracks.index(selected)
            if selected in tracks
            else self._session_ring.track_offset
        )
        new_index = max(0, min(len(tracks) - 1, old_index + delta))
        self.song.view.selected_track = tracks[new_index]
        self._session_track_offset = new_index
        self._apply_session_ring_offsets()
        self._bind_all_parameters()
        self._refresh_leds()

    def _select_relative_scene(self, delta):
        scenes = list(self.song.scenes)
        if not scenes:
            return
        selected = self.song.view.selected_scene
        old_index = scenes.index(selected) if selected in scenes else 0
        new_index = max(0, min(len(scenes) - 1, old_index + delta))
        self.song.view.selected_scene = scenes[new_index]
        self._session_scene_offset = self._session_ring.scene_offset
        if new_index < self._session_ring.scene_offset:
            self._session_scene_offset = new_index
        elif new_index >= self._session_ring.scene_offset + 4:
            self._session_scene_offset = new_index - 3
        self._apply_session_ring_offsets()
        if (
            new_index != old_index
            and len(
                list(self.song.visible_tracks)[
                    self._session_track_offset:
                    self._session_track_offset + 4
                ]
            ) < 4
        ):
            direction = (
                Live.Application.Application.View.NavDirection.down
                if new_index > old_index
                else Live.Application.Application.View.NavDirection.up
            )
            self.schedule_message(
                1,
                lambda d=direction, steps=abs(new_index - old_index):
                    self._scroll_incomplete_session_view(d, steps),
            )
        self._refresh_pad_leds()

    def _scroll_incomplete_session_view(self, direction, steps):
        if self._disconnected or self._is_arranger():
            return
        for _ in range(min(steps, 12)):
            self.application.view.scroll_view(
                direction,
                'Session',
                False,
            )

    def _select_relative_device(self, delta):
        if not delta:
            return
        track = self.song.view.selected_track
        devices = []
        for device in getattr(track, 'devices', ()):
            self._append_device_tree(device, devices)
        if not devices:
            return

        selected = track.view.selected_device
        if selected in devices:
            old_index = devices.index(selected)
            new_index = max(
                0,
                min(len(devices) - 1, old_index + delta),
            )
        else:
            new_index = 0 if delta > 0 else len(devices) - 1
        device = devices[new_index]
        self._focus_device(device)
        self._bind_pots()
        self.show_message(
            'K3 Device · {} · {}'.format(track.name, device.name)
        )

    def _zoom_arranger(self, delta):
        self.application.view.focus_view('Arranger')
        direction = (
            Live.Application.Application.View.NavDirection.right
            if delta > 0
            else Live.Application.Application.View.NavDirection.left
        )
        for _ in range(min(abs(delta), 6)):
            self.application.view.zoom_view(direction, 'Arranger', False)

    def _zoom_arranger_vertical(self, delta):
        self.application.view.focus_view('Arranger')
        direction = (
            Live.Application.Application.View.NavDirection.up
            if delta > 0
            else Live.Application.Application.View.NavDirection.down
        )
        for _ in range(min(abs(delta), 6)):
            self.application.view.zoom_view(direction, 'Arranger', False)

    def _browser_navigation_active(self):
        return self._active_layer == 1 or (
            self._active_layer == 0 and not self._is_arranger()
        )

    def _navigate_browser(self, delta):
        if not delta:
            return
        if not self._ensure_browser_level():
            return

        level = self._browser_levels[-1]
        new_index = level['index'] + delta
        if new_index < 0 and len(self._browser_levels) > 1:
            self._browser_levels.pop()
        else:
            level['index'] = max(
                0,
                min(len(level['items']) - 1, new_index),
            )
        self._show_browser_selection()
        self._schedule_browser_preview()

    def _activate_browser_item(self):
        if not self._ensure_browser_level():
            return
        item = self._current_browser_item()
        if item is None:
            return

        if bool(getattr(item, 'is_loadable', False)):
            browser = self._live_browser()
            track = self.song.view.selected_track
            before_devices = tuple(getattr(track, 'devices', ()))
            self._stop_browser_preview()
            try:
                browser.load_item(item)
            except (AttributeError, RuntimeError, TypeError):
                self.show_message(
                    'K3 Browser · cannot load {}'.format(item.name)
                )
                return
            self.show_message('K3 Browser · loaded {}'.format(item.name))
            self.schedule_message(
                1,
                lambda selected_track=track, before=before_devices:
                    self._focus_new_browser_device(selected_track, before),
            )
            return

        children = self._browser_children(item)
        if children:
            self._browser_levels.append(
                {
                    'items': children,
                    'index': 0,
                }
            )
            self._show_browser_selection()
            self._schedule_browser_preview()
        else:
            self.show_message(
                'K3 Browser · {} has no loadable items'.format(item.name)
            )

    def _ensure_browser_level(self):
        if self._browser_levels:
            return True
        browser = self._live_browser()
        if browser is None:
            self.show_message('K3 Browser · unavailable')
            return False
        color_items = self._browser_color_items(browser)
        roots = tuple(
            item
            for item in color_items + (
                getattr(browser, 'sounds', None),
                getattr(browser, 'drums', None),
                getattr(browser, 'instruments', None),
                getattr(browser, 'audio_effects', None),
                getattr(browser, 'midi_effects', None),
                getattr(browser, 'max_for_live', None),
                getattr(browser, 'plugins', None),
                getattr(browser, 'clips', None),
                getattr(browser, 'samples', None),
            )
            if item is not None
        )
        if not roots:
            self.show_message('K3 Browser · no root items')
            return False
        self._browser_levels = [
            {
                'items': roots,
                'index': 0,
            }
        ]
        return True

    @staticmethod
    def _browser_color_items(browser):
        try:
            colors = getattr(browser, 'colors', ())
            return tuple(colors)
        except (AttributeError, RuntimeError, TypeError):
            return ()

    def _live_browser(self):
        browser = getattr(self.application, 'browser', None)
        if browser is not None:
            return browser
        try:
            return Live.Application.get_application().browser
        except (AttributeError, RuntimeError, TypeError):
            return None

    @staticmethod
    def _browser_children(item):
        try:
            return tuple(item.children)
        except (AttributeError, RuntimeError, TypeError):
            return ()

    def _current_browser_item(self):
        if not self._browser_levels:
            return None
        level = self._browser_levels[-1]
        items = level['items']
        index = level['index']
        return items[index] if items else None

    def _show_browser_selection(self):
        item = self._current_browser_item()
        if item is None:
            return
        path = []
        for level in self._browser_levels:
            selected = level['items'][level['index']]
            path.append(selected.name)
        suffix = ' · Load' if getattr(item, 'is_loadable', False) else ' · Open'
        self.show_message(
            'K3 Browser · {}{}'.format(' > '.join(path), suffix)
        )

    def _schedule_browser_preview(self):
        self._browser_preview_generation += 1
        generation = self._browser_preview_generation
        self._stop_browser_preview(invalidate=False)
        item = self._current_browser_item()
        if item is not None and bool(getattr(item, 'is_loadable', False)):
            self.schedule_message(
                2,
                lambda selected=item, expected=generation:
                    self._preview_browser_item(selected, expected),
            )

    def _preview_browser_item(self, item, generation):
        if (
            self._disconnected
            or generation != self._browser_preview_generation
            or not self._browser_navigation_active()
            or item != self._current_browser_item()
        ):
            return
        browser = self._live_browser()
        try:
            browser.preview_item(item)
        except (AttributeError, RuntimeError, TypeError):
            pass

    def _stop_browser_preview(self, invalidate=True):
        if invalidate:
            self._browser_preview_generation += 1
        browser = self._live_browser()
        if browser is not None:
            try:
                browser.stop_preview()
            except (AttributeError, RuntimeError, TypeError):
                pass

    def _focus_new_browser_device(self, track, before_devices):
        if self._disconnected or self.song.view.selected_track != track:
            return
        new_devices = [
            device
            for device in getattr(track, 'devices', ())
            if device not in before_devices
        ]
        if new_devices:
            self._focus_device(new_devices[-1])

    def _mackie_scroll(self, axis, direction, steps):
        if self._scroll_directions[axis] != direction:
            self._scroll_generations[axis] += 1
            self._scroll_directions[axis] = direction
        generation = self._scroll_generations[axis]
        self.application.view.focus_view('Arranger')
        self.application.view.scroll_view(direction, 'Arranger', False)
        for delay in range(1, min(steps, 12)):
            self.schedule_message(
                delay,
                lambda a=axis, d=direction, g=generation:
                    self._scheduled_mackie_scroll(a, d, g),
            )

    def _scheduled_mackie_scroll(self, axis, direction, generation):
        if (
            not self._disconnected
            and self._is_arranger()
            and self._scroll_generations[axis] == generation
        ):
            self.application.view.scroll_view(direction, 'Arranger', False)

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
            returns = list(self.song.return_tracks)
            if selected in returns:
                offset = returns.index(selected)
                return returns[offset:offset + 4]
            if selected not in tracks:
                return []
            offset = tracks.index(selected)
            return tracks[offset:offset + 4]
        offset = self._session_ring.track_offset
        return tracks[offset:offset + 4]

    def _selected_track_is_return(self):
        return (
            self._is_arranger()
            and self.song.view.selected_track in self.song.return_tracks
        )

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
        self._select_device_chain_path(device)
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
        self._select_device_chain_path(selected_device)
        for device in self._device_path(selected_device):
            if not getattr(device, 'can_have_chains', False):
                continue
            view = getattr(device, 'view', None)
            if view is None:
                continue
            if hasattr(view, 'is_collapsed'):
                view.is_collapsed = False
            if hasattr(view, 'is_showing_chain_devices'):
                try:
                    view.is_showing_chain_devices = True
                except (RuntimeError, TypeError):
                    pass
        self._position_device_in_view(selected_device)

    def _select_device_chain_path(self, selected_device):
        for rack, chain in self._device_chain_path(selected_device):
            view = getattr(rack, 'view', None)
            if view is None:
                continue
            if hasattr(view, 'is_collapsed'):
                view.is_collapsed = False
            try:
                view.selected_chain = chain
            except (AttributeError, RuntimeError, TypeError):
                continue
            if hasattr(view, 'is_showing_chain_devices'):
                try:
                    view.is_showing_chain_devices = True
                except (RuntimeError, TypeError):
                    pass

    def _position_device_in_view(self, selected_device):
        if (
            self._positioning_device
            or selected_device not in self._flatten_selected_track_devices()
        ):
            return
        parent = getattr(selected_device, 'canonical_parent', None)
        devices = list(getattr(parent, 'devices', ()))
        if selected_device not in devices:
            return

        selected_view = getattr(selected_device, 'view', None)
        is_rack = bool(getattr(selected_device, 'can_have_chains', False))
        can_collapse_rack = bool(
            is_rack
            and selected_view is not None
            and hasattr(selected_view, 'is_collapsed')
        )
        self._positioning_device = True
        try:
            self.application.view.show_view('Detail/DeviceChain')
            self.application.view.focus_view('Detail/DeviceChain')
            if can_collapse_rack:
                selected_view.is_collapsed = True
            target_index = devices.index(selected_device)
            self.song.view.select_device(devices[-1], True)
            for _ in range(len(devices) - target_index - 1):
                self.application.view.scroll_view(
                    Live.Application.Application.View.NavDirection.left,
                    'Detail/DeviceChain',
                    False,
                )
            self.song.view.select_device(selected_device, True)
            self.song.appointed_device = selected_device
        finally:
            if can_collapse_rack:
                selected_view.is_collapsed = False
                if hasattr(selected_view, 'is_showing_chain_devices'):
                    try:
                        selected_view.is_showing_chain_devices = True
                    except (RuntimeError, TypeError):
                        pass
            self._positioning_device = False
        self._on_appointed_device_changed()
        self._refresh_pad_leds(force=True)

    def _device_path(self, selected_device):
        track = self.song.view.selected_track
        for device in getattr(track, 'devices', ()):
            path = self._find_device_path(device, selected_device)
            if path:
                return path
        return ()

    def _device_chain_path(self, selected_device):
        track = self.song.view.selected_track
        for device in getattr(track, 'devices', ()):
            path = self._find_device_chain_path(device, selected_device)
            if path is not None:
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

    def _find_device_chain_path(self, device, selected_device):
        if device == selected_device:
            return ()
        if getattr(device, 'can_have_chains', False):
            for chain in device.chains:
                for nested_device in chain.devices:
                    nested_path = self._find_device_chain_path(
                        nested_device,
                        selected_device,
                    )
                    if nested_path is not None:
                        return ((device, chain),) + nested_path
        return None

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

    @staticmethod
    def _relative_delta(value):
        return value if value < 64 else value - 128

    def disconnect(self):
        self._stop_browser_preview()
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
        if self._selected_device_track is not None:
            view = self._selected_device_track.view
            if view.selected_device_has_listener(self._on_selected_device_changed):
                view.remove_selected_device_listener(self._on_selected_device_changed)
            self._selected_device_track = None
        self._remove_track_transport_listeners()
        for control, callback in self._value_listeners:
            if control.value_has_listener(callback):
                control.remove_value_listener(callback)
        super().disconnect()
