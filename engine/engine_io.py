# SPDX-FileCopyrightText: 2026 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import supervisor
import sys

import relic_usb_host_gamepad

_KEY_MAP = {
    "J": relic_usb_host_gamepad.BUTTON_A,
    "Z": relic_usb_host_gamepad.BUTTON_A,
    "K": relic_usb_host_gamepad.BUTTON_B,
    "X": relic_usb_host_gamepad.BUTTON_B,
    "Q": relic_usb_host_gamepad.BUTTON_L1,
    "C": relic_usb_host_gamepad.BUTTON_L1,
    "E": relic_usb_host_gamepad.BUTTON_R1,
    "V": relic_usb_host_gamepad.BUTTON_R1,
    "\n": relic_usb_host_gamepad.BUTTON_START,
    "W": relic_usb_host_gamepad.BUTTON_UP,
    "S": relic_usb_host_gamepad.BUTTON_DOWN,
    "A": relic_usb_host_gamepad.BUTTON_LEFT,
    "D": relic_usb_host_gamepad.BUTTON_RIGHT,
    "\x1b[A": relic_usb_host_gamepad.BUTTON_UP,
    "\x1b[B": relic_usb_host_gamepad.BUTTON_DOWN,
    "\x1b[D": relic_usb_host_gamepad.BUTTON_LEFT,
    "\x1b[C": relic_usb_host_gamepad.BUTTON_RIGHT,
    "\x1b": relic_usb_host_gamepad.BUTTON_HOME,
}

_last_keys = []
_keys = []
_gamepad = relic_usb_host_gamepad.Gamepad()

def rumble(intensity: float) -> None:
    if _gamepad.connected and hasattr(_gamepad._device, "rumble"):
        _gamepad._device.rumble = intensity

def _tick() -> None:
    global _last_keys, _keys

    # gamepad
    _gamepad.update()

    # keyboard
    _last_keys = _keys
    _keys = []
    if (available := supervisor.runtime.serial_bytes_available) > 0:
        buffer = sys.stdin.read(available)
        while buffer:
            key = buffer[0]
            buffer = buffer[1:]
            if key == "\x1b" and buffer and buffer[0] == "[" and len(buffer) >= 2:
                key += buffer[:2]
                buffer = buffer[2:]
                if buffer and buffer[0] == "~":
                    key += buffer[0]
                    buffer = buffer[1:]
            _keys.append(key.upper())

class Button:

    def __init__(self, *button_ids: int):
        self._button_ids = button_ids
        self._button_names = tuple([relic_usb_host_gamepad.BUTTON_NAMES[i] for i in self._button_ids])
    
    def _check_events(self, pressed: bool = True) -> bool:
        return _gamepad.connected and any(event.pressed is pressed and event.key_number in self._button_ids for event in _gamepad.events)

    def _check_keys(self, pressed: bool = True) -> bool:
        return _keys and any(key in _KEY_MAP and _KEY_MAP[key] in self._button_ids for key in (_keys if pressed else _last_keys))

    @property
    def name(self) -> str:
        return self._button_names[0]

    @property
    def is_pressed(self) -> bool:
        return any(getattr(_gamepad.buttons, x) for x in self._button_names) or self._check_keys()

    @property
    def is_just_pressed(self) -> bool:
        return self._check_events() or self._check_keys()

    @property
    def is_just_released(self) -> bool:
        return self._check_events(False) or self._check_keys(False)
    
    # TODO: long pressed and double pressed?

UP = Button(relic_usb_host_gamepad.BUTTON_UP, relic_usb_host_gamepad.BUTTON_JOYSTICK_UP)
DOWN = Button(relic_usb_host_gamepad.BUTTON_DOWN, relic_usb_host_gamepad.BUTTON_JOYSTICK_DOWN)
LEFT = Button(relic_usb_host_gamepad.BUTTON_LEFT, relic_usb_host_gamepad.BUTTON_JOYSTICK_LEFT)
RIGHT = Button(relic_usb_host_gamepad.BUTTON_RIGHT, relic_usb_host_gamepad.BUTTON_JOYSTICK_RIGHT)
A = Button(relic_usb_host_gamepad.BUTTON_A)
B = Button(relic_usb_host_gamepad.BUTTON_B)
LB = Button(relic_usb_host_gamepad.BUTTON_L1)
RB = Button(relic_usb_host_gamepad.BUTTON_R1)
MENU = Button(relic_usb_host_gamepad.BUTTON_START)
_HOME = Button(relic_usb_host_gamepad.BUTTON_HOME)
