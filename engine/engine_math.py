# SPDX-FileCopyrightText: 2026 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import math

class Vector3:

    def __init__(self, x: float, y: float, z: float):
        self.x, self.y, self.z = x, y, z

    def length(self) -> float:
        return math.sqrt(pow(self.x, 2) + pow(self.y, 2) + pow(self.z, 2))
    
    def normalized(self) -> Vector3:
        length = self.length()
        return Vector3(self.x / length, self.y / length, self.z / length)
    
    def __sub__(self, other: Vector2|Vector3|tuple) -> Vector3:
        x, y, z = self.x, self.y, self.z
        if isinstance(other, (Vector2, Vector3)):
            x -= other.x
            y -= other.y
            z -= other.z if isinstance(other, Vector3) else 0
        elif isinstance(other, tuple) and len(other) >= 2:
            x -= other[0]
            y -= other[1]
            z -= other[2] if len(other) >= 3 else 0
        else:
            raise NotImplementedError()
        return Vector3(x, y, z)
    
    def __add__(self, other: Vector2|Vector3|tuple) -> Vector3:
        x, y, z = self.x, self.y, self.z
        if isinstance(other, (Vector2, Vector3)):
            x += other.x
            y += other.y
            z += other.z if isinstance(other, Vector3) else 0
        elif isinstance(other, tuple) and len(other) >= 2:
            x += other[0]
            y += other[1]
            z += other[2] if len(other) >= 3 else 0
        else:
            raise NotImplementedError()
        return Vector3(x, y, z)
    
    def __mul__(self, other: float|int) -> Vector3:
        return Vector3(self.x * other, self.y * other, self.z * other)
    
    def __div__(self, other: float|int) -> Vector3:
        return Vector3(self.x / other, self.y / other, self.z / other)
    
    def __eq__(self, other: Vector3|tuple) -> bool:
        if isinstance(other, tuple) and 2 <= len(other) <= 3:
            x, y = other[0:2]
            z = other[2] if len(other) == 3 else 0
        elif isinstance(other, Vector3):
            x, y, z = other.x, other.y, other.z
        else:
            raise NotImplementedError()
        return self.x == x and self.y == y and self.z == z
    
class Vector2:

    def __init__(self, x: float, y: float):
        self.x, self.y = x, y

    def length(self) -> float:
        return math.sqrt(pow(self.x, 2) + pow(self.y, 2))
    
    def normalized(self) -> Vector3:
        length = self.length()
        return Vector2(self.x / length, self.y / length)
    
    def __sub__(self, other: Vector2|tuple) -> Vector2:
        x, y = self.x, self.y
        if isinstance(other, Vector2):
            x -= other.x
            y -= other.y
        elif isinstance(other, tuple) and len(other) == 2:
            x -= other[0]
            y -= other[1]
        else:
            raise NotImplementedError()
        return Vector2(x, y)
    
    def __add__(self, other: Vector2|tuple) -> Vector2:
        x, y = self.x, self.y
        if isinstance(other, Vector2):
            x += other.x
            y += other.y
        elif isinstance(other, tuple) and len(other) == 2:
            x += other[0]
            y += other[1]
        else:
            raise NotImplementedError()
        return Vector2(x, y)
    
    def __mul__(self, other: float|int) -> Vector2:
        return Vector2(self.x * other, self.y * other)
    
    def __div__(self, other: float|int) -> Vector2:
        return Vector2(self.x / other, self.y / other)
    
    def __eq__(self, other: Vector2|tuple) -> bool:
        if isinstance(other, tuple) and len(other) == 2:
            x, y = other
        elif isinstance(other, Vector2):
            x, y = other.x, other.y
        else:
            raise NotImplementedError()
        return self.x == x and self.y == y

class Rectangle:

    def __init__(self, x: float, y: float, width: float, height: float):
        self.x, self.y = x, y
        self.width, self.height = width, height
