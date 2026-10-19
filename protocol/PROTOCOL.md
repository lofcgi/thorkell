# Thorkell 브리지 프로토콜 v1

봇 클라이언트의 `Thorkell.Body`와 사람 호스트의 `Thorkell.Host`가 두뇌(`brain/`)와 주고받는 메시지다.

- 구현: C# `plugin/Thorkell.Wire`(Newtonsoft.Json 13.0.2), Python `brain/thorkell/body/protocol.py`(pydantic)
- 계약: `protocol/v1/fixtures/*.json`. 메시지 타입마다 예시가 하나 이상 있고, 양쪽 테스트가 같은 fixture를 디코드→인코드해서 **정확히 같은 JSON**이 나오는지 확인한다.

## 전송

| 항목 | 값 |
|---|---|
| 연결 | TCP, 두뇌가 서버, `127.0.0.1`에서만 받는다. 실사용 47811, 테스트 47821 |
| 프레이밍 | UTF-8, 메시지 하나가 한 줄(`\n`), 한 줄 최대 256 KiB |
| 이미지 | 줄에 넣지 않는다. 파일 경로와 sha256만 보낸다 |

20Hz UDP(Eira)를 쓰지 않는 이유가 있다. 모터 제어는 C#이 프레임 단위로 하고 두뇌는 드문드문 명령만 보낸다. 대신 이벤트와 결과는 하나도 잃으면 안 되므로 순서와 신뢰성이 보장되는 TCP를 쓴다.

## 봉투

모든 메시지는 평평한 JSON 객체다.

```json
{"v": 1, "t": "<type>", "seq": 41, "ts": 1790000001001, "...": "본문"}
```

| 필드 | 뜻 |
|---|---|
| `v` | 메이저 버전. 다르면 `major_mismatch` |
| `t` | 메시지 타입. 모르면 `unknown_type` |
| `seq` | 보낸 쪽 기준으로 단조 증가(int64). 연결마다 새로 시작한다 |
| `ts` | 보낸 시각(unix ms) |

- 필드 이름은 snake_case다. 모르는 필드는 무시한다. 마이너 버전 변경은 필드 추가만 허용한다.
- 날짜처럼 생긴 문자열도 문자열로 남긴다. C#에서는 `DateParseHandling.None`으로 처리한다.
- 개체 id(ZDOID)는 `"userid:id"` 문자열로 보낸다. 64비트 정수가 JS 등에서 정밀도를 잃지 않게 하기 위해서다.
- 오류 코드(양쪽 공통): `bad_json`, `bad_envelope`, `major_mismatch`, `unknown_type`, `bad_body`, `line_too_long`, `truncated_line`.

## 핸드셰이크

```
brain  → plugin  challenge {nonce, proto:[1,0]}
plugin → brain   hello {role: body|host, proto, plugin, game{version, network, assembly_sha256}, session, caps[], mac}
brain  → plugin  welcome {accepted_caps[], state_hz, scene_hz}   또는   reject {reason}
```

- `mac` = HMAC-SHA256(key = bytes.fromhex(token), msg = `nonce|role|session`), 소문자 hex로 표기한다. 테스트 벡터는 `protocol/v1/hmac_vectors.json`에 있다.
- token은 실행마다 두뇌가 만든다. 32바이트 난수의 hex이고, 0600 cfg로 플러그인에 전달한다.
- 역할별 권한: Host는 지시(deixis), 자막 ack, 수령 확인만 보낼 수 있다. Body에게 명령할 수 없다.

## 메시지

| t | 방향 | 본문 | 비고 |
|---|---|---|---|
| `status` | plugin → brain | armed, ready, reasons[], version_gate{ok,found,tested}, perf? | 1Hz, 하트비트 겸용. Body의 armed는 월드 안·생존·브리지 인증·**리더 접속**(서버 플레이어 목록에 있음)이다. 리더가 멀어 캐릭터가 로드되지 않았어도 armed다. reasons의 `leader_absent`는 리더가 접속해 있지 않다는 뜻이다 |
| `state` | body → brain | tick, data{pos, yaw, hp, stamina, action, reflex, …} | 10Hz, 최신값만 의미 있음 |
| `scene` | body → brain | tick, data{nearby[], boss_bars?, inventory, env, leader?, leader_on_map?, …} | 2Hz, 전체 스냅샷. 아래 "리더" 참고. nearby는 40m 안(시야 또는 4m), 큰 생물은 100m 안. boss_bars는 화면 위쪽 보스 체력바(알아챈 보스가 100m 안이면 가려져도 뜬다): id, name, health |
| `event` | plugin → brain | kind, tick, data | **절대 버리지 않는다**. kind별 data 스키마는 아래 표 |
| `cmd` | brain → body | id, op, args, mode(replace\|queue\|interrupt), priority, based_on_seq, ttl_ms, resume | |
| `ack` | body → brain | cmd_id, accepted, code | |
| `progress` | body → brain | cmd_id, metrics | 최대 2Hz |
| `result` | body → brain | cmd_id, status(succeeded\|failed\|cancelled\|preempted), code, evidence | evidence는 월드 변화 근거 |
| `cancel` | brain → body | cmd_id, reason | |
| `stop_all` | brain → body | reason | |
| `query` / `query_result` | brain ↔ plugin | id, what, args / id, ok, data?, error? | |
| `config` | brain → plugin | values | |

### 명령 규칙
- **즉시 명령**(`say`, `equip`, `unequip`, `eat`)은 행동 슬롯과 모터를 차지하지 않는다. 받자마자 실행하고 ack와 result를 바로 보낸다.
  - 걸으면서 말하거나, 반사로 반격하는 중에 무기를 바꾸고 먹을 수 있어야 하기 때문이다.
- 그 밖의 명령은 진행 중 행동 1개, 대기 행동 1개까지다.
- `based_on_seq`가 Body의 최신 상태보다 오래됐거나 `ttl_ms`가 지난 명령은 `ack{accepted:false, code:"stale_decision"}`으로 거절한다(예정).
- **반사가 모터를 잡으면**(`reflex_engaged`) 진행 중 행동은 `result{status:"preempted", code:<mode>}`로 닫힌다. 이어서 할지는 두뇌가 정한다.
- 두뇌가 `attack` 명령을 보내면 self_defense 반사는 즉시 물러나고, 2.5초 동안 그 싸움은 두뇌 몫이 된다. 한 번씩 끊어 오는 공격 명령 사이에 반사가 다시 끼어들지 않게 하기 위해서다.
- 게임은 약 2m 안의 아이템을 자동으로 줍는다(`Player.AutoPickup`, 기본 켜짐). 그래서 `move_to`의 목표가 아이템인데 가는 도중 사라졌고 그 아이템 개수가 늘었으면 `result{status:"succeeded", code:"picked_up", evidence{item, added, auto:true}}`로 끝난다. 늘지 않았으면 `target_lost`다.
  - 걷거나 벌목하는 동안 목표가 아닌 아이템도 주워진다. 그래서 채집 진척은 줍기 결과가 아니라 인벤토리 증가로 센다.

### event kind
| kind | data |
|---|---|
| `chat` | from, talker(normal\|shout\|whisper), text, distance, stop_phrase? (봇이 게임에서 들은 채팅. `thorkell play`에서는 리더의 말을 이것 대신 호스트 플러그인의 `thorkell-leader-chat.jsonl`로 받는다. 게임은 루프백으로 들어온 봇에게 사람의 채팅을 보내지 않기 때문이다) |
| `damage_taken` | amount, hp_after, types{…}, blocked, hit_type, attacker_id?, attacker_name?, attacker_kind? |
| `damage_dealt` | type(normal\|resistant\|weak\|immune\|too_hard\|blocked…), text, amount?, pos, **weapon{name, damage{…}}** (타격 순간 손에 든 것), **on_target**. 한 번 휘두르면 범위 안의 여러 물체가 맞는다. 몸은 봇의 타격이 맞힌 물체·지점을 기록해 두고, 피해 숫자 위치(`hit.m_point`)가 겨냥한 대상의 타격 지점과 같을 때만 `on_target: true`로 보낸다. 두뇌는 `on_target`인 타격으로만 약점·내성을 배운다. |
| `reflex_engaged` / `reflex_released` | mode(self_defense\|self_preservation), reason, attacker_id?, attacker_name?, weapon? |
| `item_discovered` | name, type |
| `recipe_unlocked` | name, station |
| `piece_unlocked` | name, category |
| `station_discovered` | name, level |
| `text_read` | label, text (룬스톤·까마귀 글) |
| `raven_appeared` | topic, munin |
| `biome_entered` | name |
| `skill_up` | skill, level |
| `game_message` | where(center\|top_left), text, amount |
| `death` | pos |
| `creature_died` | id, size, pos (보이는 곳에 생물의 시체가 생김. 플레이어의 시체는 보내지 않는다) |
| `creature_attacking` | id, distance, size, facing_me (보이는 생물이 공격 동작을 시작한 순간. 애니메이션은 동기화되므로 사람이 화면에서 보는 것과 같다. facing_me는 정면이 나를 향하는지) |
| `env_changed` | night? \| weather? |
| `peer_joined` / `peer_left` | name |

이름은 모두 게임이 보여 주는 사용자 언어(한국어) 문자열이다. prefab 이름은 보내지 않는다.

### 행동 결과에서 자주 보는 코드와 evidence
| op | 성공 | 실패 | evidence |
|---|---|---|---|
| `move_to` | `arrived`, `picked_up`(목표 아이템이 자동 줍기로 사라짐) | `target_lost`, `timeout`, `blocked` | remaining_m, vertical_m(개체 목표와의 높이 차. 1.5m를 넘으면 도착이 아니다), unstucks, item_center_m?(아이템 기준점까지 거리) |
| `pickup` | `picked_up` | `not_found`, `out_of_reach`(가장 가까운 표면까지 2.5m 초과), `in_tar`, `ownership_timeout`, `taken_by_someone_else`, `inventory_full`, `pickup_failed` | item, added |
| `attack` | `swung`, `destroyed` | `not_found`, `out_of_reach`(distance_m·reach_m 또는 vertical_m), `cannot_attack`, `swing_not_started` | swings, melee_checks(게임이 근접 판정을 실제로 돌린 횟수), hp_before, hp_after, destroyed |

`move_to`의 도착과 `pickup`의 손 닿는 거리는 같은 기준(대상의 가장 가까운 콜라이더 표면까지 수평 거리)으로 잰다. 두 기준이 다르면 "도착했는데 손이 안 닿는" 일이 생긴다.

### scene.inventory 항목
name, stack, quality, type, weight, equipped, durability?, food{health, stamina, eitr, duration_s}?, damage{blunt, slash, pierce, chop, pickaxe, fire, frost, lightning, poison, spirit}?

`damage`는 사람이 툴팁에서 읽는 수치다. 무기 선택은 이 수치에 지금까지 배운 약점·내성을 곱해서 판단한다(`brain/thorkell/control/skills.py` `combat_score`).

### scene의 리더
- `leader{id, name, distance, bearing, pos}`: 리더 캐릭터가 봇 클라이언트에 로드돼 있을 때만 있다. 로드 범위는 게임의 시뮬레이션 거리로, 기본은 64m 구역 ±2개(축 방향 약 160m)이고 설정에 따라 350m까지다.
- `leader_on_map{name, distance, pos}`: 리더가 로드되지 않았지만 지도에서 위치 공개를 켜 둔 경우만 있다.
  - 사람 플레이어도 지도에서 보는 정보다.
  - 몇 초 늦을 수 있다.
  - `follow`는 이 위치로 60m씩 다가가며 다시 본다.
- 둘 다 없으면 리더의 위치를 모르는 것이다. 토르켈은 "지도에서 위치 공개를 켜 달라"고 말한다.
- Body는 자기 위치를 지도에 공개한다(`Body.ShowOnMap`, 기본 켬). 사람이 지도에서 토르켈을 찾을 수 있다.

### 호스트 상태 파일(`thorkell-host-status.json`, 사람 화면용)
listener, port, world, backend, leader, leader_chat, `leader_pos`, `thorkell{name, pos}`, updated.
- 호스트는 접속한 피어의 기준 위치(`ZNetPeer.m_refPos`)를 항상 안다.
- 그래서 `thorkell.pos`는 토르켈이 지도에 위치를 공개하지 않아도 있다.
- 이 위치는 GUI가 "토르켈은 내 북동쪽 300m에 있어요"로 보여 주는 데만 쓴다. 두뇌에는 넘기지 않는다(정보 동등성).
