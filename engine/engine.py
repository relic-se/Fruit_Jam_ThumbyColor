# SPDX-FileCopyrightText: 2026 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import time

import engine_main
import engine_io

_fps_limit = 30

def fps_limit(value: int) -> None:
    global _fps_limit
    _fps_limit = value

def disable_fps_limit() -> None:
    global _fps_limit
    _fps_limit = None

_fps_running = 0
_fps_running_current = 0
_fps_running_timestamp = time.monotonic()

def get_running_fps() -> float:
    return _fps_running

_running = True
def start() -> None:
    global _running
    _running = True

def end() -> None:
    global _running
    _running = False

_nodes = []
_timestamp = None
def tick() -> bool:
    global _timestamp, _fps_running, _fps_running_current, _fps_running_timestamp

    engine_main._display.refresh(
        target_frames_per_second=_fps_limit,
    )

    engine_io._tick()
    if engine_io._HOME.is_just_pressed:
        reset()
    
    # tick nodes
    now = time.monotonic()
    if _running and _timestamp is not None:
        dt = now - _timestamp
        for node in _nodes:
            node.tick(dt)
    _timestamp = now

    # update running fps
    _fps_running_current += 1
    if now - _fps_running_timestamp >= 1:
        _fps_running = _fps_running_current / (now - _fps_running_timestamp)
        _fps_running_current = 0
        _fps_running_timestamp = now

    return _running

def dt() -> float:
    return time.monotonic() - _timestamp

def time_to_next_tick() -> float:
    if _fps_limit is None:
        return 0
    return max((1 / _fps_limit) - (time.monotonic() - _timestamp), 0)

def reset(soft_reset: bool = False) -> None:
    raise SystemExit  # returns to picker
