# Thumby Color Emulator for the Adafruit Fruit Jam
Translates the [TinyCircuits Thumby Color](https://tinycircuits.com/products/thumby-color) [engine API](https://color.thumby.us/doc/landing.html) into CircuitPython for use with the [Adafruit Fruit Jam](https://www.adafruit.com/product/6200).

## Controls

All controls are mapped for compatibility with the Thumby Color. Currently, USB boot keyboards and [various gamepads](https://circuitpython-usb-host-gamepad.readthedocs.io/) are supported.

| Thumby / Action | Gamepad | Keyboard |
|--------|---------|----------|
| D-Pad | D-Pad / Left Joystick | Arrow keys / WASD |
| A | A | J / Z |
| B | B | K / X |
| LB | L1 | Q / C |
| RB | R1 | E / V |
| MENU | Start | Enter |
| Reload or exit to [Fruit Jam OS](https://github.com/adafruit/Fruit-Jam-OS) | Home | Escape |

## Compatibility List

| Game | Status |
|------|------------|
| 4Connect | ❓ _Untested_ |
| 2048 | ❓ _Untested_ |
| BadApple | ❓ _Untested_ |
| BustAThumb | ❓ _Untested_ |
| Chess | ❓ _Untested_ |
| Clouds | ❓ _Untested_ |
| ComboPool | ❓ _Untested_ |
| Demos | ❓ _Untested_ |
| FroggyRoad | ❓ _Untested_ |
| Magic8Ball | ❓ _Untested_ |
| Monstra | ❓ _Untested_ |
| PuzzleAttack | ⚠️ _Playable_ |
| Sand | ❓ _Untested_ |
| Solitaire | ❓ _Untested_ |
| SongOfMorus | ❓ _Untested_ |
| Tagged | ❓ _Untested_ |
| Tetrumb | ❓ _Untested_ |
| ThumbAtro | ❓ _Untested_ |
| ThumbSweeper | ❓ _Untested_ |
| Thumgeon_II | ❓ _Untested_ |
| WallRacerC | ❓ _Untested_ |

### Excluded Applications

The following applications are manually excluded from the list:

- FloodLight
- Screensaver
- Utilities (BatteryCheck)

## Building
Ensure that you have python 3.x installed system-wide and all the prerequisite libraries installed using the following command:

``` shell
pip install circup requests
```

Download all CircuitPython libraries and package the application using the following command:

``` shell
python build/build.py
```

The project bundle should be found within `./dist` as a `.zip` file with the same name as your repository.
