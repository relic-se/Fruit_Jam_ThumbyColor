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
from audiocore import WaveFile
from audiomixer import Mixer
import displayio
import json
import os
import math
from micropython import const
import supervisor
import sys
import time
import vectorio

import adafruit_fruitjam.peripherals
import adafruit_imageload
from adafruit_usb_host_mouse import find_and_init_boot_mouse
from relic_usb_host_gamepad import Gamepad, BUTTON_A, BUTTON_B, BUTTON_L1, BUTTON_R1, BUTTON_HOME, BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_JOYSTICK_UP, BUTTON_JOYSTICK_DOWN, BUTTON_JOYSTICK_LEFT, BUTTON_JOYSTICK_RIGHT

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

# create root group
root_group = displayio.Group()
display.root_group = root_group
display.auto_refresh = False

root_group.append(bg_group := displayio.Group())
root_group.append(sprite_group := displayio.Group())
root_group.append(ui_group := displayio.Group())
for group in root_group:
    group.x = display.width//2
    group.y = display.height//2
    group.hidden = True

# setup input devices
keys = []
KEY_MAP = {
    "J": BUTTON_A,
    "Z": BUTTON_A,
    "K": BUTTON_B,
    "X": BUTTON_B,
    "Q": BUTTON_L1,
    "C": BUTTON_L1,
    "E": BUTTON_R1,
    "V": BUTTON_R1,
    "\x1b": BUTTON_HOME,
    "W": BUTTON_UP,
    "S": BUTTON_DOWN,
    "A": BUTTON_LEFT,
    "D": BUTTON_RIGHT,
    "\x1b[A": BUTTON_UP,
    "\x1b[B": BUTTON_DOWN,
    "\x1b[D": BUTTON_LEFT,
    "\x1b[C": BUTTON_RIGHT,
}

gamepad = Gamepad()
rumbleFrames = 0
def rumble(frames, intensity):
    global rumbleFrames
    if gamepad.connected and hasattr(gamepad._device, "rumble"):
        gamepad._device.rumble = intensity
    rumbleFrames = frames
def stopRumble() -> None:
    if gamepad.connected and hasattr(gamepad._device, "rumble"):
        gamepad._device.rumble = 0
def is_just_pressed(*key_numbers: int) -> bool:
    if gamepad.connected and any(event.pressed and event.key_number in key_numbers for event in gamepad.events):
        return True
    if keys and any(key in KEY_MAP and KEY_MAP[key] in key_numbers for key in keys):
        return True
    return False

mouse = None
if config is not None and config.use_mouse and (mouse := find_and_init_boot_mouse()) is not None:
    root_group.append(mouse.tilegrid)

def atexit_callback() -> None:
    if mouse and mouse.was_attached and not mouse.device.is_kernel_driver_active(0):
        mouse.device.attach_kernel_driver(0)
atexit.register(atexit_callback)

# engine compatibility

EASE_LINEAR = const(1)
EASE_ELAST_IN_OUT = const(2)

nodes = []
timestamp = None
frame = 0
def tick() -> None:
    global timestamp, frame, rumbleFrames, keys

    display.refresh(
        target_frames_per_second=30,
    )

    # gamepad
    gamepad.update()
    if rumbleFrames > 0:
        rumbleFrames -= 1
        if rumbleFrames == 0:
            stopRumble()

    # mouse
    if mouse is not None:
        mouse.update()

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

    # tick nodes
    current = time.monotonic()
    if timestamp is not None:
        dt = timestamp - current
        for node in nodes:
            node.tick(dt)
    timestamp = current

    frame += 1

class Node:

    def __init__(self):
        global nodes
        nodes.append(self)

    def tick(self, dt: float) -> None:
        pass

class Tween(Node):

    C5 = (2 * math.pi) / 4.5

    def __init__(self):
        super().__init__()

        self.duration = None
        self.ease_type = EASE_LINEAR

        self._start = None
        self._end = None
        self._position = None
        self._playing = False
        self._finished = False

    def start(self, obj: object, attr_name: str, start: float|tuple, end: float|tuple, duration: float, ease_type: int = EASE_LINEAR) -> None:
        self._obj = obj
        self._attr_name = attr_name
        self._start = start
        self._end = end
        self.duration = duration
        self.ease_type = ease_type
        self.restart()

    def end(self) -> None:
        setattr(self._obj, self._attr_name, self._end)
        self._position = 1
        self._playing = False
        self._finished = True

    def pause(self) -> None:
        if not self._finished:
            self._playing = False

    def unpause(self) -> None:
        if not self._finished:
            self._playing = True

    def restart(self) -> None:
        setattr(self._obj, self._attr_name, self._start)
        self._position = 0
        self._playing = True
        self._finished = False

    def _ease(self, value: float) -> float:
        if self.ease_type == EASE_ELAST_IN_OUT:
            if value < 0.5:
                return -(pow(2, 20 * value - 10) * math.sin((20 * value - 11.125) * self.C5)) / 2
            else:
                return (pow(2, -20 * value + 10) * math.sin((20 * value - 11.125) * self.C5)) / 2 + 1
        return value  # EASE_LINEAR
    
    def _tween(self, position: float, start: float, end: float) -> float:
        return (end - start) * position + start

    def tick(self, dt: float) -> None:
        if self._playing:
            self._position += dt / self.duration
            if self._position >= 1:
                self.end()
            else:
                position = self._ease(self._position)
                if isinstance(self._end, tuple):
                    value = (
                        self._tween(position, self._start[0], self._end[0]),
                        self._tween(position, self._start[1], self._end[1])
                    )
                else:
                    value = self._tween(position, self._start, self._end)
                setattr(self._obj, self._attr_name, value)

    @property
    def finished(self) -> bool:
        return self._finished

class Group(Node):

    def __init__(self, position: tuple = None, scale: int = 1):
        super().__init__()
        self._group = displayio.Group(scale=scale)
        self.position = position

    @property
    def position(self) -> tuple:
        return (self._x, self._y)
    
    @position.setter
    def position(self, value: tuple) -> None:
        if value is None:
            self._x, self._y, self._group.x, self._group.y = [0] * 4
        else:
            self._x, self._y = [float(x) for x in value]
            self._group.x, self._group.y = [int(x) for x in value]

    @property
    def x(self) -> float:
        return self._x

    @property
    def y(self) -> float:
        return self._y

    def append(self, obj) -> None:
        self._group.append(obj.group if isinstance(obj, Group) else obj)

    @property
    def hidden(self) -> bool:
        return self._group.hidden

    @hidden.setter
    def hidden(self, value: bool) -> None:
        self._group.hidden = value

    @property
    def group(self) -> displayio.Group:
        return self._group

class Font:

    def __init__(self, path: str, min_character: str = " ", max_character: str = "~", transparent_index: int = 0):
        self.texture, self.palette = adafruit_imageload.load(path)
        self.palette.make_transparent(transparent_index)
        self._min = ord(min_character)
        self._size = ord(max_character) - ord(min_character) + 1
        self._tile_width = self.texture.width // self._size
    
    @property
    def tile_width(self) -> int:
        return self._tile_width

    @property
    def tile_height(self) -> int:
        return self.texture.height
    
    def index(self, character: str) -> int:
        return max(ord(character[0]) - self._min, 0) if character else 0

class Text(Group):

    def __init__(self, font: Font, text: str, width: int = None, height: int = None, pixel_shader: displayio.Palette = None, letter_spacing: int = 1, line_spacing: int = 1, position: tuple = None, scale: int = 1):
        # NOTE: letter_spacing/line_spacing?

        super().__init__(position, scale)
        self._font = font

        if width is None:
            width = max(len(x) for x in text.split("\n"))
        width = max(width, 1)

        if height is None:
            height = len(text.split("\n"))
        height = max(height, 1)

        self._tg = displayio.TileGrid(
            bitmap=font.texture, pixel_shader=font.palette,
            width=width, height=height,
            tile_width=font.tile_width, tile_height=font.tile_height,
        )
        self._tg.x = -self._tg.width * self._tg.tile_width // 2
        self._tg.y = -self._tg.height * self._tg.tile_height // 2
        self.pixel_shader = pixel_shader
        self._group.append(self._tg)

        self.text = text

    @property
    def text(self) -> str:
        return self._text
    
    @text.setter
    def text(self, value: str) -> None:
        self._text = value
        i = 0
        for y in range(self._tg.height):
            newline = False
            for x in range(self._tg.width):
                if i < len(self._text) and self._text[i] == "\n":
                    newline = True
                    i += 1
                if newline or i >= len(self._text):
                    self._tg[x, y] = self._font.index(" ")
                else:
                    self._tg[x, y] = self._font.index(self._text[i])
                    i += 1

    @property
    def pixel_shader(self) -> displayio.Palette:
        return self._tg.pixel_shader

    @pixel_shader.setter
    def pixel_shader(self, value: displayio.Palette) -> None:
        if value is None:
            self._tg.pixel_shader = self._font.palette
        elif len(value) != len(self._font.palette):
            palette = displayio.Palette(len(self._font.palette))
            for i in range(len(self._font.palette)):
                if self._font.palette.is_transparent(i):
                    palette.make_transparent(i)
                else:
                    palette[i] = value[0]
            self._tg.pixel_shader = palette

class Sprite(Group):

    def __init__(self, texture: displayio.Bitmap, pixel_shader: displayio.Palette, position: tuple = None, fps: float = 0, frame_count_x: int = 1, frame_count_y: int = 1, scale: int = 1, playing: bool = False):
        super().__init__(position, scale)

        self._tg = displayio.TileGrid(
            bitmap=texture, pixel_shader=pixel_shader,
            width=1, height=1,
            tile_width=texture.width//frame_count_x,
            tile_height=texture.height//frame_count_y,
        )
        self._tg.x = -self._tg.tile_width//2
        self._tg.y = -self._tg.tile_height//2
        self._group.append(self._tg)

        self._frame_count_x = frame_count_x
        self._frame_count_y = frame_count_y

        self.playing = playing
        self.loop = False
        self.fps = fps

    @property
    def texture(self) -> displayio.Bitmap:
        return self._tg.bitmap

    @texture.setter
    def texture(self, value: displayio.Bitmap) -> None:
        self._tg.bitmap = value

    @property
    def pixel_shader(self) -> displayio.Palette:
        return self._tg.pixel_shader

    @texture.setter
    def pixel_shader(self, value: displayio.Palette) -> None:
        self._tg.pixel_shader = value

    @property
    def frame_current_x(self) -> int:
        return self._tg[0] % self._frame_count_x
    
    @frame_current_x.setter
    def frame_current_x(self, value: int) -> None:
        self._tg[0] = (self.frame_current_y * self._frame_count_x) + (value % self._frame_count_x)

    @property
    def frame_current_y(self) -> int:
        return self._tg[0] // self._frame_count_y
    
    @frame_current_y.setter
    def frame_current_y(self, value: int) -> None:
        self._tg[0] = (value % self._frame_count_y) * self._frame_count_x + self.frame_current_x
    
    @property
    def fps(self) -> float:
        return self._fps
    
    @fps.setter
    def fps(self, value: float) -> None:
        self._fps = min(value, 0)
        self._frame_duration = 1 / value if value > 0 else None
        self._frame_time = 0

    def tick(self, dt: float) -> None:
        if self.playing:
            self._frame_time += dt
            if self._frame_time >= self._frame_duration:
                self.frame_current_x += 1
                self._frame_time = 0
                if not self.loop and self.frame_current_x == self._frame_count_x - 1:
                    self.playing = False

class Rectangle(Group):

    def __init__(self, pixel_shader: displayio.Palette, width: int, height: int, outline: bool = False, position: tuple = None, scale: int = 1):
        super().__init__(position, scale)
        self._outline = outline
        for i in range(4 if outline else 1):  # NOTE: Maybe implement `adafruit_display_shapes`?
            self._group.append(vectorio.Rectangle(pixel_shader=pixel_shader, width=1, height=1))
        self.width, self.height = width, height

    @property
    def width(self) -> int:
        return self._width
    
    @width.setter
    def width(self, value: int) -> None:
        self._width = value
        self._group[0].width = value
        self._group[0].x = -value//2
        if self._outline:
            self._group[1].width = value
            self._group[1].x = -value//2
            self._group[2].x = value//2 - 1
            self._group[3].x = value//2 - 1
        
    @property
    def height(self) -> int:
        return self._height
    
    @height.setter
    def height(self, value: int) -> None:
        self._height = value
        self._group[0].y = -value//2
        if self._outline:
            self._group[1].y = value//2 - 1
            self._group[2].height = value
            self._group[2].y = -value//2
            self._group[3].height = value
            self._group[3].y = -value//2
        else:
            self._group[0].height = value

# loading text
FONT = Font("fonts/outrunner_outline.bmp")
loading_txt = Text(FONT, "Loading...", position=(0, display.height - FONT.tile_height))
root_group.append(loading_txt.group)
display.refresh()

# get save data
SAVE_FILE = "/saves/puzzleattack.json"
save_data = {}
try:
    with open(SAVE_FILE, "r") as f:
        try:
            data = json.load(f)
        except (ValueError, AttributeError):
            pass
        else:
            if isinstance(data, dict):
                save_data = {}
except OSError:
    pass

# setup audio, buttons, and neopixels
peripherals = adafruit_fruitjam.peripherals.Peripherals(
    safe_volume_limit=(config.audio_volume_override_danger if config is not None else 0.75),
    sample_rate=11025,
)

# user-defined audio output and volume
peripherals.audio_output = config.audio_output if config is not None else "headphone"
peripherals.volume = config.audio_volume if config is not None else 0.7

mixer = Mixer(
    voice_count=1,
    sample_rate=peripherals.dac.sample_rate,
    channel_count=1,
    bits_per_sample=8,
    samples_signed=False,
    buffer_size=8192,
)
peripherals.audio.play(mixer)

# constants and files

CHEAT_MODE = const(True)

sfxWin = WaveFile("sfx/win.wav")
sfxLose = WaveFile("sfx/lose.wav")
sfxFall = WaveFile("sfx/fall.wav")
sfxSwap = WaveFile("sfx/swap.wav")
sfxNav = WaveFile("sfx/nav.wav")
sfxCursor = WaveFile("sfx/cursor.wav")
sfxPops = [WaveFile("sfx/pop"+str(i+1)+".wav") for i in range(8)]

texLogo, palLogo = adafruit_imageload.load("bitmaps/logo.bmp")
palLogo.make_transparent(103)
texBG, palBG = adafruit_imageload.load("bitmaps/bg.bmp")
texBlocks, palBlocks = adafruit_imageload.load("bitmaps/blocks.bmp")
palBlocks.make_transparent(11)
texCursor, palCursor = adafruit_imageload.load("bitmaps/cursor.bmp")
palCursor.make_transparent(1)
texCheckmark, palCheckmark = adafruit_imageload.load("bitmaps/checkmark.bmp")
palCheckmark.make_transparent(0)
texLock, palLock = adafruit_imageload.load("bitmaps/lock.bmp")
palLock.make_transparent(28)

MODE_NORMAL = const(0)
MODE_EXTRA = const(1)
MODE_CUSTOM = const(2)

BLOCK_GREEN = const(0)
BLOCK_PURPLE = const(1)
BLOCK_RED = const(2)
BLOCK_YELLOW = const(3)
BLOCK_CYAN = const(4)
BLOCK_BLUE = const(5)

BLOCK_STATE_NORMAL = const(0)
BLOCK_STATE_FALLING = const(1)
BLOCK_STATE_SQUISH = const(2)
BLOCK_STATE_DARK = const(3)
BLOCK_STATE_POP = const(4)
BLOCK_STATE_LIGHT = const(5)
BLOCK_STATE_POP2 = const(6)

SM_INTRO = const(0)
SM_PRESS_START = const(1)
SM_MODE_SELECT = const(2)
SM_STAGE_SELECT = const(3)
SM_LEVEL_LOADING = const(4)
SM_LEVEL_UNLOADING = const(5)
SM_CURSOR_SELECT = const(6)
SM_LEVEL_MENU  = const(7)
SM_SWAP_ANIM = const(8)
SM_FALL_ANIM = const(9)
SM_MATCH_ANIM = const(10)
SM_MOVE_OVER = const(11)
SM_LEVEL_LOST = const(12)
SM_LEVEL_WIN = const(13)

def solid_palette(color: int) -> displayio.Palette:
    pal = displayio.Palette(1)
    pal[0] = color
    return pal

BLACK = solid_palette(0x000000)
WHITE = solid_palette(0xffffff)
LIGHTGREY = solid_palette(0xd6d6d6)
DARKGREY = solid_palette(0x7b7b7b)

class Block(Sprite):
    def __init__(self, id: int):
        super().__init__(
            texBlocks, palBlocks,
            frame_count_x=7, frame_count_y=6,
        )
        self.frame_current_x = BLOCK_STATE_NORMAL
        self.frame_current_y = id
        self.loop = False
        self.playing = False
        self.tween = Tween()
        self.normal = True
        self.falling = False
        self.fallingY = None
    def tweenMove(self, position, duration):
        self.tween.start(self, "position", self.position, position, duration, EASE_ELAST_IN_OUT)
    def updateFalling(self):
        prevFalling = self.falling
        if self.fallingY is not None and self.normal:
            if not self.tween.finished and self.y > self.fallingY:
                self.falling = True
            elif self.tween.finished:
                self.falling = False
        else:
            self.falling = False
        self.fallingY = self.y
        if self.normal:
            if self.falling:
                self.frame_current_x = BLOCK_STATE_FALLING
            elif prevFalling:
                self.frame_current_x = BLOCK_STATE_SQUISH
            elif self.frame_current_x == BLOCK_STATE_SQUISH:
                self.frame_current_x = BLOCK_STATE_NORMAL

class Cursor(Sprite):
    def __init__(self):
        super().__init__(
            texCursor, palCursor,
            frame_count_x=1, frame_count_y=2,
        )
        self.loop = True
        self.playing = True
        self.fps = 4

BLOCK_COLS = const(6)
BLOCK_ROWS = const(12)
BLOCKS_START_X = const(10)
BLOCKS_START_Y = const(4)

stageName = ""
stagePrefix = ""
blocks = [None for _ in range(BLOCK_COLS*BLOCK_ROWS)]
moves = 0

sprBG = Sprite(texBG, palBG, position=(64, 64), scale=2)
bg_group.append(sprBG.group)

sprLogo = Sprite(texLogo, palLogo, position=(64, -64))
ui_group.append(sprLogo.group)

menuBlocks = [Block(id) for id in range(6)]
for x in menuBlocks:
    sprite_group.append(x.group)

rectMenuGameMode = Rectangle(BLACK, 120, 80, position=(64, 64), outline=True)
ui_group.append(rectMenuGameMode.group)
rectMenuGameModeBorder = Rectangle(WHITE, 118, 78, outline=True)
rectMenuGameMode.append(rectMenuGameModeBorder)
txtMenuGameModeOptions = [
    Text(FONT, "NORMAL", position=(0,-25), scale=2),
    Text(FONT, "EXTRA", scale=2),
    Text(FONT, "CUSTOM", position=(0, 25), scale=2),
]
for txt in txtMenuGameModeOptions:
    rectMenuGameMode.append(txt)

rectToast = Rectangle(LIGHTGREY, 100, 60, position=(64, 64))
ui_group.append(rectToast.group)
txtToast = Text(FONT, "", width=16, height=4, pixel_shader=BLACK)
rectToast.append(txtToast)

rectMenuStage = Rectangle(BLACK, 100, 110, position=(64, 72))
ui_group.append(rectMenuStage.group)
rectMenuStageBorder = Rectangle(WHITE, 98, 108, outline=True)
rectMenuStage.append(rectMenuStageBorder)
txtMenuStageTitle = Text(FONT, "Stage 1", position=(64, 9))
ui_group.append(txtMenuStageTitle.group)
txtMenuStageLevels = []
sprMenuStageClears = []
i = 0
for col in range(2):
    for row in range(5):
        txt = Text(FONT, str(i+1), position=(col*48-34,row*20-40))
        txtMenuStageLevels.append(txt)
        rectMenuStage.append(txt)
        spr = Sprite(texCheckmark, palCheckmark, position=(col*48-14,row*20-40), frame_count_x=2)
        sprMenuStageClears.append(spr)
        rectMenuStage.append(spr)
        i += 1
rectMenuStageLock = Rectangle(DARKGREY, 96, 106)
rectMenuStage.append(rectMenuStageLock)
sprMenuStageLock = Sprite(texLock, palLock)
rectMenuStage.append(sprMenuStageLock)

rectBorder = Rectangle(WHITE, BLOCK_COLS*10+3, BLOCK_ROWS*10+3, position=(BLOCKS_START_X-2+BLOCK_COLS*5+2, BLOCKS_START_Y-2+BLOCK_ROWS*5+2), outline=True)
bg_group.append(rectBorder.group)
cursor = Cursor()
ui_group.append(cursor.group)
lblLevelTitle = Text(FONT, "LEVEL", position=(100, 10))
ui_group.append(lblLevelTitle.group)
lblLevel = Text(FONT, "---", position=(100, 25))
ui_group.append(lblLevel.group)
lblMovesTitle = Text(FONT, "MOVES", position=(100, 80))
ui_group.append(lblMovesTitle.group)
lblMoves = Text(FONT, "0", position=(100, 105), scale=3)
ui_group.append(lblMoves.group)
lblOverlay = Text(FONT, "", position=(BLOCKS_START_X+BLOCK_COLS*5, BLOCKS_START_Y+BLOCK_ROWS*5))
ui_group.append(lblOverlay.group)
sprCheckmark = Sprite(texCheckmark, palCheckmark, position=(100, 41), frame_count_x=2)
ui_group.append(sprCheckmark.group)

for block in menuBlocks:
    block.hidden = True

rectMenuGameMode.hidden = True
rectMenuGameModeBorder.hidden = True
txtMenuGameModeOptions[0].hidden = True
txtMenuGameModeOptions[1].hidden = True
txtMenuGameModeOptions[2].hidden = True

rectMenuStage.hidden = True
rectMenuStageBorder.hidden = True
txtMenuStageTitle.hidden = True
rectMenuStageLock.hidden = True
sprMenuStageLock.hidden = True
for txt in txtMenuStageLevels:
    txt.hidden = True
for spr in sprMenuStageClears:
    spr.hidden = True

rectToast.hidden = True
txtToast.hidden = True

rectBorder.hidden = True
cursor.hidden = True
lblLevelTitle.hidden = True
lblLevel.hidden = True
lblMovesTitle.hidden = True
lblMoves.hidden = True
sprCheckmark.hidden = True

def loadLevel(stage, level):
    global stageName, stagePrefix, blocks, moves
    
    with open(stage) as f:
        stageData = json.load(f)
    
    stageName = stageData["name"]
    stagePrefix = stageData["prefix"]
    levelData = stageData["levels"][level]
    
    for i in range(len(blocks)):
        if blocks[i] is not None:
            block = blocks[i]
            blocks[i] = None
            sprite_group.remove(block.group)
            del block
            
    moves = levelData[len(levelData)-1]
            
    rowStart = BLOCK_ROWS - (len(levelData)-1)
    colStart = BLOCK_COLS//2 - len(levelData[0])//2
    for dr in range(len(levelData)-1):
        for dc in range(len(levelData[0])):
            row = rowStart + dr
            col = colStart + dc
            symbol = levelData[dr][dc]
            if symbol == "G":
                id = BLOCK_GREEN
            elif symbol == "P":
                id = BLOCK_PURPLE
            elif symbol == "R":
                id = BLOCK_RED
            elif symbol == "Y":
                id = BLOCK_YELLOW
            elif symbol == "C":
                id = BLOCK_CYAN
            elif symbol == "B":
                id = BLOCK_BLUE
            elif symbol == " ":
                id = None
            else:
                raise Exception("Unknown symbol! "+symbol)
            if id is not None:
                block = Block(id)
                sprite_group.append(block.group)
                height = 130 + (BLOCK_ROWS-row)*10
                block.position = (BLOCKS_START_X+col*10+5,BLOCKS_START_Y+row*10+5-height)
                block.tweenMove((BLOCKS_START_X+col*10+5,BLOCKS_START_Y+row*10+5),height//10*50)
                blocks[row*BLOCK_COLS+col] = block
                
    lblLevel.text = stagePrefix+"-"+str(level+1)
    lblMoves.text = str(moves)
    sprBG.texture, sprBG.pixel_shader = adafruit_imageload.load(stage[0:-5]+".bmp")
    sprCheckmark.frame_current_x = save_data.get(stage, bytearray(10))[level]

def checkFalling(blocks):
    ret = []
    for col in range(BLOCK_COLS):
        ground = True
        for row in range(BLOCK_ROWS-1,-1,-1):
            block = blocks[row*BLOCK_COLS+col]
            if block is not None:
                if not ground:
                    ret.append((col, row, block))
            else:
                ground = False
    return ret

def startFallAnim(blocksFalling):
    for col, row, block in blocksFalling:
        block.tweenMove((block.x,block.y+10),200)
        i = row*BLOCK_COLS+col
        blocks[i], blocks[i+BLOCK_COLS] = blocks[i+BLOCK_COLS], blocks[i]

def checkMatching(blocks):
    ret = []
    for row in range(BLOCK_ROWS):
        for col in range(BLOCK_COLS):
            block = blocks[row*BLOCK_COLS+col]
            if block is not None:
                id = block.frame_current_y
                matchStart, matchEnd = col, col
                while matchStart > 0:
                    checkBlock = blocks[row*BLOCK_COLS+(matchStart-1)]
                    if checkBlock is not None and checkBlock.frame_current_y == id:
                        matchStart -= 1
                    else:
                        break
                while matchEnd < BLOCK_COLS-1:
                    checkBlock = blocks[row*BLOCK_COLS+(matchEnd+1)]
                    if checkBlock is not None and checkBlock.frame_current_y == id:
                        matchEnd += 1
                    else:
                        break
                if (matchEnd - matchStart) >= 2:
                    ret.append((col, row, block))
                    continue
                matchStart, matchEnd = row, row
                while matchStart > 0:
                    checkBlock = blocks[(matchStart-1)*BLOCK_COLS+col]
                    if checkBlock is not None and checkBlock.frame_current_y == id:
                        matchStart -= 1
                    else:
                        break
                while matchEnd < BLOCK_ROWS-1:
                    checkBlock = blocks[(matchEnd+1)*BLOCK_COLS+col]
                    if checkBlock is not None and checkBlock.frame_current_y == id:
                        matchEnd += 1
                    else:
                        break
                if (matchEnd - matchStart) >= 2:
                    ret.append((col, row, block))
                    continue
    return ret

standardStages = [("stages/standard/stage"+str(i+1)+".json") for i in range(6)]
extraStages = [("stages/extra/extra"+str(i+1)+".json") for i in range(6)]
customStages = [("stages/custom/"+f) for f in os.listdir("stages/custom") if f.endswith(".json")]

extraUnlockChecked = False
extraUnlock = None
def checkExtraUnlock():
    global extraUnlockChecked, extraUnlock
    unlocked = True
    for stage in standardStages:
        clears = save_data.get(stage, bytearray(10))
        for i in range(10):
            if clears[i] == 0:
                unlocked = False
                break
        if not unlocked:
            break
    extraUnlockChecked = True
    extraUnlock = unlocked
    return unlocked

def loadTitles(stages):
    ret = []
    for stage in stages:
        with open(stage) as f:
            stageData = json.load(f)
            ret.append(stageData["name"])
    return ret

def loadLevelCounts(stages):
    ret = []
    for stage in stages:
        with open(stage) as f:
            stageData = json.load(f)
            ret.append(len(stageData["levels"]))
    return ret

stages = standardStages
levelCounts = None
titles = None
clears = None
locks = None
stage = 0
level = 0

cursorCol, cursorRow = BLOCK_COLS//2-1, BLOCK_ROWS//2
block1, block2 = None, None
blocksFalling = []
blocksMatching = []
popLevel = 0
modeSelect = 0

def toast(texts):
    global frame
    width = 0
    for text in texts:
        width = max(width,len(text)*9+10)
    height = len(texts)*9+20
        
    text = texts[0]
    for i in range(1,len(texts)):
        text += "\n"+texts[i]
    
    rectToast.hidden = False
    rectToast.width = width
    rectToast.height = height
    txtToast.hidden = False
    txtToast.text = text
    frame = 0
    while True:
        tick()
        if frame > 10 and is_just_pressed(BUTTON_A):
            break
    rectToast.hidden = True
    txtToast.hidden = True

state = SM_INTRO
frame = 0
stateLoad = True
stateUnload = False
def setState(next):
    global state, frame, stateUnload
    print("state", next)
    state = next
    frame = 0
    stateUnload = True

for x in root_group:
    x.hidden = False
loading_txt.hidden = True
display.refresh()

previous_pressed_buttons = None
while True:
    tick()

    # mouse input
    if mouse is not None:
        # TODO: Handle mouse position and click
        previous_pressed_buttons = mouse.pressed_btns

    # handle escape
    if is_just_pressed(BUTTON_HOME):
        break

    stateLoad = (frame == 1)
    stateUnload = False
        
    if state == SM_INTRO:
        if stateLoad:
            sprLogo.hidden = False
        
        if frame <= 16:
            sprLogo.position = (64,60-(1<<(16-frame)))
        else:
            setState(SM_PRESS_START)
        
    elif state == SM_PRESS_START:
        if stateLoad:
            sprLogo.hidden = False
            for block in menuBlocks:
                block.hidden = False
                
        for i in range(len(menuBlocks)):
            r = math.pi * 2 * i/len(menuBlocks) + frame * 0.08
            menuBlocks[i].position = (64+55*math.cos(r),64+55*math.sin(r))
        if is_just_pressed(BUTTON_A):
            mixer.play(sfxNav)
            rumble(3,0.4)
            modeSelect = MODE_NORMAL
            setState(SM_MODE_SELECT)
            
        if stateUnload:
            sprLogo.hidden = True
            for block in menuBlocks:
                block.hidden = True
        
    elif state == SM_MODE_SELECT:
        if stateLoad:
            rectMenuGameMode.hidden = False
            rectMenuGameModeBorder.hidden = False
            txtMenuGameModeOptions[0].hidden = False
            txtMenuGameModeOptions[0].pixel_shader = WHITE
            txtMenuGameModeOptions[1].hidden = False
            txtMenuGameModeOptions[1].pixel_shader = DARKGREY
            txtMenuGameModeOptions[2].hidden = False
            txtMenuGameModeOptions[2].pixel_shader = DARKGREY
            checkExtraUnlock()
        
        for i in range(len(menuBlocks)):
            r = math.pi * 2 * i/len(menuBlocks) + frame * 0.08
            menuBlocks[i].position = (64+55*math.cos(r),64+55*math.sin(r))
        if is_just_pressed(BUTTON_DOWN, BUTTON_JOYSTICK_DOWN):
            modeSelect = (modeSelect + 1) % 3
        if is_just_pressed(BUTTON_UP, BUTTON_JOYSTICK_UP):
            modeSelect = (modeSelect + 2) % 3
        if is_just_pressed(BUTTON_A):
            if modeSelect == MODE_EXTRA and not extraUnlock:
                toast(["Beat","Normal Mode","to unlock","Extra Mode!"])
            elif modeSelect == MODE_CUSTOM and len(customStages) == 0:
                toast(["No Custom","Mode stages","are found!"])
            else:
                mixer.play(sfxNav)
                rumble(3,0.4)
                setState(SM_STAGE_SELECT)
        if is_just_pressed(BUTTON_B):
            setState(SM_PRESS_START)
        for i in range(3):
            txtMenuGameModeOptions[i].pixel_shader = WHITE if (i == modeSelect) else DARKGREY
        
        if stateUnload:
            rectMenuGameMode.hidden = True
            rectMenuGameModeBorder.hidden = True
            txtMenuGameModeOptions[0].hidden = True
            txtMenuGameModeOptions[1].hidden = True
            txtMenuGameModeOptions[2].hidden = True
        
    elif state == SM_STAGE_SELECT:
        if stateLoad:
            if modeSelect == MODE_NORMAL:
                stages = standardStages
            elif modeSelect == MODE_EXTRA:
                stages = extraStages
            elif modeSelect == MODE_CUSTOM:
                stages = customStages
            levelCounts = loadLevelCounts(stages)              
            clears = [save_data.get(stages[i], bytearray(levelCounts[i])) for i in range(len(stages))]
            locks = [False]
            for i in range(1,len(clears)):
                clear = clears[i-1]
                locked = locks[i-1]
                if modeSelect != MODE_CUSTOM:
                    for check in clear:
                        if not check:
                            locked = True
                            break
                locks.append(locked)
            if modeSelect == MODE_CUSTOM:
                stage = 0
            else:
                stage = len(stages)-1
                for i in range(1,len(stages)):
                    if locks[i]:
                        stage = i-1
                        break
            titles = loadTitles(stages)
            rectMenuStage.hidden = False
            rectMenuStageBorder.hidden = False
            txtMenuStageTitle.hidden = False
            rectMenuStageLock.hidden = not locks[stage]
            sprMenuStageLock.hidden = not locks[stage]
            txtMenuStageTitle.text = titles[stage]
            for i in range(10):
                txt = txtMenuStageLevels[i]
                spr = sprMenuStageClears[i]
                if i < levelCounts[stage]:
                    txt.hidden = False
                    spr.frame_current_x = clears[stage][i]
                    spr.hidden = False
                else:
                    txt.hidden = True
                    spr.hidden = True
                
        
        updateStage = False
        if is_just_pressed(BUTTON_LEFT, BUTTON_JOYSTICK_LEFT) and stage > 0:
            stage -= 1
            updateStage = True
        if is_just_pressed(BUTTON_RIGHT, BUTTON_JOYSTICK_RIGHT) and stage < len(stages)-1:
            stage += 1
            updateStage = True
            
        if is_just_pressed(BUTTON_A) and not locks[stage]:
            level = 0
            for i in range(len(clears[stage])):
                if not clears[stage][i]:
                    level = i
                    break
            mixer.play(sfxNav)
            rumble(3,0.4)
            setState(SM_LEVEL_LOADING)
            
        if is_just_pressed(BUTTON_B):
            setState(SM_MODE_SELECT)
            
        if updateStage:
            updateStage = False
            rectMenuStageLock.hidden = not locks[stage]
            sprMenuStageLock.hidden = not locks[stage]
            txtMenuStageTitle.text = titles[stage]
            for i in range(10):
                txt = txtMenuStageLevels[i]
                spr = sprMenuStageClears[i]
                if i < levelCounts[stage]:
                    txt.hidden = False
                    spr.frame_current_x = clears[stage][i]
                    spr.hidden = False
                else:
                    txt.hidden = True
                    spr.hidden = True
                
        if stateUnload:
            rectMenuStage.hidden = True
            rectMenuStageBorder.hidden = True
            txtMenuStageTitle.hidden = True
            rectMenuStageLock.hidden = True
            sprMenuStageLock.hidden = True
            for txt in txtMenuStageLevels:
                txt.hidden = True
            for spr in sprMenuStageClears:
                spr.hidden = True
    
    elif state == SM_LEVEL_LOADING:
        if stateLoad:
            loadLevel(stages[stage],level)
            rectBorder.hidden = False
            lblLevelTitle.hidden = False
            lblLevel.hidden = False
            lblMovesTitle.hidden = False
            lblMoves.hidden = False
            sprCheckmark.hidden = False
        
        falling = False
        for block in blocks:
            if block is not None and not block.tween.finished:
                falling = True
                break
        if not falling:
            cursorCol, cursorRow = BLOCK_COLS//2-1, BLOCK_ROWS//2
            cursor.position = (BLOCKS_START_X+cursorCol*10+10,BLOCKS_START_Y+cursorRow*10+5)
            cursor.hidden = False
            setState(SM_CURSOR_SELECT)
            
    elif state == SM_LEVEL_UNLOADING:
        setState(SM_STAGE_SELECT)
        if stateUnload:
            for i in range(len(blocks)):
                block = blocks[i]
                if block is not None:
                    blocks[i] = None
                    sprite_group.remove(block.group)
                    del block
            rectBorder.hidden = True
            lblLevelTitle.hidden = True
            lblLevel.hidden = True
            lblMovesTitle.hidden = True
            lblMoves.hidden = True
            sprCheckmark.hidden = True
            cursor.hidden = True
            lblOverlay.hidden = True
            sprBG.texture = texBG
    
    elif state == SM_CURSOR_SELECT:
        if is_just_pressed(BUTTON_LEFT, BUTTON_JOYSTICK_LEFT) and cursorCol > 0:
            cursorCol -= 1
        if is_just_pressed(BUTTON_RIGHT, BUTTON_JOYSTICK_RIGHT) and cursorCol < BLOCK_COLS-2:
            cursorCol += 1
        if is_just_pressed(BUTTON_UP, BUTTON_JOYSTICK_UP) and cursorRow > 0:
            cursorRow -= 1
        if is_just_pressed(BUTTON_DOWN, BUTTON_JOYSTICK_DOWN) and cursorRow < BLOCK_ROWS-1:
            cursorRow += 1
            
        if is_just_pressed(BUTTON_R1):
            level = (level+1) % len(clears[stage])
            loadLevel(stages[stage],level)
        if is_just_pressed(BUTTON_L1):
            level = (level+len(clears[stage])-1) % len(clears[stage])
            loadLevel(stages[stage],level)
            
        if is_just_pressed(BUTTON_A):
            i = cursorRow*BLOCK_COLS+cursorCol
            block1 = blocks[i]
            block2 = blocks[i+1]
            if block1 is not None or block2 is not None:
                blocks[i], blocks[i+1] = blocks[i+1], blocks[i]
                if block1 is not None:
                    block1.tweenMove((block1.x+10,block1.y),200)
                if block2 is not None:
                    block2.tweenMove((block2.x-10,block2.y),200)
                moves -= 1
                lblMoves.text = str(moves)
                popLevel = 0
                setState(SM_SWAP_ANIM)
                
        if is_just_pressed(BUTTON_B):
            setState(SM_LEVEL_UNLOADING)

        cursor.position = (BLOCKS_START_X+cursorCol*10+10,BLOCKS_START_Y+cursorRow*10+5)

    elif state == SM_SWAP_ANIM:
        animDone = True
        if block1 is not None and not block1.tween.finished:
            animDone = False
        if block2 is not None and not block2.tween.finished:
            animDone = False
        if animDone:
            mixer.play(sfxSwap)
            rumble(3,0.4)
            blocksFalling = checkFalling(blocks)
            if len(blocksFalling) > 0:
                startFallAnim(blocksFalling)
                setState(SM_FALL_ANIM)
            else:
                blocksMatching = checkMatching(blocks)
                if len(blocksMatching) > 0:
                    setState(SM_MATCH_ANIM)
                else:
                    setState(SM_MOVE_OVER)
                    
    # TODO figure out how to do FALLING and SQUISH block states
    elif state == SM_FALL_ANIM:
        animDone = True
        for _, _, block in blocksFalling:
            if not block.tween.finished:
                animDone = False
                break
        if animDone:
            blocksFalling = checkFalling(blocks)
            if len(blocksFalling) > 0:
                startFallAnim(blocksFalling)
                setState(SM_FALL_ANIM)
            else:
                blocksMatching = checkMatching(blocks)
                if len(blocksMatching) > 0:
                    setState(SM_MATCH_ANIM)
                else:
                    setState(SM_MOVE_OVER)
                
    # TODO popping animation
    elif state == SM_MATCH_ANIM:
        if stateLoad:
            for _, _, block in blocksMatching:
                block.normal = False
                
        if frame < 30:
            for _, _, block in blocksMatching:
                block.frame_current_x = BLOCK_STATE_LIGHT if ((frame%2)==0) else BLOCK_STATE_NORMAL
        elif frame >= 30:
            if frame == 30:
                for _, _, block in blocksMatching:
                    block.frame_current_x = BLOCK_STATE_POP
            blockPopIndex = (frame-30)//4
            if ((frame-30)%4) == 0:
                if 0 < blockPopIndex <= len(blocksMatching):
                    blocksMatching[blockPopIndex-1][2].hidden = True
                if blockPopIndex < len(blocksMatching):
                    blocksMatching[blockPopIndex][2].frame_current_x = BLOCK_STATE_POP2
                    mixer.play(sfxPops[popLevel])
                    rumble(2,0.25)
                    popLevel = min(len(sfxPops)-1,popLevel+1)
                else:
                    for col, row, block in blocksMatching:
                        sprite_group.remove(block.group)
                        blocks[row*BLOCK_COLS+col] = None
                        del block
                    blocksFalling = checkFalling(blocks)
                    if len(blocksFalling) > 0:
                        startFallAnim(blocksFalling)
                        setState(SM_FALL_ANIM)
                    else:
                        setState(SM_MOVE_OVER)
    
    elif state == SM_MOVE_OVER:
        cleanBoard = True
        for block in blocks:
            if block is not None:
                cleanBoard = False
                break
        if cleanBoard:
            lblOverlay.text = "YOU\nWIN"
            lblOverlay.scale = 2
            lblOverlay.hidden = False
            cursor.hidden = True
            sprCheckmark.frame_current_x = 1
            setState(SM_LEVEL_WIN)
        elif moves > 0:
            setState(SM_CURSOR_SELECT)
        elif moves == 0:
            for block in blocks:
                if block is not None:
                    block.frame_current_x = BLOCK_STATE_DARK
            lblOverlay.text = " TRY \nAGAIN"
            lblOverlay.scale = 1
            lblOverlay.hidden = False
            cursor.hidden = True
            setState(SM_LEVEL_LOST)
            
    elif state == SM_LEVEL_WIN:
        lblOverlay.hidden = False if ((frame % 30) < 15) else 0
        if frame == 5:
            mixer.play(sfxWin)
        if frame > 30 and is_just_pressed(BUTTON_A):
            newClear = clears[stage][level] == 0
            clears[stage][level] = 1
            save_data[stages[stage]] = clears[stage]
            level = (level+1) % len(clears[stage])
            complete = True
            for clear in clears[stage]:
                if not clear:
                    complete = False
                    break
            
            if newClear and complete:
                level = 0
                if modeSelect == MODE_NORMAL and stage == 5:
                    toast(["NORMAL","COMPLETE","","Extra Stages","Unlocked!"])
                    extraUnlock = True
                else:
                    stage = (stage+1) % len(stages)            
                setState(SM_LEVEL_UNLOADING)
            else:
                loadLevel(stages[stage],level)
                lblOverlay.text = ""
                lblOverlay.hidden = True
                cursor.hidden = False
                cursorCol, cursorRow = BLOCK_COLS//2-1, BLOCK_ROWS//2
                setState(SM_CURSOR_SELECT)
        
    elif state == SM_LEVEL_LOST:
        lblOverlay.hidden = False if ((frame % 30) < 15) else 0
        if frame == 5:
            mixer.play(sfxLose)
        if frame > 30 and is_just_pressed(BUTTON_A):
            loadLevel(stages[stage],level)
            lblOverlay.text = ""
            lblOverlay.hidden = True
            cursor.hidden = False
            cursorCol, cursorRow = BLOCK_COLS//2-1, BLOCK_ROWS//2
            setState(SM_CURSOR_SELECT)
            
    for block in blocks:
        if block is not None:
            block.updateFalling()

try:
    with open(SAVE_FILE, "w") as f:
        json.dump(save_data, f)
except OSError as e:
    print(f"Error during save: {e}")

gamepad.disconnect()
peripherals.deinit()
supervisor.reload()
