# 상용 AI 팀원·동반자·co-playable character 업데이트 (기준일 2026-10-17)

이 문서는 `게임 플레이 AI 기술 동향 2026/commercial_ai_teammates.md`(기준일 2026-10-10)의 갱신판이다. 조사일은 2026-10-17이다.

**상태 태그**
- **[unchanged]**: 기준판 주장이 그대로 맞다.
- **[changed]**: 그 뒤 상황이 바뀌었다.
- **[new]**: 새로 나왔거나 기준판이 놓쳤다.
- **[corrected]**: 기준판이 틀렸거나 부정확했다.

**출처 태그**
- **[공식]**: 개발사·플랫폼 발표, 논문, 저장소 README, 패치 노트
- **[언론]**: 게임·테크 매체
- **[커뮤니티]**: 블로그, 위키, 모드 페이지, 집계 사이트
- **[추정]**: 이 노트 작성자의 추론

"(검색 요약)"은 원문을 열지 못하고(403 등) 검색 결과 요약으로만 확인한 항목이다. GitHub와 Thunderstore 수치는 2026-10-17에 `gh api`와 Thunderstore v1 API로 직접 확인했다.

**한눈에 보는 변경점**

| 대상 | 상태 | 핵심 |
|---|---|---|
| PUBG Ally | [changed] | 논문 v2(09-25)에서 단계별 지연(STT 0.12 / LM 0.80 / TTS 0.70s)과 언어별 안전성 수치를 확보했다. 정식 출시 발표는 여전히 없다. |
| 한국어 모델 | [corrected] | 논문은 Kanana 1.5라고 하고 인벤(06-22)은 A.X K1이라고 해서 서로 다르다. 논문 감사의 글에는 "SKT K1 Team"이 있다. |
| inZOI Smart Zoi | [changed]/[new] | v0.10.0(09-03) 맥락 판단 개선, v0.11.0(10-15) in-game MCP. **Mac판은 Core ML로 Smart Zoi를 돌린다**(기준판에서 놓침). |
| NVIDIA ACE | [new] | 10-13에 3세대 ACE SLM "Nemotron 3.5 Bolt E4B 4GB"(10-23 공개 예정)를 발표했다. Aniimo가 2세대이고, llama.cpp에서 decision model을 지원한다. |
| Ubisoft Teammates | [changed] | GTC 2026에서 on-device판을 보였다. Qwen3-4B-Instruct-2507 INT4/FP8, RTX 4090/5090. |
| Xbox Copilot | [corrected] | 콘솔판 중단 발표일은 6월이 아니라 **2026-05-05**이다. 모바일은 축소, PC Game Bar는 불명이다. |
| Tencent 和平精英 | [corrected] | 1.1억 명 수치가 GDC 2026 발표로 확인됐다. 최고 DAU 1,770만, 판당 메시지 70, 마이크 켜짐 약 75%. 혼원3 기반 "小田"도 나왔다. |
| laya / Convai | [corrected] | laya는 Convai Innovations(인도) 제품이고 NPC 플랫폼 Convai(convai.com)와는 다른 회사로 보인다. 독립 지표는 zero-shot에서 무작위에 가깝다. |
| Valheim LLM 동료 | [new] | Sapienheim(10-06), Бьёрн/valheim-bjorn(10-11, macOS), Palheim(09-11, "진짜 플레이어로 접속" 랜딩 페이지), ValheimAI(09-29, 두 번째 계정) |
| SkyrimNet | [new] | Beta26(10-03)에서 **Jev를 화자·대상·감정 결정에 도입**했고, Beta27(10-14)에서 STT 이름 힌트와 Gemini Flash reasoning 최소화를 넣었다. |
| Valheim 본체 | [new] | **Patch 1.0.17(10-06), 1.0.20(10-15)** 공개. Thorkell 버전 게이트(1.0.16)에 직접 영향이 있다. |

---

## Q1. KRAFTON PUBG Ally와 inZOI Smart Zoi — 출시 상태, 구조, 지연, 하드웨어, 반응

### Takeaway
PUBG Ally는 여전히 2026-06-17~07-01 베타 한 번뿐이고, 2026-10-17까지 정식·재오픈 발표는 없다. 논문 v2(2026-09-25)로 단계별 지연이 공개됐다. 온디바이스 음성 1회는 STT 0.12s + LM 0.80s + TTS 0.70s = 약 1.62s이고, 클라우드는 3.36s이다. 한국어 운영 분포의 안전 응답률은 84.1%로 영어(99.0%)보다 크게 낮았다. Smart Zoi는 9~10월 패치에서 조금씩 개선됐다. Mac판은 NVIDIA GPU 없이 Core ML로 Smart Zoi를 돌린다. 상용 "게임 내 LLM 캐릭터"가 Apple Silicon에서 실제로 출시된 거의 유일한 사례이다.

### Cited Findings

**PUBG Ally — 출시 상태**
- [unchanged][공식] Ally Duo 베타는 2026-06-17~07-01(NVIDIA 표기는 06-30)에 Sanhok에서 열렸고 한국어·영어·중국어를 지원했다. 재확인 출처는 [크래프톤 보도자료](https://www.krafton.com/news/press/%ED%81%AC%EB%9E%98%ED%94%84%ED%86%A4-pubg-ally-%EB%B2%A0%ED%83%80-%EC%84%9C%EB%B9%84%EC%8A%A4-%EC%B2%AB-%EA%B3%B5%EA%B0%9C/)와 [NVIDIA Q&A (2026-06-25)](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)이다(2026-10-17 재확인).
- [unchanged] 정식(상시) 모드나 재오픈 발표는 2026-10-17 검색(영문·국문)에서도 찾지 못했다. NVIDIA 2026-10-13 블로그도 "The first-generation model was in a public beta earlier this year for PUBG"라고 과거형으로만 쓴다 — [NVIDIA Blog (2026-10-13)](https://blogs.nvidia.com/blog/local-ai-rtx-spark-laptops-software-updates/)
- [new][공식] arXiv 2609.29837은 v1(2026-09-24)과 v2(2026-09-25)가 있다. 저자는 "PUBG Ally Team" 24명이고 프로젝트 리드는 Kangwook Lee와 Hyunseung Kim이다 — [arXiv abs](https://arxiv.org/abs/2609.29837)

**PUBG Ally — 구조 (기준판 내용 재확인 + 추가)**
- [unchanged][공식] 2층 구조는 그대로 확인됐다. System 1 behavior tree가 게임 틱 단위로 이동·조준·즉시 전투를 맡고, System 2 SLM이 이벤트 구동으로 의도 해석·조율·발화를 맡는다. 원문은 "Reflex-level actions never have to wait for the model." — [NVIDIA Q&A (2026-06-25)](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)
- [new][공식] 관찰 원칙: 시스템 프롬프트에 "these tool results are the only ground truth for the current match"라고 적는다. 모델이 이전 턴을 믿지 않고 tool로 다시 관찰하도록 학습시켰다. 원문은 "Ally decides what it needs to know and fetches only that through tool calls." — [NVIDIA Q&A](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)
- [new][공식] 기억은 두 층이다. 경기 간 장기 기억(플레이어 이름, 선호 무기, 즐겨 내리는 지점, 개인 정보, 순위와 인상적인 순간)과 경기 내 단기 기억(최근 발화, 현재 이벤트) — [NVIDIA Q&A](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)
- [new][공식] 추론 중에 들어온 이벤트는 큐에 쌓였다가 다음 루프에 묶여 들어간다. 추론은 한 번에 하나만 돈다. 대기 이벤트가 많으면 우선순위가 높은 것부터 받고 낮은 것은 버릴 수 있다. 행동은 "succeeds, fails, or is preempted"까지 유지되고 결과는 이벤트로 돌아온다. LM 타임아웃은 명시되지 않았다 — [arXiv v2 HTML](https://arxiv.org/html/2609.29837v2)
- [new][공식] 세션 평균 14.1분에 trajectory 59개 — [arXiv v2](https://arxiv.org/html/2609.29837v2). [추정] 대략 14초마다 LM 루프가 한 번 돈다(논문 수치가 아니라 작성자 계산).
- [new][공식] 제약: push-to-talk만 쓰고, "cannot process new player utterances while executing tool calls" — [arXiv v2](https://arxiv.org/html/2609.29837v2)

**PUBG Ally — 모델·한국어**
- [unchanged][공식] 언어별 쌍(중간 교사 → 학생)
  - 영어: Mistral-NeMo-Minitron-8B → 2B-128K
  - 한국어: `kakaocorp/kanana-1.5-8b-instruct-2505` → `kanana-1.5-2.1b-instruct-2505`
  - 중국어: Qwen3-8B → Qwen3-1.7B
  - 초기 교사: Gemma 4 31B. 프롬프트는 GEPA로 최적화했다.
  - 한국어 백본에는 추가 knowledge-injection 단계가 있다(부록 G).
  - 출처: [arXiv v2](https://arxiv.org/html/2609.29837v2)
- [corrected][언론] 인벤(2026-06-22)은 크래프톤 CAIO의 말을 빌려 "한국어판 엘라이 학습에 A.X K1이 쓰였다", "A.X K1은 한국 정부가 지원하는 소버린 AI 모델 중 하나"라고 보도했다 — [인벤 (2026-06-22)](https://m.inven.co.kr/webzine/wznews.php?idx=317656&iskin=console)
  - 반면 논문 본문에는 A.X K1이 없고, 감사의 글에 "SKT K1 Team"(한국어 역량 관련)만 나온다 — [arXiv v2](https://arxiv.org/html/2609.29837v2)
  - **두 출처가 충돌한다.** [추정] A.X K1은 배포 학생이 아니라 부록 G의 지식 주입이나 데이터 쪽에 쓰였을 가능성이 있다. 부록 G 본문은 읽지 못했다.
- [new][공식] 4bit 양자화 크기(가중치 / 총 메모리)
  - 한국어 2.1B: 1.3GB / 약 2.0GB
  - 중국어 1.7B: 1.0GB / 약 1.6GB
  - 영어 2.0B: 1.4GB / 약 2.1GB
  - 목표 하드웨어는 "8 GB consumer-GPU", 시험 장비는 "RTX 4060-class"이다. 세션당 prefix KV-cache 재사용률은 90.7% ± 3.7pp이다.
  - 출처: [arXiv v2](https://arxiv.org/html/2609.29837v2). 기준판의 Inven Global "1.6–2.1GB"와 일치한다.
- [new][언론] 크래프톤은 PC방을 빌려 1,000명 넘는 플레이어가 약 4만 판을 하게 했다. KV-cache 압축 기법을 따로 만들었고, 3D 렌더링과 AI 에이전트가 GPU 하나를 나눠 쓰도록 스케줄링했다. 초기에 쓴 가중 평가 지표는 테스터 순위와 크게 달라서 여러 번 고쳤다 — [인벤 (2026-06-22)](https://m.inven.co.kr/webzine/wznews.php?idx=317656&iskin=console)
- [new][공식] 한국어 데이터는 커뮤니티별 은어·약어·아이템/지도 콜아웃을 연구해 만들었고 언어 전문가가 자연스러움을 검수했다. 한국어 전용 기술 장치(토크나이저 등)는 설명하지 않았다 — [NVIDIA Q&A](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)

**PUBG Ally — 지연 (기준판 Gap을 메움)**
- [new][공식] 단계별 중앙값(초)

  | 단계 | 온디바이스 | 클라우드 |
  |---|---|---|
  | STT | 약 0.12 | – |
  | LM | 약 0.80 | 약 2.54 |
  | TTS | 약 0.70 | – |
  | 기대 응답 | 약 1.62 | 약 3.36 |

  - LM p90은 0.91s 대 3.46s이다.
  - 추론을 한 번 더 할 때마다 온디바이스는 약 0.78s, 클라우드는 약 2.45s가 늘어난다. 6회 연쇄도 로컬은 "under five seconds"이다.
  - 출처: [arXiv v2](https://arxiv.org/html/2609.29837v2)

**PUBG Ally — 품질·안전·반응**
- [new][공식] LLM judge 점수(2B 학생 대 교사): Fact 0.932/0.944, Event 0.954/0.952, Intent 0.953/0.960, Cmd 0.876/0.889, Traject 0.902/0.910. 기준판 Gap이던 명령 성공률은 여전히 없고, Cmd judge 점수가 가장 가까운 지표이다 — [arXiv v2](https://arxiv.org/html/2609.29837v2)
- [new][공식] 무해 응답률(모델 단독, 한/영/중)
  - 광범위 세트: 98.3 / 99.4 / 99.3
  - **운영 대표 세트: 84.1 / 99.0 / 89.3**
  - 경계 침범 세트: 63.6%. 가장 뚜렷하게 남은 실패이다.
  - 정상 입력 과잉 거부: 한 5.0%, 영 6.1%, 중 2.2%
  - 출처: [arXiv v2](https://arxiv.org/html/2609.29837v2)
- [unchanged][공식] 반응 수치는 그대로 확인됐다.
  - 추천 순응답 +25.1pp(95% CI 23.4–26.7), 17개 언어, 141개국
  - 전투 2.58, 상황 판단 2.88, 응답 속도 2.93, 명령 수행 2.99
  - 관계 인식: 도구 50.0%, 동반자 31.5%, 팀원 18.5%
  - 가장 좋은 점: 정보·전술 51%, 대화 상대 28%
  - 출처: [arXiv v2](https://arxiv.org/html/2609.29837v2)
- [new][공식] 플레이어가 보고한 실패
  - 소생할 때 머뭇거림
  - 시켜야만 콜을 함
  - 원하지 않게 된 뒤에도 아이템 찾기를 계속함
  - 경기 간 기억이 일관되지 않음
  - "okay"라고 해 놓고 이행하지 않음
  - 후반에 계속 말해서 발소리를 못 들음: "at end game constantly talking when I'm trying to hear footsteps"
  - 출처: [arXiv v2](https://arxiv.org/html/2609.29837v2)
- [changed][공식] 다음 단계가 논문으로 확인됐다. full-duplex 음성 모델(GPT-Live 또는 Raon-SpeechChat)에 백그라운드 System 2 에이전트를 붙이고, harness와 SLM을 함께 최적화한다(Meta-Harness, WHALE 인용). 기준판은 Inven Global 보도로만 적었다 — [arXiv v2](https://arxiv.org/html/2609.29837v2)
- [unchanged][언론] 하드웨어: 최소 RTX 2080 Ti / 3060(8GB), 권장 RTX 4070(12GB) — [tbreak](https://tbreak.com/pubg-ally-ai-teammate-rtx-requirements/)(2026-10-17 검색에서 같은 내용 재확인). 한국일보는 "기존 권장 사양 대비 4배 이상의 VRAM과 램 8GB 추가"라고 썼다 — [한국일보 (2026-07-23, URL 기준)](https://www.hankookilbo.com/news/article/A2026072311080002063)

**inZOI Smart Zoi**
- [unchanged][공식] Windows판은 0.5B Mistral NeMo Minitron SLM을 RTX에서 로컬로 돌린다 — [NVIDIA GeForce News](https://www.nvidia.com/en-gb/geforce/news/nvidia-ace-naraka-bladepoint-inzoi-launch-this-month/)(기준판과 같음). 위키는 시작할 때 라이선스 확인에 인터넷이 필요하다고 적었다 — [thegameswiki (검색 요약)](https://thegameswiki.com/inzoi/wiki/smart-zoi)
- [new][공식] v0.10.0(2026-09-03): "Smart Zois have been improved to use various contexts, including current location, group activity, or social event…", "Interactions selected by a Smart Zoi are indicated with a dedicated symbol." 유아가 특정 상호작용만 반복하던 버그도 고쳤다. 같은 패치에서 "AI build has been removed" — [simscommunity 패치 노트 전재 (2026-09-03)](https://simscommunity.info/2026/09/03/inzoi-update-september-3-2026-release/), [SteamDB v0.10.0 (검색 요약)](https://steamdb.info/patchnotes/25077871/)
- [new][공식] v0.11.0 Mini Update(2026-10-15)
  - "Fixed an issue where Zois with Smart Zoi enabled did not eat a proper meal when their Hunger need was low"
  - "Lua script modding can be done with the help of an LLM using the in-game MCP"
  - 게임 명령을 자연어로 LLM에 요청할 수 있다(예: "Make the maximum number of Zois in the city to 10.")
  - 출처: [simscommunity (2026-10-15)](https://simscommunity.info/2026/10/15/inzoi-update-october-15-2026-notes/)
- [new][언론] **Mac판(2025-08-20 출시)은 Smart Zoi를 Core ML로 돌린다.** 보도자료 전재에는 "on-device AI powered by Core ML ensures seamless implementation of inZOI's AI features such as 3D Printer, AI Texture, AI Motion, and Smart Zoi on Mac devices"라고 되어 있다 — [Playday (2025-06-11)](https://playday.one/2025/06/11/life-sim-inzoi-mac-pre-orders-available-june-update-details/), [tbreak](https://tbreak.com/inzoi-comes-to-mac-launching-on-august-20/)
  - [커뮤니티] 위키는 "M2 이상" 요구라고 적었다(초기 App Store 표기는 M1). Mac에서 쓰는 모델 크기와 지연은 공개되지 않았다 — [thegameswiki macOS](https://thegameswiki.com/inzoi/wiki/macos-version)
- [unchanged] Smart Zoi의 성능 부담과 정량적인 반응 자료는 여전히 없다. 커뮤니티에는 빈 생각 풍선, 메뉴 멈춤 같은 버그 보고만 있다 — [Steam 토론 (검색 요약)](https://steamcommunity.com/app/2456740/discussions/0/836123794066162014/)

### Inferences
- [추정] PUBG 실측으로 보면 온디바이스 2B의 **LM 0.8s가 TTS 0.7s와 비슷하다.** 음성 왕복에서 TTS와 STT는 무시할 수 없는 몫이다. Thorkell은 gemini-3.8-live(클라우드 speech-to-speech)라서 구성이 다르지만, "말 끝 → 첫 소리" 시간을 단계별로 재야 비교할 수 있다.
- [추정] 한국어 안전성이 영어보다 15pp 낮다(84.1 대 99.0). 같은 파이프라인이라도 한국어 guardrail은 따로 시험해야 한다는 근거이다. Thorkell은 한국어 전용이므로 친구들과 crossplay할 때 쓸 한국어 적대 입력 세트가 필요하다.
- [추정] "도구 결과만이 유일한 사실"과 "매 루프 재관찰"은 Thorkell의 정보 동등성 규칙과 같은 방향이다. 지각 스냅샷에 시각을 달고, 이전 대화 기억을 사실로 쓰지 않게 한다.
- [추정] Ally 실패 목록(시킨 일을 너무 오래 계속함, "okay" 후 불이행, 후반 수다)은 Thorkell 스킬의 **종료 조건·취소·말 줄이기 설정**에 그대로 대응한다.
- [추정] inZOI Mac판은 같은 회사가 RTX용 SLM 기능을 Core ML로 옮긴 사례이다. Apple Silicon에서 게임과 SLM을 같이 돌리는 것은 상용으로도 가능하다. 다만 모델 크기와 지연은 공개되지 않았다.

### Gaps
- PUBG Ally 정식 출시나 2차 베타 일정: 2026-10-17까지 발표가 없다.
- 논문 부록 G(한국어 knowledge injection)와 7.3절 인게임 행동 분석의 수치는 HTML이 잘려서 다 읽지 못했다. A.X K1의 실제 역할은 확인하지 못했다.
- 언어별 라이브 설문 분리값은 그림으로만 있다(본문 수치 없음).
- inZOI Mac판 Smart Zoi의 모델, 지연, 메모리 사용량은 공개 자료가 없다.

---

## Q2. NVIDIA ACE — 최신 SDK·모델·게임, 그리고 Mac에서 쓸 수 있는 것

### Takeaway
2026-10-13에 NVIDIA가 **3세대 ACE SLM "Nemotron 3.5 Bolt E4B 4GB"**(2026-10-23 공개 예정)를 발표했다. 세대 구분은 1세대 PUBG Ally, 2세대 Aniimo(Gamescom 2026 프리뷰)이다. 같은 글에서 RTX Spark 노트북(최대 128GB 통합 메모리, 10-16 출시)과 "llama.cpp·Unsloth의 decision model 지원"을 밝혔고, SkyrimNET을 사례로 들었다. ACE Game Agent SDK는 2026-06 베타 이후 새 릴리스를 찾지 못했다. macOS 지원 언급은 여전히 없다.

### Cited Findings
- [new][공식] "Nemotron 3.5 Bolt E4B 4GB is the third-generation SLM for NVIDIA ACE"
  - 공개 예정일: 2026-10-23(금)
  - 특징: "low memory footprint and fast time to first token"
  - 기능: "combines natural conversation with multi-turn tool use, instruction following and grounding in application state". 대화 모드가 있고 reasoning을 켜고 끌 수 있다.
  - 지원 언어와 런타임은 언급하지 않았다.
  - 출처: [NVIDIA Blog (2026-10-13)](https://blogs.nvidia.com/blog/local-ai-rtx-spark-laptops-software-updates/)
- [new][공식] 같은 글의 세대 구분: 1세대는 PUBG 공개 베타, 2세대는 "the more efficient second-generation model previewed in Aniimo at Gamescom" — [NVIDIA Blog (2026-10-13)](https://blogs.nvidia.com/blog/local-ai-rtx-spark-laptops-software-updates/)
- [new][공식] 같은 글
  - "Decision models are now supported in llama.cpp and Unsloth on RTX Spark and GeForce RTX GPUs". 에이전트가 다음 행동을 "up to 200x faster than traditional agents"로 고른다고 주장한다. 어떤 decision model인지(Jev/laya 등)는 밝히지 않았다.
  - Nemotron 3.5 Bolt 74B-A9B(2bit, 24GB)는 10-15 공개. 런타임은 llama.cpp, vLLM, Ollama, Unsloth, LM Studio이다.
  - RTX Spark는 "up to 128GB of unified memory and 1 petaflop of AI compute"이고 10-16 출시이다.
  - SkyrimNET(MinLL)을 "supports both cloud and local inference" 사례로 언급했다.
  - 출처: [NVIDIA Blog (2026-10-13)](https://blogs.nvidia.com/blog/local-ai-rtx-spark-laptops-software-updates/)
- [new][공식] Aniimo(FunPlus/Pawprint): 게임은 2026-09-16(콘솔·PC), 09-23(모바일)에 출시됐다. ACE는 "post-launch update"로 들어온다.
  - 기능: 음성과 자연어로 소통하고, 기술을 가르치고, "send them out to gather resources using voice input"
  - 모델과 VRAM은 공개하지 않았다.
  - 출처: [FunPlus (2026-08-27)](https://funplus.com/aniimo-x-nvidia-ace-bringing-aniimo-closer-to-life/), [NVIDIA Gamescom 2026](https://www.nvidia.com/en-us/geforce/news/gamescom-2026-nvidia-geforce-rtx-dlss-4-5-announcements/) ("will launch with DLSS 4.5, and later add NVIDIA ACE")
  - [언론] In-Game News는 ACE 통합을 "early 2027"로 보도했고, 크리처는 기지 안 몇 가지 활동으로만 제한되며 애니메이션과 이모지로 답한다고 적었다. FunPlus 발표와 시점이 충돌한다 — [In-Game News (검색 요약)](https://ingamenews.com/pc-gaming/aniimo-will-feature-ai-powered-creatures-via-nvidia-ace/)
- [unchanged][공식] ACE Game Agent SDK 베타(2026-06-16)
  - C/C++, 오픈소스
  - Agent/Chat/RAG API
  - 기본 모델: nemo-conformer-ctc-120m, Qwen 3.5 4B, Chatterbox Turbo 350M
  - 출처: [NVIDIA Developer Blog](https://developer.nvidia.com/blog/build-on-device-ai-companions-with-the-nvidia-ace-game-agent-sdk-and-unreal-engine-5-plugins/)(2026-10-17 검색으로 재확인)
  - 2026-10-17에 GitHub 검색(`org:NVIDIA ace game agent`, `ACE Game Agent SDK`)을 했지만 공개 저장소를 찾지 못했다.
  - [커뮤니티] 한 가이드는 "2026년 5월부터 GitHub Apache 2.0"이라고 썼는데 발표 시점(6월)과 맞지 않아 미검증이다 — [arcanumrpgs (검색 요약)](https://arcanumrpgs.com/blog/nvidia-ace/)
- [unchanged][공식] Total War: PHARAOH advisor(RAG로 1,200개 넘는 테이블 조회)는 여전히 실험 단계로만 언급된다. 출시 소식은 찾지 못했다 — [NVIDIA Developer Blog](https://developer.nvidia.com/blog/build-on-device-ai-companions-with-the-nvidia-ace-game-agent-sdk-and-unreal-engine-5-plugins/)
- [unchanged] macOS·Metal 지원 언급은 없다. NVIDIA 10-13 글에서 macOS는 PAIR(개인 AI 라우터) 설명에만 나온다("PAIR works on Windows, Linux and macOS") — [NVIDIA Blog (2026-10-13)](https://blogs.nvidia.com/blog/local-ai-rtx-spark-laptops-software-updates/)

### Inferences
- [추정] Bolt E4B 4GB가 공개 가중치로 나오고 llama.cpp에 올라가면, Metal 백엔드로 M4 Pro에서 돌려 볼 후보가 된다. 다만 한국어 지원 여부를 모르고, PUBG가 한국어에 Kanana를 따로 쓴 것을 보면 NVIDIA 기본 SLM의 한국어 품질은 따로 검증해야 한다.
- [추정] NVIDIA가 "decision model"을 llama.cpp 지원 범주로 공식화했다. Thorkell이 Jev(관리형)에서 laya(로컬)로 옮겨 가는 방향은 업계 흐름과 맞다.
- [추정] Aniimo가 "기지 안 몇 가지 활동, 애니메이션·이모지 응답"으로 제한한 것은 Krafton의 "한 맵, 한 모드, 고정 아이템 분류"와 같은 범위 축소 전략이다.

### Gaps
- Bolt E4B의 파라미터 수, 지원 언어, 라이선스, 배포 위치는 10-23 공개 전이라 확인하지 못했다.
- Aniimo ACE 업데이트의 실제 배포 날짜(FunPlus "post-launch"와 In-Game News "early 2027"의 충돌)를 확인하지 못했다.
- ACE Game Agent SDK의 공개 저장소와 라이선스를 공식 문서로 확인하지 못했다.

---

## Q3. 그 밖의 상용 사례 — Ubisoft, Tencent, NetEase, Microsoft, Sony, Razer, Inworld, Convai

### Takeaway
게임 안에서 **행동하는** 팀원은 모두 "BT/봇 실행층 + LLM 판단층"이다. 2026년의 흐름은 **클라우드에서 온디바이스로 이동**하는 것이다. Ubisoft도 Gemini 클라우드 데모를 Qwen3-4B 로컬판으로 옮겼다. Tencent 和平精英는 GDC 2026에서 누적 1.1억 명, 최고 DAU 1,770만 명이라는 최대 규모 지표를 공개했다. **플레이하지 않고 말만 하는** 비서형(Xbox 콘솔 Copilot, Razer AVA, Tencent 鹅次元)은 중단되거나 반응이 미지근하다. 기준판의 "laya = Convai"는 회사가 다른 것으로 보여 바로잡는다.

### Cited Findings

**Ubisoft Teammates**
- [changed][언론] GTC 2026(3월) 발표 기준으로 Teammates를 **온디바이스**로 RTX 4090/5090에 배포했다.
  - 모델: "Qwen3-4B-Instruct-2507 … quantised to INT4 for speed and FP8 for quality"
  - 로컬 TTS: KaniTTS-400m
  - 인용: "Moving the inference on-device is the next logical step to make NPC interaction scalable"
  - 출처: [Computer Weekly (2026-05-12, 검색 요약, 원문 403)](https://www.computerweekly.com/news/366642940/In-video-games-of-the-future-your-AI-teammates-will-actually-listen)
  - KaniTTS는 이 요약 하나에서만 확인됐다.
- [unchanged][언론] 2025-11 원 데모는 Snowdrop + Gemini(+ElevenLabs 음성)였다 — [GamesBeat (2025-11, 검색 요약)](https://gamesbeat.com/?p=310806). BT 위에 LLM 결정층을 둔다 — [Game Developer (2025-11-21)](https://www.gamedeveloper.com/business/ubisoft-s-first-playable-generative-ai-experience-is-an-r-d-experiment-called-teammates-)
- [new][언론] 기억은 약 1.5시간 안의 사건만 유지한다 — [CGames (검색 요약)](https://www.cgames.com/contents/2/9665.html). Ubisoft는 연간 실적 발표에서 Teammates 투자를 "accelerating"이라고 했다 — [Insider Gaming (검색 요약)](https://insider-gaming.com/ubisoft-investment-playable-generate-ai-experience/)
- [unchanged] 공개 플레이테스트 결과, 지연 수치, 상용화 일정은 찾지 못했다.

**Tencent**
- [corrected][언론] 기준판이 "미검증"으로 둔 和平精英 수치는 GDC 2026 발표 보도로 확인됐다.
  - 모든 AI NPC 플레이 누적 체험자 1.1억 명, 최고 DAU 1,770만 명, 판당 메시지 70건, 마이크 켜짐 비율 "近75%"
  - 구조는 "大模型+AI Bot". 대화와 이해는 대형 모델, 게임 행동은 Bot이 맡는다.
  - "绝地指挥" 3단계: 전문성·인간다움 → 기억·동반 → 육성형 전속 파트너
  - 예고: "全双工自然对话", "多情绪TTS"
  - 모델, 클라우드/단말 배치, 지연은 공개하지 않았다.
  - 출처: [北京日报 京报网 (2026-03-13)](https://news.bjd.com.cn/2026/03/13/11629797.shtml)
- [new][언론] AI 스타 팀원 "小田"(배우 田曦薇의 가상 형상)이 SPARK 2026 발표회(2026-05-27)에서 공개됐다.
  - "首个由混元3 preview大模型驱动的AI明星队友"
  - 행동: 엄폐물 찾기, 차량 운전, 경로·자원·위험 조언
  - 판 밖: 대화, 선물, 회상 사진 생성
  - 배치와 지연은 공개하지 않았다. 홍보성 기사이다.
  - 출처: [中华网 (2026-05-28)](https://tech.china.com/articles/20260528/202605281880774.html), [搜狐/游戏矩阵 (2026-05-30)](https://www.sohu.com/a/1029679502_267123)
- [changed][언론] 鹅次元(Goose Dimension/Goosyverse)는 **플레이하지 않는 동반자**이다. 원문: "The positioning of Goosyverse is not to create a gaming master", 핵심은 "accompany"
  - 게임 중 실시간 음성 대화와 "real-time image recognition"을 하지만 안정성은 미지수이다.
  - 내부 테스트 동안은 무료이고, 나중에 스타코인으로 에너지를 사는 과금 틀이 보인다.
  - 모델, 배치, 지연은 공개하지 않았다.
  - 출처: [36Kr (2026-09-29)](https://eu.36kr.com/en/p/4003804637304450)
  - 공개 출시일이나 가격은 발표되지 않았다 — [Inside AI (검색 요약)](https://insideai.news/news/generative-ai/tencent-goose-dimension-ai-gaming-companion/13166/)
- [unchanged][공식] F.A.C.U.L.(Arena Breakout: Infinite)과 GVoice AI Teammates voice gateway(GDC 2026)는 기준판과 같다. 새 기술 공개는 찾지 못했다.

**NetEase**
- [unchanged][언론] 2026년에 새로 발표된 NetEase의 "행동하는" LLM 팀원은 찾지 못했다. Justice Mobile AI Retainer(장기 기억)와 Dreamweaver Mode(2026-04-03)는 서사형이다 — [36Kr](https://eu.36kr.com/en/p/3394131222956417)(2026-10-17 검색으로 재확인)

**Microsoft (Gaming Copilot)**
- [corrected][언론] 콘솔 Copilot 중단은 **2026-05-05** Asha Sharma의 X 게시물로 발표됐다. 원문: "we are scaling back the mobile version of Copilot and ceasing development of the console version of Copilot". 기준판의 "2026년 6월"은 후속 인터뷰 시점이다 — [MobileSyrup (2026-05-05)](https://mobilesyrup.com/2026/05/05/xbox-ditching-microsoft-copilot-ai/), [GIGAZINE (2026-05-06)](https://gigazine.net/gsc_news/en/20260506-microsoft-copilot-no-longer-consoles-xbox-ceo), [VGC 인터뷰 (2026-06)](https://videogameschronicle.com/news/our-console-players-arent-excited-about-that-xbox-ceo-asha-sharma-says-it-ditched-copilot-because-it-didnt-solve-a-problem)
- [corrected] 범위: 콘솔은 개발 중단, 모바일은 "scaling back"(중단이 아님)이다. **PC Game Bar의 Gaming Copilot 상태는 어느 출처도 밝히지 않았다**(2026-10-17 검색).

**Sony**
- [unchanged][언론] 2025-03 Aloy 시제품 유출 이후 새 동반자 제품은 없다. 대신 "Ghost Player" 특허가 다시 보도됐다(2024-09 출원, 2025-04 공개, 2026-01 재보도). Guide Mode(풀이 시연)와 Complete Mode(대신 완료)가 있고, 출시 기능은 아니다 — [VGC (2026-01, 검색 요약)](https://www.videogameschronicle.com/news/sony-ai-patent-will-see-playstation-games-play-themselves-when-players-are-stuck)

**Razer**
- [new][공식/언론] Project AVA(CES 2026)
  - 5.5인치 홀로그램 데스크 동반자이고 xAI Grok로 동작한다.
  - PC Vision Mode로 화면을 보고 게임 조언을 한다. 게임 안에서 행동하지는 않는다.
  - 2026년 하반기 출하 예정, $20 예약금, 가격 미발표
  - 반응: "creepy AI companion no one asked for"(Android Authority), "waifu in a bottle"(Engadget)
  - 출처: [Razer Newsroom (2026-01)](https://www.razer.com/newsroom/company-news/razer-at-ces-2026), [Android Authority (2026-01)](https://www.androidauthority.com/razer-project-ava-hands-on-ces-2026-3630600/), [Engadget (2026-01)](https://www.engadget.com/gaming/pc/razer-put-a-waifu-in-a-bottle-at-ces-2026-205315908.html)
  - 2026-10-17까지 출하일과 가격은 확인되지 않았다.

**Inworld**
- [changed][커뮤니티] 게임 캐릭터 사업에서 음성·인프라 회사로 피벗했다.
  - Character Studio 은퇴: 2025-06~09 사이 리다이렉트
  - TTS-2: 2026-08-31 출시. 첫 오디오까지 "<100 ms", Flash는 25ms(벤더 주장)
  - 가격: TTS-2 100만 자당 $25(무료 플랜)~$5(엔터프라이즈). STT는 시간당 $0.10–0.15.
  - Realtime API(speech-to-speech), 220개 넘는 모델 라우터
  - 2026-10-13 홈페이지에 Ultravox 인수 배너가 있다.
  - 2026년에 Inworld를 쓰는 신작 게임 팀원 사례는 확인되지 않았다.
  - 출처: [Arcanum RPGs (2026-09-27)](https://arcanumrpgs.com/blog/inworld-ai/)

**Convai / laya / Jev**
- [corrected][공식/커뮤니티] **laya의 제작사는 ConvAI Innovations**(인도 케랄라, 창업자·CEO Nandakishor Mukkunnoth)이다 — [laya 공식 페이지](https://laya.convaiinnovations.com/), [Tracxn](https://tracxn.com/d/companies/convai-innovations/__wGaGZOqGCbF2wl-5iSy_tHqZxgJ2JF_9QpzFaxvUtY0)
  - NPC 미들웨어 **Convai**(convai.com)의 창업자·CEO는 전 NVIDIA 엔지니어 Purnendu Mukherjee이다 — [AWE USA 2025 연사 소개](https://www.awexr.com/usa-2025/speakers/1330-purnendu-mukherjee)
  - [추정] 두 회사는 별개로 보인다. 프로젝트 지침의 "laya (Convai)"는 혼동일 수 있다.
- [changed][커뮤니티] laya 현황
  - 공개: `laya`(영어 421M, 512 ctx)와 `laya-typed-decisions`는 2026-09-18, `laya-multilingual`(mmBERT-base 322M, 1,024 ctx)은 09-19
  - 벤더 지연: T4에서 32.8ms(기준판 39.5ms와 범위 32.8–39.5ms)
  - 벤더 자체는 "$0.00 (self-hosted)", 호스팅 API 없음. 기준판의 "$0.020/1M, 2026-10-12까지"는 제3자 호스팅 프로모션이었고 기한이 지났다.
  - 출처: [laya 공식](https://laya.convaiinnovations.com/), [systemonemodels (2026-10-12 갱신)](https://systemonemodels.org/models/laya/)
- [new][커뮤니티] 독립 평가 Jev Decision Index 0.3.1(2026-10-12, 0=무작위, 100=완벽)
  - Full: laya 4.43, Jev 60.11
  - Public: laya 6.19, Jev 57.96
  - 페이지 결론: laya는 "a fast base to specialise, not a zero-shot decision engine"
  - Banking77(선택지 77개): laya 0.425, Jev 0.870
  - 영어 체크포인트에 다른 문자 입력을 넣으면 실패한다(크메르어 0.000, 확신도 0.952). 한국어 결과는 없다.
  - 출처: [systemonemodels (2026-10-12)](https://systemonemodels.org/models/laya/)
- [new][커뮤니티] Apple Silicon 포트(독립)
  - Laya-MLX: 짧은 영어 결정 중앙값 13.4ms, 다국어 7.4ms
  - Laya-CoreML: Neural Engine에서 P50 4.98ms
  - FluidUse: M5 Pro에서 3.7ms
  - 출처: [systemonemodels (2026-10-12)](https://systemonemodels.org/models/laya/)
- [unchanged][커뮤니티] Convai NPC 플랫폼은 Unity/Unreal/three.js 플러그인을 제공하고, 상호작용 단위 과금(Indie $29/월)이다. 2026년 공식 신제품 소식은 찾지 못했다 — [Cinevva 가이드 (2026-07)](https://app.cinevva.com/guides/ai-npcs-dialogue)

**기타 신규**
- [new][언론] AI and Games Conference 2026(11월, 런던)
  - Arm "Project TALOS": RTS에서 NPC와 전략을 제어하는 온디바이스 AI
  - Wargaming Olga Titova: 전년도 "How to Build a Friend"의 후속
  - 폐막 기조연설: Fenris Creations와 Google DeepMind의 협업을 처음 공개
  - 아직 열리지 않은 행사이다.
  - 출처: [AI and Games (2026)](https://www.aiandgames.com/p/fenris-creations-embark-warhorse)

### Inferences
- [추정] Ubisoft(4B INT4, RTX 4090/5090)와 Krafton(2B 4bit, 8GB)을 함께 보면, 2026년 상용 팀원의 언어층 표준은 **2–4B 4bit 로컬**이다. 클라우드는 품질 기준(교사·judge)으로 물러났다.
- [추정] Tencent의 마이크 켜짐 약 75%와 판당 70메시지는 음성 입력이 실제로 많이 쓰인다는 신호이다. 반면 PUBG 후반 수다 불만은 말의 양을 상황에 따라 줄이는 장치가 필요하다는 신호이다. 둘 다 Thorkell의 "말하기 빈도 config"를 지지한다.
- [추정] 행동하지 않는 동반자(Copilot 콘솔, AVA, 鹅次元)는 이어서 중단되거나 혹평받았다. "같이 플레이한다"는 Thorkell의 핵심이 차별점이라는 기준판 판단은 그대로이다.
- [추정] laya를 zero-shot으로 쓰면 무작위에 가깝다. Thorkell이 laya로 옮기려면 자기 로그로 fine-tune과 온도 보정을 해야 한다. Apple Silicon 포트 지연(약 5–13ms)은 충분히 빠르다.

### Gaps
- Ubisoft Computer Weekly 원문(403)의 지연 수치와 정확한 게재일은 확인하지 못했다.
- 和平精英·小田의 모델 배치(클라우드/단말)와 지연은 공개 자료가 없다.
- PC Game Bar Gaming Copilot의 2026-10 현재 상태를 공식 자료로 확인하지 못했다.
- Player2가 모델을 로컬과 클라우드 중 어디에서 돌리는지는 여전히 공식 문서로 확인하지 못했다.
- EA, Roblox, 국내 넥슨·엔씨·넷마블의 "행동하는" LLM 팀원 사례는 이번에도 찾지 못했다.

---

## Q4. 기술 공개 수준, 한국어·비영어 음성, 지연 예산, 게임과 GPU 공유

### Takeaway
기술을 가장 많이 공개한 곳은 여전히 Krafton(논문 + NVIDIA Q&A + GDC)이고, 그다음은 NVIDIA 블로그와 Ubisoft(GTC 발표 보도)이다. Tencent는 사용자 지표만 공개하고 구조는 숨긴다. 한국어를 실제로 운영한 상용 사례는 PUBG Ally 하나이며, 한국어는 품질과 안전 모두 영어보다 약했다. 게임과 같은 GPU를 쓸 때는 스케줄링, KV-cache 재사용, 4bit 양자화가 공통 해법이다. Apple Silicon에서는 커뮤니티 사례가 "STT를 GPU 대신 CPU에서 돌려야 게임이 끊기지 않는다"는 실측을 남겼다.

### Cited Findings
- [new][공식] 기술 공개 범위
  - Krafton: 논문에 단계별 지연, 메모리, 안전, 설문을 실었다 — [arXiv v2](https://arxiv.org/html/2609.29837v2)
  - NVIDIA: 모델명과 세대 구분만 밝히고 지연 수치는 없다 — [NVIDIA Blog (2026-10-13)](https://blogs.nvidia.com/blog/local-ai-rtx-spark-laptops-software-updates/)
  - Tencent: 사용자 지표만 공개했다 — [京报网 (2026-03-13)](https://news.bjd.com.cn/2026/03/13/11629797.shtml)
- [new][공식] 한국어 운영 지표(PUBG): 운영 대표 세트 무해율 84.1%(영 99.0%), 과잉 거부 5.0% — [arXiv v2](https://arxiv.org/html/2609.29837v2)
- [new][공식] GPU 공유(Krafton): 맞춤 KV-cache 압축, 렌더링과 에이전트의 GPU 스케줄링, prefix 재사용 90.7% — [인벤 (2026-06-22)](https://m.inven.co.kr/webzine/wznews.php?idx=317656&iskin=console), [arXiv v2](https://arxiv.org/html/2609.29837v2)
- [new][커뮤니티] **Apple Silicon + Valheim 실측**(valheim-bjorn README, 2026-10-12)
  - STT: Parakeet TDT 0.6B v3를 parakeet-mlx로 CPU에서 돌리면 "~0.4 s на фразу без рывков в игре"(끊김 없음)
  - 설정 설명: "`gpu` быстрее без игры, но рядом с Valheim подтормаживает"(게임 없이는 GPU가 빠르지만 Valheim 옆에서는 끊긴다)
  - TTS: Silero v5 약 30ms/문장
  - 출처: [GitHub triadecom/valheim-bjorn](https://github.com/triadecom/valheim-bjorn)
- [new][커뮤니티] 같은 저장소의 음성 지연 기법
  - push-to-talk(R)을 누르고 있는 동안 스트리밍으로 인식하고, 발화가 끝나기 전에 모델에 미리 질의한다. 그래서 키를 뗀 뒤 "0,05–0,3 с"에 답한다.
  - 마지막에 문장이 바뀌면 약 1.5s가 걸린다. 이때 바로 "흠" 같은 필러 소리를 내서 들었다는 것을 알린다.
  - 말하는 중에 R을 누르면 끊을 수 있다(barge-in).
  - 출처: [valheim-bjorn](https://github.com/triadecom/valheim-bjorn)
- [new][커뮤니티] Valheim 모드는 Apple Silicon에서 Rosetta(x86_64)로 돈다. "HarmonyX из BepInEx 5 не умеет патчить arm64"(BepInEx 5의 HarmonyX는 arm64를 패치하지 못한다). 그래서 MLX STT 브리지는 `arch -arm64`로 따로 띄운다. Unity 6에서는 `[Preloader.Entrypoint] Type = GameObject`가 필요하다 — [valheim-bjorn](https://github.com/triadecom/valheim-bjorn)
- [new][공식] SkyrimNet Beta27(2026-10-14)
  - STT에 근처 인물과 지명 목록을 프롬프트로 넣는다. 고유명사 인식을 위한 "Name Hints"이고 Local/External Whisper에서 기본으로 켜진다.
  - 다국어 임베딩으로 바꾸자 러시아어 기억 회수(top-5)가 46%에서 93%로 올랐다(영어는 65%에서 76%).
  - 원격 HTTP 호출마다 60–210ms를 줄였다. 대화 한 번에 3–4회 호출하므로 "non-North-American players"에게 더 크다.
  - Gemini 3.x Flash 같은 thinking 모델은 reasoning을 minimal로 둔다. 기본값 medium이 "where most of their latency and output tokens went"였다.
  - 출처: [SkyrimNet Beta27 릴리스](https://github.com/MinLL/SkyrimNet-GamePlugin/releases/tag/vbeta27)
- [unchanged][공식] ACE ASR(Riva v1.1, nemo-conformer-ctc-120m)은 한국어를 포함한다. 단 RTX 전용이다 — [NVIDIA Developer Blog (2026-03-10)](https://developer.nvidia.com/blog/nvidia-rtx-innovations-are-powering-the-next-era-of-game-development/)

### Inferences
- [추정] Thorkell은 M4 Pro 24GB에서 Valheim 클라이언트 둘(호스트 + 봇)을 띄운다. 로컬 음성이나 결정 모델을 붙인다면 **GPU(Metal)를 피하고 CPU나 Neural Engine(Core ML)을 먼저 시도**해야 한다. bjorn의 실측과 laya-CoreML(약 5ms, ANE)이 근거이다.
- [추정] 한국에서 미국 리전 Gemini를 부르는 RTT는 SkyrimNet이 말한 "비북미 플레이어" 조건에 해당한다. 플래너 호출을 묶고 연결을 재사용해야 하며, reasoning 수준은 명시적 config로 둔다(숨은 기본값 금지 규칙).
- [추정] "트롤", "그레이드워프", "목재" 같은 Valheim 한국어 고유명사는 STT가 틀리기 쉽다. SkyrimNet처럼 지각 스냅샷의 근처 개체·지명 표시명(로컬라이즈된 화면 표기만, `$enemy_…` 토큰은 넣지 않음)을 인식 힌트로 넘길 수 있는지 gemini-live 쪽에서 확인할 가치가 있다.

### Gaps
- 한국어 음성 대화의 체감 허용 지연에 대한 게임사 공식 기준은 이번에도 찾지 못했다.
- Gemini Live 같은 클라우드 speech-to-speech를 상용 게임 팀원에 쓴 지연 실측은 찾지 못했다(PUBG는 GPT-Live를 미래 후보로만 언급).
- inZOI Mac판의 Core ML Smart Zoi가 게임 프레임에 주는 부담은 공개 자료가 없다.

---

## Q5. 모드·오픈소스 — Valheim, Minecraft, Skyrim의 LLM 동료와 구조

### Takeaway
2026-09~10월 사이 Valheim LLM 동료가 한꺼번에 나왔다.
- **Sapienheim**: Claude, 전용 서버 측 NPC
- **Бьёрн(valheim-bjorn)**: Claude Haiku, macOS 전용, 로컬 STT/TTS
- **ValheimAI**: 두 번째 Steam 계정 접속, 뼈대만 있음
- **valheim-agent**: 로컬 LLM, 미컴파일
- **Palheim**: "진짜 멀티플레이어로 접속, 친구는 바닐라"를 내건 랜딩 페이지

Palheim과 ValheimAI는 Thorkell과 같은 "두 번째 클라이언트 = 진짜 플레이어" 발상이다. 다만 공개된 구현 증거는 없거나 뼈대뿐이다. 실제로 돌아가는 LLM 동료(Sapienheim, bjorn)는 모두 **NPC 프리팹(MonsterAI) 위에 스킬을 얹고, LLM은 이벤트 단위로 계획만** 한다. Skyrim에서는 SkyrimNet이 Jev를 결정 모델로 넣어, 대사는 LLM이 쓰고 "누가·언제 말할지"는 decision model이 정하는 분업을 처음 대규모로 배포했다.

### Cited Findings

**Valheim — LLM 동료 (신규)**
- [new][공식] **Sapienheim**(Thunderstore 2026-10-06 첫 게시, v0.1.7 2026-10-10, 누적 다운로드 51, MIT, "AI Generated" 카테고리)
  - 구조: "players ──chat──▶ Valheim dedicated server + Sapienheim mod ◀──TCP (private)──▶ agent ──▶ Claude API"
  - 모드(C#, BepInEx/Harmony/Jötunn)가 서버에서 경로 탐색, 전투, 채집, 제작, 건축, 포털, 인벤토리를 실행한다.
  - Python 에이전트가 채팅과 이벤트를 Claude tool call로 바꾼다. 원문: "Calls are event-driven and rate-limited, never per frame". 분당 호출 예산이 있다.
  - 공유 비밀 `AGENT_TOKEN`을 쓰고, 포트 7777을 인터넷에 노출하지 말라고 한다. 모든 플레이어가 모드를 설치해야 한다.
  - `agent/scripts/scenario.py`로 LLM 없이 헤드리스 시나리오를 돌린다. 모드와 에이전트는 연결할 때 프로토콜 버전을 서로 확인한다.
  - 출처: [Thunderstore](https://thunderstore.io/c/valheim/p/sapiteam/Sapienheim/), [GitHub Brimbles/sapienheim](https://github.com/Brimbles/sapienheim)(2026-10-17 확인)
- [new][공식] **Бьёрн / valheim-bjorn**(GitHub 생성 2026-10-11, 최종 push 2026-10-12, 별 1, MIT)
  - 대상: macOS Apple Silicon 전용, Valheim 1.0, 러시아어
  - 두뇌: `claude-haiku-5-5`(기본) 또는 `claude-sonnet-5-5`. 스트리밍 JSON `{say, plan, remember}`를 돌려받고, 역할·규칙·기억은 프롬프트 캐시에 둔다.
  - 몸: 플레이어 프리팹 복사본이다. `Player` 대신 `Humanoid`와 바닐라 `MonsterAI`를 붙였고, 작업은 `MonsterAI.UpdateAI` 위에 얹었다. 자원은 물리 질의가 아니라 `ZNetScene` 전체에서 찾는다(70m, 몇 분의 1 ms).
  - 기억: 세계와 캐릭터별 3층(최근 발화 원문, 사실, 연대기). 이벤트가 충분히 쌓이면 백그라운드에서 요약한다.
  - LLM 브리지가 없으면 키워드 명령만 이해하고 말은 하지 않는다.
  - 리더가 50m 넘게 떨어지면 리더 곁으로 **텔레포트**한다.
  - 비용: "Одна реплика стоит доли цента"(한 마디에 1센트 미만)
  - 출처: [GitHub triadecom/valheim-bjorn](https://github.com/triadecom/valheim-bjorn)
- [new][공식] **Palheim**(GitHub 2026-09-11, 정적 랜딩 페이지만 있음)
  - 소개: "AI companion that joins your Valheim world as a real multiplayer player. Your friends stay on vanilla clients"
  - 원칙: "Invite-as-player", "No BepInEx product path"
  - 상태: "Private dogfood · Valheim 1.0". 대기자 폼은 localStorage stub이다. 기술 정보는 없다.
  - 출처: [GitHub imkirkjames/palheim](https://github.com/imkirkjames/palheim)
- [new][공식] **ValheimAI**(GitHub 2026-09-29, Windows)
  - 목표: "Run a second Steam/Valheim account as an AI-controlled teammate"
  - 구조: `Valheim -> BepInEx plugin -> localhost WebSocket -> Controller -> planner/LLM`. 원문: "The LLM chooses high-level goals. Deterministic local code executes movement…"
  - "early development scaffold"이다.
  - 출처: [GitHub Dahuchsi/ValheimAI](https://github.com/Dahuchsi/ValheimAI)
- [new][공식] **valheim-agent**(GitHub 2026-09-11)
  - 출발점: "Local LLM inference takes 1–3 seconds. Valheim's parry window is a few hundred milliseconds."
  - 분업: 플래너 약 0.3Hz, 컨트롤러는 프레임 단위
  - 스크린샷 비전은 버렸다. 이유는 "~1000 vision tokens per frame … 3–6 s round trip"이다.
  - 브리지는 NDJSON/TCP이다. "Nothing here has ever been compiled or run."
  - 출처: [GitHub kei781/valheim-agent](https://github.com/kei781/valheim-agent)
- [new][공식] **valheim-combat-bot**(2026-09-27)
  - 화면만 읽는다. OpenCV 60fps(한 바퀴 약 1ms)로 막기와 반격을 하고, 로컬 VLM(Ollama: moondream, qwen2.5vl)이 6초마다 전략을 고른다.
  - 체력 20% 미만이면 AI 판단과 상관없이 정지한다.
  - VLM이 게임을 끊기게 하면 `IA_NUM_GPU = 0`으로 CPU에서 돌린다.
  - 출처: [GitHub BenjAngelone/valheim-combat-bot](https://github.com/BenjAngelone/valheim-combat-bot)

**Valheim — 스크립트 동료 (재확인/신규)**
- [unchanged] Offline Companions(ProfMags) v1.3.0, 누적 30,913(기준판 30.3K) — [Thunderstore API 확인 (2026-10-17)](https://thunderstore.io/c/valheim/p/ProfMags/Offline_Companions/)
- [new] **Offline Companions Reborn**(Maddhattr, 2026-09-27 첫 게시, v1.5.5, 누적 5,745). Valheim 1.0용 재작업이다. 원문: "acting like another player" — [Thunderstore](https://thunderstore.io/c/valheim/p/Maddhattr/Offline_Companions_Reborn/)
- [new] **Quad's Companion**(2026-10-10, v0.24.6, 누적 661, "made with Claude Code")
  - LLM 없는 스크립트이다.
  - 전투: 적마다 휘두름을 배운 타이밍 패리, 구르기, 백스탭, 활의 리드와 낙차 보정
  - 이동: 포털·동굴·배를 따라가고, 끼임에서 스스로 빠져나온다.
  - 출처: [Thunderstore](https://thunderstore.io/c/valheim/p/Quads_Lab/Quads_Companion/), [소스](https://github.com/HardHeadHackerHead/valheim-mods/tree/main/mods/AICompanion)
- [changed] VikingNPC(RustyMods)는 **deprecated**, 누적 79,671이다. VikingNPC Continued는 v0.4.1(2026-09-23), 누적 1,153 — [Thunderstore API (2026-10-17)](https://thunderstore.io/c/valheim/p/SephrinMods/VikingNPC_Continued/). Vikings for Hire는 v1.6.2(2026-10-15), 누적 8,766 — [Thunderstore](https://thunderstore.io/c/valheim/p/Worobeyko/VikingsForHire/)
- [unchanged] Thrall은 deprecated이고 마지막 버전 1.0.11(2024-11-07), 누적 4,833. 기준판 Gap이던 마지막 업데이트 날짜가 확인됐다 — [Thunderstore](https://thunderstore.io/c/valheim/p/ego_ai/Thrall/)
- [unchanged] ValheimMCP v0.2.1(갱신 2026-09-10, 누적 283) — [Thunderstore](https://thunderstore.io/c/valheim/p/idontunderstand/ValheimMCP/)
- [new] 에이전트 구동 테스트 브리지
  - ValAgentBridge: Thunderstore v1.7.0(2026-10-15). "enter worlds, act as the player, run console commands"
  - ModTestBridge(2026-10-07)
  - ClaudeHeim(2026-09-22): 시나리오를 넣으면 스크린샷, UI 덤프, pass/fail JSON이 나온다.
  - 출처: [Thunderstore ValAgentBridge](https://thunderstore.io/c/valheim/p/BarryWhite/ValAgentBridge/), [GitHub tmac1973/ModTestBridge](https://github.com/tmac1973/ModTestBridge), [GitHub FNGApex/ClaudeHeim](https://github.com/FNGApex/ClaudeHeim)

**Valheim 본체 (Thorkell에 직접 영향)**
- [new][공식] Iron Gate가 Patch 1.0.17(2026-10-06, 소규모 버그 수정)과 **Patch 1.0.20(2026-10-15, 트로피 드롭 수정. "small delay with Mac App Store for this patch"라며 crossplay 관련 안내를 붙임. 안내 뒷부분은 요약이 잘려 못 읽음)**을 공개했다. 1.0.16은 2026-09-25이다 — [Steam 뉴스 1.0.17](https://steamstore-a.akamaihd.net/news/externalpost/steam_community_announcements/1845383656396226), [Steam 뉴스 1.0.20](https://steamstore-a.akamaihd.net/news/externalpost/steam_community_announcements/1846651706676865), [Valheim Steam 뉴스](https://store.steampowered.com/news/app/892970)
- [new][커뮤니티] Thunderstore 모드 설명에 "Built for Valheim 1.0.17"이 등장했다 — [Thunderstore API (2026-10-17)](https://thunderstore.io/c/valheim/api/v1/package/)

**Minecraft**
- [changed][공식] Mindcraft(kolbytn)
  - 최신 릴리스 v0.1.4(2026-03-20), 최종 push 2026-10-03, 별 5,896, MIT
  - 기준판에 없던 커뮤니티판 mindcraft-ce는 2026-10-10 push. 브랜치에 function calling과 RAG가 있다.
  - LLM이 코드를 써서 실행한다. README 경고: "sandboxed, but still vulnerable to injection attacks", 기본값은 끔.
  - 출처: [GitHub kolbytn/mindcraft](https://github.com/kolbytn/mindcraft), [GitHub mindcraft-ce](https://github.com/mindcraft-ce/mindcraft-ce)
  - [커뮤니티] 로컬 Ollama 구성에서는 Andy-4 모델을 권한다 — [askaillex (2026-07)](https://askaillex.com/guides/local-ai-plays-minecraft/)
- [unchanged][커뮤니티] Player2NPC v1.4.0(2026-07-17), CurseForge 누적 242.4K. GitHub 저장소의 최종 push는 2026-01-06이다 — [CurseForge](https://www.curseforge.com/minecraft/mc-mods/player2npc), [GitHub elefant-ai](https://github.com/orgs/elefant-ai/repositories)

**Skyrim**
- [new][공식] **SkyrimNet Beta26(2026-10-03)**
  - "SkyrimNet now uses **TypeSafe's Jev**, a dedicated decision model" — 누구에게 말하는지, 다음 화자, 감정 선택을 Jev가 맡는다.
  - "Your chosen dialogue models still write what characters say"
  - 다음 화자 결정은 언제나 **침묵**을 고를 수 있다.
  - 확신도 검사 2개(기본 끔)
  - Jev는 무료 등급이 없다. 결정 요청이 실패하면 이전 채팅 기반 Meta 방식으로 폴백한다.
  - 모드 작성자용 typed decision API(choice / yes-no / score)가 있다.
  - 출처: [SkyrimNet Beta26 릴리스](https://github.com/MinLL/SkyrimNet-GamePlugin/releases/tag/vbeta26-rc4)
- [new][공식] **SkyrimNet Beta27(2026-10-14)**
  - Speaker Selector Strictness를 넣었다. Chatty / Balanced(기본) / Strict(이름이 불리지 않으면 침묵이 기본)
  - 그 밖의 항목(STT 이름 힌트, 다국어 임베딩, reasoning effort, HTTP 지연 감소, 프롬프트 캐시)은 Q4 참조
  - 첫 모델이 멈추면 백업 모델로 넘긴다. 프리셋은 OpenRouter 양자화 하한을 fp8로 둔다.
  - 출처: [SkyrimNet Beta27 릴리스](https://github.com/MinLL/SkyrimNet-GamePlugin/releases/tag/vbeta27)
  - GitHub 별 349, 최종 push 2026-10-16(확인 2026-10-17)
- [changed][공식] Mantella 공식 최신 버전은 v0.14(2026-04-21)이고 최종 push는 2026-07-16, AGPL-3.0이다 — [GitHub releases](https://github.com/art-from-the-machine/Mantella/releases)
  - [커뮤니티] 구조: 별도 `Mantella.exe`(localhost:4999), STT는 Moonshine/Whisper(비영어는 Whisper 권장), LLM은 로컬(koboldcpp)이나 클라우드(OpenRouter 등)
  - 행동은 20가지 넘게 있다(follow, attack, trade, travel…).
  - 대화가 끝나면 NPC별 요약을 텍스트 파일로 저장한다.
  - 실시간 가이드 목표는 "less than 0.5 seconds"
  - 출처: [Arcanum RPGs 비교 (2026-09-26)](https://arcanumrpgs.com/blog/skyrim-ai-npc-mods/)
  - [커뮤니티] 3년 동안 41만 다운로드 — [한국일보 (2026-07-23)](https://www.hankookilbo.com/news/article/A2026072311080002063)
- [changed][커뮤니티] CHIM은 Nexus에서 2026-09-26에 갱신됐다. SKSE 플러그인과 CHIM Server 브리지 구조이고, function calling 행동을 쓴다("trade with me, move here, attack that monster") — [Nexus (검색 요약)](https://www.nexusmods.com/skyrimspecialedition/mods/126330), [Arcanum RPGs (2026-09-26)](https://arcanumrpgs.com/blog/skyrim-ai-npc-mods/)

### Inferences
- [추정] **경쟁 구도**: "진짜 플레이어로 접속, 친구는 바닐라"를 공개적으로 내건 프로젝트가 Palheim(랜딩)과 ValheimAI(뼈대) 둘 생겼다. 둘 다 2026-10-17 기준으로 실행 가능한 공개 구현이 없다. Thorkell은 이미 실게임 시나리오(S0·S0b·S1)를 돌렸으므로 공개 증거로는 여전히 앞선다. 차별점은 한국어 음성, Mac, 정보 동등성, 텔레포트·지급 금지이다.
- [추정] 돌아가는 LLM 동료(Sapienheim, bjorn)는 모두 NPC 프리팹이라 **텔레포트와 지급 같은 치트에 기댄다**(bjorn은 50m 텔레포트, 화살 매일 리필). Thorkell 하드 규칙 4는 그 길을 막는다. 그래서 이동·끼임 복구는 Quad's Companion·Offline Companions Reborn 같은 스크립트 모드의 기법(끼임 탈출, 포털·문·배 따라가기)을 참고해야 한다.
- [추정] SkyrimNet은 "대사 = 생성 모델, 누가·언제·말할지 말지 = decision model(침묵 선택지 포함)"으로 나눴다. Thorkell에서 Jev가 맡을 수 있는 범위를 잘 보여 준다. 단 SkyrimNet은 결정 실패 때 **조용히** 채팅 모델로 폴백한다. Thorkell 규칙 7(에러를 삼키지 않는다, 폴백은 명시적 config)과 다르니 그 부분은 따라 하지 않는다.
- [추정] Valheim 1.0.17·1.0.20이 나왔으므로, Thorkell의 `tested-versions.json` 게이트(1.0.16)는 지금 arm을 막을 것이다. `thorkell verify-api`를 다시 돌리고 새 빌드 해시를 확인해야 한다.

### Gaps
- Sapienheim과 bjorn의 실제 지연·비용 실측(시간당 비용)은 README에 정량값이 없다(bjorn은 "1센트 미만/마디"뿐).
- Palheim의 기술 구조(어떤 백엔드로 바닐라 클라이언트처럼 접속하는지)는 공개되지 않았다.
- Nexus Mods의 Valheim LLM 모드는 이번에도 체계적으로 검색하지 못했다(Thunderstore API와 GitHub 위주).
- CHIM의 지연과 다국어 지원 정량값은 찾지 못했다.

---

## Q6. Thorkell 설계 교훈 (2026-10-17 갱신분)

### Takeaway
새 자료가 기준판 교훈(BT/스킬 실행층 + 이벤트 구동 언어층, 알려진 명령은 플래너를 거치지 않음, 정보 우선, 지각 일관성)을 더 강하게 뒷받침한다. 이번에 새로 더할 것은 일곱 가지이다.
1. 단계별 지연 계측
2. 말하는 동안 미리 질의하고 필러 소리 내기
3. "말할지 말지"를 decision model과 침묵 선택지로 정하기
4. Gemini Flash reasoning을 명시적으로 최소화하기
5. 한국어 전용 안전 시험
6. Apple Silicon에서 로컬 음성·결정 모델은 CPU/ANE 우선
7. Valheim 1.0.20 대응

### Cited Findings
- [new][공식] 실패가 생긴 지점: 시킨 일을 계속함, "okay" 후 불이행, 후반 수다, 도구 호출 중 새 발화 처리 불가 — [arXiv v2](https://arxiv.org/html/2609.29837v2)
- [new][공식] 과부하 때 우선순위 이벤트만 받는다 — [arXiv v2](https://arxiv.org/html/2609.29837v2)
- [new][커뮤니티] 미리 질의하면 0.05–0.3s에 답하고, 바뀌면 약 1.5s에 필러 소리를 낸다. 말하는 중에 끊을 수 있다 — [valheim-bjorn](https://github.com/triadecom/valheim-bjorn)
- [new][공식] Jev로 화자와 침묵을 정하고, Strictness로 수다량을 조절한다 — [SkyrimNet Beta26](https://github.com/MinLL/SkyrimNet-GamePlugin/releases/tag/vbeta26-rc4), [Beta27](https://github.com/MinLL/SkyrimNet-GamePlugin/releases/tag/vbeta27)
- [new][공식] Gemini 3.x Flash의 reasoning 기본값(medium)이 지연과 출력 토큰의 대부분을 차지했다 — [SkyrimNet Beta27](https://github.com/MinLL/SkyrimNet-GamePlugin/releases/tag/vbeta27)
- [new][공식] Sapienheim은 이벤트 구동, 분당 호출 예산, 헤드리스 시나리오(LLM 없이), 프로토콜 버전 핸드셰이크를 쓴다 — [Sapienheim](https://github.com/Brimbles/sapienheim)

### Inferences
1. [추정] **단계별 지연 계측.** "리더 발화 끝 → STT 확정 → 결정(Jev/규칙) → 플래너(있으면) → 첫 소리·첫 행동"을 이벤트마다 타임스탬프로 남긴다. PUBG 기준선(on-device 1.62s, 클라우드 3.36s, LM p90 0.91s)과 비교한다. 응답 속도 2.93/5라는 결과는 1.6초도 느리게 느껴진다는 뜻이다.
2. [추정] **듣는 중에 미리 결정하기.** gemini-live 스트리밍 전사 중간본으로 알려진 명령("따라와", "기다려")을 미리 매칭해 둔다. 확정되면 바로 실행하고, 바뀌면 짧은 필러 대사로 "들었다"는 신호를 준다. 필러 사용 여부는 config로 둔다.
3. [추정] **말할지 말지를 결정 모델에.** Jev 선택지에 "침묵"을 넣고, 기본은 Balanced이되 전투 중에는 Strict로 둔다. PUBG 후반 수다 불만과 Tencent 판당 70메시지 사이의 균형점은 리더별 설정으로 둔다. Jev 실패 때 채팅 모델로 조용히 넘어가지 말고, 오류를 보고하거나 config로 명시한 대체 경로만 쓴다.
4. [추정] **플래너 reasoning을 명시적으로 설정.** gemini-3.8-flash 호출에 reasoning 수준을 config로 박아 둔다(숨은 기본값 금지). 하루 20회 무료 한도에서는 출력 토큰 절감이 곧 호출 여유이다.
5. [추정] **한국어 안전 세트.** PUBG의 한국어 운영 무해율 84.1%가 근거이다. 친구 crossplay 채팅에 나갈 출력과 들어올 입력을 대상으로 한국어 적대 프롬프트 회귀 세트를 둔다. 과잉 거부율(PUBG 한국어 5.0%)도 함께 잰다.
6. [추정] **도구 호출 중 새 발화.** PUBG처럼 "도구 실행 중에는 못 들음"이 되지 않게 한다. 리더의 "멈춰/그만"은 Body 반사 수준에서 바로 선점하고, 진행 중인 스킬에 typed 취소 결과를 낸다. Thorkell의 즉시 명령 경로와 같다.
7. [추정] **Apple Silicon 자원 배분.** 로컬 STT, TTS, laya를 붙일 때는 CPU 또는 Core ML(ANE)을 먼저 시도하고, Metal GPU는 두 Valheim 클라이언트에 남긴다. 근거: bjorn 실측(GPU STT는 Valheim 옆에서 끊김), laya-CoreML P50 4.98ms, inZOI Mac의 Core ML Smart Zoi.
8. [추정] **기억 층.** 리더 프로필(이름, 호칭, 선호)과 세계 연대기를 이벤트가 쌓일 때 백그라운드에서 요약 갱신한다(bjorn, PUBG 장기 기억). 이때 정보 동등성에 맞는 관찰만 기록한다.
9. [추정] **버전 게이트.** Valheim 1.0.17(10-06), 1.0.20(10-15)이 나왔다. `tested-versions.json`과 `RequiredApi.json`을 새 빌드에서 확인하기 전에는 실게임 시나리오를 arm하지 않는다(규칙 6).
10. [추정] **경쟁 대비.** Palheim·ValheimAI가 같은 발상을 공개했다. Thorkell의 차별점(한국어 음성, Mac, 정보 동등성, 치트 없음)을 README나 데모 증거로 남겨 두면 좋다.

### Gaps
- 상용 AI 팀원의 "플레이어 시간당" 공식 비용은 Krafton의 경기당 수치($5.14–7.10 클라우드, $0 로컬; [Inven Global (2026-09-29)](https://www.invenglobal.com/articles/26592/built-a-teammate-got-a-chat-partner-kraftons-first-scorecard-for-pubg-ally), 기준판과 같음) 말고는 여전히 없다.
- gemini-live가 인식 힌트(고유명사 목록)를 받는지, 받는다면 어떤 형식인지는 이번 조사 범위 밖이라 확인하지 않았다.
