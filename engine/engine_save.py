# SPDX-FileCopyrightText: 2026 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import json
import os

_DIR = "/saves/ThumbyColor"

_dir = None
_filepath = None
_data = None

def _mkdir(dir: str) -> str:
    dir = dir.strip("/")
    parts = dir.split("/")
    for i in range(len(parts)):
        path = f"{_DIR}/" + "/".join(parts[:i+1])
        try:
            os.stat(path)
        except OSError:
            os.mkdir(path)

def _init_saves_dir(dir: str) -> None:
    global _dir
    _dir = dir.strip("/")

def saves_dir() -> str:
    return _mkdir(_dir) if _dir else None

def set_location(filepath: str) -> None:
    global _filepath, _data
    if _dir:
        _filepath = filepath
        try:
            with open(f"{_DIR}/{_dir}/{_filepath}", "r") as f:
                try:
                    _data = json.load(f)
                except (ValueError, AttributeError):
                    _data = {}
        except OSError:
            _data = {}

def delete_location() -> None:
    global _filepath, _data
    if _dir and _filepath:
        try:
            os.remove(f"{_DIR}/{_dir}/{_filepath}")
        except OSError:
            pass
        else:
            _filepath = None
            _data = None

def save(entry_name: str, value) -> None:
    global _data
    if _data is not None:
        _data[entry_name] = value

def load(entry_name: str, default):
    global _data
    return _data.get(entry_name, default) if _data is not None else default

def delete(entry_name: str) -> None:
    global _data
    if _data is not None:
        _data.pop(entry_name)

def _dump() -> bool:
    if _dir and _filepath and _data is not None:
        try:
            with open(f"{_DIR}/{_dir}/{_filepath}", "w") as f:
                json.dump(_data, f)
        except (OSError, IOError):
            return False
        else:
            return True
    else:
        return False
