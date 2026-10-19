# Thorkell 실현 가능성 리서치: 로컬 Valheim에서 스스로 보고 판단하고 말하는 동료

| 항목 | 내용 |
|---|---|
| 조사 | 2026-10-01 |
| 설계 반영 | 2026-10-02 (사용자 결정 5개 반영, Gemini Live·laya 공식 문서 재확인) |
| 대상 환경 | macOS(Apple Silicon)에서 도는 Valheim 1.0.16. 사용자가 친구들과 crossplay로 노는 월드 |
| 한 줄 요약 | **가능하다. 단, 모델 하나가 화면을 보고 모든 걸 하는 방식으로는 안 되고, 역할을 나눈 계층 구조여야 한다.** 층은 모드 API(몸), 결정적 반사, 빠른 타입 결정(Jev → laya), 느린 계획·학습(`gemini-3.8-flash`), 음성 대화(`gemini-3.8-live`)다. |

---

## 0. 표기와 읽는 법

| 태그 | 뜻 |
|---|---|
| [공식] | 저자·벤더의 1차 자료(논문, 공식 블로그·문서, 모델 카드, 보도자료) |
| [코드] | 저장소 소스를 직접 확인한 것 |
| [모드 페이지] | Thunderstore·Nexus·Modrinth의 모드 설명 |
| [3자] | 독립 측정이나 언론(Artificial Analysis = AA, 9to5Google 등) |
| [커뮤니티] | 개인 저장소·블로그·벤치 |
| [2차] | 언론·커뮤니티·검색 요약을 거쳐 들어온 내용 |
| [로컬] | 이 Mac에서 직접 확인한 것(설치 파일, 로그, DLL 메타데이터, 이전 프로젝트 기록) |
| [추정] | 이 조사의 계산·해석·권고 |
| [단일출처] | 교차 확인하지 못한 것 |
| ‡ | 이번 조사에서 원문을 다시 열어 보지 않은 것 |

> **주의.** 수치 상당수는 웹 요약 도구를 거쳐 들어왔다. 구현에 쓰기 전에 반드시 원문을 다시 확인한다.
> - 특히 Jev·laya·Gemini Live 수치는 M0 계약 테스트(`thorkell contract live|jev|flash`)에서 실제 API로 측정해 확정한다.
> - 재확인이 필요한 항목은 8.11절에 모아 두었다.

---

## 1. 판정

### 1.1 결론

**가능하다.** 근거는 네 가지다.

1. **Valheim 자체가 게임 에이전트 학습 환경으로 쓰였다.**
   - DeepMind SIMA(2024-03)가 쓴 상용 게임 9종 중 하나가 Valheim이다 [공식]. 근거는 세 가지다.
     - 발표에 "8개 스튜디오, 9개 게임"이라고 나온다.
     - 크레딧에 "Coffee Stain (Valheim, Satisfactory, Goat Simulator 3)"이 있다.
     - 기술 보고서(TR)의 게임 목록에도 Valheim이 있다.
   - SIMA 2(2025-11, Gemini Flash-Lite 기반)의 TR 학습 환경 목록에도 Valheim이 있다 [공식].
   - SIMA 2는 학습하지 않은 바이킹 서바이벌 게임 ASKA에서도 성능이 올랐다 [공식].
   - "도구와 목표를 주면 Valheim을 플레이할 수 있는가"에 대한 가장 직접적인 증거다. 다만 SIMA와 SIMA 2는 비공개이고, SIMA 2는 제한적 프리뷰만 열려 있다.
2. **같은 계층 구조가 상용 게임에 들어갔다.**
   - PUBG Ally(KRAFTON + NVIDIA ACE, 베타 2026-06-17~07-01)는 행동 트리(System 1)와 온디바이스 2B SLM(System 2)으로 나눈 구조다. 1,000명 이상 규모로 검증됐다 [공식].
   - inZOI Smart Zoi(0.5B 모델, 2025-03)도 온디바이스 모델로 자율 행동과 내적 독백을 보여 준다 [공식].
3. **Valheim에서 몸을 움직이는 층은 이미 검증됐다.**
   - VikingNPC/Norsemen과 Offline Companions가 채집·전투·추종을 해낸다 [코드/모드 페이지].
   - 이전 시도 Eira는 이 Mac에서 다음을 실제 게임으로 통과했다(0.221.12) [로컬].
     - 두 클라이언트 접속
     - 벌목·요리·사냥·수리
     - 20분 평가
4. **Minecraft에서는 LLM 동반자가 실사용자를 상대로 돌아가고 있다.** Mindcraft와 Player2 AI NPC가 그 예다 [코드/모드 페이지].

**조건이 있다.**
- 계층 구조로 만들어야 한다(1.4절).
- 범위를 좁혀 단계적으로 검증해야 한다. PUBG Ally도 맵 하나, 모드 하나로 범위를 닫아서 성공했다 [공식].

**아직 없는 것: 완성된 오픈소스 Valheim LLM 동반자.**
- Thrall: 지원 종료
- Fylgja: 게임 브리지가 미구현(stub)
- ValheimAI: 추종·정지만 구현된 초기 단계
- open-valheim-bot: 초기 단계

### 1.2 요구사항별 매핑

| 요구사항 | 가능성 | 근거 사례 | Thorkell 구현 | 남는 한계 |
|---|---|---|---|---|
| 유저 말에 준실시간 응답 | **가능 (체감 약 2초)** | `gemini-3.8-live` TTFA 1.18초 [3자 AA]. Convai: "1초가 넘으면 느리게 느껴진다" [공식-벤더]. PUBG Ally 온디바이스 음성 [공식] | Live 세션(서버 VAD `silenceDurationMs` 600)에서 NON_BLOCKING 도구로 컨트롤러에 위임. 사용자가 말을 시작하면 0.3초 안에 바라본다(비언어 반응) | 첫 음성 p50 ≈ 2.0초 = VAD 0.6 + TTFA 약 1.2 + 버퍼 0.15 [추정]. 1초 미만은 현재 클라우드 음성 모델로는 어렵다 |
| 스스로 판단: 수량 ("나무 몇 개?") | **가능** | GITM(목표 → 하위 목표 → 구조화 액션) [공식]. Voyager 자동 커리큘럼 [공식]. SIMA 2의 Gemini 목표 분해 [공식]. 반례: Eira의 1.7B 모델은 목표 분해에 실패했다(결정의 33%가 선택지 1개) [로컬] | `gemini-3.8-flash` 플래너 + `craftgraph.feasible_max`를 쓴다. 코드가 운반 여유, 빈 칸, 내구도, "해 질 때까지 시간 × 관측한 채집 속도" 중 최솟값을 계산하고, 모델은 그 안에서 근거를 붙여 고른다 | 플래너 지연: AA 측정으로 10k 입력·추론 포함 시 TTFT 17.5초 [3자]. 그래서 검증된 스킬 템플릿을 먼저 쓴다 |
| 일하다 습격받으면 대응 | **가능** | Mindcraft `modes`: self_defense 등이 진행 중 행동을 끊는다 [코드]. AAMAS'26 병렬 계획-행동: 단일 슬롯 + interrupt flag [공식]. PUBG Ally 행동 트리 [공식]. Offline Companions: 막기·패리·스태미나 후퇴 [모드 페이지] | Body의 반사 모드(`self_defense`)가 즉시 반응하고 현재 행동은 일시정지한다. 이어서 Jev `threat_response`(마감 400ms)가 판단하고, 정리되면 재개한다 | 정밀한 전투 조작. SIMA 2도 키보드·마우스 정밀 조작을 한계로 밝혔다 [공식] |
| 무기를 만들거나 미리 챙겨 감 | **가능 (경험이 쌓여야 함)** | ExpeL·AutoManual(경험 → 규칙) [공식]. Voyager 스킬 라이브러리 [공식]. Optimus-1 Reflector [공식] | 패배하면 회고해서 전제조건 규칙을 만든다(예: "숲에선 무기+방패"). 다음 계획에 준비 단계를 넣고, Jev `prep_check`로 확인한다 | 규칙 품질은 에피소드 수에 좌우된다 |
| 처음 보는 몬스터 인지 | **가능** | SIMA 2의 임베디드 QA(직접 돌아다니며 질문에 답함) [공식]. Valheim 자체 발견 메커니즘: 재료를 얻으면 레시피 해금, 까마귀 팁, 룬스톤, 데미지 텍스트 [로컬: 1.0.16 호출 경로 확인] | 정보 동등성 필터: hover 이름과 `EnemyHud`에 보이는 체력·별만 넘긴다. `DamageText` 유형(weak/resistant/immune/too_hard)으로 도감을 갱신한다 | LLM이 이미 Valheim을 알고 있어 지식이 새어 나온다. 발견한 이름만 노출하고, 인용을 강제하고, 누출률을 측정한다 |
| 보스 대비 (더 좋은 무기) | **부분적으로 가능** | SIMA 2·NitroGen·Lumine 모두 장기 과제를 한계로 밝혔다 [공식]. Optimus-1 지식 그래프 기반 계획 [공식] | P2 자기 의제(더 좋은 무기, 보스 대비), 플래너 thinking high. 보스 소환은 사용자 동의가 필요하다 | 장기 계획은 아직 검증되지 않은 영역이다 |
| 대화로 게임 시스템 이해 | **가능** | Generative Agents 기억·반성 [공식]. Mindcraft `memory.json` [코드] | 사용자 발화에서 `told` 사실을 뽑아 저장하고, 경험(데미지 텍스트 등)으로 검증해 supported → verified 또는 refuted로 바꾼다 | 사용자가 틀린 정보를 주면 반증 로직에 기대야 한다 |
| 깨달으면 혼잣말·먼저 말 걸기 | **가능** | inZOI Smart Zoi 내적 독백 [공식]. Convai: 상태 변화를 스스로 말하고 "대화가 유휴일 때만 말하기" 모드가 있음 [공식-벤더]. Proact-VL: 언제 말할지 스스로 결정 [공식]. SIMA 2: 과제 완료를 먼저 보고 [공식] | 트리거(위험, 발견, 놀람, 깨달음, 마일스톤, 침묵)마다 점수를 매기고 횟수를 제한한다. 대화 상태(floor)를 보고 기다린다. 혼잣말은 Whisper 말풍선, 사용자에게는 Normal + 음성, 위험은 Shout | Live 모델은 proactive audio가 항상 켜져 있어 주입한 이벤트를 무시할 수 있다(2026-10-02 공식 문서 확인). `speech_dropped`로 측정한다 |
| 도구와 목표만으로 플레이 | **가능 (범위를 좁혀 단계적으로)** | SIMA/SIMA 2 학습 환경에 Valheim이 있다 [공식]. Voyager·Mindcraft는 게임 API로 플레이한다 [공식/코드]. Eira 20분 평가 통과 [로컬]. PUBG Ally는 범위를 닫아서 성공했다 [공식] | Player 의미 체계의 Body API(이동, 전투, 채집, 제작, 건축, 스테이션, 상자, 수면, 상호작용)를 만들고 마일스톤마다 검증한다 | 물가 내비게이션(Eira 실패 원인 중 가장 많음), 넓은 범위, 장기 계획 |

### 1.3 "픽셀을 보고 다 하는 모델 하나"로는 안 되는 이유

| 후보 | 막히는 이유 | 표기 |
|---|---|---|
| SIMA 2 | 제한적 프리뷰 | [공식] |
| Game-TARS | 비공개 | [공식] |
| Lumine | 학습 방법만 공개, 가중치 비공개 | [공식] |
| NitroGen | 비상업 라이선스, Windows 전용. README가 "빠르게 반응하는 system-1 모델이며 장기 계획은 못 한다"고 밝힘 | [공식] |
| Open-P2P | 코드는 MIT이고 M3 Max에서 34ms로 돌았다는 실증이 있다 [커뮤니티]. 그러나 이를 쓴 laya-vision-stitch README가 "기본적인 시각 이동 수준이지 일반 게임플레이가 아니다"라고 밝힘 | [커뮤니티] |
| Cradle | LLM 지연 때문에 실시간 게임은 일시정지해야 함 | [공식] |
| Muse/WHAM | 모델카드가 실시간 사용과 에이전트 플레이를 범위 밖으로 명시 | [공식] |

Valheim은 모드로 게임 상태를 읽고 네이티브 동작을 실행할 수 있다. 그러면 구조화 API가 지연과 신뢰성 두 면에서 모두 유리하다 [추정]. 시각 정보는 보조로만 쓴다. 예를 들어 처음 보는 개체를 묘사할 때 카메라 프레임을 캡처한다.

PUBG Ally의 NVIDIA 블로그도 같은 결론이다. System 1(행동 트리, 게임 틱 단위)과 System 2(2B SLM)를 나눴다 [공식].

### 1.4 계층 구조 (Thorkell)

| 층 | 주기 | 담당 | 선례 |
|---|---|---|---|
| 몸 (BepInEx C#) | 매 프레임 | 지각·행동 API, 결정적 반사(방어, 자기보존, 끼임 탈출) | VikingNPC, Offline Companions, Eira, PUBG Ally 행동 트리 |
| 빠른 결정 (Jev → laya) | 0.1~0.5초 | 위협 대응, 타깃, 준비물 같은 타입 선택 | NVIDIA ACE "게이머는 초당 8–13번 미시 결정을 한다" [공식], Jev Doom 데모 |
| 느린 계획·학습 (`gemini-3.8-flash`) | 수 초 | 목표 분해, 수량 판단, 회고, 지식 정리 | Voyager, GITM, ExpeL, Generative Agents |
| 대화 (`gemini-3.8-live`) | 스트리밍 | 한국어 음성, 비동기 도구 호출로 컨트롤러에 위임 | PUBG Ally, Convai, SIMA 2 대화 |
| 인지 컨트롤러 | 이벤트 기반 + 5Hz | 목표·의도를 혼자 결정하고, 말과 행동에 함께 전달 | Project Sid PIANO의 Cognitive Controller |

---

## 2. 유사 사례

표의 머리말 기호:
- (a) 동시 대화 · (e) 선제 발화
- (b) 목표 분해 · (c) 인터럽트
- (d) 학습
- (f) 행동 인터페이스
- (g) 지연·주기
- (h) 공개 여부

### 2.1 연구·범용 에이전트

| 항목 | 날짜 | (f) 인터페이스 | (a)(e) 대화·선제 발화 | (b)(c) 목표 분해·인터럽트 | (d) 학습 | (g) 지연·주기 | (h) 공개 |
|---|---|---|---|---|---|---|---|
| SIMA | 2024-03 | 픽셀 → KB/M | 없음(지시만 받음) | 약 10초짜리 지시 실행 | 여러 게임 행동 복제 | 미공개 | 비공개 |
| SIMA 2 | 2025-11 | 픽셀 → 구조화 텍스트 → KB/M | 한 출력에 대화·추론·행동이 함께. 완료하면 먼저 보고 | Gemini 추론으로 고수준 목표 분해 | Task Setter + Reward Model로 자기개선 | 미공개(저지연을 위해 짧은 컨텍스트) | 제한적 프리뷰 |
| Voyager | 2023-05 | Mineflayer JS 코드 | 없음 | 자동 커리큘럼, 실패하면 반복 프롬프트 | 코드 스킬 라이브러리 + 자기검증 | LLM 호출 단위(수 초) | MIT |
| Mindcraft / MineCollab | 2024~ / 2025-04 | Mineflayer 명령(+선택적 코드 생성) | 채팅·TTS. self-prompt 중에 사용자가 말하면 1회 응답 | `!goal` 루프. `modes`가 진행 중 행동을 끊음 | `memory.json` | 300ms 루프, 2초 쿨다운 | MIT |
| Project Sid (PIANO) | 2024-10 | Minecraft 스킬 실행 모듈 | Talking 모듈이 Controller 결정을 따름 | 동시 실행 모듈 + 목표 생성 | 메모리, Action Awareness | 모듈마다 다름 | 논문만 공개 |
| Odyssey | 2024-07 | Mineflayer 스킬 223개 | 없음 | planner / actor / critic | 위키 QA로 LLaMA-3 미세조정 | – | 코드 MIT, 데이터 비상업 |
| GITM | 2023-05 | 구조화 액션 | 없음 | 목표 → 하위 목표 → 액션 | 텍스트 지식·메모리 | – | 제한적 |
| JARVIS-1 / JARVIS-VLA | 2023-11 / 2025-03 | 픽셀 → KB/M | 없음 | 계획 + 자기점검 후 재계획 | 멀티모달 메모리 / ActVLP | – | VLA 공개 |
| Optimus-1/2/3 | 2024-08 ~ 2025-06 | MLLM 플래너 + 저수준 정책(GOAP) | 3편은 임바디드 QA | 지식 그래프 기반 계획 | HDKG + AMEP + Reflector | – | 일부 공개 |
| VPT / STEVE-1 | 2022-06 / 2023-06 | 픽셀 → KB/M | 없음 | 짧은 텍스트 지시 | IDM 의사라벨 행동 복제 | 20Hz | 공개 |
| Cradle | 2024-03 | 스크린샷 → KB/M 코드 | 없음 | 과제 추론 + 자기반성 | 스킬 큐레이션 | 실시간 게임은 일시정지 | MIT |
| Lumine | 2025-11 | 5Hz 관측 → 30Hz KB/M | 없음 | 필요할 때만 추론 | 추론 기록을 장기 맥락으로 보존 | 첫 행동 114ms(추론 시 234ms) | 비공개 |
| Game-TARS | 2025-10 | 통합 KB/M 원시 동작 | 지시 수행 | Sparse Thinking | 압축한 사고 기록(2단 메모리) | 행동 간격 50–100ms | 비공개 |
| NitroGen | 2025-12 | 256×256 픽셀 → 게임패드 | 없음 | 없음(빠른 반응용 system-1 모델) | 영상 40,000시간 행동 복제 | 미기재 | 비상업, Windows 전용 |
| Muse/WHAM | 2025-02 | 월드모델(프레임 + 패드 입력 생성) | 없음 | 없음 | – | 10Hz, 실시간 부적합 | MSR 라이선스, 에이전트 용도 금지 |
| Parallelized Planning–Acting | AAMAS 2026 | Mineflayer 스킬 | 팀 채팅 | 계획/행동 스레드 분리 + interrupt flag | 중앙 메모리, 의존성 DAG | 계획 지연을 실행 시간 뒤에 숨김 | 코드 미확인 |

### 2.2 산업 NPC·Valheim 프로젝트

| 항목 | 날짜·상태 | (f) 인터페이스 | (a)(e) 대화·선제 발화 | (b)(c) 목표 분해·인터럽트 | (d) 학습 | (g) 지연 | (h) 공개 |
|---|---|---|---|---|---|---|---|
| Player2 AI NPC (Minecraft) | 2025~, v1.4.0 (2026-07) | PlayerEngine(Baritone 경로탐색 + ChatClef 태스크) | Player2 앱의 STT(누르고 말하기)/TTS/LLM | 자연어 목표 → 다단계 계획 | 미기재 | 미기재 | 모드 MIT |
| PUBG Ally | 베타 2026-06-17 ~ 07-01 | 행동 트리(틱) + 2B SLM 툴 호출 | 음성, 선제 응답 | SLM = 의도·전략, 행동 트리 = 즉각 전투 | 매치 간 장기 메모리 | 미공개, VRAM 8GB | 상용 |
| inZOI Smart Zoi | 2025-03 얼리액세스 | 온디바이스 0.5B SLM | 내적 독백을 화면에 노출 | 생활 목표에 따른 자율 행동 | 하루 끝 자기성찰 | – | 상용 |
| NARAKA AI 팀원 | 2025-03 | 온디바이스 ACE | – | 전투·아이템·장비 | – | – | 상용 |
| Ubisoft Teammates | 2025-11 | Snowdrop + Gemini [2차] | 음성 지휘, 어시스턴트 Jaspar | 지시 + 맥락 반응 | – | 최대 수 초 [2차] | 비공개 |
| Convai | 2025~26 | SDK 액션(Move To, Follow 등) | 반응형/추론형 이중 마인드, 상태 변화를 스스로 내레이션 | – | 장기 메모리, 내적 독백 | "1초 넘으면 느림" | 상용 |
| Inworld | Runtime 2025-08 | STT/LLM/TTS 그래프 런타임 | 음성 파이프라인 | – | 장기 메모리 | TTS P90 130/250ms [2차] | 상용 |
| MS Gaming Copilot | 베타 2025-08, 콘솔 2026 | 스크린샷 이해(게임 조작은 확인 안 됨) | 음성 모드 | – | – | – | 상용 |
| VikingNPC / Norsemen | 2024~, Continued 0.4.1 | `MonsterAI`/`Humanoid` 파생 | 무작위 대사(YAML) | `UpdateAI` 우선순위 캐스케이드 | – | – | LICENSE 없음 |
| Offline Companions / Reborn | 2026-02~05 / v1.4.52 | `BaseAI` 경로탐색 + CompanionAI | 미리 녹음된 대사 | 전투 스탠스·작업 모드 | 스킬 레벨 | – | MIT |
| Thrall | 2024-09, 지원 종료 | Jotunn + OpenAI | 음성 PTT, Cartesia TTS | 명령형 | – | – | 독점 |
| Fylgja | v0.1.0 | Ollama 등 지원. 게임 브리지는 미구현 | 텍스트 채팅 | `/f` 명령 + 자연어 | 대화 메모리 | 30초 타임아웃 | MIT |
| ValheimAI | 초기 골격 | 두 번째 Steam 계정 + WebSocket 브리지 | 채팅 명령 | LLM은 고수준 목표, 실행은 결정적 코드 | – | – | 미확인 |
| open-valheim-bot | 2026-09 이후 [추정] | 픽셀 입력, Luna + OpenJev 0.8B(Mac) | 캐릭터 대사 | – | 월드별 메모리 | – | MIT |
| ValheimMCP | 2026 | MCP(콘솔 명령 + 카메라) | – | – | – | – | MIT |

### 2.3 항목별 노트

#### DeepMind SIMA / SIMA 2 / Genie 3

**SIMA (2024-03-13)** [공식]
- 입력은 화면과 자연어, 출력은 KB/M이다.
- 기본 스킬 600개로 약 10초짜리 과제를 다룬다.
- 대화나 목표 분해 기능은 없다.
- Valheim이 포함됐다는 근거는 1.1절에 있다.

**SIMA 2 (블로그 2025-11-13, TR 2025-12-04)** [공식]

| 측면 | 내용 |
|---|---|
| 구조 | Gemini Flash-Lite에 SFT와 RL을 적용 |
| 출력 | 정해진 형식의 구조화 텍스트. 파싱해서 KB/M 입력(키 96개, 클릭, 이산화된 마우스 이동)과 대화·내부 추론으로 나눈다 |
| 학습 환경 | Valheim 포함 |
| 학습하지 않은 평가 게임 | ASKA(바이킹 서바이벌), MineDojo, The Gunk, Genie 3 생성 세계 |
| 성과 | 학습 환경 성공률이 SIMA 1의 "사실상 2배". 평가 게임마다 10%p 이상 상승. 언론 보도 수치는 서로 맞지 않으므로 TR 원문 그림을 기준으로 본다 |
| 대화 | 요청을 확인하고, 과제를 마치면 먼저 알리고, 직접 돌아다니며 질문에 답한다(임바디드 QA) |
| 자기개선 | Gemini가 과제를 만들고(Task Setter), Gemini 보상 모델이 0–100 루브릭으로 채점 |
| 스스로 밝힌 한계 | 장기 과제, 짧은 메모리, KB/M 정밀 조작 |

**Genie 3 (2025-08-05)** [공식]: 24fps로 도는 실시간 월드모델이다. 그 안에서 SIMA를 시험했다.

2026년 후속작(SIMA 3 등)은 찾지 못했다.

#### Minecraft 에이전트

**Voyager (2023-05, MIT)** [공식]
- GPT-4가 Mineflayer 코드를 생성해서 행동한다.
- 자동 커리큘럼, 코드 스킬 라이브러리, 실행 오류와 자기검증을 반영하는 반복 프롬프트를 쓴다.
- 고유 아이템을 3.3배 더 얻었고, 테크트리를 최대 15.3배 빨리 올렸다.

**Mindcraft (MIT, 현재 mindcraft-bots 조직) + MineCollab (2025-04)**
- `modes` [코드]
  - `interrupts: all`인 모드: self_preservation, unstuck, cowardice, self_defense.
  - hunting, item_collecting 등은 `action:followPlayer`만 끊는다.
  - 매 틱 우선순위가 가장 높은 모드 하나만 켜진다.
  - 행동이 끊기면 "(AUTO MESSAGE) 이전 행동이 중단됨"을 LLM에 다시 보낸다. 유휴 1초 후에는 `resumeAction`을 호출한다.
- self-prompter [코드]
  - 매 턴 "명령을 반드시 포함하라"고 스스로 프롬프트한다.
  - 쿨다운은 2초다. 명령 없는 응답이 3번 나오면 멈춘다.
- TTS, 비전 모델, Ollama를 지원한다.
- MineCollab [공식]: 상세 계획을 말로 주고받게 하면 성능이 최대 15% 떨어진다.
- 커뮤니티 로컬 모델: Andy-4.2(2026-03, 9B) [커뮤니티].

**Project Sid / PIANO (Altera, 2024-10-31)** [공식]
- 상태가 없는 모듈들이 공유 Agent State를 읽고 쓰며 동시에 실행된다.
- Cognitive Controller가 정보를 좁혀서 받는 병목 역할을 하고, 결정을 다른 모듈에 방송한다.
  - 특히 Talking 모듈을 강하게 조건화해서 말과 행동이 어긋나지 않게 한다.
- Action Awareness 모듈은 기대한 결과와 실제 관측을 비교한다.
- 반사 모듈은 LLM이 아니라 작은 신경망이다. 주 모델은 GPT-4o다.
- 저장소에는 보고서만 있고 코드는 없다.

**기타 연구** [공식]
- Odyssey (IJCAI'25): 스킬 223개, 위키 QA 390k+로 LLaMA-3 미세조정. 코드는 MIT, 데이터는 CC BY-NC-SA.
- GITM: 목표 → 하위 목표 → 구조화 액션으로 분해한다. ObtainDiamond 성공률이 47.5%p 올랐다.
- JARVIS-1: 멀티모달 메모리로 200개 이상 과제를 수행한다.
- JARVIS-VLA: 원자 과제 1,000개 이상을 다루며 코드·모델·데이터를 공개했다.
- Optimus 시리즈:

  | 편 | 핵심 |
  |---|---|
  | Optimus-1 | 지식 그래프(HDKG), 경험 풀(AMEP), 경험 기반 Reflector |
  | Optimus-2 | MLLM 플래너 + GOAP 정책 |
  | Optimus-3 | MoE + 추론 강화 RL |

- VPT: 20Hz KB/M. IDM으로 영상에 행동 라벨을 붙였다.
- STEVE-1: MineCLIP 목표로 지시를 따르게 했다. 컴퓨트 비용은 $60.

**Player2 AI NPC (MIT, 2026-07-17 업데이트)** [모드 페이지]
- "뇌"는 Player2 앱이다. STT·TTS·LLM을 무료 게이트웨이로 제공한다.
- "몸"은 PlayerEngine이다. Baritone 계열 경로탐색에 ChatClef(AltoClef 기반) 태스크 시스템을 얹었다.
- V키를 누르고 말한다. "상자 만들 나무" 같은 다단계 목표를 처리한다.

**기타** [2차]: Altera는 GPT-4o 기반의 "친구 같은" Minecraft 동반자 제품을 목표로 했다. 2026년 상태는 확인하지 못했다.

#### 범용 3D 게임 에이전트

- **Cradle (2024-03, ICML'25, MIT)** [공식]
  - 6개 모듈 구조로 RDR2에서 40분짜리 미션을 수행했다.
  - 실시간 게임은 LLM 지연 때문에 일시정지해야 한다.
- **Lumine (2025-11-11)** [공식]

  | 측면 | 내용 |
  |---|---|
  | 구조 | Qwen2-VL-7B. 학습 데이터 1,731시간 → 200시간 → 15시간의 3단계 |
  | 속도 | 5Hz로 보고 30Hz로 행동(200ms마다 33ms 행동 청크 6개). 첫 행동까지 114ms. 최적화로 25.3배 빨라짐 |
  | 성과 | 원신 5시간 스토리를 완주. 다른 게임에서도 추가 학습 없이 작동 |
  | 한계 | 대화 기능 없음. 처음 보는 적 패턴에서 성능 하락. 가중치 비공개 |

- **Game-TARS (2025-10-27)** [공식]
  - mouseMove / mouseClick / keyPress로 행동 공간을 통일했다.
  - 결정적 순간에만 추론한다(Sparse Thinking).
  - 압축한 사고 기록으로 2,000스텝 이상의 맥락을 유지한다.
  - 행동 간격은 50–100ms다. 비공개다.
- **NitroGen (2025-12 공개, arXiv 2026-01, CVPR'26)** [공식]
  - SigLIP2와 DiT를 합친 약 0.5B 모델이고, 게임패드 입력을 낸다.
  - README가 스스로 "빠르게 반응하는 system-1 모델이며 장기 계획은 못 한다"고 밝힌다.
  - 가중치는 비상업 라이선스이고, Windows에서만 돈다.
- **Muse/WHAM (2025-02, Nature)** [공식]: 300×180 해상도, 10Hz다. 모델카드가 실시간 사용과 에이전트 플레이를 범위 밖으로 명시한다.
- **2026년 주목할 것** [공식, 날짜는 arXiv ID 기준]
  - MAIN-VLA: Minecraft·Valorant.
  - Proact-VL: 실시간 동반자가 "언제 말할지" 스스로 정한다.
  - GameWAM: 미래 프레임과 KB/M 행동을 함께 생성한다.
  - 서베이: "추론 vs 반응성" 딜레마를 정리했다.

#### 산업 NPC·AI 팀원

**NVIDIA ACE (CES 2025)** [공식]
- 지각·인지·행동·메모리(RAG)의 4계층이다.
- 인지에는 Minitron 8B/4B/2B를 쓴다.
- "게이머는 초당 8–13번 미시 결정을 한다"고 설명한다.

**PUBG Ally** [공식: Krafton 보도자료, NVIDIA 개발자 블로그 2026-06-25]

| 측면 | 내용 |
|---|---|
| 모델 | Mistral-NeMo-Minitron-2B + ASR + 자체 TTS, 모두 온디바이스. CES 2025 발표 때는 8B |
| 역할 분담 | 행동 트리(System 1): 이동·조준·즉각 전투. SLM(System 2): 의도 해석·협응·발화 |
| 관측 | SLM이 필요할 때만 툴로 상태를 가져온다. 평문(예: "M416, 24/30발, HP 78%")으로 받는다 |
| 최적화 | 지시문 앞부분을 고정해 KV 캐시를 재사용한다 |
| 메모리 | 매치 간 장기 메모리 |
| 교훈 | 맵 하나, 모드 하나로 범위를 닫은 덕분에 다룰 만했다 |

**inZOI Smart Zoi (2025-03-28) / NARAKA (2025-03-27)** [공식]
- Smart Zoi: 0.5B 모델로 내적 독백을 보여 주고, 하루가 끝나면 자기성찰로 일정을 조정한다.
- NARAKA: 온디바이스 AI 팀원이다.

**Ubisoft**
- NEO NPC (GDC 2024-03-19): Inworld와 Audio2Face를 썼다 [공식].
- Teammates (2025-11-21) [공식]: 음성으로 분대원을 지휘하고, 어시스턴트 Jaspar가 있다. 비공개 테스트는 수백 명 규모였다.
  - Gemini와 내부 미들웨어를 쓰고 팀이 80명이라는 보도가 있다 [2차].
  - 체험기에서 응답이 최대 수 초 지연됐다고 한다 [2차].

**Convai (2026-08-13)** [공식-벤더]
- 값이 바뀌는 속성만 실시간으로 밀어 넣는다(tracked properties).
- "대화가 유휴일 때만 말하기" 모드가 있다.
- 상태가 바뀌면 스스로 내레이션한다.
- "1초가 넘으면 느리게 느껴진다"고 밝힌다.

**기타**
- Inworld Runtime (2025-08-13): C++ 그래프 엔진이다 [공식].
- Gaming Copilot: 베타 2025-08, 음성과 스크린샷을 이해한다 [공식].
- Sony: 유출된 Aloy 프로토타입은 Whisper STT, GPT-4/Llama 3, 자체 TTS를 썼다 [2차]. "Ghost Player" 특허도 있다 [2차].

#### Valheim 전용

**배경** [2차]
- Valheim 1.0은 2026-09-09에 정식 출시됐고 Mac도 포함된다.
- 이 출시로 기존 모드가 한꺼번에 깨졌다(4.2절).
- 공개된 Valheim RL/Gym 환경은 찾지 못했다.

**VikingNPC/Norsemen** [코드]
- 클래스 구조
  - `public partial class VikingAI : MonsterAI`
  - `Viking : Humanoid, Interactable, TextReceiver`
- `UpdateAI(dt)`는 bool을 반환하며 다음 순서로 처리한다: 길들임 → 인벤토리 → 도망·불 회피 → 추종 → 작업 → 전투.
- 벌목 구현
  - `MoveTo(dt, tree.position, attackRange, false)` 다음에 `StartWork(axe)`를 호출한다.
  - `TreeBase.RPC_Damage`를 Harmony로 패치한다.
  - `TreeLog.m_dropWhenDestroyed` 드롭을 인벤토리에 바로 넣는다. 실제로 줍지 않으므로 사람과 다른 지름길이다. Thorkell은 이렇게 하지 않는다.
- Continued 포크가 1.0에 대응한다.

**Offline Companions (MIT)** [모드 페이지]
- `BaseAI` 경로탐색 위에 커스텀 CompanionAI를 얹었다. 끼임 감지가 있다.
- 방어 우선 전투: 막기, 패리, 스태미나를 고려한 후퇴.
- 채집·농사·제련을 하고, 상태는 ZDO에 저장한다. LLM은 없다.
- Reborn 포크가 1.0에 대응한다.

**레거시 계열** [모드 페이지]
- Friendlies Reloaded, RRR NPCs, MobAILib: 캐릭터의 내장 AI를 교체하고, Worker(제련로 연료 보급)와 Fixer(수리) AI를 붙인다.
- Cheb's Necromancy: 미니언이 벌목·채광을 한다.

**LLM을 붙인 Valheim 프로젝트**
- **Thrall (2024-09)** [모드 페이지/HN]: OpenAI, 음성 PTT, Cartesia TTS를 쓴다. 개발자 스스로 "still super janky"라고 했고, 지원이 끊겼다(Deprecated).
- **Fylgja** [코드]: Ollama/OpenAI 호환 API와 대화 메모리가 있다. 하지만 "game bridge is stubbed"라서 실제 NPC 제어는 구현되지 않았다.
- **ValheimAI** [코드]: 두 번째 Steam 계정을 쓰고, BepInEx → WebSocket → 컨트롤러로 연결한다. "LLM은 고수준 목표만, 이동·반복은 결정적 코드"라는 원칙이다. 추종·정지만 구현했다.
- **open-valheim-bot** [코드]: Apple Silicon 전용이다. Luna가 목표와 대사를, OpenJev 0.8B가 화면을 읽어 짧은 행동을 맡는다. 월드별 메모리가 있다.
- **ValheimMCP** [코드]
  - `127.0.0.1:8731`에서 MCP(JSON-RPC)를 제공한다.
  - 기능: 콘솔 명령 실행, 오프스크린 카메라 PNG, 로그 조회.
  - 구현: `Terminal.AddString` Harmony postfix + 메인 스레드 디스패처.
  - 인증이 없다.

#### 아키텍처 패턴

- **Generative Agents (UIST'23)**: 메모리 스트림 → 검색(최근성·중요도·관련성) → 반성 → 계획·재계획.
- **이중 시스템(느린 계획 + 빠른 실행)**

  | 사례 | 느린 쪽 | 빠른 쪽 |
  |---|---|---|
  | Figure Helix | 7B 모델, 7–9Hz | 80M 모델, 200Hz |
  | GR00T N1 | 10Hz | 120Hz |
  | Gemini Robotics 1.5 + ER 1.5 | ER: 계획·툴 호출·대화 지휘 | VLA: 실행 |

  - 게임에서의 대응물: PUBG Ally, Lumine, Game-TARS, open-valheim-bot.
- **LLM + 행동 트리/FSM**
  - FSE 2025: LLM이 행동 트리를 작성한다.
  - Aalto 논문: LLM은 "마음", FSM/행동 트리는 "몸".
  - PUBG Ally.
- **인터럽트할 수 있는 계층 실행**
  - Mindcraft `modes`.
  - Parallelized Planning–Acting: 단일 슬롯 버퍼 + interrupt flag. 의존성 DAG로 아이템 790개 이상을 자동 처리한다. 스킬 실행이 LLM 추론보다 길면 계획 지연이 숨겨진다.
  - DEPS‡, Inner Monologue‡.
- **경험 학습**
  - ExpeL: 경험에서 통찰을 뽑는다.
  - AutoManual: 규칙을 사람이 읽는 매뉴얼로 정리한다.
  - Optimus-1, Voyager.
- **호기심(내적 동기)**
  - ELLM, OMNI-EPIC.
  - MAGELLAN: 학습 진척을 예측해서 목표를 고른다.

### 2.4 Thorkell이 빌려올 것

| 층 | 주기 | 역할 | 빌려올 곳 |
|---|---|---|---|
| L0 몸(C#) | 매 틱 | 이동·공격·채집 원시 동작, 상태 노출 | VikingNPC, Offline Companions, ValheimMCP 디스패처, Eira |
| L1 반사 | 틱 | 자기보존·자기방어·후퇴·끼임 해소·줍기 | Mindcraft `modes`, PUBG Ally 행동 트리 |
| L2 스킬 | 수 초~분 | `ChopWood(n)`, `Craft`, `Fight`, `Flee`, `Goto`, `Deposit` | Voyager, Odyssey, 의존성 DAG |
| L3 인지 컨트롤러 | 이벤트 기반 0.2–1Hz | 의도를 정하고 말·행동에 함께 전달, 단일 슬롯 버퍼 | PIANO, Sparse Thinking, AAMAS'26 |
| L4 대화 | 스트리밍 | STT → 빠른 응답 → 느린 설명 → TTS | PUBG Ally, Convai, Proact-VL |
| 메모리 | 비동기 | 이벤트 로그 → 반성 → 규칙·도감·레시피 그래프 | Generative Agents, ExpeL, AutoManual |

1. **몸을 어떻게 만들지.** 조사 시점의 권고는 Humanoid/MonsterAI 기반 NPC로 빠르게 시작하고, 행동 API를 Player 의미 체계로 정의해 나중에 바꿀 수 있게 하는 것이었다 [추정].
   - **최종 결정은 "진짜 플레이어 봇"이다(6장).** 레시피 발견, 스태미나 같은 초심자 경험이 사람과 같아지기 때문이다.
2. **공정성.**
   - 드롭은 인벤토리에 바로 넣지 않고 실제로 줍는다. VikingNPC와 다르게 한다.
   - 콘솔·개발자 명령은 개발 도구로만 쓰고, 런타임에 Thorkell이 쓰는 툴에서는 뺀다.
3. **관측.**
   - PUBG Ally처럼 필요할 때만 툴로 가져오고, 결과는 평문으로 받는다.
   - 프롬프트 앞부분을 고정해 캐시를 재사용한다.
4. **인터럽트.**
   - 모든 스킬은 취소할 수 있고, 체크포인트에서 재개할 수 있고, 구조화된 결과를 돌려준다.
   - 반사층이 행동을 끊으면 "(AUTO) 벌목 중 공격받음 → 처치, HP 40%" 같은 이벤트를 위층에 올려 다시 계획하게 한다.
5. **말과 행동의 일관성.** 발화는 컨트롤러가 내린 결정에만 근거한다(PIANO). 대화층이 혼자 무언가를 약속하지 못하게 한다.
6. **목표 분해 예시: "나무 베어와".**
   - 수량은 현재 계획에 필요한 자재, 인벤토리, 운반 한도, 도끼 내구도, 시간대를 보고 정한다.
   - 도끼가 없으면 먼저 만들고, 벌목 후 돌아와 보고한다.
   - 모호함이 비용으로 이어질 때만 짧게 되묻는다.
7. **"다음엔 미리 준비".** 패배 후 반성해서 전제조건 규칙을 만든다(예: "검은 숲 진입 전에는 활·방어구"). 플래너가 비슷한 목표를 분해할 때 이 규칙을 앞 단계로 끼워 넣는다.
8. **처음 보는 몬스터.**
   - 내부 prefab 이름은 숨긴다.
   - 도감 항목은 hover 이름과 관측(필요하면 카메라 묘사)으로 만든다.
   - 사용자에게 묻거나 사용자 설명을 저장할 때는 출처와 신뢰도를 같이 기록한다.
   - 교전 통계로 항목을 갱신한다.
9. **먼저 말 걸기.**
   - 트리거: 첫 조우, HP 급락, 새 레시피, 밤 접근, 완료·실패.
   - 쿨다운을 두고, "대화가 유휴일 때만 말하기"를 지킨다.
   - 혼잣말과 사용자에게 하는 말을 구분한다.
10. **호기심.** 유휴 시간에 목표 후보를 만들고 새로움이나 학습 진척으로 점수를 매긴다. 안전 조건 안에서만 탐험한다.
11. **지연 예산.** LLM은 이벤트가 생길 때만 부른다. 음성은 체감 1초를 목표로 하되, 현실적인 측정치는 3.8절을 본다.
12. **개발 도구.** ValheimMCP 패턴은 재사용하되 인증을 추가한다.

---

## 3. 모델 동향 (2026-10 기준)

### 3.1 Gemini 라인업

| 모델 ID | 출시 | 특징 | 지연·가격 |
|---|---|---|---|
| `gemini-3.8-flash` | 2026-09-02 GA | 최신 Flash. thinking은 low/medium/high만 있고 minimal은 없다(minimal을 주면 오류, 2026-10-02 재확인). 함수 호출, 구조화 출력, 캐싱, Computer Use(Preview) 지원. 1M 컨텍스트. Live API 미지원 [공식] | $0.75/$3.75 per 1M(2026-12-31까지 도입가) [공식]. AA 측정 221 tok/s, TTFT 17.5초(10k 입력, 추론 포함) [3자] |
| `gemini-3.7-flash`, `3.6-flash`, `3.5-flash` | 2026년 8·7·5월 | 이전 세대 Flash | 3.5 Flash: $1.50/$9 |
| `gemini-3.5-flash-lite` | 2026-07-21 GA | 저가형 | $0.30/$2.50 |
| `gemini-3.1-flash-lite` | 2026-05 GA | 저가형. 기본 thinking minimal | $0.25/$1.50 |
| `gemini-3.1-pro-preview` | 2026-02 | 현재 Pro 플래그십. 3.5 Pro는 계속 지연, Gemini 4는 루머 단계 | $2/$12 |
| `gemini-3.8-live` | 2026-09-15 | 기본 Live 모델. 입력: 텍스트/이미지/오디오/비디오. 출력: 텍스트/오디오. 입력 131,072 / 출력 65,536 토큰 [공식] | TTFA 1.18초 [3자 AA]. 오디오 입력 $0.005/분, 출력 $0.018/분 [공식] |
| `gemini-3.8-live-extended-thinking` | 2026-09-15 | 말하면서 백그라운드로 추론. thinking low/med/high. NON_BLOCKING 도구만 허용 | TTFA 1.35초(High). Speech-to-Speech Index 82.6으로 1위 [3자] |
| `gemini-3.1-flash-live-preview` | 2026-03 | 구형. 비동기 함수 호출 미지원 | TTFA 약 3.0초 [3자] |
| `gemini-3.5-transcribe`, `-live` | 2026-09 | 스트리밍 STT, 85개 이상 언어, 화자 분리 | 스트리밍 WER 4.0% [공식] |
| `gemini-3.8-flash-tts`, `-flash-lite-tts` | 2026-09-24 GA | 각각 130개, 101개 언어 | 오디오 출력 $9 / $6 per 1M |
| `gemini-robotics-er-2-preview`, `-streaming-preview` | 2026-07 | 체화 추론 VLM. streaming 버전은 Live API 지원. 함수 호출, Computer Use 지원 | $1/$5(도입가) |
| Gemini Robotics 2, On-Device 2 (VLA) | 2026-07-30 | 로봇 제어용 VLA | 얼리액세스 파트너만. Mac에서 사용 불가 |

- Computer Use: `gemini-2.5-computer-use-preview-10-2025`는 종료됐다. 지금은 Gemini 3 계열과 `gemini-3.8-flash`의 내장 도구(Preview)로 제공된다 [공식].
- 2.5 계열: `gemini-2.5-flash-native-audio-preview-12-2025`는 9월 18일부터 기존 사용자만 쓸 수 있다 [공식].

### 3.2 Live API 세부와 2026-10-02 재확인 사항

**문서 기준(2026-10-01 조사)** [공식]

- **함수 호출**
  - 3.8 Live는 기본이 비동기(`behavior: NON_BLOCKING`)다.
  - 결과를 돌려줄 때 `scheduling`으로 `INTERRUPT` / `WHEN_IDLE` / `SILENT` 중 하나를 고른다.
  - 도구 응답은 자동으로 처리되지 않는다. 클라이언트가 직접 회신해야 한다.
  - Google Search 그라운딩은 함께 쓸 수 있다. 코드 실행과 URL context는 쓸 수 없다.
- **세션 한도**
  - 컨텍스트 압축이 없으면 오디오만 15분, 오디오+비디오 2분이다.
  - 연결 하나는 약 10분 유지된다. `GoAway` 메시지를 받은 뒤 세션 재개로 이어 간다.
  - 재개 토큰은 문서상 2시간 유효하다. changelog에는 "24시간 지속"이라는 언급이 있어 확인이 필요하다.
  - 슬라이딩 윈도우 방식의 컨텍스트 압축을 켜면 세션 길이 제한이 없어진다.
- **입출력**
  - 입력은 16kHz PCM16, 출력은 24kHz다. 비디오는 초당 1프레임 이하다.
  - VAD `silenceDurationMs`는 500~800ms를 권장한다.
- **한국어**: Live API 언어표에 한국어(`ko`)가 있다. 마케팅상으로는 97개 언어를 대화 중에 바꿀 수 있다고 한다.

**2026-10-02 공식 문서 재확인으로 바뀌거나 추가된 점** [공식]

| 항목 | 확인 내용 | Thorkell 대응 |
|---|---|---|
| 함수 호출 동작 | NON_BLOCKING이 기본이고, 함수마다 `behavior: BLOCKING`을 지정할 수 있다 | `ask_status`·`recall_knowledge`만 BLOCKING |
| proactive audio | **항상 켜져 있다.** 모델이 주입한 입력에 응답하지 않을 수 있다 | `speech_dropped`(5초 안에 전사가 없음)를 측정. 긴급 발화는 채팅에도 보낸다 |
| affective dialog | 제거됐다 | – |
| Live 모델 기능 | **structured output, 캐싱, `thinking_level` 없음** | 구조화가 필요한 일은 Flash가 맡는다 |
| `turn_complete=true` | **언제나 생성을 끊는다** | 대화 상태(floor)를 보고 주입한다. 맥락만 넣을 때는 `turn_complete=False` |
| `send_client_content` | 명시적 role로 세션 내내 쓸 수 있다 | 이벤트 주입에 사용 |
| 세션 | 연결 약 10분. 재개 핸들은 세션 종료 후 2시간 유효. 갱신 메시지에 `resumable` 플래그가 있다 | 핸들을 0600으로 저장. 재개가 실패하면 음성만 down |
| 도구 응답 형식 | Python 샘플은 `"scheduling"`을 `FunctionResponse.response` 안에 넣는다 | **SDK 버전을 고정하고 계약 테스트로 확인** |

### 3.3 Gemma (로컬용)

Gemma 4 [공식]
- 2026-04-02 출시, Apache-2.0.
- 크기: E2B, E4B, 26B-A4B(MoE, 활성 3.8B), 31B. 2026-06-03에 12B Unified가 추가됐다.
- 모든 크기가 함수 호출을 기본 지원한다. 오디오 입력(30초 이하)은 E2B, E4B, 12B만 된다.
- τ2 점수:

  | 크기 | τ2 |
  |---|---|
  | 31B | 76.9 |
  | 12B | 69.0 |
  | 26B-A4B | 68.2 |
  | E4B | 42.2 |
  | E2B | 24.5 |

- Gemma 3n은 Gemma 4 E 시리즈로 대체됐다.

### 3.4 Jev와 laya ("jev opensource laya"의 정체)

사용자가 말한 "jev"와 "opensource laya"는 둘 다 2026년 9월에 나온 "System One" 결정 모델이다. 둘 다 글을 생성하지 않는다. 텍스트로 된 상태를 받아 타입이 정해진 질문에 확률로 답한다.

**Jev (TypeSafe AI, 2026-09-15)**

| 측면 | 내용 |
|---|---|
| 질문 타입 | Choice(최대 255개 중 선택), Score(2~10단계 척도), Noul(참일 확률) |
| 학습 | 보정된 확률을 내도록 RLCD(보정용 강화학습)로 학습 |
| API [공식/커뮤니티] | `POST https://api.typesafe.ai/v1/systemone`. 모델 `jev-1.13.0` 또는 `jev-latest`. OpenRouter에서는 `typesafe/jev-1.13` |
| 요청 형태 [커뮤니티] | `{model, state, questions:{name:{type, instructions, criteria}}}` |
| 응답 형태 [커뮤니티] | `answers[name].{choice\|score\|noul, probabilities, confidence}` |
| 처리 한도 [커뮤니티] | 분당 1,200건 |
| 입력 | 텍스트만. 상태 32K, 요청 전체 64K 토큰까지 |
| 가격 | 입력 1M 토큰당 $0.042, 출력은 무료 |
| 지연 | 70~500ms(벤더 주장). OpenRouter 중앙값 175ms [3자] |
| Doom 데모 [3자 보도] | 스크린샷이 아니라 텍스트로 직렬화한 게임 상태를 넣어 초당 약 10번 결정. 결정당 0.114초, 시간당 약 $7 |
| 한계 | 산술과 개수 세기에 약하다("can't count, can't do date math" [커뮤니티]). 한국어 성능은 공개되지 않았다. laya 측은 Jev의 ECE를 0.246이라고 주장한다[laya PyPI, 벤더 주장] → 확률을 그대로 믿지 않고 임계값을 직접 보정한다 |
| Jevstiller (Apache-2.0) [커뮤니티] | Jev 응답을 학습해 로컬 소형 모델로 증류하는 프록시 캐시. CPU에서 중앙값 16ms, Jev와 일치율 99.45% |

**laya (Convai Innovations, 2026-09, Apache-2.0)**
- 설치는 `pip install laya`, 저장소는 GitHub `NandhaKishorM/laya`다.
- 개발사는 같은 비자기회귀 구조를 2025년에 arXiv에 먼저 공개했다고 주장한다.
- 체크포인트:

  | 체크포인트 | 기반 | 크기 | 언어 | 컨텍스트 |
  |---|---|---|---|---|
  | `convaiinnovations/laya` | ModernBERT-large | 421M | 영어 | 512토큰 |
  | `convaiinnovations/laya-multilingual` | mmBERT-base | 322M | 100개 이상 | – |
  | `convaiinnovations/laya-typed-decisions` | 파인튜닝 버전 | 421M | – | 1,024토큰 |

  - 컨텍스트 값은 PyPI 기준이다(2026-10-02 확인).
- 지연: T4 GPU에서 질문 하나에 32.8~39.5ms [공식]. M3 Max의 MLX에서 7.4~13.4ms [커뮤니티]. Apple GPU(MPS)를 지원한다.
- **핵심 주의점**
  - 베이스 모델을 그대로 쓰면(zero-shot) 정확도가 **0.362**로 거의 찍기 수준이다 [공식].
  - 도메인 데이터로 파인튜닝하고 temperature로 확률 보정을 해야 한다.
  - 옵션이 20개를 넘으면 정확도가 떨어진다.
- **Jev와 교체 가능** [PyPI, 2026-10-02]: `laya-serve`가 Jev wire protocol(`POST /v1/systemone`, 같은 응답 스키마)을 구현한다. 그래서 Jev에서 laya로 바꾸는 일은 base URL 변경이다.
- **학습 도구** [PyPI]
  - 데이터는 JSONL `{state, questions, answers}` 형식이다.
  - `python -m laya.train`으로 학습하고, `laya.calibrate`로 보정한다.
  - torch ≥2.14와 transformers 5.x가 필요하다. 그래서 두뇌 가상환경과 분리한다.
- **관련 프로젝트** [커뮤니티]: `DanielTea/laya-vision-stitch`
  - 구성: Qwen3.5 비전 인코더 + laya + Open-P2P 정책(LoRA) + Molmo-7B 느린 플래너(3~5초).
  - M3 Max에서 추론 중앙값 34.3ms, 스크린샷부터 입력까지 60.7ms.
  - README가 "기본적인 시각 이동 수준이지 일반 게임플레이가 아니다"라고 밝힌다. 실제 키 입력은 보내지 않는다.
- **다른 해석도 검토했다**
  - V-JEPA 2/2-AC(Meta 2025-06, 2.1은 2026-03-16): V-JEPA 2-AC는 행동 하나를 계획하는 데 약 16초가 걸린다. 빠른 제어에는 맞지 않는다.
  - LLaVA, Llama.
  - 결론: 사용자의 문구("jev opensource laya")와 정확히 맞는 실체가 있으므로 Jev와 laya로 판단했다.
  - 참고로 open-valheim-bot이 "OpenJev 0.8B"를 쓴다 [코드].

### 3.5 빠른 행동·VLA·게임 제어 모델

| 모델 | 날짜 | 입력 → 출력 | 주기·지연 | 크기 | 라이선스 | Apple Silicon에서 실용성 |
|---|---|---|---|---|---|---|
| NVIDIA NitroGen `nvidia/NitroGen` | 2025-12 공개, CVPR'26 | 256×256 화면 → 게임패드 | 공식 수치 없음. RTX 2080S에서 실시간 불가 [커뮤니티] | 493M | NVIDIA 비상업 | 낮음. 공식 실행 환경이 Windows 전용 |
| Open-P2P `elefantai/open-p2p` | 2026-01-08 | 화면 + (선택) 텍스트 → 키보드/마우스 | 20Hz, 50ms 미만 목표(RTX 5090/5080) | 150M~1.2B | 코드 MIT, 데이터 8,300시간 공개 | 중간. M3 Max에서 34ms 실증 [커뮤니티] |
| Lumine (ByteDance Seed) | 2025-11 | 5Hz 화면 → 30Hz 키/마우스 | 첫 행동 114ms(H20 4장, 텐서 병렬) | 7B | 학습 방법만 공개, 가중치 미공개 | 낮음 |
| Game-TARS / SIMA 2 | 2025-10 / 2025-11 | 화면 → 키/마우스 | – | – | 비공개 / 제한 프리뷰 | 사용 불가(SIMA 1은 Valheim을 학습에 사용) |
| GR00T N1.7 | 2026(N2는 연말 목표) | 이미지 + 언어 → 로봇 동작 | Jetson Thor에서 39.9ms(25Hz) | 3B | 코드 Apache-2.0. 가중치 라이선스는 자료마다 다름 | 낮음(CUDA 전용) |
| π0, π0-FAST, π0.5 (openpi) | 2025 | 로봇 | GPU 메모리 8GB 이상 | 약 3B | Apache-2.0 | 낮음(Ubuntu만 지원) |
| π0.6 / π0.7 | 2025-11 / 2026-04-16 | 로봇 | – | π0.7 약 5B | 가중치 미공개 | 사용 불가 |
| SmolVLA + `mlx-smolvla` | 2025-06 / 2026-09-05 | 로봇 | M5 Pro에서 50개 행동 묶음당 110.8ms(MLX) [커뮤니티] | 450M | Apache-2.0 | 높음. 단 로봇용 |
| V-JEPA 2-AC | 2025-06(2.1은 2026-03-16) | 영상 월드모델 기반 계획 | 행동 하나 계획에 약 16초 | – | – | 빠른 제어 부적합 |
| Jev / laya | 2026-09 | 텍스트 상태 → 타입 결정 | 70~500ms / 7~40ms | 비공개 / 322~421M | 상용 API / Apache-2.0 | 클라우드 / 높음 |

**결론** [추정]: Valheim에서 "빠른 행동 제어"는 다음 셋으로 나누는 것이 현실적이다.
- 모터와 반사는 C# 결정적 코드가 맡는다.
- 이산적 전술 선택은 Jev → laya가 맡는다.
- 픽셀 VLA는 보조 연구 주제로만 남긴다.

### 3.6 Apple Silicon 로컬 추론

**런타임**
- MLX 계열(`mlx-lm`, `mlx-vlm` 0.4.4)이 prefill이 가장 빠르다.
- Ollama는 0.19(2026-03-30)부터 MLX 백엔드를 쓴다. Qwen3.5-35B-A3B의 생성 속도가 58에서 112 tok/s로 올랐다는 보도가 있다 [3자].
- LM Studio는 MLX와 llama.cpp 엔진을 모두 쓴다. llama.cpp는 문법(grammar) 제약 디코딩을 지원한다.
- 참고 하드웨어: M5 Pro/Max 맥북프로(2026-03)의 메모리 대역폭은 307/460/614 GB/s다.

| 모델 | 출시 | Q4 메모리 | 도구 호출 지표 | Mac 속도 |
|---|---|---|---|---|
| Qwen3.5-4B / 9B | 2026-02~03 | 약 3GB / 5.5GB | BFCL-V4 50.3 / 66.1, τ2(9B) 79.1 [공식, 자체 보고] | 9B: M4 Pro에서 prefill 약 450, 생성 약 50 tok/s [커뮤니티] |
| Qwen3.5 / 3.6-35B-A3B | 2026-02 / 04 | 약 22GB | BFCL-V4 67.3 [공식] | M4/M5 Max에서 생성 70~112, prefill 약 1.8k tok/s [3자] |
| Qwen3.8-27B | 2026-08-14 | 약 17GB | OSWorld-Verified 84.3 [공식] | Max급에서 생성 약 20~30 tok/s [추정] |
| Gemma 4 E4B / 26B-A4B | 2026-04 | – | τ2 42.2 / 68.2 | E4B: M4 Pro에서 49~57 tok/s. 26B-A4B: M5 Max에서 생성 약 57 tok/s [커뮤니티] |
| gpt-oss-20b | 2025-08 | 약 16GB | Tau-bench Retail 54.8 [공식, 2025] | M4 Max에서 35~66 tok/s [커뮤니티] |
| Mistral Small 4 (`mistral-small-2603`), Ministral 3 | 2026-03 / 2025-12 | 119B MoE / 3~14B | 함수 호출 지원 | – |
| Llama 4.5 | 2026-06 보도 [단일출처] | 109B 이상 MoE | Maverick BFCL 37.3 | 권하지 않음 |

**BFCL 공식 리더보드(2026-04-12 갱신)**
- Qwen3.5와 Gemma 4는 아직 올라 있지 않다.
- 오픈 모델 상위권: GLM-4.6 72.4, Kimi-K2 59.1, xLAM-2-32b 54.7.
- 소형: Nanbeige4-3B 51.4, Qwen3-8B 42.6.
- Qwen3.5 점수는 자체 보고치라 직접 검증해야 한다.

**1초 이내 응답이 가능한지 [추정]**: 첫 토큰까지 시간 ≈ 새 프롬프트 토큰 수 ÷ prefill 속도다. 9B 모델을 M4 Pro에서 돌린다고 하면:

| 경우 | 시간 |
|---|---|
| 캐시 없는 1,000토큰 프롬프트 | 약 2.2초 |
| 시스템 프롬프트·도구 정의를 캐시하고 새 상태 200토큰만 넣음 | 약 0.45초 |
| 위 경우 + 40토큰짜리 도구 호출 생성 | 약 1.25초 |

1초 안에 넣으려면 4B급 모델, 프롬프트 앞부분 캐시, thinking 끄기, JSON 스키마 제약을 모두 써야 한다.

**메모리 기준 [추정]**: 게임 + 4B 빠른 뇌 + Whisper + TTS는 24~32GB면 된다. 27B 느린 뇌를 더하면 48~64GB가 필요하다. 이 Mac(24GB)에 Valheim 클라이언트 두 개를 띄우면 로컬 LLM은 4B급이 한계다.

### 3.7 한국어 실시간 음성 스택

**음성 인식(ASR)**

| 모델 | 한국어 | 지연·특징 |
|---|---|---|
| WhisperKit large-v3-turbo (Argmax, MIT) | 지원 | Apple Neural Engine에서 스트리밍. OpenAI 호환 로컬 서버 제공 [공식] |
| Apple SpeechAnalyzer (macOS 26 이상) | 지원 | 온디바이스 스트리밍, 무료, Swift 전용 |
| SenseVoice-Small | 지원 | 10초 오디오를 70ms에 처리 [공식] |
| Moonshine Voice (2026-02), tiny-ko | 지원 | MacBook Pro에서 Medium Streaming 107ms [3자] |
| Qwen3-ASR-0.6B / 1.7B (2026-01, Apache-2.0) | 지원 | 스트리밍은 vLLM(CUDA) 필요. MLX 지원은 미확인 |
| Parakeet-tdt-0.6b-v3, Canary-1b-v2 | **미지원** | 유럽 언어 25개만 |

**음성 합성(TTS)**

| 모델 | 한국어 | 특징 |
|---|---|---|
| Supertonic 3 (Supertone, 2026-04-29) | 지원(31개 언어) | 99M, CPU에서 매우 빠름. ONNX(Swift 등). 모델 OpenRAIL-M. 저장소가 2026-09-09에 아카이브됨 |
| Qwen3-TTS 0.6B / 1.7B (2026-01, Apache-2.0) | 지원(10개 언어) | 스트리밍 첫 출력 97ms(GPU) [공식]. Mac에서는 mlx-audio 또는 Argmax TTSKit(CoreML, 청크당 약 80ms) |
| Chatterbox Multilingual (MIT) | 지원(23개 언어) | 목소리 복제 |
| Fun-CosyVoice3-0.5B | 지원 | 양방향 스트리밍 약 150ms, CUDA 위주 |
| Kokoro-82M, Kyutai TTS, Sesame CSM | **미지원** | – |

**말 끊김 감지(VAD)·턴 감지**
- Silero VAD: 32ms 단위로 처리하고 CPU에서 돈다.
- Smart Turn v3/v3.2: 8MB, 23개 언어, 한국어 정확도 96.85%. CPU 12ms [공식], M5 Pro ONNX 36ms [커뮤니티].
- LiveKit 다국어 턴 감지기: 396MB, 한국어 포함, 추론 약 25ms. LiveKit Agents 1.5에는 적응형 끼어들기 감지(30ms)가 들어 있다.

**Full-duplex(동시에 듣고 말하는) 모델**
- Moshi, PersonaPlex: 영어만 된다.
- KRAFTON Raon-Speech-9B: 영어와 한국어를 지원하지만 비상업(CC BY-NC 4.0)이고 CUDA가 필요하다. Full-duplex 버전인 Raon-SpeechChat-9B는 HF 카드 기준 영어 대화만 된다.
- Qwen3-Omni-30B-A3B(Apache-2.0): 한국어 음성 입출력이 되지만 BF16 기준 약 79GB가 필요하다.
- Qwen3.5-Omni: API로만 제공된다. 첫 출력 235/435ms [공식].
- → 한국어로 쓸 수 있는 로컬 full-duplex 오픈 모델은 사실상 없다.

**프레임워크**
- Pipecat v1.6은 Gemini Live와 OpenAI Realtime을 지원한다.
- Pipecat의 `macos-local-voice-agents` 예제는 M 시리즈 Mac에서 음성→음성 800ms 미만이다(영어). 한국어로 쓰려면 Kokoro를 다른 TTS로 바꿔야 한다.

**부하 분산 [커뮤니티/추정]**: 게임과 모델이 GPU를 함께 쓰면 프레임이 떨어진다. ASR은 Neural Engine(WhisperKit, SpeechAnalyzer), TTS는 CPU(Supertonic)로 나누는 편이 좋다.

### 3.8 클라우드 음성 모델 비교

TTFA는 모두 [3자 AA] 측정이다.

| 모델 | TTFA | 가격 | 비고 |
|---|---|---|---|
| `gemini-3.8-live` | 1.18초 | 약 $1.4/시간 상한 | 비동기 도구 호출 기본, 한국어 지원 |
| OpenAI GPT-Live-1 (API 2026-09-10) | 1.24~1.34초 | $0.05/분 + 백엔드 모델 비용 | full-duplex |
| `gpt-realtime-2.1`, `gpt-realtime-2.1-mini` (2026-07-06) | 1.21초(2.1 High) | – | – |
| Grok Voice Think Fast 2.0 | 0.70초 | – | 가장 빠름 |

한국어 전용 벤치마크는 어느 모델도 찾지 못했다. 직접 비교 테스트가 필요하다.

### 3.9 조사 시점 권장 구성과 Thorkell의 선택

| | 완전 로컬 (Apple Silicon) | 로컬 + 클라우드 (**Thorkell 선택**) |
|---|---|---|
| (a) 빠른 뇌(1초 이내 반응, 도구 호출) | ① 모드 안 행동 트리·유틸리티 AI가 게임 틱 단위로 전투·추적·회피를 처리. ② 의도 → 스킬 선택은 Qwen3.5-4B(M4 Pro급)가 맡는다. thinking 끄기, JSON 스키마, 프롬프트 앞부분 캐시. ③ 선택: 느린 뇌가 매긴 라벨로 laya-multilingual을 파인튜닝 | 반사는 C#. 결정은 Jev이고, 결정 로그로 laya를 증류한다. 대화·의도는 `gemini-3.8-live`가 NON_BLOCKING 도구로 컨트롤러에 넘긴다 |
| (b) 느린 뇌(계획·회고·학습) | Qwen3.8-27B 또는 Gemma 4 31B/26B-A4B(메모리 64GB 권장) | `gemini-3.8-flash`(thinking low/medium/high). 대화에서 사실을 뽑는 일은 flash-lite가 한다 |
| (c) 음성 입출력 | Silero VAD + Smart Turn v3 → WhisperKit turbo → LM 스트리밍 → Supertonic 3 / Qwen3-TTS. 목표 0.8~1.5초 [추정] | `gemini-3.8-live` 세션 하나. 세션 재개와 컨텍스트 압축을 반드시 켠다 |

선택 이유:
- 24GB에 Valheim 클라이언트 두 개를 띄우면 로컬 LLM은 4B급이 한계다.
- Eira의 1.7B 모델은 목표 분해에 실패했다.
- 사용자가 Gemini 3.8, Jev, laya를 직접 지목했다.

---

## 4. 이 환경의 제약

### 4.1 하드웨어·툴 [로컬]

- **하드웨어**: Apple M4 Pro, RAM 24GB, macOS 26.2.
- **툴**: dotnet SDK 9.0.306, uv, `op`(1Password CLI), ffmpeg, bun/pnpm.
  - Ollama는 `qwen3:1.7b`만 받아져 있다.
  - Python은 Homebrew 3.14다. 두뇌는 uv로 3.13을 고정한다.

### 4.2 게임·모드 로더 [로컬 + 3자]

**게임**
- Valheim 1.0.16, network version 40, Unity 6000.0.75f1, Mono 백엔드. `Valheim.app`은 universal binary(x86_64 + arm64)다.
- 게임 언어 설정은 Korean이다(`com.coffeestain.valheim-steam` plist).

**모드 로더**
- 설치된 것: BepInEx 5.4.23.3(BepInExPack_Valheim 5.4.2333), Doorstop 4.4.0, HarmonyX 2.9.0.
- Valheim 1.0(2026-09-09) 출시로 모드가 한꺼번에 깨졌다. BepInExPack 5.4.2350과 Jotunn 2.30.0이 출시 당일 다시 빌드됐다 [3자].
- macheim의 Thunderstore 캐시에는 BepInExPack **5.4.2351**(2026-09-24 게시)과 5.4.2350이 있다 [로컬].
- **모드를 켜고 실행하려면 Rosetta(x86_64)가 필수다.**
  - doorstop은 `libdoorstop_x64.dylib`만 제공한다.
  - BepInEx의 Harmony/MonoMod는 x86_64에서만 돈다 [로컬: macheim 문서·Eira 기록].
  - 실행 명령: `arch -x86_64 env DOORSTOP_ENABLED=1 DOORSTOP_TARGET_ASSEMBLY=… DYLD_LIBRARY_PATH=… DYLD_INSERT_LIBRARIES=…/libdoorstop_x64.dylib …/Valheim.app/Contents/MacOS/Valheim`
  - **DYLD 변수는 `arch` 뒤에 둬야 한다.** macOS가 `/usr/bin/arch`를 거칠 때 DYLD 변수를 지우기 때문이다.

**사용자의 실제 설치 상태**
- 대형 모드팩(EpicLoot, Therzie 계열, WackyEpicMMO 등)이 들어 있지만 1.0에서는 깨졌을 가능성이 높다.
- 마지막 세션(2026-09-26)은 BepInEx 없이 바닐라로 실행했다. "helloworld"를 **crossplay(PlayFab)** 로 호스팅했고, 원격 친구가 최대 3명 접속했다.
- 이전 Eira 플러그인(`BepInEx/plugins/ValheimCompanion/ValheimCompanion.dll`)이 실제 설치에 남아 있다.
  - Eira 조사: 9/11 Dverger 버전 v0.1.0이다.
  - 설계 조사: `-companion-bot`과 0.221.12를 요구하므로 지금은 비활성으로 판단했다.
  - 실제 동작은 재확인이 필요하고, 제거는 사용자 동의를 받은 뒤에만 한다.
- 1.0 월드 세이브는 chunk 단위다(`worlds/<name>/*.chunk`, 약 1.02M ZDO). 백업할 때 chunk 디렉터리를 포함해야 한다.

### 4.3 네트워크·접속 (1.0.16 메타데이터와 IL로 확인) [로컬]

**네이티브 자동 접속**
- `FejdStartup.ParseArguments`가 `-joinserverwithcharacter <ip:port> <profileFile>`를 처리한다. 동작은 `SelectCharacter(file, FileSource.Local)` → `JoinServer()`다.
- IP로 접속할 때는 `ZPlayFabMatchmaking.FindHostByIp`를 먼저 시도하고, 그다음 `ZNet.SetServerHost(ip, port, Steamworks)`를 쓴다.
- `-savedir`은 전용 서버만 읽는다. 그래서 봇 플러그인이 `Utils.SetSaveDataPath`를 직접 호출해야 한다.
- `-password`도 있지만 `ps`에 보이므로 쓰지 않는다.

**호스트가 접속을 받는 방식**
- `ZNet.OpenServer`는 `m_hostSocket`을 정확히 하나 만든다. `ZSteamSocket`(P2P) 또는 `ZPlayFabSocket`이다.
- 새 Steam 연결은 어느 listen 소켓으로 들어오든 `ZSteamSocket.OnStatusChanged`가 정적 `ZSteamSocket.m_hostSocket`으로 보낸다.
- `CheckForIncommingServerConnections`가 `Accept()` → `new ZNetPeer(s, false)` → private `OnNewConnection(peer)`를 처리한다.

**`ZNet.RPC_PeerInfo`**
- 플레이어 중복은 Steam ID가 아니라 세션 UID로 거른다. 그래서 같은 계정의 두 클라이언트도 이 단계는 통과한다.
- Steam 세션 티켓 검증은 `m_onlineBackend == Steamworks`일 때만 한다.
- **PlayFab 백엔드(crossplay)에서는 null 검사 없이 `ZPlayFabSocket.m_remotePlayerId`를 읽는다.** 그래서 Steam-IP 루프백 피어가 들어오면 NRE가 난다.

  ```
  937 isinst ZPlayFabSocket
  948 ldfld ZPlayFabSocket::m_remotePlayerId   // NRE for a ZSteamSocket peer
  967 call PlayFabManager::CheckIfUserAuthenticated
  ```

- 플레이어가 10명 이상이면 접속을 거부한다.

**대응 (Thorkell.Host)**
- crossplay가 꺼져 있으면: `CreateListenSocketIP(127.0.0.1:54880)`만으로 네이티브 라우팅이 처리한다.
- crossplay가 켜져 있으면:
  - 루프백 리스너에서 accept한다.
  - `RPC_PeerInfo` prefix와 finalizer로 **루프백 피어일 때만** `m_onlineBackend=Steamworks`를 잠시 설정한다.
  - self-test가 실패하면 리스너를 닫고 HUD로 안내한다.

**Eira 기록 [로컬]**
- 같은 Steam 계정의 두 프로세스끼리는 Steam P2P가 안 된다. 그래서 Steam 인증 루프백 IP 리스너(테스트 포트 127.0.0.1:54879)로 해결했다.
- `-nographics`를 쓰면 월드 시간이 멈춘다. 요리가 끝나지 않는다.
- 두 번째 Steam 계정을 쓰려면 두 번째 Steam 클라이언트가 필요한데, macOS 사용자 하나로는 돌릴 수 없다.

### 4.4 격리 [로컬]

- **prefs 공유**: prefs는 `~/Library/Preferences/com.coffeestain.valheim-steam.plist`에 bundle id 기준으로 저장된다. 그래서 `Valheim.app`을 APFS로 복제해도 사람 게임과 **같은 파일**에 쓴다. 봇에서는 `PlatformPrefs`/`PlayerPrefs` 쓰기를 no-op으로 만든다.
- **Steam Cloud**: `JoinServer`는 최근 서버 목록도 쓰는데, 이 목록은 Steam Cloud와 동기화된다.
- **봇 쪽 처리**
  - 클라우드 getter를 false로 만든다.
  - `SetupSymbolicLink`을 건너뛴다.
  - `-logFile`을 별도로 지정한다.

### 4.5 상호작용 모델과 확인된 호출 경로 [로컬]

**상호작용 모델**
- `Player.FindHoverObject`(상호작용 대상)와 `Player.PieceRayTest`(건축 위치)는 눈이 아니라 `GameCamera.instance.transform`에서 레이를 쏜다. 거리는 `m_eye` 기준으로 `m_maxInteractDistance` / `m_maxPlaceDistance`와 비교한다.
- Use, 핫바, 배치(건축 모드의 `Attack`), 제거, 회전은 `Player.Update` / `UpdatePlacement`에서 `ZInput`(assembly_utils.dll의 static)으로 읽는다.
- `TakeInput`은 열린 패널, 사망, 텔레포트를 검사하지만 **창 포커스는 검사하지 않는다.** 그래서 batchmode 봇에서도 가상 입력이 통한다.

**확인된 네이티브 호출 경로**

| 기능 | 경로 |
|---|---|
| 제작 | `InventoryGui.OnCraftPressed → UpdateRecipe → DoCrafting` |
| 건축 | `UpdatePlacement → TryPlacePiece → PlacePiece` → `ConsumeResources`, 망치 내구도, 스킬 상승 |
| 까마귀·룬스톤 | 둘 다 `Player.AddKnownText`로 들어감 |
| 튜토리얼 | `Tutorial.SpawnRaven → Raven.AddTempText` |
| 스킬 | `Skills.RaiseSkill → Player.OnSkillLevelup` |
| 발견 | `Player.OnInventoryChanged → AddKnownItem` |
| 데미지 텍스트 | `DamageText.ShowText`. 호출하는 곳: `Character.ApplyDamage`, `Humanoid.BlockAttack`, `TreeBase`·`TreeLog`·`MineRock5`·`Destructible`의 `RPC_Damage`, `MineRock.RPC_Hit`, `WearNTear` |

### 4.6 1.0.16 API 변화 (Eira 0.221.12 대비) [로컬]

**컴파일이 깨지는 변화**
- **`FileHelpers.CloudStorageEnabled`가 삭제됐다.** Eira 하네스가 이것을 패치하므로 그대로 쓰면 예외가 난다.
  - 1.0.16에는 `CloudStorageSupported`, `CloudStorageSupportedAndEnabled`, `CloudAndLocalStorageSupported`가 있다(assembly_utils.dll).
  - `FileHelpers.FileSource`는 flags enum이다(Auto=1, Local=2, Cloud=4, Legacy=8).
- **`Inventory.AddItem(name, stack, quality, variant, crafterID, crafterName, cheated, pickedUp=)`** 에서 `cheated`가 필수가 됐다. Eira fixture 호출은 컴파일되지 않는다.

**바뀌었지만 기본값 덕분에 컴파일되는 것**
- `Player.SetControls(Vector3, bool 11개, dodge=)`
- `PlacePiece(..., doAttack=, cheated=)`
- `AddKnownBiome(BiomeSector)`(새 타입)
- `CraftingStation.GetLevel(checkExtensions=)`
- `MessageHud.ShowMessage`(인자 6개)
- `Minimap.AddPin(..., author=)`
- `Humanoid.Pickup(go, autoequip=, autoPickupDelay=)`

**새 enum 값**
- `Biome.DeepNorth`
- `PlacementStatus.DeepSnow/NoSnow`
- `PieceCategory.DeepNorth/Feasts/Food/Meads`
- 새 `HitType` 값
- → switch마다 default 분기가 필요하다.

**아직 남아 있는 것**: Eira가 리플렉션으로 쓰던 private 멤버 대부분이 그대로 있다(`IsFireLit`, `RepairOneItem`, `LoadMainScene`, `m_hostSocket`, `GetVersionString`). 단, 문자열 표만 보고 확인한 것이라 시그니처까지는 검증하지 못했다.

---

## 5. 이전 시도 Eira에서 얻은 교훈

Eira: `~/Desktop/project/valheim/valheim-companion`, 2026-09-11~13, Valheim 0.221.12 [로컬].

**구조**
- 두 번째 Valheim 클라이언트에 진짜 Player("EiraBot")로 접속시키고, BepInEx 플러그인이 `Player.SetControls`로 조종했다.
- 이유: 0.221.12에서는 같은 클라이언트 안에 로컬 소유 `Player`가 `m_localPlayer` 말고 또 있으면 `Player.FixedUpdate`가 파괴한다.
- 처음 만든 Dverger 크리처 NPC는 배고픔을 가짜로 만들어야 했고 모든 클라이언트에 prefab을 등록해야 해서 폐기했다.

**통신과 모델**
- 브리지: UDP JSON 20Hz(관측 ↔ 명령), 토큰·세션·틱 검증. 300ms 동안 명령이 없으면 정지한다.
- 모델: Ollama `qwen3:1.7b` 하나.
  - 결정 2,405건: p50 0.53초, p90 0.65초, p99 0.69초, 최대 1.65초.
  - 결정의 **33%가 선택지 1개**였다. 즉 목표 분해는 손으로 짠 상태머신이 했고, LLM은 사실상 타깃만 골랐다.

**검증 결과**
- 기본 동작, 벌목, 수리, 사냥·요리·납품 40개, 20분 평가(Wood 70개, 결정 788건)를 통과했다.
- 단, 20분 평가는 스크립트로 움직이는 파트너와 디버깅에 이미 쓴 시드였다. 홀드아웃 증거가 아니다.
- **31회 중 23회 실패.** 원인은 다음과 같다.
  - 내비게이션 정체 6회(물가·해안·쉼터 주변, 수영 미해결)
  - 고기를 못 찾거나 음식 체인이 막힘 약 5회
  - qwen의 빈 tool call(JSON 스키마 재시도 유발)
  - 쓰러지는 통나무에 깔려 사망
  - 리더 사망·리스폰
  - 납품 불일치: 봇은 50개를 떨어뜨렸다고 셌지만 호스트는 10개를 받았다. `DropItem`이 시선 방향이 아니라 몸이 향한 방향으로 던지기 때문이다.
- 처음 보는 시드(`EiraCurriculum3`)에서 처음 실행했을 때 작업대에 도달하지 못해 실패했다.

**구현되지 않은 것**: 제작, 건축, 상자, 일반 전투, 음성, 비전, 장기 지식, 선제 발화, 재시작 후 복구, 실제 사람과의 공동 플레이 검증.

**반복하지 말 것**

| # | 하지 말 것 | 이유·대안 |
|---|---|---|
| 1 | 크리처 NPC로 몸 만들기 | 진짜 플레이어가 아니라 배고픔을 흉내 내야 함 |
| 2 | 같은 클라이언트에 두 번째 `Player` 생성 | 게임이 파괴함 |
| 3 | Unity `JsonUtility`로 중첩 데이터 처리 | 중첩 필드를 잃음 → `DataContractJsonSerializer`. `[Serializable]` 기본값도 선택 필드가 없을 때 파싱을 깨뜨렸음 |
| 4 | `-nographics` | 월드 시간이 멈춤 |
| 5 | 같은 계정 Steam P2P | 실패함 |
| 6 | 볼록하지 않은 메시에 `Collider.ClosestPoint` | 오류와 가짜 0거리 타깃 |
| 7 | 선택지에 문자열 ID 사용 | 모델이 빈 답을 냄 → 정수 인덱스 스키마 |
| 8 | 통나무 움직임 임계값을 0.3으로 고정 | 과민 반응으로 작업이 계속 끊김 |
| 9 | 리더에게 직선으로 복귀 | 막힘 → 웨이포인트 |
| 10 | 휘두른 횟수를 진척으로 셈 | 대상 HP 감소를 요구 |
| 11 | 봇의 드롭 카운터를 납품으로 셈 | 받는 쪽 인벤토리로 확인 |
| 12 | `DropItem` 전에 시선만 돌림 | 몸이 받는 쪽을 향해야 함 |
| 13 | 후퇴 임계값 하나 | 진동함 → 켜짐/꺼짐 히스테리시스 |
| 14 | 자체 배고픔 타이머 | 게임 음식 시스템을 씀 |
| 15 | 플래너 도달 거리(2.9m)를 실행기(3m)보다 엄격하게 | 불일치 |
| 16 | 홀드아웃 시드로 튜닝 | 평가 오염 |

**살릴 것**
- 실행 직전에 최신 관측으로 선택을 다시 확인한다.
- 결정 기록은 (state, goal, options, selected)만 모델 입력으로 쓴다. 결과는 감사용으로만 둔다.
- 월드 시드 단위로 데이터를 나눈다(SHA-256 버킷).
- LLM 없이 상태를 요약해 답한다.
- 채팅이 요청하지 않은 명령을 일으키지 못하게 의도 가드를 둔다.
- 안전 검사, 명시적 정지, 아이템 소유권은 하드 제약으로 둔다.

---

## 6. Thorkell 설계 결정과 이유

### 6.1 사용자 결정 (2026-10-02)

| # | 결정 | 이유 | 대가·대응 |
|---|---|---|---|
| 1 | **몸 = 진짜 플레이어 봇.** 두 번째 클라이언트에 "Thorkell" 캐릭터로 접속 | 음식·스태미나·레시피 발견·제작·건축 규칙이 사람과 같다("처음 하는 사람" 경험의 동등성). 자기 주변 구역을 로딩하므로 독립 탐험이 된다. 자기 카메라가 있다. Eira에서 검증됐다 | 게임 두 개 분량의 RAM·GPU → M1에서 측정. 기각한 대안: 게임 안 Humanoid NPC(규칙 흉내 필요), 같은 클라이언트의 두 번째 Player(게임이 파괴, 미검증) |
| 2 | **하이브리드 모델**: Live(음성), Flash(계획·회고·학습), Jev(빠른 결정) → laya로 증류 | 24GB에서 로컬 LLM은 4B가 한계. 1.7B는 목표 분해에 실패. 사용자가 지목한 모델 | 비용 상한 기본 $2/h(예상 $1~1.5/h). 키는 `op`로만 주입 |
| 3 | **바닐라 1.0.16 + Thorkell 플러그인만** | 1.0 출시로 모드가 깨진 상태라 변수를 줄인다 | 모드팩 호환은 나중 단계 |
| 4 | **친구와 함께, crossplay(PlayFab) 켬** | 사용자의 실제 플레이 방식 | 호스트 `RPC_PeerInfo` shim(루프백 피어만, finalizer로 복원). 다른 플레이어 보호 규칙 |
| 5 | **격리된 호스트 복제본** | 실제 설치와 모드팩을 건드리지 않는다 | 실제 세이브는 체크섬 백업과 동의 후 사용 |

### 6.2 구조 요약

```
[사람 Mac]
 Valheim 호스트 복제본 + Thorkell.Host ──PlayFab── 친구들
   │ 127.0.0.1:54880 Steam 루프백 리스너 (crossplay shim)
   ▼
 Valheim 봇 클라이언트 복제본(batchmode, 640x360, 20~30fps, 음소거) + Thorkell.Body
   │ TCP NDJSON 127.0.0.1:47811 (HMAC 핸드셰이크)
   ▼
 brain (Python asyncio, uv 패키지 `thorkell`)
   body/link ─► world/state(블랙보드) ─► control/controller(유일한 목표·의도 작성자)
     decide/ Jev(→laya)   plan/ gemini-3.8-flash   mind/ SQLite 지식·학습
     talk/ gemini-3.8-live(마이크 16k / 스피커 24k) + Valheim 채팅 말풍선
```

**몸 (C#)**
- 입력: `Player.SetControls` + `ZInput` 가상 버튼.
- 지각: 정보 동등성 필터를 거친다. hover 이름만 넘기고, prefab 이름·도구 tier는 숨긴다.
- 이벤트: `DamageText` 유형, `AddKnown*`, 까마귀 팁, 룬스톤 등.
- 반사 모드 우선순위: `hard_stop` > `self_preservation` > `self_defense` > `hazard_avoidance` > `unstuck` > 두뇌 행동.
- 반사가 끼어들면 현재 행동은 취소하지 않고 일시정지한 뒤 재개한다.

**브리지**
- TCP NDJSON + HMAC 핸드셰이크.
- `state` 10Hz, `scene` 2Hz. 이벤트는 절대 버리지 않는다.
- JSON Schema와 golden fixture를 C#과 pytest가 함께 쓴다.

**두뇌**
- PIANO식 컨트롤러가 목표와 의도를 혼자 결정한다. 목표 계층은 P0 생존 / P1 사용자 명령 / P2 자기 의제 / P3 호기심이다.
- 실행: `next_plan` 단일 슬롯 + interrupt flag.
- 플래너: 검증기가 인용과 발견한 이름만 쓰는지 확인하고, 수량 계산은 코드가 한다.
- Jev 결정 지점 7개: threat_response, target_select, prep_check, resume_or_switch, idle_activity, speak_worthy, intent_guard.
  - 마감을 넘기면 지점마다 정해 둔 동작을 한다. 숨은 기본값은 없다.
  - 차단기가 있다.

**지식**
- SQLite: entities / facts / rules / events / places / skills / utterances.
- 사실마다 출처(observed/game_ui/told/inferred/experiment)와 상태(hypothesis → supported → verified/refuted)를 둔다.
- 누출 차단: 발견한 이름만 노출하고, 인용을 강제하고, lexicon 스캔과 카나리 질문으로 확인한다.

**학습**
- 회고 → 규칙.
- 대화 추출 → `told` 사실 → 데미지 텍스트로 검증.
- 안전 조건 안의 호기심 실험.

**대화**
- `gemini-3.8-live` 도구: `set_goal`, `cancel`, `ask_status`, `recall_knowledge`, `teach_fact`, `reply_to_request`, `set_talk_level`. 움직임·공격 도구는 없다.
- 선제 발화는 floor 상태를 보고 하고, 횟수를 제한한다.
- 채널: Whisper / Normal / Shout + 음성.

**안전**
- 명령은 리더만 내릴 수 있다. 친구 채팅에는 대화로만 답한다.
- 다른 플레이어 5m, 건물 8m 안에서는 무기를 휘두르지 않는다. PvP는 하지 않는다.
- 보스 소환·철거는 동의가 필요하다.
- 프로덕션 코드에는 치트가 없다.

### 6.3 마일스톤 (요약)

| M | 범위 |
|---|---|
| M0 기반 | 이 문서, AGENTS.md, `verify-api`, Wire/Core 테스트, Live/Jev/Flash 계약 테스트 |
| M1 접속 | 5.4.2351, 격리 런타임, S0(Steam 백엔드) / S0b(crossplay + shim), 성능 기준선 |
| M2 몸 기본 | 입력·지각·이벤트·브리지, 가짜 월드(sim), S1 |
| M3 반사·채집·전투 | S2 chop_attack, LLM 없는 컨트롤러·스킬 |
| M4 결정·계획·제작 | 첫 E2E "나무 좀 해줘", S4 제작, S5 작업대+지붕 |
| M5 지식·학습 | S3 미지 몬스터, S6 밤 귀가, 누출 목표 |
| M6 음성·선제 발화 | 첫 음성 p50 2.0초 이하, 사용자 말 위로 말하기 0회 |
| M7 실전 공동 플레이 | 동의·백업 후 친구와 60분 |
| M8 laya 증류 | 승격 게이트 |

---

## 7. 알려진 난제와 열린 질문

### 7.1 알려진 난제

| 난제 | 내용 | 대응 |
|---|---|---|
| 지능과 지연의 균형 [공식] | 2026 서베이가 핵심 문제로 꼽는다. Cradle은 게임을 멈춰야 하고, WHAM은 실시간에 맞지 않는다. Teammates도 수 초 지연이 보고됐다 [2차] | 계층 구조, 템플릿 우선, 실행 중에 계획 |
| 말과 행동의 불일치, 성공 착각 | PIANO가 존재하는 이유다 | 단일 Decision 기록, 월드 기반 진척 |
| 모델의 한계 | 장기 과제·짧은 메모리·정밀 조작(SIMA 2가 스스로 밝힘), 처음 보는 적(Lumine), 장기 계획 불가(NitroGen) | 반사·스킬은 코드로, 장기 계획은 검증기와 규칙으로 |
| 넓은 범위 | PUBG Ally는 맵 하나로 좁혀 성공했지만 Valheim은 바이옴·보스·건축까지 훨씬 넓다 | 마일스톤별로 범위를 좁힘 |
| 통신 비용 | MineCollab에서 상세 계획을 말로 주고받으면 성능이 최대 15% 떨어졌다 | 대화층은 위임만 함 |
| 물가 내비게이션 | Eira 실패 원인 중 가장 많았고, 수영은 미해결 | AvoidWater → NoSwim, 수심 샘플링, 해안 시드 회귀 테스트 |
| 사전지식 누출 | LLM이 바닐라 Valheim을 알고 있다 | 동적 enum, 검증기, lexicon 스캔, 카나리. 자유 대화는 완전히 막을 수 없으므로 측정한다 |
| 보안 | 코드를 쓰는 에이전트(Mindcraft도 경고), 인증 없는 로컬 엔드포인트(ValheimMCP) | 코드 생성 없음. 루프백 + HMAC |
| 멀티플레이 | ZDO 소유권(`RequestOwn`), 1.0 이후 모드 호환성 | 바닐라만. 소유권을 요청한 뒤 행동 |

### 7.2 열린 질문 (측정·확인할 것)

1. **Live API 계약** (M0):
   - `scheduling` 필드 위치
   - `turn_complete=False`가 응답을 일으키지도 끊지도 않는지
   - 대기 중인 도구 호출이 있을 때 GoAway → 재개가 되는지
   - 재개 토큰 유효기간(문서 2시간 vs changelog "24시간")
   - 누적 컨텍스트가 턴마다 다시 과금되는지
2. **Jev** (M0):
   - 한국에서 본 지연(직접 vs OpenRouter)
   - 한국어 의도 판단 정확도(200문장)
   - 아직 초기 서비스라 API가 바뀔 위험
3. **crossplay shim** (M1 S0b):
   - 인증 흐름을 루프백 피어로만 한정할 수 있는지
   - `FindHostByIp`를 먼저 시도하는 데 걸리는 시간
   - 친구가 실제로 접속했을 때 회귀가 없는지(M7)
4. **성능** (M1):
   - Rosetta 클라이언트 두 개 + 약 1M ZDO 월드가 24GB에서 버티는지(목표: 사람 p95 프레임 1.25배 이하, 스왑 증가 없음, 총 RSS 16GB 이하 [추정])
   - 봇 카메라를 캡처할 때만 렌더링해도 되는지(확인 필요)
5. **Steam Cloud**: 두 프로세스 중 하나만 종료될 때 동기화가 어떻게 되는지.
6. **누출 측정의 신뢰도**: 주장 누출은 사람 라벨 100개로 보정한 flash 판정기로 잰다.
7. **laya 승격 데이터**: 지점당 결정 2,000개, 경합 결정 200개를 실제 플레이로 모을 수 있는지.
8. **첫 등장**: 시작 신전에서 걸어오게 할지, 동의를 받아 리더 옆으로 한 번 이동시킬지(M7 사용자 결정).
9. **권한**: 기지 근처 벌목, 상자, 건축 권한과 사람 FPS 손실 허용치(M7 사용자 결정).
10. **구 Eira DLL**이 실제로 비활성인지, 제거할지.

---

## 8. 출처

날짜는 자료에 나온 날짜다. 날짜가 없으면 arXiv ID에서 추정했거나(표시함) "–"로 둔다. 접속일은 2026-10-01이고, "2026-10-02"로 표시한 것은 그날 다시 확인한 것이다.

### 8.1 Gemini·Google

| 자료 | 날짜 | 태그 |
|---|---|---|
| Gemini API changelog — https://ai.google.dev/gemini-api/docs/changelog | 접속 2026-10-01/02 | [공식] |
| Gemini models — https://ai.google.dev/gemini-api/docs/models | 접속 2026-10-01 | [공식] |
| Gemini 3.8 Live 모델 페이지 — https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live | 모델 2026-09-15, 접속 2026-10-02 | [공식] |
| Gemini 3.8 Flash — https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash | 모델 2026-09-02, 접속 2026-10-02 | [공식] |
| Gemini 3.5 Flash-Lite — https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite | GA 2026-07-21 | [공식] |
| Live API tools (2026-10-01 조사 경로) — https://ai.google.dev/gemini-api/docs/live-api/tools | 접속 2026-10-01 | [공식] |
| Live tools (2026-10-02 재확인 경로) — https://ai.google.dev/gemini-api/docs/live-tools | 접속 2026-10-02 | [공식] |
| Live session management — https://ai.google.dev/gemini-api/docs/live-api/session-management | 접속 2026-10-01 | [공식] |
| Live session — https://ai.google.dev/gemini-api/docs/live-session | 접속 2026-10-02 | [공식] |
| Live guide — https://ai.google.dev/gemini-api/docs/live-guide | 접속 2026-10-02 | [공식] |
| Live capabilities — https://ai.google.dev/gemini-api/docs/live-api/capabilities | 접속 2026-10-01 | [공식] |
| Async function calling (Cloud) — https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/live-api/asynchronous-function-calling | 접속 2026-10-02 | [공식] |
| Gemini pricing — https://ai.google.dev/gemini-api/docs/pricing | 접속 2026-10-01/02 | [공식] |
| Gemma 4 모델 카드 — https://ai.google.dev/gemma/docs/core/model_card_4 | Gemma 4 2026-04-02 | [공식] |
| 9to5Google, Gemini 3.8 Flash 출시 — https://9to5google.com/2026/09/02/gemini-3-8-flash-launch/ | 2026-09-02 | [3자] |
| DataCamp, Gemini 3.8 Live — https://www.datacamp.com/blog/gemini-3-8-live | – | [3자] |
| Artificial Analysis Speech-to-Speech — https://artificialanalysis.ai/speech-to-speech | 접속 2026-10-01 | [3자] |

### 8.2 Jev·laya

| 자료 | 날짜 | 태그 |
|---|---|---|
| laya (PyPI) — https://pypi.org/project/laya/ | 접속 2026-10-02 | [공식-패키지] |
| laya GitHub — https://github.com/NandhaKishorM/laya | 2026-09 | [코드] |
| Jev 실무 가이드 (dev.to) — https://dev.to/valyuai/how-to-use-jev-a-practical-guide-to-typesafes-system-one-model-g5e | – | [커뮤니티] |
| MarkTechPost, Jev 활용 사례 20선 — https://www.marktechpost.com/2026/09/27/20-agentic-use-cases-of-typesafe-ais-jev/ | 2026-09-27 | [3자] |
| The Register, Jev 증류 도구 — https://www.theregister.com/ai-and-ml/2026/09/29/open-source-tool-distills-jev-so-you-can-run-it-locally/5299856 | 2026-09-29 | [3자] |
| Jevstiller — https://github.com/tomerglick57/Jevstiller | – | [커뮤니티/코드] |
| laya-vision-stitch — https://github.com/DanielTea/laya-vision-stitch | – | [커뮤니티] |
| Jev setup — https://openclawdatabase.com/jev/setup/index.md | 접속 2026-10-02 | [커뮤니티] |
| DataCamp Jev API tutorial — https://www.datacamp.com/tutorial/jev-api-tutorial | 접속 2026-10-02 | [커뮤니티] |
| What is Jev (nocode.mba) — https://www.nocode.mba/articles/what-is-jev-ai | 접속 2026-10-02 | [커뮤니티] |

### 8.3 VLA·게임 제어 모델

| 자료 | 날짜 | 태그 |
|---|---|---|
| NitroGen 프로젝트 — https://nitrogen.minedojo.org/ | 2025-12 공개, arXiv 2026-01 | [공식] |
| NitroGen HF — https://huggingface.co/nvidia/NitroGen | 2025-12 | [공식] |
| Open-P2P — https://github.com/elefant-ai/open-p2p/ | 2026-01-08 | [공식/코드] |
| Lumine (HF papers) — https://huggingface.co/papers/2511.08892 / arXiv https://arxiv.org/abs/2511.08892 | 2025-11-11 | [공식] |
| Game-TARS — https://arxiv.org/abs/2510.23691 | 2025-10-27 | [공식] |
| Isaac GR00T README — https://raw.githubusercontent.com/NVIDIA/Isaac-GR00T/main/README.md | 접속 2026-10-01 | [공식] |
| GR00T N1 — https://arxiv.org/abs/2503.14734 | 2025-03(arXiv ID 기준) | [공식] |
| openpi — https://github.com/Physical-Intelligence/openpi | 2025 | [공식] |
| π0.7 (TechCrunch) — https://techcrunch.com/2026/04/16/physical-intelligence-a-hot-robotics-startup-says-its-new-robot-brain-can-figure-out-tasks-it-was-never-taught/ | 2026-04-16 | [3자] |
| mlx-smolvla — https://discuss.huggingface.co/t/mlx-smolvla-smolvla-checkpoint-execution-and-validation-on-apple-silicon/179927 | 2026-09-05 | [커뮤니티] |
| Microsoft WHAM — https://huggingface.co/microsoft/wham | 2025-02 | [공식] |

### 8.4 로컬 추론·모델

| 자료 | 날짜 | 태그 |
|---|---|---|
| BFCL 리더보드 — https://gorilla.cs.berkeley.edu/leaderboard.html | 2026-04-12 갱신 | [공식/3자] |
| Qwen3.5-9B — https://huggingface.co/Qwen/Qwen3.5-9B | 2026-02~03 | [공식] |
| Qwen3.8-27B — https://huggingface.co/Qwen/Qwen3.8-27B | 2026-08-14 | [공식] |
| Ollama MLX 백엔드 — https://dev.to/alanwest/ollama-just-got-93-faster-on-mac-heres-how-to-enable-it-3gce | Ollama 0.19 2026-03-30 | [커뮤니티] |

### 8.5 음성

| 자료 | 날짜 | 태그 |
|---|---|---|
| WhisperKit — https://github.com/argmaxinc/WhisperKit | – | [공식] |
| Supertonic — https://github.com/supertone-inc/supertonic | Supertonic 3 2026-04-29, 아카이브 2026-09-09 | [공식] |
| Qwen3-TTS — https://github.com/QwenLM/Qwen3-TTS | 2026-01 | [공식] |
| Smart Turn v3 — https://www.daily.co/blog/announcing-smart-turn-v3-with-cpu-inference-in-just-12ms/ | – | [공식] |
| LiveKit turn detector — https://docs.livekit.io/agents/logic/turns/turn-detector | – | [공식] |
| KRAFTON Raon-Speech-9B — https://huggingface.co/KRAFTON/Raon-Speech-9B | – | [공식] |
| Qwen3-Omni-30B-A3B — https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Instruct | – | [공식] |
| Pipecat macos-local-voice-agents — https://github.com/kwindla/macos-local-voice-agents | – | [커뮤니티/코드] |
| gpt-realtime-2.1 — https://datanorth.ai/news/openai-releases-gpt-realtime-2-1-voice-models | 2026-07-06 | [3자] |
| GPT-Live-1 — https://datanorth.ai/news/openai-launches-gpt-live-1-in-the-api | 2026-09-10 | [3자] |

### 8.6 게임 에이전트 연구

| 자료 | 날짜 | 태그 |
|---|---|---|
| SIMA 블로그 — https://deepmind.google/blog/sima-generalist-ai-agent-for-3d-virtual-environments/ | 2024-03-13 | [공식] |
| SIMA TR — https://arxiv.org/abs/2404.10179 | 2024-04(arXiv ID 기준) | [공식] |
| SIMA 2 블로그 — https://deepmind.google/blog/sima-2-an-agent-that-plays-reasons-and-learns-with-you-in-virtual-3d-worlds/ | 2025-11-13 | [공식] |
| SIMA 2 TR — https://arxiv.org/abs/2512.04797 | 2025-12-04 | [공식] |
| Genie 3 — https://deepmind.google/blog/genie-3-a-new-frontier-for-world-models/ | 2025-08-05 | [공식] |
| Voyager — https://github.com/MineDojo/Voyager | 2023-05 | [공식] |
| Mindcraft — https://github.com/kolbytn/mindcraft | 2024~ | [코드] |
| MineCollab — https://arxiv.org/abs/2504.17950 | 2025-04 | [공식] |
| Project Sid (PIANO) — https://arxiv.org/abs/2411.00114 | 2024-10-31 | [공식] |
| Project Sid 저장소 — https://github.com/altera-al/project-sid | – (보고서만) | [공식] |
| Odyssey — https://github.com/zju-vipa/Odyssey | 2024-07(IJCAI'25) | [공식] |
| GITM — https://arxiv.org/abs/2305.17144 | 2023-05 | [공식] |
| JARVIS-1 — https://arxiv.org/abs/2311.05997 | 2023-11 | [공식] |
| JARVIS-VLA — https://arxiv.org/abs/2503.16365 | 2025-03 | [공식] |
| Optimus-1 — https://arxiv.org/abs/2408.03615 | 2024-08 | [공식] |
| Optimus-2 — https://arxiv.org/abs/2502.19902 | 2025-02(arXiv ID 기준) | [공식] |
| Optimus-3 — https://arxiv.org/abs/2506.10357 | 2025-06 | [공식] |
| VPT — https://arxiv.org/abs/2206.11795 | 2022-06 | [공식] |
| STEVE-1 — https://arxiv.org/abs/2306.00937 | 2023-06 | [공식] |
| Player2 AI NPC — https://modrinth.com/mod/player2npc | 2026-07-17 업데이트 | [모드 페이지] |
| PlayerEngine — https://modrinth.com/mod/playerengine | – | [모드 페이지] |
| Player2 앱 — https://player2.game/ | – | [공식] |
| Andy-4.2 — https://featherless.ai/models/Mindcraft-CE/Andy-4.2 | 2026-03 | [커뮤니티] |
| Cradle — https://github.com/BAAI-Agents/Cradle | 2024-03(ICML'25) | [공식] |
| MAIN-VLA — https://arxiv.org/abs/2602.02212 | 2026-02(arXiv ID 기준) | [공식] |
| Proact-VL — https://arxiv.org/abs/2603.03447 | 2026-03(arXiv ID 기준) | [공식] |
| GameWAM — https://arxiv.org/abs/2608.26200 | 2026-08(arXiv ID 기준) | [공식] |
| 게임 에이전트 서베이 — https://arxiv.org/abs/2605.09965 | 2026-05(arXiv ID 기준) | [공식] |
| Parallelized Planning–Acting — https://arxiv.org/abs/2503.03505 | 2025-03(arXiv), AAMAS 2026 | [공식] |

### 8.7 산업 NPC·AI 팀원

| 자료 | 날짜 | 태그 |
|---|---|---|
| NVIDIA ACE 자율 동반자 — https://www.nvidia.com/en-eu/geforce/news/nvidia-ace-autonomous-ai-companions-pubg-naraka-bladepoint/ | CES 2025 | [공식] |
| NVIDIA ACE NARAKA·inZOI 출시 — https://www.nvidia.com/en-us/geforce/news/nvidia-ace-naraka-bladepoint-inzoi-launch-this-month/ | 2025-03 | [공식] |
| PUBG Ally 제작기 (NVIDIA 개발자 블로그) — https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/ | 2026-06-25 | [공식] |
| PUBG Ally 베타 보도자료 — https://www.gamedeveloper.com/press-release/krafton-introduces-pubg-ally-beta-test | 베타 2026-06-17~07-01 | [공식] |
| Ubisoft Teammates — https://news.ubisoft.com/en-us/article/3mWlITIuWuu0MoVuR6o8ps | 2025-11-21 | [공식] |
| Respawn, Teammates 보도 — https://respawn.outlookindia.com/gaming/gaming-news/ubisoft-launches-teammates-a-genai-npc-prototype | – | [2차] |
| Convai 에이전트 플랫폼 — https://home.convai.com/blog/agentic-platform-virtual-worlds-convai | – | [공식-벤더] |
| Convai AI Player — https://convai.com/blog/ai-player-live-game-state-unreal-engine-convai-part-1 | 2026-08-13 | [공식-벤더] |
| Inworld Runtime — https://www.globenewswire.com/de/news-release/2025/08/13/3132320/0/en/Inworld-Runtime-The-first-AI-runtime-for-consumer-applications.html | 2025-08-13 | [공식] |
| Xbox Gaming Copilot 베타 — https://news.xbox.com/en-us/2025/08/06/gaming-copilot-beta-begins-rolling-out-to-xbox-insiders-on-game-bar-today/ | 2025-08-06 | [공식] |
| Sony Aloy 유출 프로토타입 — https://www.techradar.com/gaming/playstation/future-playstation-games-could-have-ai-powered-characters-if-this-leaked-prototype-of-aloy-is-anything-to-go-by | – | [2차] |

### 8.8 Valheim 모드·프로젝트

| 자료 | 날짜 | 태그 |
|---|---|---|
| Valheim 1.0 출시 — https://gamingtrend.com/news/viking-survival-hit-valheim-releases-into-1-0-on-september-9th/ | 2026-09-09 | [2차] |
| Valheim 1.0 모드 호환 — https://supercraft.host/wiki/valheim/valheim-1-0-mod-compatibility/ | 2026-09 | [3자] |
| Norsemen (VikingNPC) — https://github.com/RustyMods/Norsemen | 2024~ | [코드] |
| VikingNPC Continued — https://thunderstore.io/c/valheim/p/SephrinMods/VikingNPC_Continued/ | 0.4.1 | [모드 페이지] |
| Offline Companions — https://thunderstore.io/c/valheim/p/ProfMags/Offline_Companions/ | 2026-02~05 | [모드 페이지] |
| Offline Companions Reborn — https://old.thunderstore.io/c/valheim/p/Maddhattr/Offline_Companions_Reborn/ | v1.4.52 | [모드 페이지] |
| Friendlies Reloaded — https://thunderstore.io/c/valheim/p/Horem/Friendlies_Reloaded/v/0.8.4/ | – | [모드 페이지] |
| MobAILib — https://www.nexusmods.com/valheim/mods/1188 | – | [모드 페이지] |
| Cheb's Necromancy — https://www.nexusmods.com/valheim/mods/2040 | – | [모드 페이지] |
| Thrall — https://thunderstore.io/c/valheim/p/ego_ai/Thrall/ | 2024-09(지원 종료) | [모드 페이지] |
| Thrall HN 글 — https://news.ycombinator.com/item?id=41485356 | 2024-09 | [공식-개발자] |
| Fylgja — https://github.com/FeverDream-dev/Fylgja | v0.1.0 | [코드] |
| ValheimAI — https://github.com/Dahuchsi/ValheimAI | – | [코드] |
| open-valheim-bot — https://github.com/Paureel/open-valheim-bot | 2026-09 이후 [추정] | [코드] |
| ValheimMCP — https://github.com/myrcutio/ValheimMCP | 2026 | [코드] |
| Macheim — https://github.com/lofcgi/macheim | 2026-09(v1.3.0) | [코드] |

### 8.9 아키텍처·학습 패턴

| 자료 | 날짜 | 태그 |
|---|---|---|
| Generative Agents — https://arxiv.org/abs/2304.03442 | 2023-04(UIST'23) | [공식] |
| Figure Helix — https://www.figure.ai/news/helix | – | [공식] |
| Gemini Robotics 1.5 — https://deepmind.google/blog/gemini-robotics-15-brings-ai-agents-into-the-physical-world/ | – | [공식] |
| FSE 2025 (LLM으로 게임 AI 행동 강화) — https://conf.researchr.org/details/fse-2025/fse-2025-industry-papers/25/Enhancing-Game-AI-Behaviors-with-Large-Language-Models-and-Agentic-AI | 2025 | [공식] |
| Aalto 학위논문 — https://aaltodoc.aalto.fi/items/307c8b44-d9bd-4b26-831c-ca69ddc808c6 | – | [공식] |
| DEPS — https://arxiv.org/abs/2302.01560 | 2023-02(arXiv ID 기준) | [공식] ‡ |
| Inner Monologue — https://arxiv.org/abs/2207.05608 | 2022-07(arXiv ID 기준) | [공식] ‡ |
| ExpeL — https://arxiv.org/abs/2308.10144 | 2023-08(arXiv ID 기준) | [공식] |
| AutoManual — https://arxiv.org/abs/2405.16247 | 2024-05(arXiv ID 기준) | [공식] |
| ELLM — https://arxiv.org/abs/2302.06692 | 2023-02(arXiv ID 기준) | [공식] |
| OMNI-EPIC — https://arxiv.org/abs/2405.15568 | 2024-05(arXiv ID 기준) | [공식] |
| MAGELLAN — https://arxiv.org/abs/2502.07709 | 2025-02(arXiv ID 기준) | [공식] |

### 8.10 로컬 자료 (이 Mac)

| 자료 | 내용 |
|---|---|
| `~/Library/Application Support/Steam/steamapps/common/Valheim/` | 설치본. `changelog.txt`, `BepInEx/LogOutput.log`(BepInEx 5.4.23.3), `Valheim.app` universal binary |
| `.../Valheim.app/Contents/Resources/Data/Managed/assembly_valheim.dll`, `assembly_utils.dll` | 1.0.16 API의 기준. 메타데이터와 IL로 4.3~4.6절을 확인 |
| `~/Library/Preferences/com.coffeestain.valheim-steam.plist` | `language = Korean` |
| `~/Desktop/project/valheim/valheim-companion/` | Eira: README.md, LEARNING.md, VALIDATION.md, docs/, plugin/, native-tests/, scripts/, artifacts/ |
| `~/Desktop/project/valheim/macheim/` | README(Rosetta 실행, "BepInEx Requires Rosetta"), docs/(relicheim 테스트, AUDIT-1.2.0), Thunderstore 캐시 |

### 8.11 단일출처·재확인 필요 목록

구현에서 의존하기 전에 원문이나 실측으로 확인할 것.

**모델·API**
- Llama 4.5(2026-06 보도) [단일출처]
- Live 재개 토큰 "24시간" (changelog 언급) vs 문서 2시간
- Live 도구 응답의 `scheduling` 위치: Python 샘플 기준이므로 SDK를 고정하고 계약 테스트로 확인
- `gemini-3.8-flash` TTFT 17.5초: AA, 10k 입력·추론 포함 조건 [3자]
- Jev 관련
  - 지연 70~500ms(벤더), OpenRouter 중앙값 175ms
  - Doom 데모 수치 [3자 보도]
  - API 형태·분당 1,200건 [커뮤니티]
  - ECE 0.246은 laya 측 주장
- laya MLX 지연 7.4~13.4ms(M3 Max) [커뮤니티]
- Jevstiller 16ms·99.45% [커뮤니티]
- Qwen3.5 BFCL·τ2 [자체 보고]
- Ollama MLX 58 → 112 tok/s [3자]
- 각종 Mac tok/s 수치 [커뮤니티]

**사례**
- SIMA 2 성과 수치: 언론 보도가 서로 맞지 않으므로 TR 원문 그림을 기준으로
- Ubisoft Teammates의 Gemini 사용·지연·팀 규모 [2차]
- Inworld TTS P90 [2차]
- open-valheim-bot 날짜 [추정]
- Valheim 1.0 출시일 2026-09-09 [2차, 복수 출처 일치]

**로컬**
- 1.0.16 private 멤버 확인은 문자열 표·메타데이터 기준이다. 런타임 증명은 M1 self-test로 한다.
