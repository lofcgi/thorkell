# Thorkell — 작업 지침

Valheim 1.0.16 월드에 **진짜 플레이어로 접속**해서, 처음 게임하는 사람처럼 보고·판단·행동·대화하는 동료 "Thorkell"을 만든다.

```
사람의 Valheim(호스트 복제본 + Thorkell.Host) ──PlayFab── 친구들
   │ 127.0.0.1 Steam 루프백 리스너
봇 Valheim 클라이언트(복제본 + Thorkell.Body) ──TCP NDJSON──► brain (Python)
                                                     ├─ 빠른 결정: Jev → laya
                                                     ├─ 계획·회고·학습: gemini-3.8-flash
                                                     └─ 음성 대화: gemini-3.8-live
```

- 설계 근거와 조사: `docs/research/2026-10-01-thorkell-feasibility.md`
- 게임 API 메모(1.0.16): `docs/api/1.0.16.md`
- 프로토콜: `protocol/PROTOCOL.md`, 공용 fixture `protocol/v1/fixtures/`

## 하드 규칙

1. **실제 게임 설치·세이브·설정에 쓰지 않는다.** 대상은 Steam 설치 폴더, `~/Library/Application Support/IronGate/Valheim`, `~/Library/Preferences/com.coffeestain.valheim-steam.plist`이다. 사용자가 그때그때 동의한 경우만 예외다. 게임 런타임은 `~/Library/Application Support/Thorkell/` 아래 APFS 클론에서만 돌린다.
2. **비밀을 읽거나 출력하지 않는다.** 토큰, 서버 비밀번호, API 키가 해당한다. 키는 `op run`으로 주입한다. `.env*`는 열지 않는다.
3. **실게임(네이티브) 시나리오는 한 번에 하나만 돌린다.** 포트와 Steam 세션을 공유하기 때문이다.
4. **프로덕션 코드는 아이템 지급·피해 주입·텔레포트를 하지 않는다.** 테스트 fixture만 할 수 있고, `cheated: true`(`Inventory.AddItem`)로 표시한다.
5. **두뇌에는 토르켈 자신의 화면에서 사람이 알 수 있는 정보만 보낸다(정보 동등성).** 사람 플레이어의 화면을 보는 것이 아니다. 사람이 토르켈 캐릭터를 직접 조작한다면 얻었을 양과 종류의 정보다. 그래야 판단도 사람처럼 한다.
   - 보내지 않는 것: prefab 이름, 도구 tier, AI 내부값.
   - 개체 키로 쓰는 로컬라이즈 토큰(`$enemy_…`)은 모델 프롬프트에 넣지 않는다.
6. **버전 게이트를 지킨다.** `plugin/Thorkell.Compat/tested-versions.json`과 다른 빌드에서는 arm하지 않는다. 새 리플렉션 대상은 `GameApi`와 `RequiredApi.json`에 같이 추가한다.
7. **에러를 삼키지 않는다. 폴백은 요청이 있을 때만 만든다.** 대체 경로가 필요하면 config로 명시적으로 고르게 한다. 숨은 기본값을 두지 않는다.
8. **게임 디컴파일 결과는 레포에 넣지 않는다.** 세션 scratchpad에만 두고, 문서에는 시그니처와 요약만 적는다.

## 명령

```bash
# 환경 점검 / vendor 고정 다운로드 / 게임 DLL API 오프라인 점검
cd brain && uv run thorkell doctor
cd brain && uv run thorkell vendor
cd brain && uv run thorkell verify-api

# C# (Wire/Core 단위 테스트, 플러그인 빌드)
dotnet test Thorkell.sln
dotnet build Thorkell.sln -c Release

# Python
cd brain && uv run pytest && uv run ruff check && uv run ruff format --check && uv run mypy

# 게임 없이 두뇌를 돌려 보기 (2D 시뮬레이터, 콘솔에서 리더 대사 입력)
cd brain && uv run thorkell sim --time-scale 4 [--config thorkell.toml]

# 실게임 시나리오 (Steam 로그인 필요, 진짜 Valheim은 꺼 둔다, 한 번에 하나)
cd brain && uv run thorkell scenario peer --backend steam|playfab
cd brain && uv run thorkell scenario primitives
# 몸 동작(제작·건축·활·아이템 쓰기) / 두뇌 스킬(쉼터→화살→사냥→요리)
cd brain && uv run thorkell scenario actions|skills
# 첫 보스: 제단에 트로피 → 토르켈이 알아채고 생각해서 싸움 → 회고. 같은 --mind로 다시 돌리면 두 번째 도전
# --together: 리더가 "같이 잡자"고 하고 맨손으로 보스 곁에서 막는다(시험 전용 무적). 빼면 리더는 "혼자 해 봐"
# --mortal-leader(--together와 같이): 리더가 무적 없이 음식 세 칸을 먹고 몽둥이로 막는다. 사람 리더처럼 쓰러질 수 있다
cd brain && uv run --env-file ../.env thorkell scenario boss [--together] --config thorkell.play.toml --mind ../artifacts/boss-mind.sqlite
# 눈: 토르켈 자신의 화면을 찍어(look) 비전 모델로 읽는다(포털·표지판 앞, 사방·한쪽, 속도) / 문 열고 오두막 들어가기·포털 건너기
cd brain && uv run --env-file ../.env thorkell scenario sight --config thorkell.play.toml
cd brain && uv run thorkell scenario travel
# 새 월드 처음부터: 빈손 → 도끼 → 나무 20개 → "집을 지어야겠어"(규모를 되묻는지) → "작게 지어 줘" → 먹을 것 → 사슴 트로피. 리더는 말만 한다
cd brain && uv run --env-file ../.env thorkell scenario fresh --config thorkell.play.toml
# 영어로 플레이(두 게임·리더의 말·토르켈의 생각과 말): language = "en"인 설정으로 같은 시나리오를 돌린다
cd brain && uv run --env-file ../.env thorkell scenario talk|fresh|sight --config thorkell.play.en.toml
cd brain && uv run --env-file ../.env thorkell scenario boss --together --config thorkell.play.en.toml --mind ../artifacts/boss-mind-en.sqlite
# 게임 채팅 대화: 리더(하네스)가 채팅으로 말하고, 토르켈이 자기 이름으로 답하고 따라오고 멈추고 멀리서 찾아온다
cd brain && uv run thorkell scenario talk --backend playfab
cd brain && uv run --env-file ../.env thorkell scenario talk --backend playfab --config thorkell.play.toml  # 실제 플래너로 잡담까지
# 실제 모델의 판단(집 짓자, 멧돼지, 식량, 잡담 / 보스를 처음 봄, 교훈을 따름, 진 싸움 회고)
cd brain && uv run --env-file ../.env thorkell judge [--case boss_seen] [--language en]

# 실제 API 계약 확인 (키는 op로 주입. 사용자가 레포 루트 .env에 둔 경우: uv run --env-file ../.env ...)
cd brain && op run --env-file secrets.op -- uv run thorkell contract flash|jev|live

# 사람 세이브 백업(Steam Cloud·로컬·prefs, 원본은 읽기만) / 백업 복사본으로 같이 플레이(리허설)
cd brain && uv run thorkell backup [--verify]
cd brain && uv run thorkell scenario rehearsal --backend playfab      # 백업 월드가 격리 호스트에서 열리고 봇이 들어오는지
cd brain && uv run --env-file ../.env thorkell play --rehearsal helloworld --config thorkell.play.toml
```

시뮬레이터(`brain/thorkell/sim/world.py`)는 Body와 같은 명령·이벤트 규약을 따른다. 몸의 동작 규칙(즉시 명령, 반사 선점, 두뇌 인계)을 바꾸면 시뮬레이터도 같이 바꾼다.

## 구조

| 경로 | 내용 |
|---|---|
| `plugin/Thorkell.Wire` | netstandard2.1. 프로토콜 DTO, NDJSON 코덱(게임 내장 Newtonsoft.Json 13.0.2), HMAC |
| `plugin/Thorkell.Core` | netstandard2.1, Unity 없음. 반사 모드 중재, 히스테리시스, 버전 게이트 판정 등 순수 로직 |
| `plugin/Thorkell.Compat` | Body/Host가 함께 쓰는 소스. 게임 API 핸들, 버전 읽기, `RequiredApi.json`, `tested-versions.json` |
| `plugin/Thorkell.Body` | 봇 클라이언트 플러그인. 격리, 입력, 지각, 이벤트, 스킬, 반사 |
| `plugin/Thorkell.Host` | 사람 호스트 플러그인. 루프백 리스너, crossplay shim, HUD |
| `tools/Thorkell.ApiCheck` | DLL 메타데이터로 필요한 멤버와 빌드 해시를 확인 (`thorkell verify-api`) |
| `tools/gui` | 사람용 앱 `Thorkell.app`(SwiftUI). 엔진은 `thorkell play --ui jsonl`이고 표준 입출력 JSON 줄로 대화한다. `build.sh`로 `~/Applications`에 만든다. 확인: `--selftest`(창 없이 점검 모드), `--snapshot 경로.png`(예시 대화 창 그림) |
| `tools/launcher` | 터미널용 실행기 `thorkell-play.command`(점검 후 리허설 실행) |
| `brain/` | uv 프로젝트, 패키지 `thorkell`. 브리지, 컨트롤러, 계획, 결정, 지식, 대화, 운영 CLI |
| `protocol/v1` | 공용 fixture와 HMAC 벡터. C# 테스트와 pytest가 같은 파일로 왕복 검증한다 |
| `tests/csharp` | xunit (net9.0) |

## 새 행동·이벤트·리플렉션 대상을 추가할 때

1. 게임 API를 `docs/api/1.0.16.md`에서 확인한다(없으면 디컴파일해서 시그니처를 적는다).
2. private 멤버라면 `plugin/Thorkell.Compat/RequiredApi.json`에 넣고 `thorkell verify-api`로 확인한다.
3. 메시지 모양이 바뀌면 `protocol/v1/fixtures`에 예시를 추가한다. C#과 Python 양쪽 테스트가 같은 fixture를 쓴다.
4. 행동은 사전조건, 네이티브 경로, **월드 변화로 하는 결과 검증**, 타입 결과 코드를 갖춘다.
   - 월드 변화의 예: 대상 HP 감소, 인벤토리 증감, 받는 쪽 확인.
   - 휘두르기를 수락했다는 것만으로는 진척으로 치지 않는다.

## 실게임 시나리오에서 배운 것 (2026-10-02, S0·S0b·S1) — 반복하지 않는다

자세한 근거는 `docs/api/1.0.16.md` G절에 있다.
- 플러그인 `Awake`는 플랫폼 초기화보다 먼저 돈다. 클라우드·세이브 경로 확인은 `PlatformInitializer.InitializeSaveDataStorage` 직전에 한다.
- Unity는 시작할 때와 끝날 때 공용 prefs에 네이티브로 쓴다. Harmony로는 못 막는다. 봇·테스트 런타임은 `sandbox-exec` 거부 프로파일 안에서 띄운다(`ops/runtime.py`). `CFFIXED_USER_HOME`은 prefs를 옮기지 못한다.
- 게임은 2m 안의 아이템을 자동으로 줍는다. 채집 진척은 줍기 결과가 아니라 인벤토리 증가로 센다.
- 도착 판정과 손 닿는 거리·휘두름 범위는 같은 기준으로 잰다(가장 가까운 콜라이더 표면, 높이 포함). 기준이 다르면 "도착했는데 안 닿는" 일이 생긴다.
- `StartAttack`이 true여도 휘두른 것이 아니다. 공격 애니메이션이 시작된 것을 보고 센다.
- 한 번 휘두르면 범위 안의 다른 물체(덤불·바위)도 맞는다. 약점·내성은 `damage_dealt.on_target`인 타격으로만 배운다.
- 테스트 fixture는 지형이 다 불러와진 뒤에 놓는다. 콜라이더 바닥을 지면 위로 올리고, 리더와 5m 이상 떨어뜨린다. 떨어뜨린 통나무는 조금만 기울어도 구르니 베기 시험은 서 있는 나무로 한다.
- 사람의 게임 채팅은 루프백으로 들어온 봇에게 아예 전해지지 않는다(보내기 전 플랫폼 권한 확인이 Error). 리더의 말은 호스트 플러그인이 파일로 넘기고 `thorkell play`가 읽는다. 일반 채팅은 15m 제한도 있어서, 토르켈은 리더가 멀면 외쳐서 답한다. 봇 게임 소리는 게임이 다시 켜므로 매 프레임 끈다.
- 같은 Steam 계정이라 채팅창은 토르켈의 말을 사람 이름으로 찍는다(이름을 플랫폼 ID로 찾음). 호스트 플러그인이 루프백 피어의 말만 토르켈 이름으로 찍는다. 루프백 피어는 소켓 호스트 이름(Steam ID)으로는 못 가린다.
- 리더가 멀면 리더 캐릭터가 봇에게 로드되지 않는다. arm 조건은 "리더가 근처"가 아니라 "리더 접속"이다. 멀리 있는 리더는 지도 위치 공개로 찾는다(`leader_on_map`).
- 아는 명령("따라와", "기다려", "나무 10개")은 검증된 스킬로 바로 시작한다. 플래너에 보내면 실게임에서 20초 늦게, 엉뚱한 조건(체력 비율 대신 10.0)으로 바로 멈췄다. 플래너는 처음 보는 말과 수량 판단만 맡는다.
- 플래너 출력은 검증기가 단위까지 확인한다(`hp_below`는 0~1 비율). 모델 API 오류(503 등)는 `ModelError`로 바꿔서 말로 알린다.
- 플러그인 로그(BepInEx)는 SIGKILL 때 마지막 몇 줄이 사라진다. 끝부분 진단은 결과 evidence나 report에 싣는다.

## 실게임 시나리오에서 배운 것 (2026-10-17, actions·shelter·skills·boss) — 반복하지 않는다

- 게임의 조준(이름표·상호작용)은 눈이 아니라 **카메라 광선**이다. 카메라는 머리 뒤·위에 있다. 생물을 쳐다볼 때는 카메라에서 그 생물로 향하는 방향을 준다(`Geometry.CrosshairDirection`).
- `SetLookDir`는 좌우만 돌리고 위아래(`m_lookPitch`)는 그대로 둔다. 위아래는 `SetMouseLook`으로 맞춘다(`Motor`). 안 그러면 조준점이 땅이나 먼 곳을 가리켜 이름표가 안 뜬다.
- 건물의 `pos`는 다가갈 지점(가장 가까운 겉면)이다. 둘레에 벽을 세우거나 불 위에 요리대를 놓을 때는 `center`를 쓴다. 폭 3m 작업대에서는 둘이 1.6m 달랐다.
- 건축 광선이 겨눈 땅보다 덤불·바위·작업대에 먼저 맞으면 미리보기가 그 위에 뜬다. 땅(terrain)을 겨누고, 광선이 겨눈 점에 맞았는지 본다. 불 위 요리대는 미리보기가 비켜난 만큼 조준점을 옮겨 맞춘다(`within_m`).
- 반사(방어)가 몸을 잡고 있으면 움직이는 명령은 진행되지 않는다. 기다리게 두지 말고 바로 `preempted`로 돌려준다. 때리기·쏘기·구르기는 두뇌가 싸움을 넘겨받는 명령이라 반사를 놓게 한다.
- 시험 월드는 시작 신전 말고는 장소를 만들지 않는다(속도). 보스 제단 같은 장소는 `Setup.locations`로 만든다. `ZoneSystem.FindClosestLocation`은 애셋 참조 이름으로 비교해서 못 찾는다. `m_prefabName`으로 찾는다.
- 사냥 시험의 멧돼지는 다른 단계(쉼터 짓기)를 하는 동안 멀리 가 버린다. 필요한 순간에 하네스 cue(`spawn`)로 내보낸다.
- 방어 반사는 활을 든 채 맞아도 상대에게 달려가 근접 반격했다. 보스에게 그러다 뿔에 세 번 맞고 죽었다. 큰 적(보스)이나 활을 든 싸움은 반사가 아니라 두뇌가 맡는다.
- 전술(몇 m 떨어질지, 언제 물러날지, 먼저 먹을지, 죽은 뒤 혼자 갈지)을 실행할 때마다 코드 숫자로 고치지 않는다. 그건 개발자가 배운 것이지 토르켈이 배운 것이 아니다. 판단은 모델이 지각과 기억으로 하고(`plan/tactics.py`), 배움은 토르켈의 기억에 남긴다: 싸움 기록(episode) → 회고 → 근거 숫자가 든 교훈(lesson) → 다음 싸움에서 따르고 맞았는지 판정. 코드는 언제 생각할지(큰 것이 나를 알아챔, 싸움이 끝남, 죽음)와 몸 기술만 맡는다.
- 실게임에서 진 싸움(음식 한 칸, 16m 안에서 번개, 5m 안에서 뿔)을 실제 모델에게 회고시키면 숫자를 근거로 교훈을 만들고, 다음 판단에서 그 교훈을 인용해 거리를 늘리고 먼저 먹었다(`thorkell judge --case boss_lost|boss_again`).
- 상대가 안 보이게 된 것은 쓰러진 것이 아니다. 해치웠다는 판단은 쓰러지는 것(`creature_died`)이나 공격 결과로만 한다. 맞은 순간에는 상대가 장면(초당 두 번)에 아직 없을 수 있다.
- 실제 gemini-3.8-flash는 enum·숫자 범위·설명이 다 들어간 스키마를 400으로 거절했다. 범위는 검증기가 본다. 모델 판단은 `thorkell judge`로 확인한다.
- 반사 중재기(`ModeArbiter`)는 반사가 끝난 뒤 1초 기다렸다가 몸을 놓는다. 그 1초 동안 반사 동작을 계속하면 안 된다. 쓰러져 없어진 상대를 쫓다가 매 프레임 예외가 났고, 그동안 링크 갱신이 멈췄다(2026-10-18).
- 싸움 기록은 사람이 기억하는 대로 남긴다. 먹기 전의 음식 칸(1칸)을 적었더니, 모델이 세 칸을 채우고 싸운 판을 보고 "1칸만 채우지 말자"는 틀린 교훈을 만들었다.
- 물러날 때 리더 쪽으로 갈지는 판단이다(`retreat_to_leader`). 모델이 리더가 최근에 한 말을 보고 정한다.
  - 리더 쪽으로 가지 않을 때: 곧장 반대로 물러나다 리더에게서 230m 떨어진 검은 숲에서 죽었다.
  - 늘 리더 쪽으로 갈 때: 싸우지 않는 하네스 리더에게 보스를 끌고 가 리더가 죽었다.
- 시체(`Ragdoll`)는 주인을 모른다. 플레이어의 시체를 곁의 보스가 쓰러진 것으로 읽어 "해치웠어"라고 했다(`Falls`).
- 리더의 말은 호스트로 들어와도 대화 기억에 남긴다(`hear_leader`). 안 남기면 플래너와 싸움 판단이 리더의 말을 모른다.
- 계획(플래너)으로 한 일은 계획이 멈추면 같이 멈춰야 한다. 단계를 따로 띄운 작업이 남아 "멈춰" 뒤에도 나무를 하고, 싸움 두 개가 한 몸을 움직였다. 계획의 싸움도 기록·회고하고, 생존 목표로 다룬다.
- 싸움 기록은 사람이 기억하는 것을 빠짐없이: 다른 놈에게 맞은 것(멧돼지 8방에 죽고 보스 탓으로 회고했다), 내 체력바 흐름, 무엇에 시간을 썼는지(물러나기 98초, 쏘기 8초).
- 지각 빈틈은 실패로 드러난다. 보스의 공격 동작(애니메이션, `creature_attacking`), 40m 밖의 큰 생물, 가려져도 뜨는 보스 체력바(`boss_bars`), 화면 가운데 "…를 처치했습니다". 사람은 다 보는 것이었다.
- 코드의 고정 횟수(싸움 400차례)나 가까우면 매번 구르기 같은 내 규칙이 싸움을 망쳤다. 끝내는 조건은 진척(상대 체력)으로, 구르기는 보이는 공격 동작으로.
- 리허설(2026-10-18): 물체 목록만으로는 장면을 모른다(포털을 못 봄, 소환수를 적으로 앎, 집에 못 들어옴). 토르켈 자신의 화면을 찍어 비전 모델(flash-lite, 한 장 약 2초)로 읽는다(`world/sight.py`, Body `Sight`). 이름표 목록을 같이 주면 안 보이는 것도 본 척하니 "그림에 보이는 것만"을 못 박는다. 돌려 찍으면 모션 블러로 번지니 봇은 끈다.
- 싸울지 말지도 판단이다. 큰 것을 알아챘다고 코드가 싸움을 정하면 리더의 소환수를 때린다. 전술에 leave가 있고, 싸우는 중의 리더 말은 미루지 않고 다시 판단한다. 안전 규칙을 코드로 넣는 대신 보여 주고 판단시킨다(사용자: "안전 규칙을 추가하는 순간 결정론적 npc가 된다").

## 새 월드에서 배운 것 (2026-10-18, fresh) — 반복하지 않는다

- 한 단계가 안 되면 부탁을 끝내지 말고, 해 본 것과 결과를 모델에게 다시 보여 준다(`[이 부탁으로 해 본 것]`). 첫 실행에서는 나뭇가지 줍기가 한 번 실패하자 9분 동안 서 있었다.
- 레시피는 재료를 손에 넣어야 메뉴에 뜬다. 모델은 재료 모으기까지만 계획할 수 있으니 `think_again_after`로 이어서 생각하게 한다. 계획 횟수 상한은 진척이 있는 동안 넉넉히 두고(12), 잇단 실패(3)로 멈춘다. 상한 5는 거의 다 만든 도끼를 끊었다.
- 긴 것(나뭇가지)을 따면 떨어진 것이 자동 줍기 거리(2m) 밖에 놓인다. 떨어진 것을 보고 걸어가 줍는다. 장면(인벤토리 포함)은 초당 두 번이라 몸이 주웠다고 알린 뒤에도 잠깐 기다린다.
- 도끼가 없으면 나무를 베러 가지 않는다(나뭇가지에서 얻는다).
- 사슴은 사람이 달리는 것보다 빠르다. 웅크리고(토글 키, `m_crouchToggled`) 몰래 다가가 친다. 달아난다는 것을 겪으면 기억에 남기고 다음부터 몰래 다가간다.
- 쓰러진 짐승의 전리품은 `creature_died`의 자리에서 줍는다(마지막으로 본 자리는 달리던 만큼 어긋난다). 무엇이 나왔는지는 싸우기 전 인벤토리와 비교한다.
- 시간이 지난 질의(`look`)의 답이 늦게 오면 버린다. 안 그러면 링크 처리기가 죽는다.
- 몸이 실패한 동작은 두뇌 기록(brain.log)에 남긴다. 실패 원인을 찾을 근거가 됐다.

## 죽을 수 있는 리더와 보스 (2026-10-20, boss --mortal-leader) — 반복하지 않는다

- 몸이 플레이어 시체를 통째로 버려서, 앞에서 막던 리더가 쓰러져도 토르켈은 몰랐다. 같은 방법으로 쏘다 번개에 죽었다. 시체는 2초 안에 그 자리(3m)에 보였던 플레이어로 맞춰 `creature_died`(리더 id, `player: true`)로 알린다(`Falls.FallenPlayer`). 생물 쪽 판정(`Falls.Fallen`)은 그대로 플레이어 시체를 생물로 읽지 않는다.
- 리더가 쓰러지면 싸움을 다시 판단한다("The leader is down!"). 기록과 회고에 쓰러진 시각이 남는다.
- 막지도 구르지도 않는 하네스 리더는 50초 안팎에 쓰러진다. 그 뒤는 혼자 싸움이라 세 번 다 졌다(보스 59%, 58%, 29%). 같은 기억으로 다시 하니 교훈 둘을 인용했지만 27%에서 졌다(시야가 막혀 못 쏜 것 19번). 시야가 막히면 몸이 가까이에서 보이는 자리(`clear_from`, `Geometry.ClearSpot`)를 찾아 준다. 옆걸음 몇 번으로는 넓은 덤불을 못 벗어났다. 공격 동작은 언제·몇 m에서 봤고 굴렀는지를 맞은 기록과 함께 남긴다(`wind_ups`). 그래야 회고가 "그 동작 뒤에 번개가 왔다"를 숫자로 배우고 다음 싸움의 구르기 거리를 스스로 정한다(5m→16m). 굴러도 바로 맞는 일이 남아 있다. 사람 리더가 버티는지가 같이 잡기의 관건이다.

## Eira(이전 시도)에서 배운 것 — 반복하지 않는다

- 같은 클라이언트 안에 두 번째 `Player`를 두면 게임이 파괴한다. 그래서 두 번째 클라이언트로 접속한다.
- 같은 Steam 계정 두 프로세스는 P2P로 만날 수 없다. 루프백 IP 리스너로 연결한다.
- `-nographics`를 쓰면 월드 시간이 멈춘다(요리가 끝나지 않음). batchmode에서도 Metal 그래픽은 켜 둔다.
- Unity `JsonUtility`는 중첩 필드를 잃는다.
- 비볼록 메시에 `Collider.ClosestPoint`를 쓰면 가짜 0거리가 나온다. 레이캐스트를 쓴다.
- 단일 임계값 후퇴는 진동한다. 진입·이탈 히스테리시스를 쓴다.
- 휘두른 횟수나 자기 드롭 카운터를 진척으로 세지 않는다. 대상 HP나 받는 쪽 인벤토리로 센다.
- `DropItem`은 시선이 아니라 **몸이 향한 방향**으로 던진다.
- 일직선 귀환은 끼인다. 경로점을 따라간다.
- 플래너의 도달 거리가 실행기보다 엄격하면 안 된다(Eira: 2.9m 대 3m).
- 홀드아웃 시드로 튜닝하지 않는다.
- 1.7B 모델은 목표를 분해하지 못했다. 목표 분해는 계획 모델이, 수치 계산은 코드가 맡는다.
- 31회 중 23회가 실패했다. 실패 원인 중 가장 많았던 것은 물가·해안 내비게이션 정체(6회)였고, 그다음은 음식 체인 막힘(약 5회)이었다. 해안 시드를 회귀 세트에 둔다.
