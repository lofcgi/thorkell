# 상용 AI 팀원(co-playable character)·미들웨어·Valheim AI 동료 모드 (기준일 2026-10-10)

조사일: 2026-10-11. 표기 규칙: **[공식]** 개발사·플랫폼 자체 발표/논문/문서, **[언론]** 게임·테크 매체, **[커뮤니티]** 블로그·포럼·모드 페이지·집계 사이트, **[추정]** 이 노트 작성자의 추론. 검색 요약에서만 확인하고 원문을 열지 못한 항목은 "(검색 요약)"이라고 적었다.

## Q1. KRAFTON PUBG Ally(NVIDIA ACE)와 inZOI Smart Zoi — 출시 상태, 구조, 지연, 하드웨어, 반응

### Takeaway
PUBG Ally는 2026-06-17~07-01(NVIDIA 표기로는 06-30까지) 2주 동안 Sanhok 맵의 "Ally Duo" 아케이드 베타로 출시됐고, 정식 상시 모드는 아직 없다. 구조는 "System 1 = 결정적 behavior tree(이동·조준·전투), System 2 = 이벤트 구동 2B급 SLM 에이전트(16개 bounded tool)"이며, STT·SLM·TTS가 모두 RTX 8GB+ GPU에서 로컬로 돈다. 음성 1회 왕복은 약 1.6초(클라우드 3.4초)였다. 플레이어는 Ally를 "팀원"(18.5%)보다 "도구"(50%)로 봤고, 전투 평가가 가장 낮았다(2.58/5).

### Cited Findings
**일정·모드**
- [공식] 2026-06-17 "Ally Duo" 베타 시작. 2인 팀에서 AI 캐릭터 "Ella"와 Sanhok을 플레이하고, 음성으로 이동·아이템 수집·전략을 협의한다. 기간 06-17~07-01, 언어는 한국어·중국어·영어 — [Digital Today (2026-06-16)](https://www.digitaltoday.co.kr/en/view/64940/krafton-introduces-ai-partner-in-pubg-starts-pubg-ally-beta-service)
- [공식] NVIDIA 공지는 종료일을 "until June 30th, via Steam"으로 적었다(Krafton 쪽 07-01과 하루 차이) — [NVIDIA GeForce News (2026-06-17)](https://www.nvidia.com/en-us/geforce/news/pubg-ally-ai-teammate-beta-available-now/)
- [공식] GDC 2026(03-09~13) 세션 "Building a Co-Playable Character: 'PUBG' Ally, an AI Teammate Powered by NVIDIA ACE"에서 STT→SLM→TTS 파이프라인을 발표했다 — [GDC schedule](https://schedule.gdconf.com/session/building-a-co-playable-character-pubg-ally-an-ai-teammate-powered-by-nvidia-ace-presented-by-nvidia/917523)

**구조 (논문: arXiv 2609.29837, 2026-09-24)**
- [공식] 2층 구조이다. System 2(LM agent)는 이벤트 구동으로 상위 결정을 내리고 System 1(behavior tree)은 의도를 매 틱 제어로 바꾼다. "System 2 sends intent to System 1 and receives state in return." — [PUBG Ally 논문](https://arxiv.org/html/2609.29837v1)
- [공식] LM은 bounded tool 16개만 부른다. 6그룹으로 나뉜다: 경기 관찰 7, 지식·기억 2, 행동 실행 2(`execute_action()`), 플레이어 소통 3, 에이전트 루프 제어 1, 안전 제어 1 — [논문](https://arxiv.org/html/2609.29837v1)
- [공식] 관찰은 전체 상태가 아니라 "focused views of decision relevant match state"를 텍스트로 준다. 예: "Two enemies are 40 m east. One can be engaged now." 항목은 전투 요약, 장비·인벤토리, 플레이어 핑, 자기장 상태, 위치·이동 상태이다 — [논문](https://arxiv.org/html/2609.29837v1)
- [공식] 에이전트는 플레이어 발화, 게임 상태 변화, 발화 수명주기, 행동 결과 이벤트에 깨어난다. 루프는 `compact()` 호출로 끝나고, 못 끝낸 일은 짧은 plan으로 압축해 다음 루프로 넘긴다. 사실은 상태로 들고 있지 않고 매 루프마다 tool로 새로 관찰한다 — [논문](https://arxiv.org/html/2609.29837v1)
- [공식] "Reactivity priors": 이벤트 유형마다 말·행동 반응을 require/recommend/optional/do-not으로 지정한다. 재학습 없이 조정할 수 있다 — [논문](https://arxiv.org/html/2609.29837v1)
- [공식] 프롬프트 순서는 system → tool 정의 → 이벤트 이력 → 이월 plan → 현재 입력이다. KV cache 재사용을 노린 배치이다. 컨텍스트는 약 5,000 토큰이고 LM 추론은 동시에 1개만 돈다 — [논문](https://arxiv.org/html/2609.29837v1)
- [공식] behavior tree는 틱 간 상태 유지, 우선순위 선점(preemption), 지속 선호용 모드 변수, 실패 복구 반응 평가를 갖춘다(부록 C) — [논문](https://arxiv.org/html/2609.29837v1)
- [공식] NVIDIA 설명: "a traditional, fast-paced behavior tree that handles immediate tactical actions such as movement, precise aiming, and instant combat responses"와 "NVIDIA ACE, which drives the teammate's cognitive abilities"의 결합 — [NVIDIA GeForce News](https://www.nvidia.com/en-us/geforce/news/pubg-ally-ai-teammate-beta-available-now/)

**모델·학습**
- [공식] 배포 SLM: "NVIDIA Mistral-Nemo-Minitron, a 2 billion parameter small language model", STT "lightweight NVIDIA Parakeet", TTS "custom KRAFTON in-house" — [NVIDIA GeForce News](https://www.nvidia.com/en-us/geforce/news/pubg-ally-ai-teammate-beta-available-now/)
- [공식] 논문 기준으로 언어마다 학생 모델이 따로 있다. 영어 Mistral-NeMo-Minitron-2B-128K, **한국어 Kanana 1.5 2.1B**, 중국어 Qwen3 1.7B. 중간 교사는 8B(영어 Minitron-8B, 한국어 Kanana 1.5 8B, 중국어 Qwen3 8B)이고, 초기 교사는 Gemma 4 31B, 품질 기준은 Claude Opus이다 — [논문](https://arxiv.org/html/2609.29837v1)
- [공식] 데이터는 PC방에서 28일 동안 1,046명이 38,956세션을 플레이하며 모았다. 교사 예시 약 464K(교사 rollout 420K + 합성·안전 44K), 학생 반복 교정 예시 313K. 학습은 SFT(8B) → off-policy distillation(2B) → on-policy distillation 순서이고 KL은 T=1.0이다 — [논문](https://arxiv.org/html/2609.29837v1)
- [공식] 평가는 규칙 기반 검사(tool 호출 순서, 프로토콜 준수)와 LLM judge(Gemini 3 Flash, GPT-5.1, temperature 0)로 했다. 차원은 factual grounding, 게임 이벤트 반응, 의도 이해, 지시 이행, 궤적 품질이다. 후보를 고른 뒤 PC방에서 대규모 A/B를 돌렸다 — [논문](https://arxiv.org/html/2609.29837v1)
- [언론] 4bit 양자화 모델 크기 1.6–2.1GB — [Inven Global (2026-09-29)](https://www.invenglobal.com/articles/26592/built-a-teammate-got-a-chat-partner-kraftons-first-scorecard-for-pubg-ally)

**하드웨어·지연·비용**
- [공식] "RTX GPUs with at least 8GB of VRAM". 모든 모델이 "locally on RTX GPUs"에서 돌고, 그래픽과 동시 추론하는 in-game inferencing toolset을 쓴다 — [NVIDIA GeForce News](https://www.nvidia.com/en-us/geforce/news/pubg-ally-ai-teammate-beta-available-now/)
- [언론] 최소 RTX 2080 Ti / RTX 3060, 권장 RTX 4070(12GB) — [tbreak / TweakTown 검색 요약](https://tbreak.com/pubg-ally-ai-teammate-rtx-requirements/)
- [공식] 음성 1회 교환 약 1.6초(on-device), 클라우드 구성 3.4초 — [논문](https://arxiv.org/html/2609.29837v1)
- [언론] RTX 4060급에서 1회 약 1.6초, LM 6라운드 추론은 on-device 5초 미만·클라우드 10초 초과. 블라인드 선호는 on-device(v1) 69.5%, 클라우드 18.8%. 클라우드 API 비용(Claude Opus 4.8)은 경기당 $5.14–$7.10, on-device는 $0 — [Inven Global (2026-09-29)](https://www.invenglobal.com/articles/26592/built-a-teammate-got-a-chat-partner-kraftons-first-scorecard-for-pubg-ally)

**반응·성과**
- [공식] 141개국 플레이어에게 닿았다. 플레이 확인 응답자의 추천 문항에서 긍정이 부정보다 25.1%p 높았다. 관계 인식은 "teammate" 18.5%, "companion" 31.5% — [논문](https://arxiv.org/html/2609.29837v1)
- [언론] NPS +25.1%p(초기 +8%p → 마지막 단계 +36%p). 항목 점수: 전투 2.58/5(최저), 상황 판단 2.88, 응답 속도 2.93, 명령 수행 2.99. "도구" 인식 50.0%. 가장 좋은 점은 "정보/전술" 51%, "대화 상대" 28%. Krafton 다음 단계: push-to-talk를 full-duplex 음성으로 바꾸고, 구조를 로보틱스(Ludo Robotics 'Ludi 0.1')로 확장 — [Inven Global](https://www.invenglobal.com/articles/26592/built-a-teammate-got-a-chat-partner-kraftons-first-scorecard-for-pubg-ally)
- [언론] PCGamesN 실사용기(Paul Kelly, 2026-06-22): 200m 넘게 떨어진 적을 나무 너머로 지도에 표시했지만, 다른 순간에는 보이는 적을 "없다"고 했다. 보급품을 가져갔다는 안내 없이 말을 바꿨고, 원거리 교전 지시를 따르지 않았다. 게임 밖 주제(레시피 등)는 거부했다. 총평은 "a soulless companion that feeds me inconsistent information with zero banter" — [PCGamesN](https://www.pcgamesn.com/playerunknowns-battlegrounds/ai-teammate)
- [언론] 다른 매체는 반대로 Ella가 "painfully artificial", "borderline sycophantic", 지나치게 수다스러워 경쟁 플레이 흐름을 끊는다고 비판했다. 근거리에서 적이 쏘는데 가만히 서 있었다는 보고도 있다 — [TechRadar](https://www.techradar.com/computing/gpu/forget-npcs-now-we-have-cpcs-co-playable-characters-or-ai-teammates-in-pubg-courtesy-of-nvidia-ace-tech-but-im-not-impressed-so-far), [talkesport](https://www.talkesport.com/news/pubg/pubg-ally-duo-beta-ai-companion-ella/) (둘 다 검색 요약. 본문은 403/잘림)

**inZOI Smart Zoi / NARAKA**
- [공식] Smart Zoi는 "a .5B billion parameter Mistral NeMo Minitron small language model"로 돌고 GeForce RTX 전용 on-device이다. 기능은 성격 기반 반응, 경험에 따른 일과 조정, 실시간 "inner thoughts" 표시, 자유 텍스트 입력이다. inZOI는 2025-03-28 출시 — [NVIDIA GeForce News](https://www.nvidia.com/en-gb/geforce/news/nvidia-ace-naraka-bladepoint-inzoi-launch-this-month/)
- [공식] 같은 글: "runs 100% locally ... no need to communicate with a data center ... eliminating the need for subscription fees" — [NVIDIA GeForce News](https://www.nvidia.com/en-gb/geforce/news/nvidia-ace-naraka-bladepoint-inzoi-launch-this-month/)

### Inferences
- [추정] Krafton 구조는 Thorkell의 "Body 반사(결정적) + brain 계획"과 거의 같은 분업이다. 다른 점은 LM이 직접 부르는 tool이 16개뿐이라는 것, 그리고 관찰도 tool로 당겨 온다는 것(pull)이다. Thorkell의 typed command와 이벤트 스트림도 이 크기로 묶어 두면 검증과 평가가 쉬워진다.
- [추정] Ella의 "보이는 적을 없다고 함" 실패는 대화(LM 컨텍스트)와 행동(BT 지각)이 다른 시점의 상태를 본 데서 생긴 것으로 보인다. Thorkell은 말로 하는 보고를 같은 지각 스냅샷(정보 동등성 규칙)에서 만들고 시각을 달아야 한다.
- [추정] 응답 속도가 2.93/5에 그쳤으니 1.6초도 "느리다"는 체감이다. 그래서 아는 명령은 플래너를 우회해야 한다는 Thorkell의 기존 교훈이 상용 사례에서도 확인된다.
- [추정] 한국어 2B 학생 모델로 Kanana 1.5 2.1B가 실전에 쓰였다. Thorkell이 나중에 로컬 소형 모델을 고를 때 한국어 후보가 된다(Mac에서는 MLX/llama.cpp로 돌려야 하고, ACE 런타임은 못 쓴다).

### Gaps
- Krafton이 공개한 명령 성공률 수치는 찾지 못했다(논문 요약에도 없음).
- PUBG Ally 정식 출시(상시 모드) 일정은 2026-10-10까지 확인된 발표가 없다.
- STT/TTS·SLM 구성요소별 지연과 VRAM 분해는 공개 자료에서 찾지 못했다.
- inZOI Smart Zoi의 성능 부담이나 플레이어 반응은 신뢰할 만한 정량 자료를 찾지 못했다(커뮤니티 일반론만 있음).

## Q2. NVIDIA ACE (2026) — on-device 모델, Game Agent SDK, Mac 지원, 이식 가능한 부분

### Takeaway
2026년 ACE의 중심은 "RTX GPU에서 게임과 같이 도는 소형 모델"이다. 3월에 Nemotron 3 Nano 4B, Riva ASR v1.1(한국어 포함), Chatterbox 350M TTS가 나왔고, 6월 16일에 C/C++ 오픈소스 **ACE Game Agent SDK beta**(Agent/Chat/RAG API, Qwen 3.5 4B, nemo-conformer-ctc-120m, Chatterbox Turbo 350M)와 UE5 플러그인이 공개됐다. macOS 지원 언급은 어디에도 없다. Mac에서 쓸 수 있는 것은 공개 가중치 모델과 설계 패턴뿐이다.

### Cited Findings
- [공식] 2026-03-10 발표 모델: NVIDIA Riva v1.1 ASR(메모리 사용량 축소, 영·중·**한**·불·독·이·일), Nemotron 3 Nano 4B SLM("strong instruction following, game agent capabilities, and VRAM scaling", hybrid reasoning·thinking budget), Resemble.ai Chatterbox v1.0.0 TTS 350M(paralinguistic tag, zero-shot voice cloning). 파트너는 Creative Assembly(Total War: Pharaoh), Krafton(PUBG, inZOI), Meaning Machine — [NVIDIA Developer Blog (2026-03-10)](https://developer.nvidia.com/blog/nvidia-rtx-innovations-are-powering-the-next-era-of-game-development/)
- [공식] 2026-06-16 ACE Game Agent SDK beta: "lightweight, C/C++ agentic framework designed for seamless, native in-game integration", "open source, fully customizable". API는 Agent API(chat history를 소유하고 multi-step tool 추론을 자율로 진행하는 stateful API), Chat API(stateless, 추론 직접 제어), RAG API(semantic/lexical/hybrid 검색) — [NVIDIA Developer Blog (2026-06-16)](https://developer.nvidia.com/blog/build-on-device-ai-companions-with-the-nvidia-ace-game-agent-sdk-and-unreal-engine-5-plugins/)
- [공식] 같은 SDK의 기본 모델: ASR nemo-conformer-ctc-120m(영어 즉시 사용, 그 밖에 7개 언어), LM "Qwen 3.5 4B"(저지연 생성 + function calling), TTS "Chatterbox Turbo 350M". 실전 예는 Total War: PHARAOH 실험 AI advisor로, RAG로 "1,200+ interlinked game data tables"를 조회한다 — [NVIDIA Developer Blog](https://developer.nvidia.com/blog/build-on-device-ai-companions-with-the-nvidia-ace-game-agent-sdk-and-unreal-engine-5-plugins/)
- [공식] 2025-10-21: ACE에 Qwen3-8B 추가. In-Game Inferencing(IGI) SDK 플러그인이 AI 추론과 그래픽 동시 처리를 최적화한다. MultiLoRA, Vulkan용 CUDA in Graphics, function calling 샘플, Magpie TTS Flow — [NVIDIA Developer Blog (2025-10-21)](https://developer.nvidia.com/blog/nvidia-ace-adds-open-source-qwen3-slm-for-on-device-deployment-in-pc-games/)
- [공식] NARAKA: BLADEPOINT Mobile PC 버전(2025-03-27)의 on-device AI 팀원은 Free Training 파티 합류, 특정 아이템 찾기, 장비 교환, 스킬 추천, 승리를 돕는 플레이를 한다 — [NVIDIA GeForce News](https://www.nvidia.com/en-gb/geforce/news/nvidia-ace-naraka-bladepoint-inzoi-launch-this-month/)
- [언론] NARAKA AI 팀원의 기반은 Qwen 모델이다. ACE 음성 모델로 음성 명령을 이해하고 ACE SLM으로 추론해 적 태그, 상황 보고 같은 행동을 한다 — [36Kr (검색 요약)](https://eu.36kr.com/en/p/3997468580958089)
- [커뮤니티] "small, game-specific language models … responding to game events in tens of milliseconds rather than seconds"라는 설명이 있다. 그러나 Krafton 실측(약 1.6초/교환)과 맞지 않는 마케팅성 표현이다 — [pikorafy 블로그 (검색 요약)](https://pikorafy.com/blog/nvidia-ace-autonomous-ai-npcs-pubg-inzoi-2026); 반대 근거 [PUBG Ally 논문](https://arxiv.org/html/2609.29837v1)

### Inferences
- [추정] macOS·Metal 지원 언급은 위 공식 글 어느 것에도 없다. IGI·CUDA in Graphics·RTX 전제이므로 Thorkell(M4 Pro)에서 ACE 런타임과 SDK 바이너리는 쓸 수 없다고 봐야 한다.
- [추정] 이식할 수 있는 것: (1) 공개 가중치. Qwen3/Qwen 3.5 4B, Nemotron 3 Nano 4B, Kanana 1.5 2.1B, Chatterbox(350M) 등을 MLX나 llama.cpp Metal로 돌릴 수 있다. (2) Agent/Chat/RAG 3분할 API 설계. (3) RAG로 게임 데이터 표를 조회하는 advisor 패턴. Thorkell의 지식층에 대응한다.
- [추정] 24GB 통합 메모리에서 Valheim 클라이언트 2개(호스트 + 봇)를 띄운 상태라면, 4bit 2B 모델(약 1.6–2.1GB, Krafton 수치)은 들어갈 여지가 있다. 4B 이상과 로컬 TTS를 함께 올리는 것은 실측이 필요하다.

### Gaps
- ACE Game Agent SDK의 저장소 URL, 라이선스 종류(Apache/MIT 등), VRAM·지연 벤치마크는 공개 글에 없었다.
- Mac/Apple Silicon 지원 여부를 NVIDIA가 명시적으로 부정한 문서는 찾지 못했다. 언급이 없는 것만 확인했다.

## Q3. 그 밖의 2025–2026 사례 — 실제로 게임 안에서 행동하는 AI 팀원과 미들웨어

### Takeaway
"말만 하는" 비서형(Microsoft Gaming Copilot, Sony Aloy 시제품, Tencent Lingbao)과 "게임 안에서 행동하는" 팀원형(PUBG Ally, NARAKA, Tencent F.A.C.U.L., Ubisoft Teammates, Player2 Minecraft NPC)이 갈린다. 행동하는 쪽은 예외 없이 **behavior tree/스크립트 실행층 + LLM 의사결정층**이다. Ubisoft만 클라우드 Gemini를 썼고 NVIDIA 계열은 on-device이다. Xbox는 콘솔 Copilot을 2026년 6월에 접었다.

### Cited Findings
**Ubisoft Teammates (2025-11-21)**
- [언론] "first playable generative AI research project". Snowdrop 엔진, LLM은 Google Gemini + Ubisoft 자체 middleware. Xavier Manzanares: "We use behavior trees...then we add a layer with our LLM to take decisions based on context." 팀 80명(2024 Neo NPC는 약 25명). 원칙: "If this is something that could be done better with a controller, let's scrap it." — [Game Developer (2025-11-21)](https://www.gamedeveloper.com/business/ubisoft-s-first-playable-generative-ai-experience-is-an-r-d-experiment-called-teammates-)
- [공식] 음성 비서 Jaspar(적·물체 하이라이트, 로어, 설정 변경, 일시정지)와 분대원 Pablo·Sofia가 음성 명령에 따라 실시간으로 행동한다 — [Ubisoft News](https://news.ubisoft.com/en-us/article/3mWlITIuWuu0MoVuR6o8ps/ubisoft-reveals-teammates-an-ai-experiment-to-change-the-game)

**Tencent**
- [공식] F.A.C.U.L.(FPS AI Companion who Understands Language), Arena Breakout: Infinite, MoreFun Studios. "take cover behind the red truck and lay down suppressive fire" 같은 자연어를 의도 인식 + LLM으로 해석해 엄폐, 제압사격, 측면 기동을 한다. "over 17,000 in-game objects"를 구별한다(빨간 트럭 대 파란 세단) — [Tencent (2025-04-17)](http://www.tencent.com/gamers-have-a-new-teammate-ai/)
- [공식] GDC 2026: GVoice가 ASR, 끼어들기(interruption) 처리, 방향성 음성 수음을 제공하고, LLM·TTS와 이어지는 voice gateway로 "AI Teammates"를 만들 수 있게 한다 — [PR Newswire (GDC 2026)](https://www.prnewswire.com/news-releases/tencent-cloud-unveils-ai-powered-gaming-solutions-at-gdc-2026-transforming-connection-creation-and-security-for-the-future-of-games-302708877.html)
- [언론] Peacekeeper Elite(和平精英)의 AI 팀원 "Xiaotian", Honor of Kings의 AI 비서 "Lingbao" — [36Kr](https://eu.36kr.com/en/p/3827658881323649)
- [커뮤니티] Peacekeeper Elite "Absolute Commander 2.0" AI 팀원은 전술 은어를 이해하고, 엄폐·소생·잡담을 하며, 1억 1천만 명에게 적용됐다고 한다 — 출처는 집계 사이트 검색 요약뿐이다([nexworld.wiki](https://nexworld.wiki/en/ai-games/ai-games-panorama-2026/)). **미검증**
- [언론] "Goose Dimension": 화면 인식으로 진행 중인 게임에 반응하는 음성 동반자. 2026-09-29 비공개 베타 모집. 직접 플레이하는지는 불명 — [TechNode (2026-09-29)](https://technode.com/2026/09/29/tencent-tests-ai-gaming-companion-that-responds-to-live-gameplay/)

**NetEase**
- [언론] Justice Mobile "Dreamweaver Mode"(2026-04-03): 텍스트·음성으로 스토리를 지시하면 AI가 장면, 인물, 대사를 생성한다. 서사형이고 플레이 대행은 아니다 — [검색 요약, Tencent/NetEase 관련 보도](https://eu.36kr.com/en/p/3394131222956417)

**Microsoft / Sony**
- [언론] Xbox CEO Asha Sharma가 콘솔용 Gaming Copilot 개발을 중단했다(2026년 6월). 모바일 앱 Copilot도 더 개발하지 않는다. "our console players aren't excited about that experience" — [VGC](https://www.videogameschronicle.com/news/xbox-has-scrapped-its-copilot-ai-companion-on-consoles-asha-sharma-says/), [Pure Xbox](https://www.purexbox.com/news/2026/06/asha-sharma-on-removing-copilot-for-xbox-our-console-players-arent-excited-about-it)
- [언론] Sony 내부 Aloy 시제품 유출(2025-03): STT는 OpenAI Whisper, 대사는 GPT-4/Llama 3, 음성은 Sony Emotional Voice Synthesis, 얼굴은 Mockingbird. 반응은 "creepy", "cursed" 등 부정적이었다. 대화형이고 플레이는 하지 않는다 — [80.lv](https://80.lv/articles/ai-powered-aloy-from-horizon-forbidden-west-fails-to-impress-viewers/), [Tom's Guide](https://www.tomsguide.com/gaming/playstation/ai-powered-playstation-characters-are-being-tested-at-sony-what-we-know) (검색 요약. 일부 요약은 Whisper를 TTS로 잘못 적음)

**미들웨어**
- [커뮤니티] Player2: 백그라운드 앱이 "free drop-in alternative to Ollama"로 동작하며 STT·LLM·TTS를 제공한다. 키 없이 `http://localhost:4315` API를 쓴다. 흐름은 "Game -> Player2 app -> Player2 AI model". "the Player2 app provides the AI brain … the mod provides the body" — [Modrinth player2npc 등 (검색 요약)](https://modrinth.com/mod/player2npc)
- [커뮤니티] Player2NPC(Minecraft)는 PlayerEngine 프레임워크 쇼케이스이다. 몸과 인벤토리를 가진 동료가 나무 베기, 채광, 몬스터 방어, 블록 설치를 하고 자연어로 지시받는다. v1.4.0(2026-07-17) — [CurseForge](https://www.curseforge.com/minecraft/mc-mods/player2npc)
- [커뮤니티] Player2 운영사 Elefant는 "$2M revenue with 1000 indie developers"를 12개월 동안 나누겠다고 밝혔다 — [Elefant blog](https://blog.elefant.gg/p/we-are-sharing-2m-revenue-with-1000)
- [공식] Inworld Runtime: UE 5.4+ 플러그인. 그래프 편집기로 노드와 엣지 파이프라인을 만들고 asset으로 저장해 런타임에 실행한다. 클라우드 API는 Base64 Runtime API key로 쓴다 — [Inworld Docs](https://docs.inworld.ai/docs/unreal-engine/runtime/get-started)
- [커뮤니티] Inworld TTS는 200ms 미만, 분당 1센트 미만이라는 소개가 있다 — [eesel.ai (검색 요약)](https://www.eesel.ai/de/blog/inworld-ai)
- [언론] Inworld(2024-05)는 당시 서버 기반이었고 하이브리드("Some services could run locally, some services run on cloud")를 거쳐 "run locally, offline, on devices like consoles"로 가겠다고 했다 — [Wccftech (2024-05-14)](https://wccftech.com/inworld-reckons-costs-are-going-to-go-down-a-lot-and-its-gen-ai-npc-tech-will-run-locally-even-on-consoles/amp/)
- [공식/연구] Altera Project Sid: Minecraft 에이전트 1,000명, PIANO(Parallel Information Aggregation via Neural Orchestration) 구조. LLM과 전용 모듈로 여러 출력 스트림의 일관성을 유지한다 — [arXiv 2411.00114](https://arxiv.org/abs/2411.00114), [GitHub project-sid](https://github.com/altera-al/project-sid)

**결정 모델 (Thorkell이 쓰는 Jev·laya의 위치)**
- [커뮤니티] Jev(TypeSafe AI, 관리형 API, 독점)와 laya(Convai Innovations, Apache 2.0 공개 가중치)는 텍스트를 생성하지 않고 choice/score/noul(예/아니오 확률)에 답하는 "decision model"이다. 지연: Jev 70–500ms, laya 39.5ms(단일)·158.6ms(10개 배치). 컨텍스트: laya 512토큰(영어), 1,024토큰(다국어). 정확도: laya 특화 체크포인트 76.6%, 일반 영어 36.2%(기준선 46.1%보다 낮음). 선택지 권장 상한: laya 약 20개(확률 과신 경향), Jev 255개. 가격(1M 입력 토큰): Jev $0.042, laya $0.020(출력 무료, laya는 2026-10-12까지) — [Runware blog (2026-09-28)](https://runware.ai/blog/jev-laya-and-the-emerging-role-of-decision-models)
- [커뮤니티] laya 영어 체크포인트는 ModernBERT-large + decision head로 약 421M, 다국어는 mmBERT-base 322M(100개 넘는 언어)이고 2026년 9월 공개 — [gradually.ai (검색 요약)](https://www.gradually.ai/en/ai-models/laya/)
- [커뮤니티] 게임 시험: ViZDoom에서 laya가 한 번에 결정 하나를 내리도록 붙인 저장소가 있다(보이는 몬스터 이름과 좌/중/우 위치, 체력·탄약을 입력) — [GitHub Laya_plays_Doom](https://github.com/vipulcodess/Laya_plays_Doom). 고속도로 시나리오에서 laya는 181수 중 116수(64%)를 "없다고 알려준 차선"으로 꺾었고 10회 중 9회 충돌했다 — [Medium (검색 요약, 원문 403)](https://medium.com/learnwithnk/i-tested-jev-and-laya-two-new-ai-decision-models-on-games-they-were-never-trained-for-d839992b75c0)

### Inferences
- [추정] 실제로 몸을 움직이는 상용 사례는 모두 LLM에 연속 제어를 맡기지 않는다. LLM은 의도, 대상, 모드를 정하고 실행은 BT/스크립트가 한다. Thorkell의 "스킬 + 반사" 설계는 업계 표준과 같은 방향이다.
- [추정] Xbox Copilot 중단과 Sony 반응은 "플레이하지 않는 대화형 비서"의 수요가 약하다는 신호이다. PUBG Ally 설문에서도 정보·전술 가치(51%)가 대화 상대 가치(28%)보다 높았다.
- [추정] laya 실험 결과(존재하지 않는 선택지로 감)는 decision model 출력을 Body 쪽 사전조건 검증으로 막아야 한다는 근거이다. Thorkell의 typed 결과 코드와 검증기가 이 역할을 한다.

### Gaps
- EA SEED, Roblox의 2025–2026 "게임 안에서 행동하는" AI 팀원 사례는 이번 조사에서 확인하지 못했다(검색 시간 부족).
- Ubisoft Teammates의 지연 수치, 공개 플레이테스트 결과, 상용화 여부는 찾지 못했다.
- Tencent F.A.C.U.L.과 Peacekeeper Elite AI 팀원의 모델, 클라우드/디바이스 배치, 지연은 공개 자료가 없었다.
- Player2가 어느 모델을 어디(로컬/클라우드)에서 돌리는지는 공식 문서로 확인하지 못했다. "비싼 GPU가 필요 없다"는 문구로 보아 호스팅형으로 추정된다.
- Altera의 2025–2026 행보(제품화 여부)는 확인하지 못했다.

## Q4. Valheim AI 동료 모드 (Offline Companions, VikingNPC, Thrall, Fylgja, ValheimMCP 등)

### Takeaway
Valheim 동료 모드는 둘로 나뉜다. (1) 대량 사용되는 **스크립트 NPC**(Offline Companions 30.3K, VikingNPC 75K 다운로드)는 채집, 전투, 제련, 수리까지 한다. (2) **LLM 모드**는 작고 미완성이거나 폐기됐다(Thrall: 폐기·싱글 전용·All rights reserved, Fylgja: 게임 브리지 stub, bukeperry: 대화 전용). 찾은 모드 중 **두 번째 클라이언트로 진짜 플레이어처럼 접속하는 것은 없다.** 전부 서버/로컬에 스폰된 NPC이거나 콘솔·채팅 브리지이다.

### Cited Findings
- [커뮤니티] **Offline Companions** (ProfMags): 고용형 NPC 동료이다. 방어 우선 전투(방패 막기, 패링, 후퇴), 대형 유지, 나무·통나무·그루터기 자동 벌목, 돌, 광석, 채집, 제련 관리, 농사 구역, 낚시, 사냥, 솥 요리, 발효통, 50m 안 건물 수리(Stay Home), 모닥불 연료 보충, 상자 정리를 한다. AI는 **LLM이 아니라 자체 `CompanionAI`**(경로 탐색, context steering 장애물 회피, 끼임 감지·복구, 위협 평가)이다. 지시는 포인트앤클릭이다. v1.3.0, 30.3K 다운로드, MIT, BepInEx 5.4.2200+, Valheim 0.219+. 멀티플레이에서는 ZDO 소유권으로 스폰한 플레이어만 조작한다 — [Thunderstore](https://thunderstore.io/c/valheim/p/ProfMags/Offline_Companions/)
- [커뮤니티] **VikingNPC (Norsemen)** (RustyMods): 길들일 수 있는 바이킹이 채광, 벌목, 낚시를 하고 도발하지 않으면 우호적이다. 75K 다운로드. **VikingNPC Continued**(SephrinMods)가 Valheim 1.0 호환판이다. **Vikings for Hire**(Worobeyko)는 떠도는 바이킹을 코인으로 고용해 전투나 기지 일꾼으로 쓴다 — [Thunderstore VikingNPC Continued](https://thunderstore.io/c/valheim/p/SephrinMods/VikingNPC_Continued/), [Vikings for Hire](https://thunderstore.io/c/valheim/p/Worobeyko/VikingsForHire/) (다운로드 수는 검색 요약)
- [커뮤니티] **Thrall** (ego_ai): LLM 기반 NPC 동료. push-to-talk(T) 음성, 성격 커스터마이즈, 채집, 전투, follow/patrol/gather/attack 명령. v1.0.8부터 "AI voices powered by Cartesia". v1.0.11, 4.7K 다운로드. Valheim 0.218.20, Jotunn 2.20.1+. **싱글플레이 전용**, 제작·건축 불가, 영어만, VikingNPC 등과 충돌, 라이선스 "All rights reserved", **Deprecated** 표시 — [Thunderstore](https://thunderstore.io/c/valheim/p/ego_ai/Thrall/)
- [커뮤니티] Thrall은 OpenAI API로 동작하고 Jotunn을 쓴다(2024-09 Show HN) — [Hacker News](https://news.ycombinator.com/item?id=41485356) (검색 요약)
- [커뮤니티] **Fylgja** (FeverDream-dev): Ollama(로컬), Z.AI, OpenAI 호환 provider를 쓰는 동료 모드. `CompanionBrain` → `IActionPlanner` → follow/attack/defend/gather/patrol/deposit/stop 큐. RequestTimeoutSeconds 30, 재시도 2회, 분당 20요청 제한. README가 **"game bridge is stubbed"**라고 밝힌다(보이는 캐릭터 모델 없음). MIT, 별 1개, 2026-04-05 생성·마지막 push(같은 날). Valheim 0.221.12+, BepInEx만 필요 — [GitHub](https://github.com/FeverDream-dev/Fylgja), GitHub API 확인(2026-10-11)
- [커뮤니티] **bukeperry** (jim-brighter): 트롤 상인 NPC가 근접 채팅과 외침에 말풍선으로 답한다. BepInEx 5 + Jötunn, ZRoutedRpc로 브로드캐스트. 백엔드는 AWS Lambda + Bedrock "google.gemma-4-31b" + DynamoDB 대화 기록 + 로컬 RAG. Discord `/bukeperry`, 전용 서버를 지원한다. 행동은 하지 않고 대화만 한다. 2026-10-02 생성, 2026-10-09 push, 라이선스 없음, 별 0개 — [GitHub](https://github.com/jim-brighter/bukeperry), GitHub API 확인(2026-10-11)
- [커뮤니티] **ValheimMCP** (idontunderstand / © 2026 myrcutio): 127.0.0.1:8731에 HTTP를 여는 BepInEx 플러그인이다. `POST /mcp`(JSON-RPC 2.0 MCP), `/health`, `/commands`, `/command`, `/log`, `render_view()`, `wait_for_log()`. **콘솔 명령만 실행**하고 이동이나 전투 제어는 없다. 인증은 없고 allow/deny 목록만 있다. 비동기(coroutine) 명령 출력은 잡지 못한다. v0.2.1, 268 다운로드, MIT. Claude Code가 게임 상태를 재현 가능하게 다루려고 만들었다 — [Thunderstore](https://thunderstore.io/c/valheim/p/idontunderstand/ValheimMCP/)
- [커뮤니티] **VikingAI** (pzelant): 검색 결과에는 이슈 "#682 [epic] V1 basic version: Einar in the game controlled by an LLM - talks, takes orders in his own words, acts on his own"와 "#601 Thrall (ego_ai) companion mod: closed source, feature gap vs VikingAI"가 나온다. 그러나 2026-10-11 현재 저장소와 이슈 URL이 404(비공개 전환 또는 삭제)이다 — [GitHub issue #682 (404)](https://github.com/pzelant/VikingAI/issues/682), [#601 (404)](https://github.com/pzelant/VikingAI/issues/601)

### Inferences
- [추정] Valheim에서 "LLM이 실제로 오래 플레이하는 동료"는 공개된 성공 사례가 없다. Thorkell의 "두 번째 클라이언트로 진짜 플레이어 접속" 방식은 찾은 모드 중 유일하다.
- [추정] Offline Companions의 스크립트 기능 목록(끼임 감지·복구, context steering, 제련·요리·수리 루틴)은 Thorkell Body 스킬 설계의 참고 체크리스트로 쓸 만하다. MIT라 코드 참조도 가능하다(단, NPC용 `MonsterAI` 계열이라 플레이어 입력 경로와 다를 수 있다).
- [추정] ValheimMCP의 무인증 루프백 HTTP는 Thorkell의 HMAC NDJSON 브리지와 대조된다. 같은 머신의 다른 프로세스가 명령을 주입할 수 있는 위험을 Thorkell은 이미 피하고 있다.
- [추정] Thrall이 폐기된 이유(싱글 전용, 비공개, 영어만, 클라우드 비용 추정)는 Thorkell이 피하는 지점(멀티, 한국어, 비용 통제)과 겹친다. 폐기 사유는 공식 확인이 안 됐다.

### Gaps
- Thrall의 폐기 사유와 마지막 업데이트 날짜는 Thunderstore 페이지에서 확인하지 못했다.
- VikingNPC 계열의 정확한 다운로드 수와 최신 버전 날짜는 검색 요약에만 의존했다.
- 2025–2026에 Nexus Mods에 올라온 LLM 기반 Valheim 동료 모드는 이번 조사에서 확인하지 못했다(Thunderstore와 GitHub 위주로 찾음).

## Q5. 공통 설계 교훈 — 지연 예산, 플레이어 시간당 비용, guardrail, 플레이어가 싫어한 것

### Takeaway
상용 사례의 지연 기준은 "즉시 행동은 결정적 실행층(BT, 수십 ms~틱 단위), 언어 판단은 1~2초"이다. Krafton은 클라우드 대형 모델(경기당 $5–7)을 on-device 2B(경기당 $0, 1.6초)로 바꿨고, 블라인드 테스트에서도 on-device가 이겼다(69.5% 대 18.8%). 플레이어가 싫어한 것은 수다·아첨, 지각 불일치, 전투 무능, 게임과 무관한 비서 기능이었다.

### Cited Findings
**지연**
- [공식] PUBG Ally 음성 1회 교환: on-device 약 1.6초, 클라우드 3.4초 — [PUBG Ally 논문](https://arxiv.org/html/2609.29837v1)
- [언론] LM 6라운드 연쇄: on-device 5초 미만, 클라우드 10초 초과. 응답 속도 만족도 2.93/5 — [Inven Global](https://www.invenglobal.com/articles/26592/built-a-teammate-got-a-chat-partner-kraftons-first-scorecard-for-pubg-ally)
- [공식] 이동, 정밀 조준, 즉각 전투 반응은 BT가 맡는다(지연에 민감한 행동은 LM에 두지 않는다) — [NVIDIA GeForce News](https://www.nvidia.com/en-us/geforce/news/pubg-ally-ai-teammate-beta-available-now/), [논문](https://arxiv.org/html/2609.29837v1)
- [커뮤니티] decision model 지연: laya 39.5ms(단일), Jev 70–500ms — [Runware blog](https://runware.ai/blog/jev-laya-and-the-emerging-role-of-decision-models)

**비용**
- [언론] 클라우드(Claude Opus 4.8) 경기당 $5.14–$7.10, on-device $0 — [Inven Global](https://www.invenglobal.com/articles/26592/built-a-teammate-got-a-chat-partner-kraftons-first-scorecard-for-pubg-ally)
- [커뮤니티] 한 스튜디오는 초기 최적화 전 "$3 per player per hour"를 냈다. 계층별 턴당 비용 가이드: 잡담 $0.0001–0.001, 일반 $0.001–0.005, 중대 결정 $0.01–0.05. Stanford Generative Agents를 실시간 환산하면 에이전트당 사람 시간당 약 $25 — [TrackIt](https://trackit.io/connecting-npcs-to-llms-in-games), [abratabia](https://abratabia.com/llm-npcs/latency-and-cost.php) (검색 요약)
- [공식] NVIDIA는 on-device로 "eliminating the need for subscription fees"를 내세운다 — [NVIDIA GeForce News](https://www.nvidia.com/en-gb/geforce/news/nvidia-ace-naraka-bladepoint-inzoi-launch-this-month/)

**Guardrail**
- [공식] Krafton은 안전 범주 6개(이념 민감, 혐오, 자해, 모욕, 성적, 프라이버시)를 두고, 게임 내 폭력은 예외로 허용한다. 실행 중에는 출력 키워드 차단·수정 표시를 하고, 위험한 입력 발화를 `[REDACTED FOR SAFETY]`로 바꾼다. 학습 데이터는 적대적 인간 작성 데이터, Nemotron Content Safety V2/Aegis 2.0, 희귀 실패 합성 데이터이다. 안전 제어 전용 tool이 1개 있다 — [논문](https://arxiv.org/html/2609.29837v1)
- [언론] 결과적으로 Ella는 게임 밖 주제를 거부했고, 리뷰어는 이를 "zero banter"로 봤다 — [PCGamesN](https://www.pcgamesn.com/playerunknowns-battlegrounds/ai-teammate)

**플레이어가 싫어한 것**
- [언론] 지각 불일치(멀리 있는 적은 표시하면서 보이는 적은 없다고 함), 지시 불이행, 쓸모없는 사후 논평 — [PCGamesN (2026-06-22)](https://www.pcgamesn.com/playerunknowns-battlegrounds/ai-teammate)
- [언론] 지나친 수다와 아첨("borderline sycophantic"), 근거리 피격에도 무반응 — [TechRadar / talkesport (검색 요약)](https://www.techradar.com/computing/gpu/forget-npcs-now-we-have-cpcs-co-playable-characters-or-ai-teammates-in-pubg-courtesy-of-nvidia-ace-tech-but-im-not-impressed-so-far)
- [언론] 전투 2.58/5가 최저점. "팀원"으로 본 사람은 18.5%뿐이다 — [Inven Global](https://www.invenglobal.com/articles/26592/built-a-teammate-got-a-chat-partner-kraftons-first-scorecard-for-pubg-ally)
- [언론] 콘솔 플레이어가 Copilot에 "not excited" — [VGC](https://www.videogameschronicle.com/news/xbox-has-scrapped-its-copilot-ai-companion-on-consoles-asha-sharma-says/)
- [언론] Ubisoft 원칙: 컨트롤러로 더 잘할 수 있는 것은 음성 AI로 만들지 않는다 — [Game Developer](https://www.gamedeveloper.com/business/ubisoft-s-first-playable-generative-ai-experience-is-an-r-d-experiment-called-teammates-)

### Inferences (Thorkell이 가져갈 것)
- [추정] **계층별 지연 예산.** 반사와 스킬 실행은 Body 프레임 단위, 알려진 명령은 즉시(플래너 우회), decision model(laya 약 40ms, Jev 0.07–0.5s)은 전술 선택, 클라우드 플래너는 몇 초~십수 초가 걸리는 드문 재계획에만 쓴다. Krafton도 1.6초에서 "느리다"는 평을 받았다.
- [추정] **비용 제약이 더 세다.** gemini-3.8-flash 무료 등급은 하루 20회이다. Krafton식 "이벤트마다 LM 루프"(경기당 여러 라운드)는 불가능하다. 플래너는 세션 시작, 목표 완료·실패, 처음 듣는 말에만 부르고, 나머지 이벤트 반응은 reactivity prior 표(config)와 decision model로 처리해야 한다.
- [추정] **Reactivity prior를 config로.** 이벤트마다 말하기/행동을 require/recommend/optional/do-not으로 정한 표를 두면, 수다 과잉(PUBG 비판)과 무반응(근거리 피격 무시)을 재학습 없이 조절할 수 있다. Thorkell의 "숨은 기본값 금지" 규칙에 맞게 명시적 설정으로 둔다.
- [추정] **말보다 정보.** 플레이어는 정보·전술 가치를 가장 높게 봤다(51%). 토르켈 대사는 짧은 상황 보고(방향과 거리, 자원, 위협)를 우선하고, 잡담은 리더가 걸 때만 받는다.
- [추정] **지각 일관성.** 보고 문장은 행동과 같은 지각 스냅샷에서 만들고 "마지막으로 본 시각"을 붙인다. 한 번 본 위협은 일정 시간 기억해서 "없다"고 단정하지 않는다.
- [추정] **관찰을 tool로 당기기 + compaction.** 약 5k 토큰 예산, 매 루프 새 관찰, 못 끝낸 일은 짧은 plan으로 압축해 이월한다. 프롬프트를 캐시 친화 순서로 놓는 Krafton 방식은 Gemini 호출 토큰도 줄인다.
- [추정] **교사-학생 데이터 축적.** Krafton은 대형 교사 → 8B → 2B로 증류했다. Thorkell도 플래너(Gemini)의 입력과 출력, 결과 검증 코드를 로그로 남기면 나중에 로컬 소형 모델(예: Kanana 1.5 2.1B 한국어, MLX)로 증류할 수 있는 자산이 된다. 단, 정보 동등성 규칙에 맞는 관찰만 로그에 담아야 한다.
- [추정] **안전.** 친구들과 하는 crossplay이므로 입력 발화 redaction과 출력 키워드 차단 같은 최소 guardrail을 대화 경로(gemini-live)와 채팅 출력에 둘 필요가 있다.

### Gaps
- 상용 AI 팀원의 "플레이어 시간당" 공식 비용 수치는 Krafton의 경기당 수치 말고는 찾지 못했다. TrackIt의 $3/시간은 출처 스튜디오가 익명이다.
- 음성 대화의 체감 허용 지연(예: 몇 ms 이하면 자연스러운지)에 대한 게임사 공식 기준은 찾지 못했다.
- Gemini Live 같은 클라우드 실시간 음성 API를 상용 게임 팀원에 쓴 사례와 지연 실측은 찾지 못했다.
