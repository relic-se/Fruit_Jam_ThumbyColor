# SPDX-FileCopyrightText: 2026 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import displayio
import math
import supervisor

import adafruit_fruitjam

_DISPLAY_SIZE = 128
_LAYERS = 128

def _init() -> None:
    global _config, _display, _group, _layers, _peripherals, _bg_palette

    # get Fruit Jam OS config if available
    try:
        import launcher_config
        _config = launcher_config.LauncherConfig()
    except ImportError:
        _config = None

    # setup display
    try:
        adafruit_fruitjam.peripherals.request_display_config()  # user display configuration
    except ValueError:  # invalid user config or no user config provided
        adafruit_fruitjam.peripherals.request_display_config(720, 400)  # default display size
    _display = supervisor.runtime.display

    # create root group
    _group = displayio.Group()
    _group.scale = math.floor(min(_display.width, _display.height) / _DISPLAY_SIZE)
    _group.x = (_display.width - _DISPLAY_SIZE * _group.scale) // 2
    _group.y = (_display.height - _DISPLAY_SIZE * _group.scale) // 2
    _display._group = _group
    _display.auto_refresh = False
    _display.refresh()  # clear screen

    # setup background
    _bg_bitmap = displayio.Bitmap(_DISPLAY_SIZE, _DISPLAY_SIZE, 1)
    _bg_palette = displayio.Palette(1)
    _bg_palette[0] = 0x000000
    _bg_tg = displayio.TileGrid(_bg_bitmap, _bg_palette)
    _group.append(_bg_tg)

    _layers = [None] * _LAYERS

    # setup audio, buttons, and neopixels
    _peripherals = adafruit_fruitjam.peripherals.Peripherals(
        safe_volume_limit=(_config.audio_volume_override_danger if _config else 0.75),
        sample_rate=11025,
    )
    _peripherals.audio_output = _config.audio_output if _config else "headphone"
    _peripherals.volume = _config.audio_volume if _config else 0.7

def _get_layer(index: int) -> displayio.Group:
    index = min(max(index, 0), _LAYERS-1)
    if _layers[index] is None:
        _layers[index] = displayio.Group()
        _group.append(_layers[index])  # TODO: sorting?
    return _layers[index]
