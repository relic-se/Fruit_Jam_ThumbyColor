# SPDX-FileCopyrightText: 2026 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import math
from micropython import const

from engine_nodes import EmptyNode

LOOP = const(1)
ONE_SHOT = const(2)
PING_PONG = const(3)

EASE_LINEAR = const(1)
EASE_SINE_IN = const(2)
EASE_SINE_OUT = const(3)
EASE_SINE_IN_OUT = const(4)
EASE_QUAD_IN = const(5)
EASE_QUAD_OUT = const(6)
EASE_QUAD_IN_OUT = const(7)
EASE_CUBIC_IN = const(8)
EASE_CUBIC_OUT = const(9)
EASE_CUBIC_IN_OUT = const(10)
EASE_QUART_IN = const(11)
EASE_QUART_OUT = const(12)
EASE_QUART_IN_OUT = const(13)
EASE_QUINT_IN = const(14)
EASE_QUINT_OUT = const(15)
EASE_QUINT_IN_OUT = const(16)
EASE_EXP_IN = const(17)
EASE_EXP_OUT = const(18)
EASE_EXP_IN_OUT = const(19)
EASE_CIRC_IN = const(20)
EASE_CIRC_OUT = const(21)
EASE_CIRC_IN_OUT = const(22)
EASE_BACK_IN = const(23)
EASE_BACK_OUT = const(24)
EASE_BACK_IN_OUT = const(25)
EASE_ELAST_IN = const(26)
EASE_ELAST_OUT = const(27)
EASE_ELAST_IN_OUT = const(28)
EASE_BOUNCE_IN = const(29)
EASE_BOUNCE_OUT = const(30)
EASE_BOUNCE_IN_OUT = const(31)

class Tween(EmptyNode):

    C5 = (2 * math.pi) / 4.5

    def __init__(self):
        super().__init__()

        self._duration = None
        self.loop_type = ONE_SHOT  # TODO: looping
        self.ease_type = EASE_LINEAR

        self._start = None
        self._end = None
        self._position = None
        self._playing = False
        self._finished = False
        self._after = None

    def start(self, object: object, attribute_name: str, start: float|tuple, end: float|tuple, duration: int, speed: float = None, loop_type: int = ONE_SHOT, ease_type: int = EASE_LINEAR) -> None:
        # TODO: speed?
        self._object = object
        self._attribute_name = attribute_name
        self._start = start
        self._end = end
        self.duration = duration
        self.loop_type = loop_type
        self.ease_type = ease_type
        self.restart()

    def end(self) -> None:
        setattr(self._object, self._attribute_name, self._end)
        self._position = 1
        self._playing = False
        self._finished = True
        if self._after and self.loop_type is ONE_SHOT:
            self._after.restart()

    def pause(self) -> None:
        if not self._finished:
            self._playing = False

    def unpause(self) -> None:
        if not self._finished:
            self._playing = True

    def restart(self) -> None:
        setattr(self._object, self._attribute_name, self._start)
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
        if self._playing and self._duration > 0:
            self._position += dt / self._duration
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
                setattr(self._object, self._attribute_name, value)

    def after(self, tween: Tween) -> None:
        self._after = tween

    @property
    def duration(self) -> int:
        return int(self._duration * 1000) if self._duration else 0
    
    @duration.setter
    def duration(self, value: int) -> None:
        self._duration = max(value, 0) / 1000

    @property
    def finished(self) -> bool:
        return self._finished

class Delay(EmptyNode):

    def __init__(self):
        super().__init__()

        self._delay = None
        self._time = None
        self._finished = False
        self.after = None

    def start(self, delay: float, after: function):
        self.delay = delay
        self._time = 0
        self._finished = False
        self._after = after

    def tick(self, dt: float) -> None:
        if not self._finished and self._delay and self.after and self._time:
            self._time += dt
            if self._time >= self._delay:
                self._finished = True
                if callable(self.after):
                    self.after()

    @property
    def delay(self) -> float:
        return self._delay * 1000
    
    @delay.setter
    def delay(self, value: float) -> None:
        self._delay = value / 1000

    @property
    def finished(self) -> bool:
        return self._finished
