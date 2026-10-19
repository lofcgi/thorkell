"""Cutting the README video: captions follow who said what, GIFs keep the talk and skip the waiting."""

from __future__ import annotations

from thorkell.ops.video import Caption, Clock, captions, pieces


def test_a_caption_lasts_until_the_next_line() -> None:
    timeline = [
        {"kind": "video", "start": 100.0},
        {"kind": "said", "who": "Leader", "text": "We should build a house", "at": 110.0},
        {"kind": "said", "who": "Thorkell", "text": "How big?", "at": 112.0},
        {"kind": "said", "who": "Thorkell", "text": "before the video", "at": 90.0},
    ]
    assert captions(timeline, Clock([(100.0, 60.0)])) == [
        Caption(10.0, 12.0, "Leader", "We should build a house"),
        Caption(12.0, 16.5, "Thorkell", "How big?"),
    ]


def test_the_talk_plays_at_normal_speed_and_the_long_work_runs_fast() -> None:
    lines = [Caption(10.0, 14.0, "Leader", "chop wood"), Caption(200.0, 204.0, "Thorkell", "Got 20 Wood")]
    parts = pieces(5.0, 210.0, lines)
    assert parts[0] == (5.0, 8.5, 1.1666666666666667)
    assert parts[1] == (8.5, 15.0, 1.0)
    fast = parts[2]
    assert fast[0] == 15.0 and fast[1] == 198.5 and fast[2] > 50  # 3분 넘는 일은 몇 초로
    assert parts[3] == (198.5, 205.0, 1.0)


def test_recording_in_pieces_joins_into_one_clock() -> None:
    # 시스템이 스트림을 끊으면 새 파일로 이어 간다. 두 파일 사이에 있었던 일은 다음 파일의 처음으로 간다.
    clock = Clock([(100.0, 110.0), (213.0, 300.0)])
    assert clock(150.0) == 50.0
    assert clock(211.0) == 110.0
    assert clock(250.0) == 147.0
    assert clock.covers(100.0) and not clock.covers(99.0) and not clock.covers(513.0)
