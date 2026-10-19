# Thorkell

Valheim에 **진짜 플레이어로 접속**해서 처음 게임하는 사람처럼 보고, 판단하고, 행동하고, 말하는 동료.

- "나무 좀 해줘" → 지금 필요한 양과 해 질 시간을 보고 몇 개 할지 정한다.
- 일하다가 습격받으면 싸우고 다시 일한다. 다음엔 무기를 챙긴다.
- 처음 보는 몬스터를 알아 가고, 사람이 가르쳐 준 것을 기억했다가 직접 확인한다.
- 깨달은 게 있으면 혼잣말을 하거나 먼저 말을 건다.

## 구조

| 층 | 주기 | 구현 |
|---|---|---|
| 몸 | 매 프레임 | BepInEx C# 플러그인. 지각·행동 API와 결정적 반사(방어·자기보존·끼임 탈출) |
| 빠른 결정 | 0.1~0.5초 | Jev(TypeSafe "System One") → 로그로 laya 파인튜닝 후 로컬 대체 |
| 계획·학습 | 수 초 | `gemini-3.8-flash` |
| 대화 | 스트리밍 | `gemini-3.8-live`(한국어 음성) + Valheim 채팅 말풍선 |

자세한 근거는 [`docs/research/2026-10-01-thorkell-feasibility.md`](research/2026-10-01-thorkell-feasibility.md), 작업 규칙은 [`AGENTS.md`](../AGENTS.md)를 본다.

## 진행 상황

| 단계 | 내용 | 상태 |
|---|---|---|
| M0 기반 | 리서치 문서, 레포 뼈대, 프로토콜 v1 코덱(C#/Python 공용 fixture), `verify-api`(83개 멤버), `thorkell contract flash\|jev\|live` | **완료.** 실제 API 계약 확인(2026-10-02): Flash low 2.2초, Jev p50 188ms, Live 첫 음성 1.19초. 결과는 [비용 문서 7절](research/2026-10-02-api-costs-and-keys.md) |
| M1 접속 | 격리 런타임(APFS 복제 + `sandbox-exec` 거부 프로파일), Host 루프백 리스너 + crossplay `RPC_PeerInfo` transpiler shim, Body 격리·접속, 시나리오 러너(prefs·세이브 가드, SIGKILL 종료) | **실게임 통과:** S0(Steam 호스트)·S0b(crossplay 호스트) 봇 접속, 사람 prefs·세이브 변화 0 |
| M2 몸 기본 | 지각(동등성 필터), 이벤트 16종, 모터 입력, 행동 9종, 즉시 명령, 브리지 클라이언트/서버, `BodySession` | **실게임 S1 통과:** 두뇌가 브리지로 장비·먹기·이동·줍기·나무 베기(HP 감소 확인)·바라보기·말하기·자동 줍기를 시킴 |
| M3 반사·채집·전투 | 몸: self_defense·self_preservation 반사, Pathfinding 이동·끼임 탈출. 두뇌: 목표 계층·중재·중단/재개·스킬·먹기(P0) | 두뇌는 시뮬레이터로 검증. 실게임에서는 구르는 통나무 회피 반사가 실제로 발동하는 것만 봤다. S2(벌목 중 습격) 미실행 |
| M4 결정+계획 | Gemini Flash 플래너(구조화 JSON·동적 enum·검증·1회 수정), 수량 계산, Jev/laya 클라이언트, 결정 실행기(마감·차단기·JSONL 로그) | 시뮬레이터 + 가짜 모델로 검증. 실제 모델 미검증 |
| M5 지식·학습 | SQLite 지식(출처·상태), 경험으로 약점·내성 학습, 들은 사실 검증, 깨달음 발화, 첫 목격 혼잣말, 무기 선택에 지식 반영 | 시뮬레이터로 검증 |
| M6 음성·선제 발화 | Gemini Live 세션(도구 5종, 재개 핸들, GoAway 재접속, floor), 마이크/스피커, 발화 라우터, 발화 빈도 제한 | 가짜 세션으로 검증. 실제 음성 미검증 |
| M7 실전 | 친구와 함께 실제 월드 | 대기 |
| M8 laya 증류 | Jev 결정 로그 → laya | 대기(로그 형식만 준비됨) |

**2026-10-17 현황** (첫 보스까지 같이 가기, [`docs/design/eikthyr-companion.md`](design/eikthyr-companion.md))
- 실게임 통과: 몸 동작(`actions`: 제작·건축·활·아이템 쓰기), 두뇌 스킬(`skills`: 쉼터 → 화살 → 활 사냥 → 요리, 2회 연속).
- 실제 모델 판단(`thorkell judge`) 8/8: 집 짓자 → 규모 되묻기, 모르는 멧돼지 → 찾아보며 잡기, 본 멧돼지 → 사냥, 식량 → 덤불 따기, 잡담 → 말로만, 보스를 처음 봄 → 화면 위 체력바를 보고 보스로 여겨 활로 거리 두기, 진 싸움 → 숫자를 근거로 교훈, 다시 싸움 → 교훈을 인용해 따르기.
- 싸움 판단과 배움은 코드 숫자가 아니라 모델과 토르켈의 기억(싸움 기록·교훈)이 한다. 실게임 보스 도전(기억을 이어 여러 번)은 아직 확인 중이다.
- 테스트: C# 72개, Python 254개.

검증 현황(2026-10-02): C# 단위 테스트 61개, Python 145개(시뮬레이터 시나리오 포함) 통과. 실게임 S0·S0b·S1 통과, 실제 모델 API 계약 확인. 실게임에서 찾아 고친 것은 [`docs/api/1.0.16.md`](api/1.0.16.md) G절에 있다.

### 시뮬레이터로 지금 해 볼 수 있는 것

```bash
cd brain && uv run thorkell sim --time-scale 4
> 토르켈, 그레이드워프는 둔기에 약해      # 들은 사실(가설)로 기억
> /spawn                                  # 습격 → 반사 반격 → 곤봉으로 교체 → "네 말이 맞았어!"
> 그레이드워프 약점이 뭐야?               # "둔기에 약해. 직접 싸워 보고 알았어."
> 토르켈, 나무 10개 캐줘
> 뭐해?
> 토르켈 멈춰
```
`--config thorkell.toml`에서 `planner.backend = "gemini"`, `voice.backend = "gemini-live"`, `decide.threat_response = "jev"`를 켜면 실제 모델로 같은 시나리오를 돌린다(키 필요, `secrets.op.example` 참고).

## 토르켈과 같이 플레이하기 (리허설)

지금은 **내 월드의 복사본**에서만 같이 놀 수 있다. 원래 세이브·Steam Cloud·설정은 건드리지 않는다(끝날 때 자동 확인).

**처음부터 같이 하려면 새 월드로.** 백업한 내 월드가 이미 첫 보스를 잡은 월드라면, 앱에서 **새 월드**를 켜고 월드 이름(예: `thorkell`)을 적은 뒤 시작한다. 게임 메뉴에서 그 이름으로 새 월드를 만들면(새 캐릭터 권장) 토르켈도 처음 온 사람처럼 시작한다. 터미널: `thorkell play --rehearsal thorkell --new --config thorkell.play.toml`. 진행은 다음 실행에도 이어진다.

**영어로 하려면.** 앱에서 **English**를 켜면 두 게임 화면, 리더의 말, 토르켈의 생각과 말이 모두 영어가 된다(진짜 게임 설정은 그대로). 한국어로 놀던 월드와 기억이 섞이지 않게 다른 월드 이름을 쓴다. 터미널: `thorkell play --rehearsal thorkell-en --new --config thorkell.play.en.toml`. README 영상용 장면과 그 실게임 시험은 [`docs/video/readme-scenarios.md`](video/readme-scenarios.md)에 있다.

**가장 쉬운 방법: Thorkell 앱.** Spotlight에서 "Thorkell"을 찾거나 `~/Applications/Thorkell.app`을 연다(Dock에 끌어다 두면 편하다).
1. **리허설 시작**을 누른다. 앱이 Steam·진짜 Valheim·빌드·백업을 점검하고, 처음이면 서버 비밀번호를 묻는다.
2. 내 게임 창(리허설 복사본)이 뜨면 노란 안내대로 helloworld를 서버로 연다(crossplay 켬, 같은 비밀번호).
3. 토르켈이 접속하면 게임 채팅으로 말한다(앱 아래 입력창이나 버튼으로 말해도 된다).
   - 토르켈이 어디 있는지는 앱 위쪽에 "토르켈은 내 북동쪽 300m에 있어요"처럼 나온다. 게임 지도에도 토르켈이 보인다(토르켈이 위치를 공개한다).
   - 멀리 있을 때 "따라와"라고 하면 토르켈이 지도를 보고 찾아온다. 그러려면 내 지도에서 **위치 공개**를 켜 둔다(꺼져 있으면 토르켈이 켜 달라고 말한다).
4. **끝내기**를 누르거나 앱 창을 닫으면 토르켈이 캐릭터를 저장하고 나간다. 내 게임 창은 그대로 둔다.
- 앱 만들기/다시 만들기(코드를 바꿨거나 레포를 옮겼을 때): `tools/gui/build.sh`
- 문제가 생기면 앱의 **기술 로그**를 켜서 원인을 본다. **점검** 버튼은 게임을 띄우지 않고 준비 상태만 확인한다.
- 앱 없이 터미널로: `tools/launcher/thorkell-play.command` (Finder에서 더블클릭, `--check`는 점검만)

터미널에서 직접 하려면:

```bash
# 0. 진짜 Valheim은 끄고 Steam만 켠다
cd brain
uv run thorkell backup                       # 처음 한 번: 세이브(Steam Cloud 포함)·설정을 sha256과 함께 백업
uv run --env-file ../.env thorkell play --rehearsal helloworld --config thorkell.play.toml
```

1. 처음 실행하면 서버 비밀번호를 한 번 묻는다(권한 600 파일에만 저장, 화면·로그에 안 남음).
2. 내 게임 창(리허설 복사본)이 뜨면: 캐릭터 선택 → 월드 `helloworld` → **서버 시작**(crossplay 켬) + 같은 비밀번호 → 시작.
3. 월드에 들어가면 토르켈 창이 작게 뜨고, 토르켈은 **시작 신전**에 나타난다. 신전으로 가서 만나거나, 지도에서 위치 공개를 켜고 게임 채팅으로 "따라와"라고 부른다. 콘솔의 `/status`가 토르켈 위치도 알려 준다.
4. 게임 채팅이나 터미널 콘솔에 말한다(토르켈은 거리와 상관없이 게임 채팅을 듣고, 멀면 외쳐서 답한다).
   - "따라와", "기다려", "멈춰", "뭐해?"
   - 처음엔 빈손이다. 도끼를 발밑에 떨어뜨리고 "이 도끼 받아" → 주워서 "나무 10개 캐줘"
   - `thorkell.play.toml`(Gemini Flash + Jev)을 쓰면 정해진 말이 아니어도 알아듣는다. `--config` 없이 실행하면 규칙만 쓴다.
5. 끝낼 때는 콘솔에 `/quit`(또는 Ctrl-C). 토르켈은 캐릭터를 저장하고 나간다. 내 게임 창은 그대로 둔다.

### 첫 보스까지 같이 하기

`--config thorkell.play.toml`(실제 모델)로 실행해야 정해진 말이 아닌 부탁과 싸움 판단이 된다. 토르켈에게 이렇게 해 볼 수 있다.

| 해 볼 것 | 토르켈이 하는 일 |
|---|---|
| "집을 지어야겠어" | 가진 재료와 망치 메뉴를 보고 규모를 되묻거나 제안한다. 정하면 작업대 둘레에 벽·지붕을 올린다 |
| "멧돼지 잡아와" | 본 적이 없으면 무엇인지 묻거나 둘러보며 찾는다. 이름표로 알아보면 활로 사냥하고 고기를 줍는다 |
| "식량이 필요해" | 보이는 덤불을 따거나 사냥하고 불 위 요리대에서 굽는다 |
| 침대에 눕기 | 리더가 누운 것을 보고 자기 침대(없으면 옆에 지어서)에 눕는다 |
| 제단에 트로피를 바치기 | 나타난 것을 보고 무엇인지, 어떻게 싸울지 스스로 정해 말하고 싸운다. 리더가 시키지 않아도 합류한다 |
| "이거 보여?" | 리더가 보는 쪽을 쳐다보고(자기 화면을 비전 모델로 읽는다) 보이는 것으로 답한다 |
| 리더의 소환수·길들인 동물 | 큰 것을 봐도 싸울 상대인지 먼저 본다. 리더가 "내가 소환한 거야"라고 하면 건드리지 않는다 |
| 집·포털 | 가는 길의 닫힌 문을 열고 들어간다. "포탈 들어가면 집이야"면 이름표를 보고 건너가고, 리더가 포털로 사라지면 따라 들어간다 |
| "같이 잡자, 내가 앞에서 막을게" / "혼자 해 봐" | 리더의 말을 듣고 리더 쪽으로 물러날지 정한다. 활로 쏘다가 보스가 공격 동작을 하면(보인다) 정한 거리 안에서 구르고, 끼어든 놈은 먼저 처리한다. 활이 부서지면 다시 생각한다 |
| 싸움이 끝나거나 토르켈이 죽음 | 싸움을 돌아보고 배운 것을 말한다("16m 안에서 번개를 맞았어, 다음엔 더 멀리서"). 다음 싸움에서 그 교훈을 따르고 맞았는지 확인한다. 죽었으면 묘비에 혼자 갈지 같이 갈지 정한다 |

확인 범위:
- 집·멧돼지·식량은 실게임 스킬 시나리오와 실제 모델 판단으로 확인했다.
- 보스 싸움은 실게임으로 확인했다(2026-10-18, `thorkell scenario boss [--together]`, 같은 기억 파일로 15번 넘게 도전).
  - 혼자 싸우기는 아직 못 깼다. 보스 체력을 78%까지 깎았고, 교훈이 쌓이며 판정된다.
  - 같이 싸우기(시험용 리더가 맨손으로 앞에서 막음)는 4번째에 깼다. 토르켈이 활로 99%에서 약 1%까지 깎았고 보스에게 한 대도 안 맞았다.
- 침대는 시뮬레이터에서만 확인했다.

토르켈의 기억(본 것, 들은 것, 싸움 기록, 교훈)은 월드마다 남는다. 같은 월드로 다시 하면 지난번에 배운 것을 쓴다.

리허설에서 한 진행(월드·내 캐릭터·토르켈)은 다음 리허설에 이어진다. 처음부터 다시 하려면 `~/Library/Application Support/Thorkell/runtimes/rehearsal-host`를 지운다.

## 빠른 시작 (개발)

```bash
cd brain
uv run thorkell doctor        # 환경 점검
uv run thorkell vendor        # BepInExPack 5.4.2351 (sha256 고정)
uv run thorkell verify-api    # 게임 DLL에 필요한 API가 있는지
cd .. && dotnet test Thorkell.sln && dotnet build Thorkell.sln -c Release
cd brain && uv run thorkell scenario peer --backend steam        # S0: 격리 호스트 + 봇 접속 (Steam 필요)
cd brain && uv run thorkell scenario peer --backend playfab      # S0b: crossplay 호스트 + RPC_PeerInfo shim
cd brain && uv run thorkell scenario primitives                  # S1: 두뇌가 브리지로 봇을 조종
cd brain && uv run thorkell scenario talk --backend playfab      # 게임 채팅 대화·따라오기·멈춤·멀리서 찾아오기
cd brain && op run --env-file secrets.op -- uv run thorkell contract live   # 실제 API 계약 확인
```

요구 사항: macOS(Apple Silicon은 Rosetta 필요), Valheim 1.0.16(Steam), .NET SDK 9, uv.
