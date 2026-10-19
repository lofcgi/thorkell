# 범용 게임 에이전트·게임 파운데이션 모델·월드 모델 (2026-10-10 기준)

조사일: 2026-10-11. 표기는 다음과 같다.
- [공식]: 연구실 블로그·논문·모델 카드·공식 레포
- [보도]: 언론
- [커뮤니티]: 개인 블로그, 방송, 사용자 벤치마크
- [추정]: 이 노트를 쓴 사람의 판단

날짜가 2025년인 사실은 "오래된 사실"이므로 날짜를 붙였다. WebFetch 요약을 거친 수치는 원문 표를 직접 보지 못한 경우가 있다. 그런 경우는 따로 적었다.

## 1. 2026년 10월 현재 주요 시스템의 상태 (SIMA 2, Game-TARS/UI-TARS-2, Lumine, NitroGen, Open-P2P, Muse/WHAM, Genie 3, Minecraft VLA, 2026 신규)

### Takeaway
2026-10 시점에 "아무 3D 게임이나 화면 픽셀로 플레이하는 범용 에이전트"가 최고 수준으로 가장 잘 하는 것은 두 갈래다.
- 닫힌 대형 VLM 기반 에이전트: SIMA 2, Game-TARS, Lumine.
- 공개 소형 행동복제 정책: NitroGen 493M, Open-P2P 150M~1.2B.

닫힌 쪽은 가중치가 공개되지 않았다. 공개된 소형 정책은 언어 지시, 장기 계획, 처음 보는 3D 게임으로의 전이가 약하다. 2026년에 SIMA 3이나 Genie 4는 발표되지 않았다. 새로 나온 것은 대부분 공개 소형 정책(NitroGen, Open-P2P), 벤치마크, 공개 실시간 월드 모델이다.

### Cited Findings

**Google DeepMind SIMA 2 (2025-11-13 발표, 2025-12-04 논문)**
- [공식] Gemini를 추론 핵심으로 쓴다. 화면 픽셀을 보고 키보드·마우스로 조작하며, 게임 내부 상태에는 접근하지 않는다. "limited research preview"로 공개했고, "small cohort of academics and game developers"에게만 조기 접근을 준다. — [DeepMind blog](https://deepmind.google/blog/sima-2-an-agent-that-plays-reasons-and-learns-with-you-in-virtual-3d-worlds/)
- [공식] 블로그가 밝힌 한계:
  - 상호작용 기억이 짧다("a relatively short memory").
  - 지연을 낮추려고 컨텍스트 창을 제한한다("limited context window to achieve low-latency interaction").
  - 아주 긴 과제와 정밀한 저수준 조작에 약하다. — [DeepMind blog](https://deepmind.google/blog/sima-2-an-agent-that-plays-reasons-and-learns-with-you-in-virtual-3d-worlds/)
- [공식] 모델과 행동 출력:
  - 사전학습된 Gemini Flash-Lite 체크포인트에서 시작했다.
  - 행동은 구조화된 텍스트로 낸다. 이 텍스트는 결정적으로 파싱되어 키보드·마우스 명령이 된다. 키 96개, 마우스 클릭, 이산화한 상대 마우스 이동이며 청크 단위로 낸다.
  - 제어 주파수, 지연, 하드웨어는 논문에 없다. — [arXiv 2512.04797](https://arxiv.org/html/2512.04797)
- [공식] **학습 환경에 Valheim이 들어 있다.** 목록은 Construction Lab, Playhouse, WorldLab, Goat Simulator 3, Hydroneer, No Man's Sky, Satisfactory, Space Engineers, Valheim, Wobbly Life다.
  - 논문은 Valheim의 사슴 사냥을 기술 예시로 든다("approaching from downwind while crouching").
  - 감사의 글에는 Coffee Stain이 파트너로 나온다.
  - 홀드아웃 평가 환경은 ASKA, MineDojo, The Gunk, Genie 3 세계다. — [arXiv 2512.04797](https://arxiv.org/html/2512.04797)
- [공식] 홀드아웃 성능(논문 그림을 WebFetch로 요약한 근사치):

  | 환경 | SIMA 2 | SIMA 1 | 처음 하는 사람 |
  |---|---|---|---|
  | ASKA (바이킹 생존게임) | 약 40% | 약 5% | 약 32% |
  | MineDojo (26/50 과제군) | 약 30% | 미미 | 약 19% |
  | 학습 환경 | 약 50% | — | 약 60% (시간제한 포함) |

  — [arXiv 2512.04797](https://arxiv.org/html/2512.04797)
- [보도] 언론은 학습 환경 기준으로 "SIMA 2 약 65%, SIMA 1 약 31%, 사람 약 71%"라고 전했다. 논문 요약치(약 50% 대 약 60%)와 지표 정의가 다를 수 있으며, 원문 그림으로 확인하지 못했다. — [eWeek](https://www.eweek.com/news/google-deepmind-sima/), [MIT Technology Review 2025-11-13](https://www.technologyreview.com/2025/11/13/1127921/google-deepmind-is-using-gemini-to-train-agents-inside-goat-simulator-3/)
- [공식] 자기개선: Gemini가 과제와 보상을 만들고 에이전트가 스스로 플레이해서 배운다.
  - ASKA 고정 과제에서는 반복 학습 후 사람 기준점을 넘었다.
  - 열린 진행에서는 1시간 안에 쉼터를 지었다. — [arXiv 2512.04797](https://arxiv.org/html/2512.04797)
- [보도] 2026-06 기준으로도 SIMA 2와 Genie 3는 제한된 연구 프리뷰다. "SIMA 3"은 찾지 못했다. — [TechTimes 2026-06-06](https://www.techtimes.com/articles/317932/20260606/deepmind-world-models-train-robots-imagined-worlds-sima-practices-inside-genie-3-model.htm)

**ByteDance Seed Game-TARS (2025-10-27)**
- [공식] 행동 공간은 mouseMove(dx,dy), mouseClick, keyPress의 3가지 원시 동작이다.
- [공식] 학습 데이터: 500B 토큰 이상, 약 500개 게임, 2만 게임시간 이상.
- [공식] 모델:

  | 변형 | 구성 |
  |---|---|
  | Game-TARS-MoE-mini | 비전 인코더 632M + 활성 파라미터 2.5B인 MoE LLM |
  | Game-TARS-MoE-Large | 크기 미기재 |
  | Game-TARS-Dense | Qwen2.5-VL-7B-Instruct 기반 |

- [공식] "Sparse-Thinking": 중요한 결정 지점에서만 추론한다. Doom에서는 반응성을 위해 추론을 줄이고, Minecraft에서는 과제 시작 때 깊게 생각한다. — [arXiv 2510.23691](https://arxiv.org/html/2510.23691v1)
- [공식] 성능:
  - Minecraft MCU: 임베디드 과제 72.0%, GUI 과제 55.4%, 전투 66.1%. 이전 SOTA의 약 2배다.
  - VizDoom: GPT-5, Gemini-2.5-Pro, Claude-4-Sonnet보다 대부분 맵에서 높다.
  - 처음 보는 Poki 웹 게임: 처음 하는 사람과 비슷한 수준이다.
  - 가중치나 코드 공개 문구는 논문에 없다. — [arXiv 2510.23691](https://arxiv.org/html/2510.23691v1)

**ByteDance UI-TARS-2 (2025-09-02) / UI-TARS-1.5 (2025-04-17)**
- [공식] UI-TARS-2는 게임 15종에서 평균 정규화 점수 59.8을 냈다(사람의 약 60%). OSWorld는 47.5다. 가중치 공개는 확인하지 못했다. — [arXiv 2509.02544](https://arxiv.org/abs/2509.02544)
- [공식] UI-TARS-1.5-7B는 Apache 2.0으로 공개됐고 8B 파라미터다. — [HF 모델 카드](https://huggingface.co/ByteDance-Seed/UI-TARS-1.5-7B)
  - 같은 카드의 게임 표에는 다음 결과가 있다.
    - Poki 14종 100%
    - Minecraft Mine Blocks 0.42
    - Kill Mobs 0.31 (추론 모드)
  - 이 표가 공개된 7B인지 비공개 상위 모델(UI-TARS-1.5)인지는 확인하지 못했다. 2025-04 발표문은 크기를 밝히지 않았다. — [Seed blog](https://seed.bytedance.com/en/blog/bytedance-seed-agent-model-ui-tars-1-5-open-source-achieving-sota-performance-in-various-benchmarks)

**Lumine (ByteDance Seed, 2025-11-12)**
- [공식] 모델과 데이터:
  - Qwen2-VL-7B-Base에 사람이 원신을 플레이한 1,731시간(영상과 키보드·마우스 동기화)을 학습시켰다.
  - 3단계로 학습했다: Base, Instruct, Thinking.
  - 지각은 5Hz, 키보드·마우스 행동은 30Hz다. 200ms 동안 33ms 청크 6개를 낸다. 추론은 필요할 때만 켠다. — [arXiv 2511.08892](https://arxiv.org/html/2511.08892v1)
- [공식] 추론 구성:
  - NVIDIA H20 4장, tensor parallel 4.
  - W8A8 SmoothQuant, 드래프트 모델 없는 투기적 디코딩, StreamingLLM KV 재사용을 썼다.
  - 첫 행동 청크까지 약 110ms(추론 없음)이고, 전체 지연을 25.3배 줄였다. — [arXiv 2511.08892](https://arxiv.org/html/2511.08892v1)
- [공식] 성과:
  - 몬드 메인 스토리(5시간)를 사람 수준 효율로 끝냈다.
  - 미세조정 없이 명조 100분 미션과 붕괴: 스타레일 1장(5시간)을 해냈다.
  - 제목은 "Open Recipe"지만 가중치, 코드, 데이터 공개는 논문과 프로젝트 페이지에서 확인하지 못했다. — [arXiv 2511.08892](https://arxiv.org/html/2511.08892v1), [lumine-ai.org](https://www.lumine-ai.org/)

**NVIDIA NitroGen (2026-01-04)**
- [공식] 데이터: 1,000개 이상 게임의 게임플레이 영상 40,000시간.
  - 행동 라벨은 영상에 찍힌 패드 입력 오버레이에서 뽑았다. 템플릿 매칭과 SegFormer를 썼다.
  - 조이스틱 R² 0.84, 버튼 정확도 0.96.
- [공식] 구조:
  - 256×256 RGB 입력, SigLIP 2 비전 인코더와 flow-matching DiT, 16-행동 청크.
  - 평가 때는 모델이 예측하는 동안 게임을 멈췄다(synchronous inference).
- [공식] 결과: 상용 게임 10종의 과제 30개에서, 처음부터 학습한 모델보다 성공률이 최대 52% 상대 개선됐다.
- [공식] 한계:
  - 언어 지시가 없고 장기 계획을 못 한다. 짧은 컨텍스트에만 반응한다.
  - 데이터가 액션·게임패드 게임에 치우쳤다. — [arXiv 2601.02427](https://arxiv.org/html/2601.02427v1)
- [공식] 모델 카드:
  - 파라미터 4.93×10⁸.
  - 라이선스는 "NVIDIA License"이고 SigLIP2 부분만 Apache 2.0이다. WebFetch 요약은 비상업이라고 했지만 원문 조항은 직접 확인하지 못했다.
  - 패드용 게임(액션, 플랫포머, 레이싱)에서 가장 잘 되고, 키보드·마우스 중심 게임(RTS, MOBA)에는 덜 효과적이다. — [HF nvidia/NitroGen](https://huggingface.co/nvidia/NitroGen)
- [공식] 실행:
  - 추론 서버(Linux 가능)와 Windows 전용 게임 클라이언트로 나뉜다.
  - 입력은 게임패드만 지원한다.
  - "마지막 프레임만 본다"고 적혀 있다. — [GitHub MineDojo/NitroGen](https://github.com/MineDojo/NitroGen)

**Open-P2P / Open Pixel2Play (Elefant AI, 2026-01-08)**
- [공식] 입력은 192×192 이미지와 선택적 텍스트 지시이고, 출력은 키보드·마우스다.
- [공식] 모델은 150M, 300M, 600M, 1.2B 체크포인트 4종이 모두 공개됐다. 사람이 주석을 단 게임플레이 8,000시간 이상을 학습했다.
- [공식] 시험한 게임: Roblox(Rivals, Hypershot, Be a Shark), DOOM, Quake.
- [공식] 실행 요구:
  - Windows 11과 RTX 5090/5080 2장에서 시험했다.
  - 종단 간 지연이 50ms 미만이어야 한다.
- [공식] 학습 비용: 150M은 H100 8장으로 약 70시간, 1.2B는 약 140시간. — [GitHub elefant-ai/open-p2p](https://github.com/elefant-ai/open-p2p)
- [공식] 논문 제목은 "Scaling Behavior Cloning Improves Causal Reasoning"이다.
  - 데이터 8,300시간 이상과 코드, 체크포인트를 공개했다.
  - "여러 3D 게임에서 사람과 견줄 만한 성능"이라고 주장한다. — [arXiv 2601.04575](https://arxiv.org/abs/2601.04575)
- **라이선스 충돌**: GitHub와 HF 모델 카드는 MIT다. arXiv 페이지에는 CC BY-NC-ND 4.0이 적혀 있는데, 논문 문서 자체의 라이선스로 보인다[추정]. — [HF elefantai/open-p2p](https://huggingface.co/elefantai/open-p2p), [arXiv 2601.04575](https://arxiv.org/abs/2601.04575)

**Microsoft Muse / WHAM (2025-02, 오래된 사실)**
- [공식] WHAM-1.6B는 Bleeding Edge의 이미지와 컨트롤러 행동 10억 개 이상으로 학습했다. 사람이 7년 넘게 연속으로 플레이한 분량이다. — [Microsoft Research blog](https://www.microsoft.com/en-us/research/blog/introducing-muse-our-first-generative-ai-model-designed-for-ga), [GeekWire](https://www.geekwire.com/2025/microsoft-reveals-new-gaming-focused-generative-ai-model-muse-that-could-revive-classic-games/)
- [공식] HF 공개 정보:

  | 항목 | 내용 |
  |---|---|
  | 모델 | 200M(3.7GB), 1.6B(18.9GB) |
  | 라이선스 | Microsoft Research License, 학술 연구 전용 |
  | 실행 환경 | CUDA, A6000/A100에서 시험 |
  | 입력 | 300×180 |
  | 속도 | "Inference time is currently too slow for real-time use" |
  | 범위 | Bleeding Edge 밖의 이미지는 생성하지 못한다 |

  행동 정책(화면을 보고 컨트롤러 행동 예측)으로도 쓸 수 있다. — [HF microsoft/wham](https://huggingface.co/microsoft/wham)

**Genie 3 / Project Genie**
- [보도] Genie 3는 2025-08-05에 발표됐다. 720p 24fps로 실시간 탐색할 수 있고, 일관성은 "몇 분"간 유지된다. — [TechCrunch 2025-08-05](https://techcrunch.com/2025/08/05/deepmind-thinks-genie-3-world-model-presents-stepping-stone-towards-agi/)
- [공식] Project Genie는 2026-01-29에 미국 Google AI Ultra 구독자(18세 이상)에게 열렸다. 한계는 다음과 같다.
  - 시뮬레이션은 60초로 제한된다.
  - 캐릭터 조작 지연이 더 클 수 있다.
  - 실제 물리나 프롬프트를 늘 따르지는 않는다. — [Google blog: Project Genie](https://blog.google/innovation-and-ai/models-and-research/google-deepmind/project-genie/), [9to5Google 2026-01-29](https://9to5google.com/2026/01/29/google-project-genie/)
- [보도] 2026-05에 Street View 기능을 붙여 전 세계로 넓혔다. 이 내용은 출처 하나뿐이다. — [TechTimes](https://www.techtimes.com/articles/317932/20260606/deepmind-world-models-train-robots-imagined-worlds-sima-practices-inside-genie-3-model.htm)
- "Genie 4" 발표는 검색에서 찾지 못했다. — [검색 결과 근거: Wikipedia Genie](https://en.wikipedia.org/wiki/Genie_(AI_model))

**Minecraft VLA (모두 2025년, 오래된 사실)**
- [공식] JARVIS-VLA: Qwen2-VL-7B 기반으로 키보드·마우스 Minecraft를 플레이한다. HF에 `CraftJarvis/JarvisVLA-Qwen2-VL-7B`로 공개됐다(2025-03-21). — [HF collection](https://huggingface.co/collections/CraftJarvis/jarvis-vla-v1)
- [공식] ROCKET-2 (arXiv 2503.02505, AAAI):
  - 사람 시점의 분할 마스크로 목표를 정한다.
  - 추론 효율이 ROCKET-1의 3~6배다.
  - Minecraft로만 학습했는데 행동 공간 매핑만으로 Doom, DMLab, Unreal에 zero-shot으로 옮겨진다. — [arXiv 2503.02505](https://arxiv.org/pdf/2503.02505)
- [공식] Optimus-3 (arXiv 2506.10357): 과제 단위로 라우팅하는 MoE와 추론 강화 RL을 쓴다. Minecraft 과제에서 기존 SOTA와 범용 MLLM보다 높다고 주장한다. — [arXiv 2506.10357](https://arxiv.org/abs/2506.10357v1)

**2026년 서베이와 신규 벤치마크**
- [공식] 2026-05-11 서베이(칭화대, HKU MMLab, UCAS)는 VLA 계열을 이렇게 묶는다: VPT, STEVE-1, SIMA/SIMA2, JarvisVLA, OpenHA, CombatVLA, Game-TARS, OpenP2P.
  - 남은 상충관계 5가지를 든다. 그중 둘이 "Reasoning vs Reactivity(지연-지능 딜레마)"와 "Harness Paradox(모듈식 워크플로 대 모델 단독)"다.
  - 실시간 3D 게임(FPS, MOBA, ARPG)은 ms 단위 반응이 필요한데 데이터가 부족하다고 지적한다.
  - CombatVLA는 action-of-thought를 잘라 디코딩해서 50배 빨라졌다. — [arXiv 2605.09965](https://arxiv.org/html/2605.09965v1)

**General Intuition (Medal 분사, 2025-10)**
- [보도] 2025-10에 시드 1억 3,370만 달러를 받았다(Khosla, General Catalyst).
- [보도] 이후 기업가치 23억 달러에 3억 2천만 달러를 유치했다.
- [보도] "2026년 여름 끝나기 전 API를 더 개방"할 계획이었다. — [The Next Web](https://thenextweb.com/news/general-intuition-300m-world-models-gaming-data), [GamesBeat](https://gamesbeat.com/?p=327574), [i-scoop](https://www.i-scoop.eu/general-intuition-bets-billions-that-video-games-can-teach-ai-to-act-in-the-real-world/)

### Inferences
- [추정] 2025~2026년의 큰 흐름은 두 가지다.
  - 대형 VLM을 키보드·마우스 행동으로 후학습한다(SIMA 2, Game-TARS, Lumine).
  - 반응형 소형 행동복제 정책을 공개한다(NitroGen, Open-P2P).
- [추정] 대형 쪽 공통 설계는 "느린 추론은 드물게, 빠른 행동은 청크로"다.
  - Lumine: 5Hz 지각, 30Hz 행동, 적응형 추론.
  - Game-TARS: Sparse-Thinking.
  - SIMA 2: 컨텍스트를 제한한 Flash-Lite.
  - Thorkell의 구조(결정적 반사, 빠른 타입 결정, 드문 플래너)와 같은 방향이다.
- [추정] Valheim이 학습 세트에 들어 있다고 확인된 범용 에이전트는 SIMA 2뿐이다. SIMA 2는 닫혀 있으므로 Thorkell이 쓸 수 없다.

### Gaps
- SIMA 2의 Valheim 단독 성공률은 공개되지 않았다(논문에는 포트폴리오 평균만 있다). 프리뷰 신청 경로는 찾지 못했다.
- 확인하지 못한 것:
  - Game-TARS, Lumine, UI-TARS-2의 가중치 공개 여부(2026-10). 프로젝트 페이지에서 공개 문구를 찾지 못했다.
  - ROCKET-2와 Optimus-3의 가중치·라이선스.
  - JARVIS-VLA의 라이선스.
  - NitroGen 라이선스의 정확한 상업 이용 조항(원문 미확인).
  - General Intuition이 2026 여름 이후 실제로 API나 모델을 냈는지.
- 2026년 신규 아카이브 논문 중 Matrix-Game 3.5(2608.29910), Zing-0.5(2609.17909), SolarWM(2609.02886)은 검색 결과의 제목만 확인했다.

## 2. 시스템별 공개 여부·라이선스·크기·하드웨어·지연·Apple Silicon·3D 오픈월드 성능

### Takeaway
가중치가 공개됐고 실시간을 겨냥한 모델은 둘이다.
- Open-P2P: MIT, 150M~1.2B, 키보드·마우스, <50ms.
- NitroGen: NVIDIA License, 493M, 게임패드 전용.

둘 다 Windows와 NVIDIA를 기준으로 만들고 시험했다. Apple Silicon 지원은 어디에도 문서화되어 있지 않다. 2026-06 UE5 신작 벤치마크에서는 둘 다 거의 0점이었다. 3D 오픈월드나 생존 게임에서 장시간 성과를 보인 것(SIMA 2, Lumine)은 모두 비공개이거나 데이터센터 GPU가 필요하다.

### Cited Findings

| 시스템 | 가중치 | 라이선스 | 크기 | 추론 하드웨어 / 지연 | Apple Silicon | 3D 오픈월드·생존 성과 |
|---|---|---|---|---|---|---|
| SIMA 2 | 비공개, 제한 프리뷰 [공식] | — | Gemini Flash-Lite 기반, 크기 미공개 | 미공개 | 해당 없음 | ASKA 약 40%(처음 하는 사람 약 32%), Valheim은 학습 세트 [공식] |
| Game-TARS | 공개 문구 없음 [공식] | — | MoE-mini: 2.5B 활성 + 632M ViT / Dense: 7B | 미공개 | — | Minecraft MCU 72.0% 임베디드 [공식] |
| UI-TARS-1.5-7B | 공개 [공식] | Apache 2.0 | 8B | 미기재 | MLX 변환 가능성 [추정] | Minecraft Mine Blocks 0.42(어느 모델 수치인지 불명) [공식] |
| Lumine | 공개 확인 못 함 | — | 7B (Qwen2-VL) | H20 4장, 첫 청크 약 110ms [공식] | 불가에 가까움 [추정] | 원신 5시간 메인 스토리 완주 [공식] |
| NitroGen | 공개 [공식] | NVIDIA License (+Apache 2.0 SigLIP2) | 493M | 미기재, 평가는 게임 정지 방식 / 게임은 Windows 전용 [공식] | 문서 없음 | 3D ARPG 일부 과제, 오픈월드 생존 수치 없음 [공식] |
| Open-P2P | 공개 [공식] | MIT (논문은 CC BY-NC-ND) | 150M / 300M / 600M / 1.2B | RTX 5090/5080, Windows 11, <50ms 필요 [공식] | 문서 없음 | Roblox, DOOM, Quake에서 "사람과 견줄 만함" [공식] |
| WHAM | 공개 [공식] | MS Research License (학술 전용) | 200M / 1.6B | A6000/A100, 실시간 불가 [공식] | CUDA 전용 | Bleeding Edge 전용 |
| JARVIS-VLA | 공개 [공식] | 확인 못 함 | 7B | 미확인 | — | Minecraft 전용 |

출처: [DeepMind](https://deepmind.google/blog/sima-2-an-agent-that-plays-reasons-and-learns-with-you-in-virtual-3d-worlds/), [arXiv 2512.04797](https://arxiv.org/html/2512.04797), [arXiv 2510.23691](https://arxiv.org/html/2510.23691v1), [HF UI-TARS-1.5-7B](https://huggingface.co/ByteDance-Seed/UI-TARS-1.5-7B), [arXiv 2511.08892](https://arxiv.org/html/2511.08892v1), [HF NitroGen](https://huggingface.co/nvidia/NitroGen), [GitHub NitroGen](https://github.com/MineDojo/NitroGen), [GitHub open-p2p](https://github.com/elefant-ai/open-p2p), [HF WHAM](https://huggingface.co/microsoft/wham), [HF JARVIS-VLA](https://huggingface.co/collections/CraftJarvis/jarvis-vla-v1)

- [공식] OmniGameArena(2026-06-08, 새로 만든 UE5 게임 12종):
  - 특화 정책인 NitroGen(게임패드)과 Open-P2P(키보드·마우스)는 대부분 게임에서 거의 0점이었다.
  - 공개 가중치 VLM인 Qwen3.5 계열은 모든 게임에서 0.15 미만이었고, 몇 게임은 정확히 0.00이었다.
  - 상용 VLM이 우세했다. GPT-5.5가 솔로 7종 중 4종에서 1위였고, Claude Opus 4.6은 CueChase에서 0.840을 냈다. — [arXiv 2606.09826](https://arxiv.org/html/2606.09826)
- [공식] NitroGen의 52% 개선은 처음 보는 게임에 **미세조정한 뒤** 처음부터 학습한 모델과 비교한 상대 개선이다. 미세조정 없는 zero-shot 수치가 아니다. — [arXiv 2601.02427](https://arxiv.org/html/2601.02427v1)
- [커뮤니티] Lumine을 "7B 모델이 원신을 5시간 플레이"라고 소개한 블로그 글이 있다. — [Daniel Hussey blog](https://danhussey.bearblog.dev/lumine-how-a-7b-model-plays-genshin-impact-for-5-hours/)

### Inferences
- [추정] Open-P2P가 키보드·마우스와 텍스트 지시를 받으므로 형태상 Thorkell에 가장 가깝다. 그래도 다음 이유로 Valheim에는 쓸모가 거의 없다.
  - 학습 게임이 Roblox와 FPS다.
  - 해상도가 192×192다.
  - 새 UE5 게임에서 거의 0점이었다.
  - Valheim에 쓰려면 Valheim 시연 데이터로 미세조정해야 한다. 그러려면 사람 플레이를 수십~수백 시간 녹화하고 H100급 학습을 해야 한다.
- [추정] Open-P2P 150M은 PyTorch MPS로 돌릴 수는 있을 것이다. 하지만 같은 M4 Pro GPU에서 Valheim 클라이언트 두 개(Rosetta)가 렌더링하는 중에 <50ms 루프를 지킬 수 있는지는 검증된 바 없다.
- [추정] 정보 동등성 면에서는 픽셀 입력 정책이 이상적이다. 사람이 보는 화면만 보기 때문이다. 하지만 Thorkell은 이미 "사람이 화면에서 알 수 있는 정보"로 걸러낸 구조화 지각을 갖고 있다. 픽셀로 바꾸면 비용만 늘고 검증 가능성(타입 결과 코드, 월드 변화 검증)이 떨어진다.

### Gaps
- NitroGen과 Open-P2P의 Apple Silicon(MPS/MLX) 실행 사례를 찾지 못했다. 공식 문서는 Windows와 NVIDIA만 언급한다.
- Lumine과 Game-TARS를 소비자 GPU에서 돌린 사례가 없다.
- 어떤 공개 모델도 Valheim에서 평가된 적이 없다(SIMA 2 학습 세트를 빼면).

## 3. 월드 모델은 에이전트 플레이에 도움이 되는가 (계획·학습 데이터·평가), 아니면 아직 콘텐츠 생성기인가

### Takeaway
연구 수준에서는 "도움이 된다"는 증거가 생겼다.
- Dreamer 4: 오프라인 데이터만으로 Minecraft 다이아몬드를 얻었다.
- SIMA 2: Genie 3 세계에서 자기개선했다.
- World-in-World (ICLR 2026): 폐루프 계획에서 이득을 보였다.

다만 다음 조건이 모두 필요하다.
- 대상 게임 전용으로 학습한 월드 모델
- 데이터센터 GPU
- 비공개 모델이거나 연구 코드

공개된 실시간 월드 모델(Matrix-Game 3.0, WHAM)은 사실상 콘텐츠·영상 생성기다. 상용 프리뷰인 Project Genie는 60초 제한이 있다. 취미 개발자가 Valheim 에이전트를 위해 쓸 수 있는 단계는 아니다.

### Cited Findings
- [공식] Dreamer 4 (2025-09-29):
  - 빠르고 정확한 월드 모델 안에서 강화학습한다.
  - 고정된 오프라인 데이터만으로 Minecraft 다이아몬드를 얻은 첫 에이전트다. 2만 개 이상의 키보드·마우스 행동이 필요한 과제다.
  - OpenAI VPT 오프라인 에이전트보다 데이터를 100배 적게 쓰고도 성능이 크게 높다.
  - 월드 모델은 단일 GPU에서 실시간으로 대화형 추론을 한다. — [arXiv 2509.24527](https://arxiv.org/abs/2509.24527v1), [project page](https://danijar.com/project/dreamer4/)
  - [보도/2차] "21 FPS"라는 수치는 2차 요약에서만 확인했다. — [InfoQ](https://www.infoq.com/news/2025/10/dreamer-4-minecraft-agent)
- [공식] SIMA 2는 Genie 3가 만든 사실적 세계에서 자기개선했다. 학습 과제 대부분에서 점수가 넓게 올랐고, 홀드아웃 자연 환경으로도 일반화했다. Genie 3 세계 평가는 정성 평가다. — [arXiv 2512.04797](https://arxiv.org/html/2512.04797)
- [보도] Demis Hassabis는 이 구조를 "Infinite Training Loop"라고 부른다. — [TechTimes](https://www.techtimes.com/articles/317932/20260606/deepmind-world-models-train-robots-imagined-worlds-sima-practices-inside-genie-3-model.htm)
- [공식] World-in-World (ICLR 2026 oral)는 월드 모델을 폐루프 과제 성공률로 평가한 첫 공개 플랫폼이다. 발견 세 가지:
  1. 시각 품질이 과제 성공을 보장하지 않는다. 조작 가능성(controllability)이 더 중요하다.
  2. 행동-관측 데이터로 후학습을 늘리는 편이 사전학습 영상 생성기를 바꾸는 것보다 효과가 크다.
  3. 추론 시간 연산을 늘리면 폐루프 성능이 크게 오른다. — [arXiv 2510.18135](https://arxiv.org/pdf/2510.18135), [ICLR 2026](https://iclr.cc/virtual/2026/oral/10006575)
- [공식] Matrix-Game 3.0 (Skywork, 2026-03-27, MIT): 장기 기억을 가진 실시간 스트리밍 월드 모델이다. 검색 요약상 5B 모델이 720p 최대 40FPS를 낸다. 레포 페이지에는 필요한 GPU가 적혀 있지 않다. — [GitHub SkyworkAI/Matrix-Game](https://github.com/SkyworkAI/Matrix-Game), [arXiv 2604.08995](https://arxiv.org/html/2604.08995v1)
- [공식] Hunyuan-GameCraft-2 (2025-11)는 지시를 따르는 대화형 게임 월드 모델이다(제목과 초록 수준만 확인). — [arXiv 2511.23429](https://arxiv.org/pdf/2511.23429)
- [공식] WHAM은 실시간에 너무 느리고 Bleeding Edge 밖으로 일반화하지 못한다. — [HF microsoft/wham](https://huggingface.co/microsoft/wham)
- [공식] Project Genie는 60초 제한, 조작 지연, 물리 불일치가 있다. 연구 프로토타입으로 내놓았다. — [Google blog](https://blog.google/innovation-and-ai/models-and-research/google-deepmind/project-genie/)
- [공식] 2026 서베이는 "Code Engine vs World Model (Simulation Gap)"을 남은 상충관계로 꼽는다. — [arXiv 2605.09965](https://arxiv.org/html/2605.09965v1)

### Inferences
- [추정] Thorkell에게 월드 모델은 당분간 쓸 데가 없다.
  - Valheim 자체와 2D 시뮬레이터(`brain/thorkell/sim/world.py`)가 이미 정확한 시뮬레이터다.
  - 월드 모델의 장점(오프라인 상상 학습)은 실환경 상호작용이 비싸거나 위험할 때 나온다.
  - Thorkell은 APFS 클론 런타임에서 실게임을 안전하게 돌릴 수 있다.
- [추정] World-in-World의 "조작 가능성 > 시각 품질"은 Thorkell의 2D 시뮬레이터 방향을 지지한다. 픽셀을 흉내 낼 필요 없이, 명령·이벤트 규약과 결과 검증을 Body와 맞추는 것이 중요하다.

### Gaps
- Dreamer 4 월드 모델의 크기, GPU 종류, 데이터 시간, 다이아몬드 성공률을 원문에서 확인하지 못했다(프로젝트 페이지와 초록에 없음).
- Matrix-Game 3.0이 실시간을 내는 GPU 사양을 확인하지 못했다.
- Genie 3 위에서 SIMA 2가 학습한 결과를 정량화한 공개 수치가 없다.

## 4. 컴퓨터 사용·화면 에이전트(OpenAI, Anthropic, Google 등)의 실시간 게임 플레이: 지연과 결과

### Takeaway
2026년 프런티어 모델(GPT-5.x, Claude 4.6, Gemini 3)은 브라우저·UE5 게임에서 처음 하는 사람의 절반~2/3 수준까지 왔다. 하지만 한 스텝에 수 초~16초가 걸린다. 그래서 실시간 제어 루프로는 쓸 수 없다. 대신 게임을 멈추거나 상위 결정만 맡기는 구조에서는 유용하다.

### Cited Findings
- [공식] VideoGameBench (2025-05, 오래된 사실): 1990년대 게임 10종이다. 최고 모델(Gemini 2.5 Pro, Claude 3.7 Sonnet)은 실시간 버전을 0.48%, 게임을 멈추는 Lite 버전을 1.6% 완료했다. — [arXiv 2505.18134](https://arxiv.org/pdf/2505.18134)
- [공식] GameWorld (2026-04-08): 브라우저 게임 34종, 과제 170개, 100행동 제한.

  진행률(progress):

  | 구분 | 모델 | 진행률 |
  |---|---|---|
  | 범용 인터페이스 | Gemini-3-Flash-Preview | 41.9% |
  | 범용 인터페이스 | GPT-5.2 | 40.6% |
  | 범용 인터페이스 | Claude-Sonnet-4.6 | 39.3% |
  | 범용 인터페이스 | Seed-1.8 | 39.0% |
  | 컴퓨터 사용 인터페이스 | Seed-1.8 | 39.8% |
  | 컴퓨터 사용 인터페이스 | Claude-Sonnet-4.6 | 38.3% |
  | 컴퓨터 사용 인터페이스 | Gemini-2.5-Computer-Use | 36.1% |
  | 사람 | 처음 하는 사람 | 64.1% (성공 55.3%) |
  | 사람 | 숙련자 | 82.6% (성공 77.1%) |

  — [arXiv 2604.07429](https://arxiv.org/html/2604.07429)
- [공식] GameWorld 실시간 모드에서 잰 스텝당 지연:

  | 모델 | 스텝당 지연 |
  |---|---|
  | Qwen3-VL-235B-A22B | 6.2~6.4초 |
  | Qwen3-VL-30B-A3B | 2.4~3.4초 |

  기억 라운드를 늘리면 입력이 약 1.3k에서 3.1k 토큰으로, 지연이 5.5초에서 8.6초로 늘었다. — [arXiv 2604.07429](https://arxiv.org/html/2604.07429)
- [공식] OmniGameArena (2026-06-08):
  - GPT-5.5는 행동 하나에 약 16초가 걸린다. 추론 지연을 시간에 넣으면 SharedFloor 점수가 0.368에서 0.048로 떨어졌다. 정상이라면 84번 행동할 시간에 14번만 했다.
  - 행동당 점수는 거의 그대로였다. 즉 판단의 질이 아니라 상호작용 횟수가 줄어서 생긴 손실이다.
  - Claude Opus 4.6이 더 새로운 Opus 4.7보다 솔로 7종 중 5종에서 높았다. — [arXiv 2606.09826](https://arxiv.org/html/2606.09826)
- [공식] 같은 범위에서 Game-TARS는 VizDoom(FPS)에서 GPT-5, Gemini-2.5-Pro, Claude-4-Sonnet을 이겼다. 전용 학습 모델이 범용 프런티어 모델보다 반응형 게임에서 낫다는 신호다. — [arXiv 2510.23691](https://arxiv.org/html/2510.23691v1)
- [공식] Compiled Agency (2026-07-17, 개정 2026-09-26):
  - 코딩 에이전트가 구조화된 관측·행동 인터페이스만 보고 **모델 호출이 0번인 컨트롤러 코드**를 만든다.
  - 이 코드는 StarCraft II의 공정한 내장 AI를 모두 이겼고, Civilization을 정복으로 끝냈다.
  - 사용한 에이전트 이름은 요약에 없었다. — [arXiv 2609.18996](https://arxiv.org/abs/2609.18996)
- [커뮤니티] Gemini 3 Pro가 Pokémon Crystal을 완주했다(배지 16개, 사천왕, 레드). Gemini 2.5 Pro보다 토큰과 이동이 약 절반이었다. ARISE Foundation의 Joel Zhang이 Twitch로 중계했다. — [youmind 요약](https://youmind.com/landing/x-viral-articles/gemini-3-pro-pokemon-benchmark)
- [커뮤니티] Claude는 Pokémon Red 완주가 늦었고, Opus 4.5에서 일부 난관을 넘었다. — [Alignment Forum, julian bradshaw](https://www.alignmentforum.org/users/julian-bradshaw)
- 포켓몬은 턴제라서 실시간 지연 문제는 없다.
- [공식] MineCollab / MINDcraft (2025-04): Minecraft에서 LLM 에이전트가 도구 47개(API)와 대화로 협업한다.
  - 단계별 계획을 말로 하게 하면 성능이 최대 15% 떨어졌다.
  - 병목은 효율적인 자연어 소통이었다. — [arXiv 2504.17950](https://arxiv.org/abs/2504.17950)
- [공식] SIMA 2도 저지연을 위해 컨텍스트 창을 제한한다고 밝혔다. — [DeepMind blog](https://deepmind.google/blog/sima-2-an-agent-that-plays-reasons-and-learns-with-you-in-virtual-3d-worlds/)

### Inferences
- [추정] Valheim처럼 몹이 실시간으로 공격하는 게임에서 범용 컴퓨터 사용 에이전트에게 매 프레임 제어를 맡기면 실패한다. 2026 측정치가 2~16초/스텝이기 때문이다. 이는 Thorkell이 실게임에서 겪은 "플래너 경유 20초 지연" 교훈과 같은 결론이다.
- [추정] 프런티어 모델의 쓸모는 "상위 결정과 대화"에 있다. 반사와 숙련 동작은 결정적 코드가 맡는다.
  - Compiled Agency 결과(모델 호출 0인 코드가 SC2와 Civ를 이김)는 Thorkell의 "검증된 스킬은 코드로, 모델은 처음 보는 말과 수량 판단만"이라는 원칙을 지지한다.
  - MineCollab은 API 기반 동료 에이전트의 병목이 조작보다 소통에 있음을 보여 준다. Thorkell의 대화 설계에 참고할 만하다.

### Gaps
- Claude, OpenAI(CUA/Operator), Gemini 2.5 Computer Use가 3D 실시간 오픈월드 게임(Valheim급)을 직접 플레이한 공개 측정치를 찾지 못했다.
- GameWorld와 OmniGameArena의 프런티어 모델 지연은 API 왕복을 포함하므로 지역과 시점에 따라 달라진다. GPT-5.5의 16초는 한 과제의 값이다.

## 5. 24GB M4 Pro 맥에서 취미 개발자가 2026년에 실제로 쓸 수 있는 것 vs 연구 전용, 그리고 Thorkell 판단

### Takeaway
24GB 맥에서 Valheim 클라이언트 두 개(Rosetta)와 함께 "픽셀→행동 범용 게임 모델"을 실시간 제어 정책으로 돌리는 것은 2026-10 현재 현실적이지 않다.
- 공개 모델은 Windows와 NVIDIA 기준이고, 새 게임에 약하다.
- 강한 모델은 비공개이거나 데이터센터 GPU가 필요하다.

취미 개발자가 쓸 수 있는 것은 소형 공개 VLM(4~8B, MLX)을 가끔 화면을 설명하는 보조 도구로 쓰는 정도다. 게임 파운데이션 모델은 Gemini 무료 등급 문제(flash 하루 20회)의 해법도 아니다.

### Cited Findings
- [커뮤니티] Qwen3-VL-30B-A3B 4bit의 Apple Silicon 측정치:

  | 기계 | 컨텍스트 | prefill | 생성 | TTFT |
  |---|---|---|---|---|
  | M4 Pro 20코어 GPU, 48GB (2026-03-10) | 16k | 507.7 tok/s | 36.3 tok/s | 32.3초 |
  | M4 Pro 16코어 GPU (검색 요약) | 4k | — | — | 약 6.4초 |

  — [omlx.ai benchmark](https://omlx.ai/benchmarks/9cohma58)
- [공식] 같은 Qwen3-VL 계열은 GameWorld 실시간 모드에서 데이터센터 서빙 기준으로도 스텝당 2.4~6.4초였다. — [arXiv 2604.07429](https://arxiv.org/html/2604.07429)
- [공식] 공개 게임 정책의 실행 요구:
  - Open-P2P: Windows 11, RTX 5090/5080, <50ms. — [GitHub open-p2p](https://github.com/elefant-ai/open-p2p)
  - NitroGen: 게임 클라이언트 Windows 전용, 게임패드만. — [GitHub NitroGen](https://github.com/MineDojo/NitroGen)
  - WHAM: CUDA, 실시간 불가. — [HF WHAM](https://huggingface.co/microsoft/wham)
  - Lumine: H20 4장. — [arXiv 2511.08892](https://arxiv.org/html/2511.08892v1)
- [공식] OmniGameArena에서 공개 가중치 VLM과 특화 정책은 새 게임에서 거의 0점이었다. — [arXiv 2606.09826](https://arxiv.org/html/2606.09826)
- [공식] UI-TARS-1.5-7B는 Apache 2.0으로 공개된 8B 모델이다. 공개 범용 GUI·게임 에이전트 가운데 맥에 올릴 수 있는 크기에 해당한다. — [HF](https://huggingface.co/ByteDance-Seed/UI-TARS-1.5-7B)

### Inferences

**[추정] 사용 가능성 분류 (24GB M4 Pro, Valheim 두 개 동시 실행 기준)**

| 범주 | 항목 | 판단 |
|---|---|---|
| 지금 써 볼 만함 | 소형 공개 VLM (Qwen3-VL 4B/8B 4bit, UI-TARS-1.5-7B를 MLX로) | 메모리 약 3~6GB [추정]. 실시간 제어가 아니라 "가끔 스크린샷을 묘사·질의"하는 도구로만 쓴다. 수 초 지연을 감수한다. 정보 동등성은 픽셀이라 자연히 지켜진다. |
| 지금 써 볼 만함 | 설계 패턴 참고 | Lumine(5Hz/30Hz, 적응형 추론), Game-TARS(Sparse-Thinking), SIMA 2(짧은 컨텍스트 Flash-Lite), Compiled Agency(스킬을 코드로). 지금 구조를 바꾸지 않고 검증 근거로 쓴다. |
| 손이 많이 듦 | Open-P2P 150M을 MPS로 이식하고 Valheim 시연으로 미세조정 | 사람 플레이 녹화 수십 시간 이상, H100급 학습, 입력 주입 경로 새로 작성이 필요하다. 얻는 것은 반응형 저수준 조작뿐이고, 이건 이미 결정적 반사와 스킬이 더 확실하게 한다. |
| 연구 전용 / 접근 불가 | SIMA 2, Game-TARS, Lumine, UI-TARS-2 | 비공개 또는 데이터센터 GPU 필요 |
| 연구 전용 / 접근 불가 | Genie 3 / Project Genie | 미국 Ultra 구독, 60초 |
| 연구 전용 / 접근 불가 | Dreamer 4, WHAM, Matrix-Game 3.0 | CUDA, 게임 전용 학습 |
| 연구 전용 / 접근 불가 | NitroGen | 게임패드, Windows, 비상업 가능성 |

- [추정] GPU와 메모리 경합: Valheim x86_64 클라이언트 두 개가 Rosetta로 같은 통합 GPU에서 Metal 렌더링을 한다. 여기에 30B급 VLM은 메모리상 들어가지 않는다. 4~8B를 돌려도 프레임 저하와 추론 지연이 서로 악화될 수 있다(실측 필요).
- [추정] Thorkell의 병목 두 가지(Gemini 무료 등급 하루 20회, 클라우드 플래너 수~수십 초)는 게임 파운데이션 모델로 풀리지 않는다. 다음 방향이 맞다(다른 연구 범위).
  - 로컬 텍스트 LLM이나 증류 모델(laya)로 빠른 결정을 맡긴다.
  - 플래너 호출 횟수를 줄인다(아는 명령은 바로 스킬로).
- [추정] 요약 판단: 2026-10 기준으로 Thorkell이 범용 게임 에이전트나 게임 파운데이션 모델을 **실행 경로에 넣을 이유는 없다.** 현재 하이브리드 구조(구조화 지각 + 결정적 반사 + 타입 결정 + 드문 플래너)가 업계 최전선(SIMA 2, Lumine, Game-TARS)의 설계 방향과 일치한다. 실익은 다음 두 가지다.
  1. 선택적 "화면 보기" 보조 도구(소형 VLM)
  2. 위 논문들의 지연 예산과 추론 빈도 설계를 근거로 인용하는 것

### Gaps
- 소형 VLM(4~8B)을 MLX로 M4 Pro 24GB에서 Valheim 두 개와 동시에 돌린 실측 지연과 프레임 영향은 공개 자료가 없다. 직접 재야 한다.
- Open-P2P와 NitroGen을 MPS/MLX로 옮긴 사례, 그리고 macOS 게임 입력 주입과 결합한 사례가 없다.
- SIMA 2 프리뷰에 취미 개발자가 접근할 수 있는지는 공개 정보로 판단할 수 없다.
