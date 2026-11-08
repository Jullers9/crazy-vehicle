"""Шагающий самолёт «Топот»: реализация замороженного ТЗ SPEC.md 1.0."""

import math

__all__ = [
    "CrazyVehicleError",
    "WalkingPlaneError",
    "PlaneUnsupportedTerrain",
    "PlaneLegsDamaged",
    "PlaneObstacleTooHigh",
    "PlaneNoEnergy",
    "WalkingPlane",
]

_ENERGY_TOLERANCE = 1e-7
_MAX_ENERGY = 100.0


class CrazyVehicleError(Exception):
    """Базовое исключение для безумных транспортных средств."""


class WalkingPlaneError(CrazyVehicleError):
    """Базовое исключение для ошибок шагающего самолёта."""


class PlaneUnsupportedTerrain(WalkingPlaneError):
    """Самолёт не может передвигаться по воде или воздуху."""


class PlaneLegsDamaged(WalkingPlaneError):
    """Повреждённые ноги запрещают движение и перешагивание."""


class PlaneObstacleTooHigh(WalkingPlaneError):
    """Препятствие выше предельной высоты перешагивания."""


class PlaneNoEnergy(WalkingPlaneError):
    """Для выполнения действия недостаточно энергии."""


def _finite_number(value: float, argument: str) -> float:
    """Проверить число без преждевременного преобразования большого int."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{argument}: ожидается int или float, кроме bool")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{argument}: требуется конечное число")
    return value


def _positive_number(value: float, argument: str) -> float:
    """Проверить, что числовой аргумент строго положителен."""
    result = _finite_number(value, argument)
    if result <= 0.0:
        raise ValueError(f"{argument}: требуется положительное число")
    return result


def _ground_terrain(terrain: str) -> str:
    """Проверить название среды, затем запретить движение по воде и воздуху."""
    if not isinstance(terrain, str):
        raise TypeError("terrain: ожидается строка")
    if terrain not in ("road", "rough", "water", "air"):
        raise ValueError("terrain: допустимы road, rough, water и air")
    if terrain in ("water", "air"):
        raise PlaneUnsupportedTerrain(
            "Шагающий самолёт не плавает и не летает"
        )
    return terrain


def _finite_result(value: float, description: str) -> float:
    """Отклонить неконечный результат до изменения состояния."""
    try:
        result = float(value)
    except OverflowError as error:
        message = f"{description}: результат вне диапазона конечных float"
        raise ValueError(message) from error
    if not math.isfinite(result):
        raise ValueError(f"{description}: результат должен быть конечным")
    return result


def _movement_cost(distance_km: float, terrain: str) -> float:
    """Вычислить конечный расход для уже проверенного наземного участка."""
    rate = 2 if terrain == "road" else 4
    return _finite_result(distance_km * rate, "Расход энергии на движение")


class WalkingPlane:
    """Одноместный наземный транспорт с публичными свойствами для чтения."""

    __slots__ = (
        "_name",
        "_mass_kg",
        "_leg_length_m",
        "_max_speed_kmh",
        "_energy",
        "_position_km",
        "_legs_intact",
    )

    def __init__(
        self,
        name: str,
        mass_kg: float,
        leg_length_m: float,
        max_speed_kmh: float,
        energy: float = 100.0,
    ) -> None:
        """Проверить аргументы по порядку и задать начальное состояние."""
        if not isinstance(name, str):
            raise TypeError("name: ожидается строка")
        if not name.strip():
            raise ValueError("name: нужен хотя бы один непробельный символ")
        mass = _finite_result(_positive_number(mass_kg, "mass_kg"), "Масса")
        leg_length = _finite_result(
            _positive_number(leg_length_m, "leg_length_m"), "Длина ног"
        )
        max_speed = _finite_result(
            _positive_number(max_speed_kmh, "max_speed_kmh"), "Скорость"
        )
        initial_energy = _finite_number(energy, "energy")
        if not 0.0 <= initial_energy <= _MAX_ENERGY:
            raise ValueError("energy: требуется значение от 0 до 100")

        self._name = name
        self._mass_kg = mass
        self._leg_length_m = leg_length
        self._max_speed_kmh = max_speed
        self._energy = float(initial_energy)
        self._position_km = 0.0
        self._legs_intact = True

    @property
    def name(self) -> str:
        """Исходное имя с сохранением пробелов по краям."""
        return self._name

    @property
    def mass_kg(self) -> float:
        """Масса в килограммах; на расход энергии не влияет."""
        return self._mass_kg

    @property
    def leg_length_m(self) -> float:
        """Длина механических ног в метрах."""
        return self._leg_length_m

    @property
    def max_speed_kmh(self) -> float:
        """Скорость на дороге в километрах в час."""
        return self._max_speed_kmh

    @property
    def max_step_height_m(self) -> float:
        """Предельная высота препятствия, равная половине длины ног."""
        return self._leg_length_m * 0.5

    @property
    def energy(self) -> float:
        """Текущая энергия в диапазоне от 0 до 100 включительно."""
        return self._energy

    @property
    def position_km(self) -> float:
        """Суммарный пройденный путь в километрах."""
        return self._position_km

    @property
    def legs_intact(self) -> bool:
        """Признак исправности опорных ног."""
        return self._legs_intact

    def _has_energy(self, cost: float) -> bool:
        """Проверить запас энергии с абсолютным допуском из SPEC 3.1."""
        return cost <= self._energy or cost - self._energy <= _ENERGY_TOLERANCE

    def move(self, distance_km: float, terrain: str) -> float:
        """Пройти наземный участок с расходом энергии и вернуть время в часах.

        Неверные аргументы вызывают TypeError или ValueError. Запрещённая
        среда, повреждение ног и нехватка энергии вызывают соответствующие
        доменные исключения. При любом отказе всё состояние сохраняется.
        """
        distance = _positive_number(distance_km, "distance_km")
        surface = _ground_terrain(terrain)
        if not self._legs_intact:
            raise PlaneLegsDamaged("Перед движением необходимо починить ноги")

        speed = self._max_speed_kmh * (1.0 if surface == "road" else 0.5)
        if speed == 0.0:
            raise ValueError("При расчётной скорости время движения неконечно")
        try:
            hours = distance / speed
        except OverflowError as error:
            message = "Время движения выходит за диапазон конечных float"
            raise ValueError(message) from error
        hours = _finite_result(hours, "Время движения")
        cost = _movement_cost(distance, surface)
        if not self._has_energy(cost):
            raise PlaneNoEnergy("Недостаточно энергии для прохождения участка")
        position = _finite_result(
            self._position_km + distance, "Пройденный путь"
        )
        energy = max(0.0, self._energy - cost)

        self._position_km = position
        self._energy = energy
        return hours

    def calculate_energy(self, distance_km: float, terrain: str) -> float:
        """Рассчитать расход без проверки ног, запаса энергии и скорости.

        Неверные аргументы или неконечный расход вызывают TypeError,
        ValueError либо PlaneUnsupportedTerrain. Состояние не меняется.
        """
        distance = _positive_number(distance_km, "distance_km")
        surface = _ground_terrain(terrain)
        return _movement_cost(distance, surface)

    def can_step_over(self, height_m: float) -> bool:
        """Проверить возможность манёвра без расхода энергии и смены состояния.

        Неверный аргумент вызывает TypeError или ValueError. Если аргумент
        корректен, поломка ног или превышение высоты дают False до расчёта
        расхода. Переполнение расхода допустимого манёвра вызывает ValueError.
        """
        height = _positive_number(height_m, "height_m")
        if not self._legs_intact or height > self.max_step_height_m:
            return False
        cost = _finite_result(height * 10, "Расход энергии на манёвр")
        return self._has_energy(cost)

    def step_over(self, height_m: float) -> None:
        """Выполнить локальный манёвр с расходом энергии без изменения пути.

        По порядку проверяются аргумент, ноги, высота, конечность расхода
        и запас энергии. Отказ вызывает TypeError, ValueError или
        соответствующее доменное исключение без изменения состояния.
        """
        height = _positive_number(height_m, "height_m")
        if not self._legs_intact:
            raise PlaneLegsDamaged("Для перешагивания нужно починить ноги")
        if height > self.max_step_height_m:
            raise PlaneObstacleTooHigh("Препятствие выше допустимого предела")
        cost = _finite_result(height * 10, "Расход энергии на манёвр")
        if not self._has_energy(cost):
            raise PlaneNoEnergy("Недостаточно энергии для перешагивания")
        self._energy = max(0.0, self._energy - cost)

    def refuel(self, amount: float) -> None:
        """Пополнить энергию до 100, в том числе при повреждённых ногах.

        Добавляемое количество должно быть положительным и конечным.
        Неверный аргумент вызывает TypeError или ValueError без изменения
        состояния. Переполнение промежуточной суммы не считается ошибкой.
        """
        added = _positive_number(amount, "amount")
        if added >= _MAX_ENERGY - self._energy:
            self._energy = _MAX_ENERGY
        else:
            self._energy += added

    def damage_legs(self) -> None:
        """Повредить ноги; повтор допустим, остальные атрибуты сохраняются."""
        self._legs_intact = False

    def repair_legs(self) -> None:
        """Бесплатно починить ноги; повторный вызов допустим."""
        self._legs_intact = True

    def get_status(self) -> dict:
        """Вернуть новый обычный словарь с восемью публичными атрибутами."""
        return {
            "name": self.name,
            "mass_kg": self.mass_kg,
            "leg_length_m": self.leg_length_m,
            "max_speed_kmh": self.max_speed_kmh,
            "max_step_height_m": self.max_step_height_m,
            "energy": self.energy,
            "position_km": self.position_km,
            "legs_intact": self.legs_intact,
        }
