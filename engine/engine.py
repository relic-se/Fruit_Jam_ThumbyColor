# SPDX-FileCopyrightText: 2026 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import time

import engine_main
import engine_io

_fps_limit = 60
def fps_limit(value: int) -> None:
    global _fps
    _fps_limit = value

_nodes = []
_timestamp = None
def tick() -> None:
    global _timestamp

    engine_main._display.refresh(
        target_frames_per_second=_fps_limit,
    )
    engine_io._tick()

    # tick nodes
    now = time.monotonic()
    if _timestamp is not None:
        dt = _timestamp - now
        for node in _nodes:
            node.tick(dt)
    _timestamp = now

    frame += 1
