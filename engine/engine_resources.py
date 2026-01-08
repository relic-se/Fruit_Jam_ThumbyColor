# SPDX-FileCopyrightText: 2026 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import audiocore
import fontio

import adafruit_imageload

class TextureResource:

    def __init__(self, filepath: str):
        self._bitmap, self._palette = adafruit_imageload.load(filepath)

    @property
    def width(self) -> int:
        return self._bitmap.width
    
    @property
    def height(self) -> int:
        return self._bitmap.height
    
class WaveSoundResource:

    def __init__(self, filepath: str):
        self._wave = audiocore.WaveFile(filepath)

    def sample_rate(self) -> int:
        return self._wave.sample_rate

class FontResource:

    _MIN = ord(" ")
    _MAX = ord("~")

    def __init__(self, filepath: str):
        self.texture = TextureResource(filepath)
        
        self._widths = []
        self._offsets = []
        y = self.texture.height - 1
        color = self.texture._bitmap[0, y]
        width = 0
        for x in range(self.texture.width):
            value = self.texture._bitmap[x, y]
            if value is not color:
                self._widths.append(width)
                self._offsets.append(x - width)
                width = 1
            else:
                width += 1
        self._widths.append(width)
        self._offsets.append(self.texture.width - width)
        self._widths = tuple(self._widths)
        self._offsets = tuple(self._offsets)

    @property
    def widths(self) -> bytearray:
        return bytearray(self._widths)
    
    @property
    def offsets(self) -> bytearray:
        return bytearray(self._offsets)

    @property
    def height(self) -> int:
        return self.texture.height - 1
