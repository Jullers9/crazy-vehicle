"""Сценарные проверки TC-17…TC-20 через команды пилота."""

from walking_plane import (
    PlaneNoEnergy, PlaneLegsDamaged, PlaneUnsupportedTerrain, PlaneObstacleTooHigh,
)
from tests.pilot import Pilot
from tests.support import PlaneTestCase, new_plane


class TestJourneys(PlaneTestCase):
    def test_TC_17_delivery_over_pass(self):
        """TC-17: доставка через каменный перевал (SPEC 4.2.1)."""
        # Given: самолёт с полным баком на старте.
        p = new_plane()
        pilot = Pilot(p)
        # When: дорога, затем каменистый участок.
        self.assertHours(pilot.идти_по_дороге(5), 0.25)
        # Then
        self.assertPlaneState(p, position=5, energy=90)
        # When
        self.assertHours(pilot.идти_по_камням(3), 0.3)
        # Then
        self.assertPlaneState(p, position=8, energy=78)
        # When: проверка и преодоление камня.
        before = p.get_status()
        self.assertIs(pilot.проверить_преграду(1), True)
        self.assertEqual(p.get_status(), before)
        pilot.перешагнуть(1)
        # Then
        self.assertPlaneState(p, position=8, energy=68)
        # When: последний участок.
        self.assertHours(pilot.идти_по_дороге(2), 0.1)
        # Then
        self.assertPlaneState(p, position=10, energy=64)

    def test_TC_18_last_fuel(self):
        """TC-18: последние капли топлива (SPEC 4.2.2)."""
        # Given
        p = new_plane(energy=10)
        pilot = Pilot(p)
        # When
        self.assertHours(pilot.идти_по_камням(2), 0.2)
        # Then
        self.assertPlaneState(p, position=2, energy=2)
        # When / Then: длинный участок недоступен, короткий расходует остаток.
        self.assertRefusedWithoutChanges(p, PlaneNoEnergy, pilot.идти_по_дороге, 2)
        self.assertHours(pilot.идти_по_дороге(1), 0.05)
        self.assertPlaneState(p, position=3, energy=0)
        # When / Then: камень недоступен без топлива.
        self.assertIs(pilot.проверить_преграду(0.5), False)
        self.assertRefusedWithoutChanges(p, PlaneNoEnergy, pilot.перешагнуть, 0.5)
        # When
        pilot.заправиться(15)
        self.assertPlaneState(p, position=3, energy=15)
        pilot.перешагнуть(0.5)
        # Then
        self.assertPlaneState(p, position=3, energy=10)
        # When
        self.assertHours(pilot.идти_по_камням(2), 0.2)
        # Then
        self.assertPlaneState(p, position=5, energy=2)

    def test_TC_19_breakdown_at_rubble(self):
        """TC-19: поломка у завала (SPEC 4.2.3)."""
        # Given
        p = new_plane(energy=50)
        pilot = Pilot(p)
        # When
        self.assertHours(pilot.идти_по_дороге(2), 0.1)
        pilot.повредить_ноги()
        # Then
        self.assertPlaneState(p, position=2, energy=46, intact=False)
        # When / Then: повреждение блокирует оба вида движения.
        self.assertIs(pilot.проверить_преграду(0.5), False)
        self.assertRefusedWithoutChanges(p, PlaneLegsDamaged, pilot.идти_по_дороге, 1)
        self.assertRefusedWithoutChanges(p, PlaneLegsDamaged, pilot.перешагнуть, 0.5)
        # When: расчёт и заправка доступны при поломке.
        before = p.get_status()
        self.assertAlmostEqual(pilot.оценить_расход_на_камнях(3), 12, delta=1e-7)
        self.assertEqual(p.get_status(), before)
        pilot.заправиться(100)
        # Then
        self.assertPlaneState(p, position=2, energy=100, intact=False)
        # When
        pilot.починить_ноги()
        self.assertPlaneState(p, position=2, energy=100)
        pilot.перешагнуть(0.5)
        self.assertPlaneState(p, position=2, energy=95)
        self.assertHours(pilot.идти_по_камням(3), 0.3)
        # Then
        self.assertPlaneState(p, position=5, energy=83)

    def test_TC_20_plane_did_not_take_off(self):
        """TC-20: самолёт, который не взлетел (SPEC 4.2.4)."""
        # Given
        p = new_plane(energy=40)
        pilot = Pilot(p)
        # When / Then: крылья не позволяют летать и плавать.
        for command in (pilot.идти_по_воде, pilot.взлететь):
            with self.subTest(command=command.__name__):
                self.assertRefusedWithoutChanges(p, PlaneUnsupportedTerrain, command, 1)
        self.assertIs(pilot.проверить_преграду(1.01), False)
        self.assertRefusedWithoutChanges(p, PlaneObstacleTooHigh, pilot.перешагнуть, 1.01)
        # When: препятствие точно на пределе.
        pilot.перешагнуть(1)
        # Then
        self.assertPlaneState(p, position=0, energy=30)
        # When
        self.assertHours(pilot.идти_по_камням(5), 0.5)
        # Then
        self.assertPlaneState(p, position=5, energy=10)
        # When
        pilot.заправиться(200)
        # Then
        self.assertPlaneState(p, position=5, energy=100)
        # When
        self.assertHours(pilot.идти_по_дороге(5), 0.25)
        # Then
        self.assertPlaneState(p, position=10, energy=90)
