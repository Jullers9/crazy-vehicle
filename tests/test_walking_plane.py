"""Модульные тесты TC-01…TC-16; подготовка, действие, проверка (AAA)."""

from walking_plane import (
    CrazyVehicleError, WalkingPlaneError, PlaneUnsupportedTerrain,
    PlaneLegsDamaged, PlaneObstacleTooHigh, PlaneNoEnergy,
)
from tests.support import PlaneTestCase, new_plane


class TestWalkingPlane(PlaneTestCase):
    def test_TC_01_initial_state(self):
        """TC-01: значения по умолчанию, границы энергии и сохранение имени."""
        # Arrange / Act
        p = new_plane(name=" Топот ")
        # Assert
        self.assertEqual(p.name, " Топот ")
        self.assertAlmostEqual(p.mass_kg, 1000, delta=1e-7)
        self.assertAlmostEqual(p.leg_length_m, 2, delta=1e-7)
        self.assertAlmostEqual(p.max_speed_kmh, 20, delta=1e-7)
        self.assertAlmostEqual(p.max_step_height_m, 1, delta=1e-7)
        self.assertPlaneState(p, position=0, energy=100)
        for energy in (0, 100):
            with self.subTest(energy=energy):
                self.assertAlmostEqual(new_plane(energy=energy).energy, energy, delta=1e-7)

    def test_TC_02_constructor_invalid_values(self):
        """TC-02: диапазоны и конечность аргументов конструктора."""
        # Arrange
        cases = [("name", ""), ("name", " \t\n")]
        for field in ("mass_kg", "leg_length_m", "max_speed_kmh"):
            cases += [(field, x) for x in (0, -1, float("nan"), float("inf"), -float("inf"))]
        cases += [("energy", x) for x in (-1, 101, float("nan"), float("inf"), -float("inf"))]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                # Act / Assert
                with self.assertRaises(ValueError):
                    new_plane(**{field: value})
        # Arrange: соседние аргументы с различимыми ошибками.
        for earlier, later in (("name", "mass_kg"), ("mass_kg", "leg_length_m"),
                               ("leg_length_m", "max_speed_kmh"), ("max_speed_kmh", "energy")):
            with self.subTest(earlier=earlier, later=later):
                with self.assertRaises(ValueError):
                    new_plane(**{earlier: "" if earlier == "name" else 0, later: "wrong"})

    def test_TC_03_constructor_types(self):
        """TC-03: типы конструктора, bool запрещён, большие конечные значения."""
        # Arrange
        for field in ("name", "mass_kg", "leg_length_m", "max_speed_kmh", "energy"):
            values = (None, 42, True) if field == "name" else (None, "2", True, [])
            for value in values:
                with self.subTest(field=field, value=value):
                    # Act / Assert
                    with self.assertRaises(TypeError):
                        new_plane(**{field: value})
        p = new_plane(leg_length_m=1e308)
        self.assertAlmostEqual(p.max_step_height_m, 5e307, delta=1e-7)

        tiny = new_plane(leg_length_m=5e-324)
        self.assertEqual(tiny.max_step_height_m, 0.0)
        self.assertIs(tiny.can_step_over(5e-324), False)
        self.assertRefusedWithoutChanges(tiny, PlaneObstacleTooHigh, tiny.step_over, 5e-324)

        # Regression D-01: обязательные float-атрибуты не вмещают большой int.
        for field in ("mass_kg", "leg_length_m", "max_speed_kmh"):
            with self.subTest(large_integer_field=field):
                with self.assertRaises(ValueError):
                    new_plane(**{field: 10**400})

    def test_TC_04_attributes_read_only(self):
        """TC-04: все публичные атрибуты защищены от присваивания и удаления."""
        # Arrange
        p = new_plane()
        for field in p.get_status():
            with self.subTest(field=field):
                # Act / Assert
                self.assertRefusedWithoutChanges(p, AttributeError, setattr, p, field, None)
                self.assertRefusedWithoutChanges(p, AttributeError, delattr, p, field)

    def test_TC_05_movement_formulas(self):
        """TC-05: время, расход и накопление позиции на двух поверхностях."""
        # Arrange
        p = new_plane()
        before = p.get_status()
        # Act
        road = p.move(5, "road")
        rough = p.move(5, "rough")
        # Assert
        self.assertHours(road, 0.25)
        self.assertHours(rough, 0.5)
        self.assertPlaneState(p, position=10, energy=70)
        for mass in (500, 2000):
            with self.subTest(mass=mass):
                other = new_plane(mass_kg=mass)
                self.assertHours(other.move(5, "road"), 0.25)
                self.assertHours(other.move(5, "rough"), 0.5)
                self.assertPlaneState(other, position=10, energy=70)
        for key in before.keys() - {"position_km", "energy"}:
            self.assertEqual(p.get_status()[key], before[key])

    def test_TC_06_exact_movement_energy(self):
        """TC-06: движение на весь запас энергии для обеих поверхностей."""
        for terrain, distance in (("road", 50), ("rough", 25)):
            with self.subTest(terrain=terrain):
                # Arrange
                p = new_plane()
                # Act
                hours = p.move(distance, terrain)
                # Assert
                self.assertHours(hours, 2.5)
                self.assertPlaneState(p, position=distance, energy=0)

        # Arrange / Act: накопленная ошибка округления не блокирует остаток пути.
        p = new_plane()
        for _ in range(10):
            p.move(0.1, "road")
        self.assertHours(p.move(49, "road"), 2.45)
        self.assertEqual(p.energy, 0.0)
        for energy, allowed in ((2 - 5e-8, True), (2 - 2e-7, False)):
            with self.subTest(energy=energy, allowed=allowed):
                p = new_plane(energy=energy)
                if allowed:
                    self.assertHours(p.move(1, "road"), 0.05)
                    self.assertEqual(p.energy, 0.0)
                else:
                    self.assertRefusedWithoutChanges(p, PlaneNoEnergy, p.move, 1, "road")

    def test_TC_07_move_validation_and_overflow(self):
        """TC-07: неверные аргументы, приоритет валидации и переполнение."""
        # Arrange
        p = new_plane()
        cases = [(TypeError, x, "road") for x in (None, "1", True)]
        cases += [(ValueError, x, "air") for x in (0, -1, float("nan"), float("inf"), -float("inf"))]
        cases += [(TypeError, 1, x) for x in (None, 1, [])]
        cases += [(ValueError, 1, x) for x in ("lava", "ROAD", "")]
        cases += [(ValueError, 1e308, "rough"), (ValueError, 0, None),
                  (PlaneNoEnergy, 1e307, "road"), (ValueError, 1e308, "road")]
        for exc, distance, terrain in cases:
            with self.subTest(distance=distance, terrain=terrain):
                # Act / Assert
                self.assertRefusedWithoutChanges(p, exc, p.move, distance, terrain)
        p.damage_legs()
        self.assertRefusedWithoutChanges(p, PlaneLegsDamaged, p.move, 1e308, "rough")
        slow = new_plane(max_speed_kmh=1e-308)
        self.assertRefusedWithoutChanges(slow, ValueError, slow.move, 10, "road")

        # Regression D-01/D-02: приоритеты сохраняются до вычислений.
        p = new_plane()
        self.assertRefusedWithoutChanges(p, PlaneUnsupportedTerrain, p.move, 10**400, "air")
        self.assertRefusedWithoutChanges(p, ValueError, p.move, 10**400, "road")
        p.damage_legs()
        self.assertRefusedWithoutChanges(p, PlaneLegsDamaged, p.move, 10**400, "road")
        tiny_speed = new_plane(max_speed_kmh=5e-324, energy=0)
        self.assertRefusedWithoutChanges(tiny_speed, ValueError, tiny_speed.move, 5e-324, "rough")
        self.assertHours(tiny_speed.move(5e-324, "road"), 1.0)
        tiny_speed.damage_legs()
        self.assertRefusedWithoutChanges(tiny_speed, PlaneLegsDamaged, tiny_speed.move, 5e-324, "rough")
        self.assertRefusedWithoutChanges(tiny_speed, PlaneUnsupportedTerrain, tiny_speed.move, 5e-324, "water")

    def test_TC_08_move_domain_errors(self):
        """TC-08: запрещённая среда, ноги, нехватка и порядок доменных отказов."""
        # Arrange
        p = new_plane(energy=0)
        p.damage_legs()
        # Act / Assert
        for terrain in ("air", "water"):
            with self.subTest(terrain=terrain):
                self.assertRefusedWithoutChanges(p, PlaneUnsupportedTerrain, p.move, 1, terrain)
        for terrain in ("road", "rough"):
            with self.subTest(terrain=terrain):
                self.assertRefusedWithoutChanges(p, PlaneLegsDamaged, p.move, 1, terrain)
        p.repair_legs()
        self.assertRefusedWithoutChanges(p, PlaneNoEnergy, p.move, 1, "road")
        p = new_plane(energy=1.999)
        self.assertRefusedWithoutChanges(p, PlaneNoEnergy, p.move, 1, "road")

    def test_TC_09_energy_calculation(self):
        """TC-09: чистый расчёт, формулы, валидация, независимость от ног/топлива."""
        # Arrange
        p = new_plane(energy=0)
        p.damage_legs()
        before = p.get_status()
        # Act / Assert
        for mass in (500, 1000):
            for terrain, expected in (("road", 20), ("rough", 40)):
                with self.subTest(mass=mass, terrain=terrain):
                    other = new_plane(mass_kg=mass, energy=0)
                    other.damage_legs()
                    before_other = other.get_status()
                    self.assertAlmostEqual(other.calculate_energy(10, terrain), expected, delta=1e-7)
                    self.assertEqual(other.get_status(), before_other)
        cases = [(TypeError, True, "road"), (TypeError, "1", "road"),
                 (TypeError, 1, None), (ValueError, 0, "air"),
                 (ValueError, -1, "road"), (ValueError, float("nan"), "road"),
                 (ValueError, float("inf"), "road"), (ValueError, 1, "lava"),
                 (ValueError, 1e308, "rough"),
                 (PlaneUnsupportedTerrain, 1, "water"),
                 (PlaneUnsupportedTerrain, 1, "air")]
        for exc, distance, terrain in cases:
            with self.subTest(distance=distance, terrain=terrain):
                self.assertRefusedWithoutChanges(p, exc, p.calculate_energy, distance, terrain)
        self.assertEqual(p.get_status(), before)
        slow = new_plane(max_speed_kmh=1e-308)
        self.assertAlmostEqual(slow.calculate_energy(10, "road"), 20, delta=1e-7)

        self.assertRefusedWithoutChanges(p, ValueError, p.calculate_energy, 10**400, "road")
        tiny_speed = new_plane(max_speed_kmh=5e-324, energy=0)
        before = tiny_speed.get_status()
        self.assertAlmostEqual(tiny_speed.calculate_energy(1, "rough"), 4.0, delta=1e-7)
        self.assertEqual(tiny_speed.get_status(), before)

    def test_TC_10_obstacle_query(self):
        """TC-10: предикат учитывает высоту, ноги и энергию, не меняя состояние."""
        for energy, height, intact, expected in (
            (10, 1, True, True), (10, 1.001, True, False),
            (9.999, 1, True, False), (100, 0.5, False, False),
            (100, 1e308, True, False), (100, 1e308, False, False),
            (0.21, 0.021, True, True),
            (10 - 5e-8, 1, True, True), (10 - 2e-7, 1, True, False),
        ):
            with self.subTest(energy=energy, height=height, intact=intact):
                # Arrange
                p = new_plane(energy=energy)
                if not intact:
                    p.damage_legs()
                before = p.get_status()
                # Act
                result = p.can_step_over(height)
                # Assert
                self.assertIs(result, expected)
                self.assertEqual(p.get_status(), before)
        p = new_plane()
        for value, exc in ((True, TypeError), (None, TypeError), ("1", TypeError),
                           (0, ValueError), (-1, ValueError),
                           (float("nan"), ValueError), (float("inf"), ValueError),
                           (-float("inf"), ValueError)):
            with self.subTest(value=value, exception=exc.__name__):
                self.assertRefusedWithoutChanges(p, exc, p.can_step_over, value)

        large = new_plane(leg_length_m=1e308)
        self.assertRefusedWithoutChanges(large, ValueError, large.can_step_over, 5e307)

        p = new_plane()
        before = p.get_status()
        self.assertIs(p.can_step_over(10**400), False)
        self.assertEqual(p.get_status(), before)

    def test_TC_11_step_success(self):
        """TC-11: манёвр на пределе высоты и энергии, возврат None."""
        # Arrange
        p = new_plane(energy=15)
        # Act / Assert
        self.assertIsNone(p.step_over(0.5))
        self.assertPlaneState(p, position=0, energy=10)
        self.assertTrue(p.can_step_over(1))
        self.assertIsNone(p.step_over(1))
        self.assertPlaneState(p, position=0, energy=0)

        for energy, height, allowed in ((0.21, 0.021, True),
                                        (10 - 5e-8, 1, True), (10 - 2e-7, 1, False)):
            with self.subTest(energy=energy, height=height):
                p = new_plane(energy=energy)
                if allowed:
                    self.assertIsNone(p.step_over(height))
                    self.assertEqual(p.energy, 0.0)
                else:
                    self.assertRefusedWithoutChanges(p, PlaneNoEnergy, p.step_over, height)

    def test_TC_12_step_errors_and_priority(self):
        """TC-12: валидация, приоритеты, переполнение и атомарность манёвра."""
        # Arrange
        p = new_plane(energy=0)
        p.damage_legs()
        # Act / Assert
        for value, exc in ((True, TypeError), (None, TypeError), ("1", TypeError),
                           (0, ValueError), (-1, ValueError),
                           (float("nan"), ValueError), (float("inf"), ValueError),
                           (-float("inf"), ValueError), (2, PlaneLegsDamaged), (1e308, PlaneLegsDamaged)):
            with self.subTest(value=value, exception=exc.__name__):
                self.assertRefusedWithoutChanges(p, exc, p.step_over, value)
        p.repair_legs()
        self.assertRefusedWithoutChanges(p, PlaneObstacleTooHigh, p.step_over, 1e308)
        self.assertRefusedWithoutChanges(p, PlaneObstacleTooHigh, p.step_over, 1.001)
        self.assertRefusedWithoutChanges(p, PlaneNoEnergy, p.step_over, 1)
        large = new_plane(leg_length_m=1e308)
        self.assertRefusedWithoutChanges(large, PlaneObstacleTooHigh, large.step_over, 1e308)
        self.assertRefusedWithoutChanges(large, ValueError, large.step_over, 5e307)

        p = new_plane()
        self.assertRefusedWithoutChanges(p, PlaneObstacleTooHigh, p.step_over, 10**400)
        p.damage_legs()
        self.assertRefusedWithoutChanges(p, PlaneLegsDamaged, p.step_over, 10**400)

    def test_TC_13_refuel(self):
        """TC-13: заправка, предел 100, неверные аргументы, повреждённые ноги."""
        # Arrange
        p = new_plane(energy=20)
        p.damage_legs()
        # Act / Assert
        self.assertIsNone(p.refuel(50))
        self.assertPlaneState(p, position=0, energy=70, intact=False)
        for amount in (1000, 1e308, 1, 10**400):
            with self.subTest(amount=amount):
                self.assertIsNone(p.refuel(amount))
                self.assertPlaneState(p, position=0, energy=100, intact=False)
        for value, exc in ((True, TypeError), (None, TypeError), ("1", TypeError),
                           (0, ValueError), (-1, ValueError),
                           (float("nan"), ValueError), (float("inf"), ValueError),
                           (-float("inf"), ValueError)):
            with self.subTest(value=value, exception=exc.__name__):
                self.assertRefusedWithoutChanges(p, exc, p.refuel, value)

    def test_TC_14_damage_and_repair(self):
        """TC-14: повреждение и ремонт повторяемы и не тратят энергию."""
        # Arrange
        p = new_plane(energy=0)
        before = p.get_status()
        # Act / Assert
        for action, expected in ((p.damage_legs, False), (p.damage_legs, False),
                                 (p.repair_legs, True), (p.repair_legs, True)):
            self.assertIsNone(action())
            after = p.get_status()
            self.assertIs(after.pop("legs_intact"), expected)
            self.assertEqual(after, {k: v for k, v in before.items() if k != "legs_intact"})

    def test_TC_15_status_snapshot(self):
        """TC-15: точные ключи, типы, значения и независимость снимков."""
        # Arrange
        p = new_plane()
        expected = dict(name="Топот", mass_kg=1000.0, leg_length_m=2.0,
                        max_speed_kmh=20.0, max_step_height_m=1.0,
                        energy=100.0, position_km=0.0, legs_intact=True)
        # Act
        snapshot = p.get_status()
        # Assert
        self.assertIs(type(snapshot), dict)
        self.assertStatusValues(snapshot, expected)
        for key, value in expected.items():
            self.assertIs(type(snapshot[key]), type(value))
            if type(value) is float:
                self.assertAlmostEqual(getattr(p, key), value, delta=1e-7)
            else:
                self.assertEqual(getattr(p, key), value)
        snapshot["energy"] = -1
        snapshot["extra"] = True
        self.assertStatusValues(p.get_status(), expected)
        frozen = p.get_status()
        self.assertIsNot(frozen, p.get_status())
        p.move(1, "road")
        self.assertStatusValues(frozen, expected)
        self.assertAlmostEqual(p.get_status()["energy"], 98, delta=1e-7)
        self.assertAlmostEqual(p.get_status()["position_km"], 1, delta=1e-7)

    def test_TC_16_exception_hierarchy(self):
        """TC-16: публичная иерархия доменных исключений."""
        # Arrange / Act / Assert
        self.assertTrue(issubclass(CrazyVehicleError, Exception))
        self.assertTrue(issubclass(WalkingPlaneError, CrazyVehicleError))
        for exc in (PlaneUnsupportedTerrain, PlaneLegsDamaged,
                    PlaneObstacleTooHigh, PlaneNoEnergy):
            with self.subTest(exception=exc.__name__):
                self.assertTrue(issubclass(exc, WalkingPlaneError))
