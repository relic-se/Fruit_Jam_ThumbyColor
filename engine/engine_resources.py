# SPDX-FileCopyrightText: 2026 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import audiocore
from displayio import Bitmap
from fontio import Glyph
import os

import adafruit_imageload
import adafruit_rtttl

def _get_filepath(filepath: str) -> str:
    # redirect absolute path to filesystem directory
    if filepath.startswith("/"):
        filepath = "/" + "/".join(os.getcwd().strip("/").split("/")[:-2]) + filepath
    return filepath

class TextureResource:

    def __init__(self, width: str|int, height: bool|int = False, color: int = None, bit_depth: int = None):  # NOTE: We're not respecting the options here at the moment
        if isinstance(width, str):
            self._bitmap, self._palette = adafruit_imageload.load(_get_filepath(width))
            self.data = None
        else:
            self.data = bytearray(width * height * 2)  # 16-bit RGB565

    @property
    def width(self) -> int:
        return self._bitmap.width
    
    @property
    def height(self) -> int:
        return self._bitmap.height
    
class WaveSoundResource:

    def __init__(self, filepath: str):
        self._wave = audiocore.WaveFile(_get_filepath(filepath))

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
            if value != color:
                color = value
                self._widths.append(width)
                self._offsets.append(x - width)
                width = 1
            else:
                width += 1
        self._widths.append(width)
        self._offsets.append(self.texture.width - width)
        self._widths = tuple(self._widths)
        self._offsets = tuple(self._offsets)

        self._letter_spacing = 1
        self._line_spacing = 1
        self._glyphs = [None] * (self._MAX - self._MIN + 1)

    @property
    def widths(self) -> bytearray:
        return bytearray(self._widths)
    
    @property
    def offsets(self) -> bytearray:
        return bytearray(self._offsets)

    @property
    def height(self) -> int:
        return self.texture.height - 1

    # `fontio.FontProtocol`

    @property
    def bitmap(self) -> Bitmap:
        return self.texture
    
    def get_bounding_box(self) -> tuple:
        return max(self.widths), self.height
    
    def get_glyph(self, codepoint: int) -> Glyph:
        if self._MIN <= codepoint <= self._MAX:
            index = codepoint - self._MIN
            if index in self._glyphs:
                return self._glyphs[index]
            else:
                glyph = Glyph(
                    self.texture._bitmap,
                    index,
                    self._widths[index],
                    self.texture._bitmap.height,
                    self._offsets[index],
                    0,
                    self._widths[index] + self._letter_spacing,
                    self.height + self._line_spacing
                )
                self._glyphs[index] = glyph
                return glyph

class RTTTLSoundResource:

    def __init__(self, filepath: str):
        filepath = _get_filepath(filepath)
        with open(filepath, "r") as f:
            data = f.read()
        _, defaults, tune = data.lower().split(":")

        # get defaults
        self._duration = 4
        self._octave = 6
        self._tempo = 63

        for default in defaults.split(","):
            key, value = default.split("=")
            value = int(value)
            if key == "d":
                self._duration = value
            elif key == "o":
                self._octave = value
            elif key == "b":
                self._tempo = value

        # read notes
        self._data = []
        for note in tune.split(","):
            note_frequency, note_duration = adafruit_rtttl._parse_note(note, self._duration, self._octave)
            if note_frequency is None:
                note_frequency = 0
            self._data.append((note_frequency, 4 / note_duration * 60 / self._tempo))
    
    @property
    def tempo(self) -> int:
        return self._tempo
    
    @property
    def data(self) -> bytearray:
        pass
