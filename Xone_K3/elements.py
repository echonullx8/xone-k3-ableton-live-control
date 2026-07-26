from ableton.v3.control_surface import ElementsBase, MapMode
from ableton.v3.control_surface import MIDI_NOTE_TYPE, MIDI_CC_TYPE

from .midi import (
    ALL_POTENT_CCS,
    L1_BUTTONS,
    L1_FADER_CCS,
    L1_HI_POTENT_BTNS,
    L1_MID_POTENT_BTNS,
    L1_LOW_POTENT_BTNS,
    L1_SHFT,
    L1_LAYER,
    L1_TOP_ENCODER_BTNS,
    L1_TOP_ENCODER_CCS,
    L1_BOTTOM_ENCODER_BTNS,
    L1_BOTTOM_ENCODER_CCS,
)


# K3 Editor uses MIDI Channel 16; Ableton's API represents it as 15.
CHANNEL = 15


class Elements(ElementsBase):

    def __init__(self, *a, **k):
        super().__init__(global_channel=CHANNEL, *a, **k)

        self.add_encoder_matrix(
            L1_TOP_ENCODER_CCS,
            'top_encoders',
            msg_type=MIDI_CC_TYPE,
            map_mode=MapMode.AccelTwoCompliment,
        )
        self.add_button_matrix(
            L1_TOP_ENCODER_BTNS,
            'top_buttons',
            msg_type=MIDI_NOTE_TYPE,
            is_momentary=True,
        )

        self.add_encoder_matrix(
            ALL_POTENT_CCS,
            'pot_controls',
            msg_type=MIDI_CC_TYPE,
            needs_takeover=True,
        )
        self.add_button_matrix(
            L1_HI_POTENT_BTNS,
            'mute_buttons',
            msg_type=MIDI_NOTE_TYPE,
            is_momentary=True,
        )
        self.add_button_matrix(
            L1_MID_POTENT_BTNS,
            'solo_buttons',
            msg_type=MIDI_NOTE_TYPE,
            is_momentary=True,
        )
        self.add_button_matrix(
            L1_LOW_POTENT_BTNS,
            'arm_buttons',
            msg_type=MIDI_NOTE_TYPE,
            is_momentary=True,
        )

        self.add_encoder_matrix(
            L1_FADER_CCS,
            'volume_faders',
            msg_type=MIDI_CC_TYPE,
            needs_takeover=True,
        )
        self.add_button_matrix(
            L1_BUTTONS,
            'pad_buttons',
            msg_type=MIDI_NOTE_TYPE,
            is_momentary=True,
        )

        self.add_encoder_matrix(
            [L1_BOTTOM_ENCODER_CCS],
            'bottom_encoders',
            msg_type=MIDI_CC_TYPE,
            map_mode=MapMode.AccelTwoCompliment,
        )
        self.add_button_matrix(
            [L1_BOTTOM_ENCODER_BTNS],
            'bottom_buttons',
            msg_type=MIDI_NOTE_TYPE,
            is_momentary=True,
        )

        self.add_button(L1_SHFT, 'shift_button', msg_type=MIDI_NOTE_TYPE, is_momentary=True)
        self.add_button(L1_LAYER, 'layer_button', msg_type=MIDI_NOTE_TYPE, is_momentary=True)
