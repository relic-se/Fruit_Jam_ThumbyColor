# SPDX-FileCopyrightText: 2026 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import displayio

from adafruit_display_text.label import Label

from engine_main import _LAYERS, _get_layer, _display, _group
import engine
from engine_math import Vector2, Vector3, Rectangle
from engine_resources import TextureResource, FontResource
from engine_draw import Color

def _get_vector3(value: Vector2|Vector3|tuple|float|int) -> Vector3:
    if isinstance(value, Vector3):
        return value
    elif isinstance(value, tuple):
        if len(value) == 2:
            value = value + (0,)
        return Vector3(*value)
    elif isinstance(value, Vector2):
        return Vector3(value.x, value.y, 0)
    elif isinstance(value, (float, int)):
        return Vector3(float(value), float(value), 0)
    else:
        return Vector3(0, 0, 0)

def _get_vector2(value: Vector2|tuple|float|int) -> Vector2:
    if isinstance(value, Vector2):
        return value
    elif isinstance(value, tuple):
        if len(value) == 1:
            value = value + (0,)
        return Vector2(*value)
    elif isinstance(value, (float, int)):
        return Vector2(float(value), float(value))
    else:
        return Vector2(0, 0)
    
def _get_color(value: Color|int) -> Color:
    if isinstance(value, int):
        return Color(value)
    return value

class EmptyNode:

    def __init__(self, position: Vector2|Vector3|tuple = None, rotation: Vector2|Vector3|tuple = None, layer: int = 0):
        self._layer = None
        self._children = []

        self.position = position
        self.rotation = rotation
        self.layer = layer
        
        engine._nodes.append(self)

    def add_child(self, child: EmptyNode) -> None:
        self._children.append(child)

    def get_child(self, index: int) -> EmptyNode:
        return self._children[index]
    
    def get_child_count(self) -> int:
        return len(self._children)
    
    def mark_destroy_all(self) -> None:
        self.mark_destroy_children()
        self.mark_destroy()

    def mark_destroy(self) -> None:
        if len(self._children):
            raise ValueError("children not empty")

    def mark_destroy_children(self) -> None:
        while len(self._children):
            self.remove_child(self._children[len(self._children)-1])

    def remove_child(self, child) -> None:
        self._children.remove(child)

    def tick(self, dt: float) -> None:
        pass

    @property
    def position(self) -> Vector3:
        return self._position
    
    @position.setter
    def position(self, value: Vector3|tuple) -> None:
        self._position = _get_vector3(value)

    @property
    def rotation(self) -> Vector3:
        return self._rotation
    
    @rotation.setter
    def rotation(self, value: Vector3|tuple) -> None:
        self._rotation = _get_vector3(value)

    @property
    def layer(self) -> int:
        return self._layer
    
    @layer.setter
    def layer(self, value: int) -> None:
        self._layer = min(max(value, 0), _LAYERS-1)

class CameraNode(EmptyNode):

    def __init__(self, position: Vector3|tuple, zoom: float = 1, viewport: Rectangle = None, rotation: Vector3|tuple = None, fov: float = 0, view_distance: float = 0, layer: int = 0):
        super().__init__(position, rotation, layer)
        self.zoom = zoom
        self.viewport = viewport
        self.fov = fov
        self.view_distance = view_distance

    @property
    def position(self) -> Vector3:
        return self._position
    
    @position.setter
    def position(self, value: Vector3|tuple) -> None:
        self._position = _get_vector3(value)
        _group.x = _display.width // 2 - self._position.x * _group.scale
        _group.y = _display.height // 2 - self._position.y * _group.scale

class _GroupNode(EmptyNode):

    def __init__(self, position: Vector2, rotation: float = None, scale: Vector2 = None, opacity: float = 1, layer: int = 0):
        self._parent = None
        self._group = displayio.Group()
        super().__init__(position, rotation, layer)
        self.scale = scale
        self.opacity = opacity

    @property
    def layer(self) -> int:
        return self._layer
    
    @layer.setter
    def layer(self, value: int) -> None:
        if self._parent and self._group in self._parent:
            self._parent.remove(self._group)
        self._layer = min(max(value, 0), _LAYERS-1)
        self._parent = _get_layer(self._layer)
        self._parent.append(self._group)

    @property
    def scale(self) -> Vector2:
        return self._scale
    
    @scale.setter
    def scale(self, value: Vector2|tuple) -> None:
        self._scale = _get_vector2(value)
        self._group.scale = max(int(self._scale.x), 1)

    @property
    def position(self) -> Vector2:
        return self._position
    
    @position.setter
    def position(self, value: Vector3|tuple) -> None:
        self._position = _get_vector2(value)
        self._group.x = int(self._position.x)
        self._group.y = int(self._position.y)

    @property
    def rotation(self) -> float:
        return self._rotation
    
    @rotation.setter
    def rotation(self, value: float) -> None:
        self._rotation = value

    def add_child(self, child: EmptyNode) -> None:
        super().add_child(child)
        if hasattr(child, "_group"):
            if child._group in child._parent:
                child._parent.remove(child._group)
            child._parent = self._group
            self._group.append(child._group)
    
    def mark_destroy(self) -> None:
        super().mark_destroy()
        while len(self._group):
            self._group.pop()
        if self._group in self._parent:
            self._parent.remove(self._group)
            self._parent = None
        self._group = None

    def remove_child(self, child) -> None:
        super().remove_child(child)
        if hasattr(child, "_group") and child._group in self._group:
            self._group.remove(child._group)
            child._parent = None

    @property
    def opacity(self) -> float:
        return self._opacity
    
    @opacity.setter
    def opacity(self, value: float) -> None:
        self._opacity = value
        self._group.hidden = self._opacity <= 0.01

    # TODO: global_position

class Sprite2DNode(_GroupNode):

    def __init__(self, position: Vector2 = None, texture: TextureResource = None, transparent_color: Color|int = None, fps: float = 30, frame_count_x: int = 1, frame_count_y = 1, rotation: float = None, scale: Vector2|tuple = None, opacity: float = 1, playing: bool = True, loop: bool = True, layer: int = 0):
        super().__init__(position, rotation, scale, opacity, layer)
        self._frame_count_x = min(frame_count_x, 1)
        self._frame_count_y = min(frame_count_y, 1)
        self._tg = None
        self._texture = None
        self._transparent_color = None

        self.playing = playing
        self.loop = loop
        self.fps = fps

        self.texture = texture
        self.transparent_color = transparent_color

    def _make_tg(self) -> bool:
        if self._tg or not self._texture or not self._frame_count_x or not self._frame_count_y:
            return False
        
        self._tg = displayio.TileGrid(
            bitmap=self._texture._bitmap, pixel_shader=self._texture._palette,
            width=1, height=1,
            tile_width=self._texture.width//self._frame_count_x,
            tile_height=self._texture.height//self._frame_count_y,
        )
        self._tg.x = -self._tg.tile_width//2
        self._tg.y = -self._tg.tile_height//2
        self._group.append(self._tg)

    @property
    def texture(self) -> TextureResource:
        return self._texture
    
    @texture.setter
    def texture(self, value: TextureResource) -> None:
        self._texture = value
        if self._texture:
            if not self._make_tg():
                self._tg.bitmap = self._texture._bitmap
                self._tg.pixel_shader = self._texture._palette
            if self._transparent_color:
                self.transparent_color = self._transparent_color
    
    @property
    def transparent_color(self) -> Color:
        return self._transparent_color

    @transparent_color.setter
    def transparent_color(self, value: Color|int) -> None:
        self._transparent_color = _get_color(value)
        if self._texture:
            if isinstance(self._texture._palette, displayio.ColorConverter) and self._transparent_color:
                try:
                    self._texture._palette.make_transparent(self._transparent_color._rgb888)
                except RuntimeError:  # prevents multiple transparent color error
                    pass
            else:
                for i in len(self._texture._palette):
                    if self._transparent_color and self._texture._palette[i] == self._transparent_color._rgb88:
                        self._texture._palette.make_transparent(i)
                    else:
                        self._texture._palette.make_opaque(i)

    @property
    def frame_count_x(self) -> int:
        return self._frame_count_x
    
    @frame_count_x.setter
    def frame_count_x(self, value: int) -> None:
        self._frame_count_x = min(value, 1)
        self._make_tg()

    @property
    def frame_count_y(self) -> int:
        return self._frame_count_y

    @frame_count_y.setter
    def frame_count_y(self, value: int) -> None:
        self._frame_count_y = min(value, 1)
        self._make_tg()

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
        if self.playing and self._frame_duration:
            self._frame_time += dt
            if self._frame_time >= self._frame_duration:
                self.frame_current_x += 1
                self._frame_time = 0
                if not self.loop and self.frame_current_x == self._frame_count_x - 1:
                    self.playing = False
        
class Rectangle2DNode(_GroupNode):

    def __init__(self, position: Vector2|tuple, width: float, height: float, color: Color, opacity: float = 1, outline: bool = False, rotation: float = 0, scale: Vector2|tuple|float|int = 1, layer: int = 0):
        super().__init__(position, rotation, scale, opacity, layer)
        self._outline = outline
        
        self._bitmap = displayio.Bitmap(width, height, 1 + int(outline))
        self._palette = displayio.Palette(1 + int(outline))
        self.color = _get_color(color)
        if outline:
            self._palette.make_transparent(0)
            for y in range(height):
                self._bitmap[0, y] = 1
                self._bitmap[width-1, y] = 1
                if y in (0, height - 1):
                    for x in range(1, width-1):
                        self._bitmap[x, y] = 1
        
        _bg_tg = displayio.TileGrid(bitmap=self._bitmap, pixel_shader=self._palette)
        _bg_tg.x, _bg_tg.y = -width // 2, -height // 2
        self._group.append(_bg_tg)

    @property
    def color(self) -> Color:
        return self._color
    
    @color.setter
    def color(self, value: Color|int) -> None:
        self._color = _get_color(value)
        self._palette[int(self._outline)] = self._color._rgb888

    @property
    def width(self) -> int:
        return self._bitmap.width
    
    @property
    def height(self) -> int:
        return self._bitmap.height
    
    # TODO: width/height setters?

# TODO: Line2DNode, Circle2DNode - may require adafruit_display_shapes

class Text2DNode(_GroupNode):

    def __init__(self, position: Vector2|tuple, font: FontResource, text: str = "", rotation: float = 0, scale: Vector2|tuple|float|int = 1, opacity: float = 1, letter_spacing: int = 1, line_spacing: int = 1, color: Color|int = None, layer: int = 0):
        super().__init__(position, rotation, scale, opacity, layer)

        self._font = font
        self._label = Label(
            self._font,
            anchor_point=(0.5, 0.5),
            anchored_position=(0, 0),
        )
        self._group.append(self._label)

        self.letter_spacing = letter_spacing
        self.line_spacing = line_spacing
        self.color = _get_color(color)
        self.text = text

    @property
    def font(self) -> FontResource:
        return self._font

    @property
    def color(self) -> Color:
        return self._color
    
    @color.setter
    def color(self, value: Color|int) -> None:
        self._color = _get_color(value)
        self._label.color = self._color._rgb888

    @property
    def text(self) -> str:
        return self._label.text
    
    @text.setter
    def text(self, value: str) -> None:
        self._label.text = value

    @property
    def line_spacing(self) -> int:
        return self._font._line_spacing
    
    @line_spacing.setter
    def line_spacing(self, value: int) -> None:
        self._font._line_spacing = value
        self._label.line_spacing = value / self.font.texture._bitmap.height
