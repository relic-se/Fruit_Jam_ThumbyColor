# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3

# load included modules if we aren't installed on the root path
if len(__file__.split("/")[:-1]) > 1:
    lib_path = "/".join(__file__.split("/")[:-1]) + "/lib"
    try:
        import os
        os.stat(lib_path)
    except:
        pass
    else:
        import sys
        sys.path.append(lib_path)

import atexit
import displayio
import sys
import supervisor
from terminalio import FONT

from adafruit_display_text.label import Label
import adafruit_fruitjam.peripherals
from adafruit_usb_host_mouse import find_and_init_boot_mouse

# get Fruit Jam OS config if available
try:
    import launcher_config
    config = launcher_config.LauncherConfig()
except ImportError:
    config = None

# setup display
try:
    adafruit_fruitjam.peripherals.request_display_config()  # user display configuration
except ValueError:  # invalid user config or no user config provided
    adafruit_fruitjam.peripherals.request_display_config(720, 400)  # default display size
display = supervisor.runtime.display

# setup audio, buttons, and neopixels
peripherals = adafruit_fruitjam.peripherals.Peripherals(
    safe_volume_limit=(config.audio_volume_override_danger if config is not None else 0.75),
)

# user-defined audio output and volume
peripherals.audio_output = config.audio_output if config is not None else "headphone"
peripherals.volume = config.audio_volume if config is not None else 0.7

# create root group
root_group = displayio.Group()
display.root_group = root_group

# example text
root_group.append(Label(
    font=FONT, text="Hello, World!",
    anchor_point=(0.5, 0.5),
    anchored_position=(display.width//2, display.height//2),
))

# mouse device
mouse = None
if config is not None and config.use_mouse and (mouse := find_and_init_boot_mouse()) is not None:
    root_group.append(mouse.tilegrid)

def atexit_callback() -> None:
    if mouse and mouse.was_attached and not mouse.device.is_kernel_driver_active(0):
        mouse.device.attach_kernel_driver(0)
atexit.register(atexit_callback)

# flush input buffer
while supervisor.runtime.serial_bytes_available:
    sys.stdin.read(1)

try:
    previous_pressed_btns = None
    while True:

        # keyboard input
        if (available := supervisor.runtime.serial_bytes_available) > 0:
            key = sys.stdin.read(available)
            if key == "\x1b":  # escape
                peripherals.deinit()
                supervisor.reload()
        
        # mouse input
        if mouse is not None and mouse.update() is not None:
            if "left" in mouse.pressed_btns and (previous_pressed_btns is None or "left" not in previous_pressed_btns):
                pass  # left click
            previous_pressed_btns = mouse.pressed_btns

except KeyboardInterrupt:
    peripherals.deinit()
