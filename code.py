# SPDX-FileCopyrightText: 2026 Cooper Dalrymple (@relic-se)
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

import displayio
import math
import os
import sys
import supervisor
import terminalio
from terminalio import FONT
import time

from adafruit_argv_file import read_argv, write_argv
from adafruit_fruitjam.peripherals import request_display_config
import adafruit_imageload
from relic_usb_host_gamepad import Gamepad, BUTTON_A, BUTTON_HOME, BUTTON_UP, BUTTON_DOWN, BUTTON_JOYSTICK_UP, BUTTON_JOYSTICK_DOWN, BUTTON_NAMES

ROOT = "/".join(__file__.split("/")[:-1])
os.chdir(ROOT)  # force cwd

def timed_reload(message: str) -> None:
    print(f"{message}\nReloading in", end="")
    for i in range(3, 0, -1):
        print(f" {i}...", end="")
        time.sleep(1)
    print()
    supervisor.reload()

# query games
GAMES = []
for name in os.listdir("games"):
    if not name.startswith("."):
        try:
            os.stat(f"{ROOT}/games/{name}/main.py")
        except OSError:
            pass
        else:
            GAMES.append(name)
if not GAMES:
    timed_reload("No games installed!")
GAMES.sort()  # sort alphabetically

# check if we need to be launching a game
args = read_argv(__file__)
if args is not None and len(args) > 0:
    name = args[0]
    if not name in GAMES:
        timed_reload("Invalid game selection!")
    
    # add engine api to `sys.path`
    sys.path.append(f"{ROOT}/engine")

    # change cwd
    os.chdir(f"{ROOT}/games/{name}")

    # initialize saves dir
    import engine_save
    engine_save._init_saves_dir(f"Games/{name}")

    # initialize engine
    import engine_main
    engine_main._init()

    # run program
    try:
        __import__(f"{ROOT}/games/{name}/main.py")
    except SystemExit:
        pass
    except Exception as e:
        raise e

    # handle save data
    engine_save._dump()

    # reload application
    supervisor.set_next_code_file(f"{ROOT}/code.py")
    supervisor.reload()

# get Fruit Jam OS config if available
try:
    import launcher_config
    config = launcher_config.LauncherConfig()
except ImportError:
    config = None

# setup display
try:
    request_display_config()  # user display configuration
except ValueError:  # invalid user config or no user config provided
    request_display_config(720, 400)  # default display size
display = supervisor.runtime.display

# create root group
root_group = displayio.Group()
display.root_group = root_group

# create terminal
class Terminal(terminalio.Terminal):
    def __init__(self, *args, **kwargs):
        self._terminal = terminalio.Terminal(*args, **kwargs)
    def cursor(self, x: int, y: int) -> None:
        self._terminal.write(f"\033[{y+1};{x+1}H")
    def clear(self) -> None:
        self._terminal.write("\033H\033[2J")
    def write(self, text: str, x: int = None, y: int = None) -> None:
        if x is not None and y is not None:
            self.cursor(x, y)
        self._terminal.write(text)

CHAR_WIDTH, CHAR_HEIGHT = FONT.get_bounding_box()[0:2]
SCREEN_WIDTH, SCREEN_HEIGHT = display.width // 2 // CHAR_WIDTH, display.height // CHAR_HEIGHT

palette = displayio.Palette(2)
palette[0] = config.palette_bg if config else 0x000000
palette[1] = config.palette_fg if config else 0xffffff

tilegrid = displayio.TileGrid(
    bitmap=FONT.bitmap, pixel_shader=palette,
    width=SCREEN_WIDTH, height=SCREEN_HEIGHT,
    tile_width=CHAR_WIDTH, tile_height=CHAR_HEIGHT,
)
terminal = Terminal(tilegrid, FONT)
root_group.append(tilegrid)

# game icon
default_icon_bmp, default_icon_palette = adafruit_imageload.load("bitmaps/default_icon.bmp")
default_icon_palette.make_transparent(0)

icon_group = displayio.Group(
    scale=math.floor((display.width//2)/default_icon_bmp.width),
    x=display.width*3//4,
    y=display.height//2,
)
root_group.append(icon_group)

icon = displayio.TileGrid(
    bitmap=default_icon_bmp,
    pixel_shader=default_icon_palette,
    x=-default_icon_bmp.width//2,
    y=-default_icon_bmp.height//2,
)
icon_group.append(icon)

# write header and controls
terminal.write("Thumby Color\n\r", 0, 0)
terminal.write("Keyboard = Enter: select | Escape: quit\n\rGamepad = A: select | Home: quit", 0, SCREEN_HEIGHT - 2)

terminal.cursor(0, 1)
for i, name in enumerate(GAMES):
    name = name[:min(len(name), SCREEN_WIDTH - 2)]
    terminal.write(f"  {name}\n\r")

selected_index = None
def select(index: int) -> None:
    global selected_index
    if selected_index:
        terminal.write("  ", 0, 1 + selected_index)
    
    selected_index = index % len(GAMES)
    terminal.write("=>", 0, 1 + selected_index)

    icon_path = f"{ROOT}/games/{GAMES[selected_index]}/icon.bmp"
    try:
        os.stat(icon_path)
    except OSError:
        icon.bitmap = default_icon_bmp
        icon.pixel_shader = default_icon_palette
    else:
        icon_bmp, icon_palette = adafruit_imageload.load(icon_path)
        if icon_bmp.width == icon.tile_width and icon_bmp.height == icon.tile_height:
            icon.bitmap = icon_bmp
            icon.pixel_shader = icon_palette
        else:
            icon.bitmap = default_icon_bmp
            icon.pixel_shader = default_icon_palette
select(0)

# setup input devices
keys = []
KEY_MAP = {
    "\n": BUTTON_A,
    "\x1b": BUTTON_HOME,
    "W": BUTTON_UP,
    "S": BUTTON_DOWN,
    "\x1b[A": BUTTON_UP,
    "\x1b[B": BUTTON_DOWN,
}

gamepad = Gamepad()
def is_pressed(*buttons: int) -> bool:
    if any(getattr(gamepad.buttons, BUTTON_NAMES[i]) for i in buttons):
        return True
    if keys and any(key in KEY_MAP and KEY_MAP[key] in buttons for key in keys):
        return True
    return False
def is_just_pressed(*buttons: int) -> bool:
    if gamepad.connected and any(event.pressed and event.key_number in buttons for event in gamepad.events):
        return True
    if keys and any(key in KEY_MAP and KEY_MAP[key] in buttons for key in keys):
        return True
    return False

# flush input buffer
while supervisor.runtime.serial_bytes_available:
    sys.stdin.read(1)

while True:

    # gamepad
    gamepad.update()

    # keyboard
    keys = []
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
            keys.append(key.upper())

    # handle button press
    if is_just_pressed(BUTTON_HOME) or (gamepad.buttons.SELECT and gamepad.buttons.START):
        supervisor.reload()
    elif is_just_pressed(BUTTON_UP, BUTTON_JOYSTICK_UP):
        select(selected_index - 1)
    elif is_just_pressed(BUTTON_DOWN, BUTTON_JOYSTICK_DOWN):
        select(selected_index + 1)
    elif is_just_pressed(BUTTON_A):
        write_argv(f"{ROOT}/code.py", [GAMES[selected_index]])
        supervisor.set_next_code_file(
            f"{ROOT}/code.py",
            sticky_on_error=True,
            reload_on_error=True,
        )
        supervisor.reload()
