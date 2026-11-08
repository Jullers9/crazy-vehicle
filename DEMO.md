# Демо шагающего самолёта «Топот»

Материал автора для совместной защиты с разработчиком. Согласование D пока не получено.
Нужен Python 3.10+, сторонние пакеты не нужны. Запускать из корня репозитория.

## Маршрут и отказ без изменений

Сохранить код во временный файл вне репозитория или выполнить в Python-консоли:

```python
from walking_plane import PlaneLegsDamaged, PlaneUnsupportedTerrain, WalkingPlane

plane = WalkingPlane("Топот", 1000, 2, 20)
assert plane.move(5, "road") == 0.25
assert plane.move(3, "rough") == 0.3
assert plane.can_step_over(1)
plane.step_over(1)
assert plane.move(2, "road") == 0.1
assert plane.position_km == 10.0
assert plane.energy == 64.0
print("Доставка:", plane.get_status())

before = plane.get_status()
try:
    plane.move(1, "water")
except PlaneUnsupportedTerrain:
    print("Вода запрещена")
assert plane.get_status() == before

plane.damage_legs()
before = plane.get_status()
try:
    plane.move(1, "road")
except PlaneLegsDamaged:
    print("Ноги повреждены: движение запрещено")
assert plane.get_status() == before
plane.repair_legs()
plane.refuel(100)
assert plane.legs_intact and plane.energy == 100.0
print("После ремонта и заправки:", plane.get_status())
```

Показать: ноги определяют предел 1 м; rough снижает скорость и увеличивает расход;
манёвр не меняет позицию; отказ атомарен; ремонт бесплатный, заправка ограничена 100.

## Прогон тестов

```bash
python -m unittest discover -s tests -t . -v
```

Ожидается 20 тестов, OK (16 модульных, 4 сценарных).

## Три случая для обсуждения

1. Округление энергии: математической границы недостаточно без правила float.
   SPEC 3.1 задаёт допуск 1e-7; TC-06/10/11 проверяют допуск и обнуление.
2. Большой int: refuel(10**400) ограничивает результат сотней, тогда как расчёт
   непредставимого расхода вызывает ValueError. Доменный приоритет сохраняется.
3. Скорость 5e-324: дорога допускает конечное время для минимальной дистанции,
   rough округляет скорость до нуля и даёт ValueError без частичного движения.

Это наблюдённые различия трактовок, а не три найденных дефекта кода.
