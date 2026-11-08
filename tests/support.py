"""Доменные утверждения без копирования производственных формул."""

import unittest

from walking_plane import WalkingPlane


def new_plane(**overrides):
    args = dict(name="Топот", mass_kg=1000, leg_length_m=2,
                max_speed_kmh=20, energy=100)
    args.update(overrides)
    return WalkingPlane(**args)


class PlaneTestCase(unittest.TestCase):
    def assertPlaneState(self, plane, *, position, energy, intact=True):
        self.assertAlmostEqual(plane.position_km, position, delta=1e-7,
                               msg="Самолёт оказался не на ожидаемой отметке маршрута")
        self.assertAlmostEqual(plane.energy, energy, delta=1e-7,
                               msg="Запас топлива не соответствует выполненным командам")
        self.assertIs(plane.legs_intact, intact, "Неверное состояние опорных ног")

    def assertRefusedWithoutChanges(self, plane, exception, command, *args):
        before = plane.get_status()
        with self.assertRaises(exception):
            command(*args)
        self.assertEqual(plane.get_status(), before,
                         "Отказанная команда изменила состояние самолёта")

    def assertHours(self, actual, expected):
        self.assertAlmostEqual(actual, expected, delta=1e-7,
                               msg="Время прохождения участка неверно")

    def assertStatusValues(self, actual, expected):
        self.assertEqual(actual.keys(), expected.keys())
        for key, value in expected.items():
            with self.subTest(attribute=key):
                self.assertIs(type(actual[key]), type(value))
                if type(value) is float:
                    self.assertAlmostEqual(actual[key], value, delta=1e-7)
                else:
                    self.assertEqual(actual[key], value)
