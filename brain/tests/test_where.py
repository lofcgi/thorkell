from __future__ import annotations

from thorkell.world.where import direction_ko, rough_m, where_ko


def test_compass_follows_the_map_north_up() -> None:
    # 발헤임 지도는 위쪽이 +z(북), 오른쪽이 +x(동)다.
    origin = [0.0, 30.0, 0.0]
    assert direction_ko(origin, [0.0, 0.0, 100.0]) == "북"
    assert direction_ko(origin, [100.0, 0.0, 0.0]) == "동"
    assert direction_ko(origin, [-70.0, 0.0, -70.0]) == "남서"
    assert direction_ko(origin, [-100.0, 0.0, 20.0]) == "서"


def test_distances_are_rounded_like_a_map_reading() -> None:
    assert rough_m(43.0) == "45m"
    assert rough_m(296.4) == "300m"
    assert rough_m(1234.0) == "1250m"


def test_where_reads_direction_then_distance() -> None:
    assert where_ko([0.0, 0.0, 0.0], [250.0, 5.0, 160.0]) == "북동쪽 300m"
    assert where_ko([0.0, 0.0, 0.0], [1.0, 0.0, 1.0]) == "바로 옆"
