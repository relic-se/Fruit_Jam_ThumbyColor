# SPDX-FileCopyrightText: 2026 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import engine_main
from engine_resources import TextureResource

class Color:

    def __init__(self, *value: int):
        self.set(*value)

    def set(self, *value: float|int) -> None:
        if len(value) == 1:
            r5 = (value[0] >> 11) & 0b11111
            g6 = (value[0] >> 5) & 0b111111
            b5 = value[0] & 0b11111

            self._r = min(max(r5 / 0b11111, 0), 1)
            self._g = min(max(g6 / 0b111111, 0), 1)
            self._b = min(max(b5 / 0b11111, 0), 1)

        elif len(value) == 3:
            self._r, self._g, self._b = [min(max(x, 0), 1) for x in value]

            r5 = min(max(int(self._r * 0xff), 0), 0b11111)
            g6 = min(max(int(self._g * 0xff), 0), 0b111111)
            b5 = min(max(int(self._b * 0xff), 0), 0b11111)

        else:
            raise ValueError("Invalid number of color components")

        self._rgb565 = (r5 << 11) | (g6 << 5) | b5

        r8 = min(max(int(self._r * 0xff), 0), 0xff)
        g8 = min(max(int(self._g * 0xff), 0), 0xff)
        b8 = min(max(int(self._b * 0xff), 0), 0xff)
        self._rgb888 = (r8 << 16) | (g8 << 8) | b8

    @property
    def value(self) -> int:
        return self._rgb565

black = Color(0x0000)
navy = Color(0x000F)
darkgreen = Color(0x03E0)
darkcyan = Color(0x03EF)
maroon = Color(0x7800)
purple = Color(0x780F)
olive = Color(0x7BE0)
lightgrey = Color(0xD69A)
darkgrey = Color(0x7BEF)
blue = Color(0x001F)
green = Color(0x07E0)
cyan = Color(0x07FF)
red = Color(0xF800)
magenta = Color(0xF81F)
yellow = Color(0xFFE0)
white = Color(0xFFFF)
orange = Color(0xFDA0)
greenyellow = Color(0xB7E0)
pink = Color(0xFE19)
brown = Color(0x9A60)
gold = Color(0xFEA0)
silver = Color(0xC618)
skyblue = Color(0x867D)
violet = Color(0x915C)

def set_background_color(background_color: Color|int) -> None:
    if isinstance(background_color, int):
        background_color = Color(background_color)
    engine_main._bg_palette[0] = background_color._rgb888

def set_background(background: TextureResource) -> None:
    pass  # TODO
