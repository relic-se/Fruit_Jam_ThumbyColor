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
    
class Vector2:

    def __init__(self, x: float, y: float):
        self.x, self.y = x, y

    def length(self) -> float:
        return math.sqrt(pow(self.x, 2) + pow(self.y, 2))
    
    def normalized(self) -> Vector3:
        length = self.length()
        return Vector2(self.x / length, self.y / length)

class Rectangle:

    def __init__(self, x: float, y: float, width: float, height: float):
        self.x, self.y = x, y
        self.width, self.height = width, height
