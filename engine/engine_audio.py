# SPDX-FileCopyrightText: 2026 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import audiomixer

import engine_main
import engine_resources

_CHANNELS = 4

_mixer = audiomixer.Mixer(
    voice_count=_CHANNELS,
    sample_rate=engine_main._peripherals.dac.sample_rate,
    channel_count=1,
    bits_per_sample=8,
    samples_signed=False,
    buffer_size=8192,
)
engine_main._peripherals.audio.play(_mixer)

_volume = 1
_channels = []
class AudioChannel:
    
    def __init__(self):
        self._index = len(_channels)
        _channels.append(self)
        self._gain = 1
        self._source = None

    def play(self, sound_resource: engine_resources.WaveSoundResource, loop: bool = False) -> None:
        self._source = sound_resource
        _mixer.voice[self._index].play(sound_resource._wave, loop=loop)

    def stop(self) -> None:
        _mixer.voice[self._index].stop()

    @property
    def source(self) -> engine_resources.WaveSoundResource:
        if self._source and not _mixer.voice[self._index].playing:
            self._source = None
        return self._source
    
    @property
    def gain(self) -> float:
        return self._gain
    
    @gain.setter
    def gain(self, value: float) -> None:
        self._gain = min(max(value, 0), 1)
        _mixer.voice[self._index].level = self._gain * _volume
    
    @property
    def time(self) -> float:
        return 0  # TODO?
    
    @property
    def amplitude(self) -> float:
        return 0  # TODO? Possible?
    
    @property
    def loop(self) -> bool:
        return _mixer.voice[self._index].loop
    
    @loop.setter
    def loop(self, value: bool) -> None:
        _mixer.voice[self._index].loop = value

    @property
    def done(self) -> bool:
        return not _mixer.voice[self._index].playing

for i in range(_CHANNELS):
    AudioChannel()

def play(sound_resource: engine_resources.WaveSoundResource, channel_index: int, loop: bool = False) -> AudioChannel:
    if channel_index < 0 or channel_index >= _CHANNELS:
        raise ValueError("Invalid channel")
    _channels[channel_index].play(sound_resource, loop=loop)
    return _channels[channel_index]

def stop(channel_index: int) -> None:
    if channel_index < 0 or channel_index >= _CHANNELS:
        raise ValueError("Invalid channel")
    _channels[channel_index].stop()

def set_volume(set_volume: float) -> None:
    global _volume
    _volume = set_volume
    for i in range(_CHANNELS):
        _mixer.voice[i].level = _channels[i]._gain * _volume

def get_volume() -> float:
    return _volume
