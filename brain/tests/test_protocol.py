from __future__ import annotations

import json
from pathlib import Path

import pytest

from thorkell.body import auth, protocol
from thorkell.paths import REPO_ROOT

FIXTURES = REPO_ROOT / "protocol/v1/fixtures"
FIXTURE_FILES = sorted(FIXTURES.glob("*.json"))


@pytest.mark.parametrize("path", FIXTURE_FILES, ids=lambda p: p.stem)
def test_fixture_round_trips_exactly(path: Path) -> None:
    fixture = json.loads(path.read_text())
    message = protocol.decode(json.dumps(fixture, ensure_ascii=False))
    assert message.t == fixture["t"]
    assert json.loads(protocol.encode(message)) == fixture


def test_every_type_has_a_fixture() -> None:
    covered = {json.loads(p.read_text())["t"] for p in FIXTURE_FILES}
    assert covered == set(protocol.TYPES)


def test_korean_and_date_like_text_stay_strings() -> None:
    message = protocol.decode((FIXTURES / "event_chat_ko.json").read_text())
    assert isinstance(message, protocol.Event)
    assert message.data["text"] == "토르켈, 나무 좀 해줘. 2026-10-02 까지!"


def test_sequence_beyond_double_precision_survives() -> None:
    message = protocol.decode((FIXTURES / "ack.json").read_text())
    assert message.seq == 9007199254740993
    assert '"seq":9007199254740993' in protocol.encode(message)


def test_unknown_fields_are_ignored() -> None:
    message = protocol.decode('{"v":1,"t":"stop_all","seq":1,"ts":2,"reason":"x","added_in_1_1":true}')
    assert isinstance(message, protocol.StopAll)
    assert message.reason == "x"


@pytest.mark.parametrize(
    ("line", "code"),
    [
        ('{"v":2,"t":"stop_all","seq":1,"ts":2}', "major_mismatch"),
        ('{"t":"stop_all","seq":1,"ts":2}', "bad_envelope"),
        ('{"v":1,"seq":1,"ts":2}', "bad_envelope"),
        ('{"v":true,"t":"stop_all","seq":1,"ts":2}', "bad_envelope"),
        ('{"v":1,"t":"teleport","seq":1,"ts":2}', "unknown_type"),
        ('{"v":1,"t":"ack","seq":"many","ts":2}', "bad_body"),
        (
            '{"v":1,"t":"result","seq":1,"ts":2,"cmd_id":"c","status":"won","code":"","evidence":{}}',
            "bad_body",
        ),
        ("not json", "bad_json"),
        ("[1,2]", "bad_envelope"),
    ],
)
def test_rejects_bad_envelopes(line: str, code: str) -> None:
    with pytest.raises(protocol.ProtocolError) as error:
        protocol.decode(line)
    assert error.value.code == code


def test_rejects_oversize_encode() -> None:
    huge = protocol.Event(
        seq=1, ts=1, kind="chat", tick=0, data={"text": "가" * (protocol.MAX_LINE_BYTES // 3 + 1)}
    )
    with pytest.raises(protocol.ProtocolError) as error:
        protocol.encode(huge)
    assert error.value.code == "line_too_long"


def test_hmac_matches_shared_vectors() -> None:
    vectors = json.loads((REPO_ROOT / "protocol/v1/hmac_vectors.json").read_text())
    for vector in vectors:
        mac = auth.mac(vector["token"], vector["nonce"], vector["role"], vector["session"])
        assert mac == vector["mac"]
        assert auth.verify(vector["token"], vector["nonce"], vector["role"], vector["session"], mac.upper())


def test_hmac_rejects_wrong_role_and_tampering() -> None:
    token = auth.new_hex(32)
    mac = auth.mac(token, "n", "body", "s")
    assert not auth.verify(token, "n", "host", "s", mac)
    assert not auth.verify(token, "n", "body", "s", mac[1:] + "0")
    assert not auth.verify(token, "n", "body", "s", "")
