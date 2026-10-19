# 게임 플레이 LLM/VLM 에이전트 아키텍처와 벤치마크 — 갱신판 (기준일 2026-10-17)

기준선: `docs/research/research_notes/게임 플레이 AI 기술 동향 2026/agent_architectures_and_benchmarks.md` (기준일 2026-10-10)

**변경 표기**

| 표기 | 뜻 |
|---|---|
| [unchanged] | 이번에 다시 확인했고 그대로다 |
| [changed] | 사실이 바뀌었거나 기준선의 Gap이 해소됐다 |
| [new] | 기준선에 없던 항목. 2026-09-01 이후 것과, 그 전에 나왔지만 기준선이 놓친 것을 모두 포함한다(놓친 것은 "놓침"으로 적음) |
| [corrected] | 기준선이 틀렸다 |

**출처 유형 표기**

| 표기 | 뜻 |
|---|---|
| [논문] | arXiv 프리프린트 또는 학회 논문. 학회 채택 여부는 따로 적는다 |
| [리더보드] | 벤치마크 사이트의 표 |
| [코드] | GitHub 저장소 메타데이터와 README |
| [공식 블로그] | 개발사나 벤더의 글 |
| [검색 요약] | 검색 결과 요약으로만 확인한 것. 원문을 열지 않았으니 신뢰도가 낮다 |
| [커뮤니티] | 비공식 보도·집계 |
| [추정] | 이 노트 작성자의 추론 |

모든 확인일은 2026-10-17이다.

## 1. 기준선(2026-10-10)의 핵심 주장은 아직 맞는가

### Takeaway
구조적 결론은 그대로다. 결정적 실행층과 이벤트·문(gate) 기반 언어 모델층으로 나누고, 구조화 텍스트로 지각하며, 소형 zero-shot 플래너는 약하다는 결론이다. 다만 기준선의 BALROG 환경별 수치는 **틀렸다**. "NetHack 65%"는 MiniHack 점수였고, frontier의 NetHack 최고는 13.2%다. 상위 5개 제출은 모두 BALROG 팀이 재현하지 않은(미검증) 결과다.

### Cited Findings
**[corrected] BALROG 환경별 수치.** 리더보드 HTML을 직접 파싱해서 확인했다. 열 순서는 BabyAI, Crafter, TextWorld, BabaIsAI, MiniHack, NetHack이다. — [balrogai.com](https://balrogai.com)

| 모델 (등록일) | 평균 | BabyAI | Crafter | TextWorld | BabaIsAI | MiniHack | NetHack | 검증 |
|---|---|---|---|---|---|---|---|---|
| GPT-6-Astra-Max (2026-09-18) | 68.3±2.0 | 100.0 | 76.8 | 54.5 | 100.0 | 65.0 | 13.2±2.7 | 없음 |
| Claude-Opus-5-Max (2026-09-20) | 63.4±1.8 | 100.0 | 68.2 | 71.6 | 95.8 | 37.5 | 7.3±1.6 | 없음 |
| GPT-5.6-Sol-Max (2026-09-18) | 60.0±2.0 | 98.0 | 55.9 | 63.5 | 96.7 | 42.5 | 3.2±0.4 | 없음 |

- 기준선은 셋을 잘못 적었다.
  - Astra를 "Crafter 100%, NetHack 65%"로 적었다. 100%는 BabaIsAI, 65%는 MiniHack이다.
  - Opus-5-Max의 "NetHack 37.5%"와 Sol-Max의 "NetHack 42.5%"도 MiniHack 값이다.
- 기준선 Gap이던 "NetHack 65% 재확인"은 이것으로 해소됐다. 실제 NetHack 최고 13.2%도 논문 시점 o1의 1.57%보다 약 8배 높다.
- ✔("Checked": BALROG 팀이 접근권을 받아 재현함)가 없는 항목은 5개다. Astra-Max, Opus-5-Max, Sol-Max, Terra-Max, Luna-Max. "-Max" 접미사의 뜻은 페이지에 설명이 없다.
- 페이지에는 "매주 월요일 갱신"이라고 적혀 있다. 그런데 가장 최근 등록일은 여전히 2026-09-20이다.

**[unchanged] BALROG 순위·평균·소형 모델·VLM 표.** 1~3위 평균(68.3 / 63.4 / 60.0)은 그대로다. — [balrogai.com](https://balrogai.com), 확인 2026-10-17
- 소형 모델도 그대로다. Llama-3.1-8B 15.1, Qwen-2.5-7B 7.8, Mistral-Nemo 17.6, Llama-3.2-11B 16.8.
- VLM 표는 2025-04-25 이후 새 항목이 없다. 1위는 Gemini-2.5-Pro-Exp 35.7이다.

**[new] BALROG에서 기준선이 적지 않은 검증 항목.** — [balrogai.com](https://balrogai.com)
- Gemini 계열은 모두 ✔다.
  - Gemini-3-Flash 48.1 (2026-02-13). NetHack 4.0, MiniHack 30.0
  - Gemini-3-Pro 58.1
  - Gemini-3.1-Pro 56.9
  - Gemini-3.1-Pro-Thinking 57.0
- Claude 계열.
  - Claude-Opus-4.5 43.5 ✔
  - Claude-Haiku-4.5 31.2 ✔
- 미검증 항목: GPT-5.6-Terra-Max 53.2, GPT-5.6-Luna-Max 45.6.
- Thorkell이 쓰는 gemini-3.8-flash는 표에 없다.

**[unchanged] lmgame-Bench 리더보드.** 표기 갱신일은 여전히 2025-06-07이고, 1위 o3 66.17도 같다. 2026년 모델은 없다. — [HF Space](https://lmgame-lmgame-bench.hf.space)
- 저장소 `lmgame-org/GamingAgent`의 마지막 push는 2025-11-16이다. — [GitHub](https://github.com/lmgame-org/GamingAgent)

**[unchanged] VideoGameBench.** — [arXiv 2505.18134](https://arxiv.org/abs/2505.18134)
- 최신판은 v3(2026-05-14)다. 초록의 수치는 그대로다. 최고 0.48%, Lite 1.6%, Gemini 2.5 Pro와 Claude 3.7.
- 저장소 마지막 push는 2025-05-30이다. — [GitHub alexzhang13/videogamebench](https://github.com/alexzhang13/videogamebench)
- 2026년 모델 결과는 이번에도 찾지 못했다.

**[unchanged] Orak.** 논문은 다시 열지 않았다. 저장소 `krafton-ai/Orak`의 마지막 push는 2025-06-17이다. 결과가 갱신된 흔적은 없다. — [GitHub](https://github.com/krafton-ai/Orak)

**[unchanged] Mindcraft 본가.** — [GitHub](https://github.com/mindcraft-bots/mindcraft)
- develop 브랜치 마지막 push는 2026-10-03으로 그대로다.
- 별은 5,896개다(기준선 5,872).
- 새 릴리스는 없다. 최신은 여전히 v0.1.4(2026-03-20)다.

**[changed] mindcraft-ce의 차이(기준선 Gap 해소).** README가 스스로 "Mindcraft의 실험판"이라고 밝힌다. 브랜치는 `stable`, `develop`, `agent-system` 셋이다. 마지막 push는 2026-10-10, 별은 142개다. — [GitHub mindcraft-ce](https://github.com/mindcraft-ce/mindcraft-ce)
- `agent-system` 브랜치에 있는 것:
  - `use_function_calling`: 텍스트 명령 대신 구조화 툴 호출. Claude, GPT, Gemini, Grok, DeepSeek, Mistral을 지원한다.
  - LanceDB 기반 RAG(`RAGManager`)
  - XML 템플릿 기반 툴 프롬프트
- 기본 모델 게이트웨이는 Andy API(`andy/auto`)다.

**[unchanged] PUBG Ally (NVIDIA 블로그, 2026-06-25).** 다시 확인했고 내용이 같다. — [NVIDIA](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)
- 모델은 Mistral-NeMo-Minitron-2B다.
- 행동 트리가 System 1을 맡는다. 원문은 "Reflex-level actions never have to wait for the model"이다.
- 이벤트 구동 루프이고, 8GB VRAM에서 돈다.
- ms 단위 지연 수치는 없다.
- 베타 기간은 6월 17일~30일이다. 수정 공지는 없다.

**[unchanged] System Switch (arXiv 2610.09683).** — [arXiv](https://arxiv.org/abs/2610.09683)
- 여전히 v1(2026-10-07)뿐이다.
- 단독 저자(Gian Luca Bailo)이고, 14쪽, cs.AI, 심사를 거치지 않은 프리프린트다.
- 코드는 GitHub `system-switch` 브랜치에 있다.

**[unchanged] 병렬 계획-행동(Li et al., AAMAS 2026).** 이번에 원문은 다시 열지 않았다. 2026-04 AgenticCache 논문이 이 연구를 "다음 계획을 실행 중에 계산해 지연을 숨기지만, 환경이 바뀌면 계획이 무효가 되어 재계획 오버헤드가 생긴다"고 평가했다. — [검색 요약] [AgenticCache arXiv 2604.24039](https://arxiv.org/html/2604.24039v1)

**이번에 다시 확인하지 않은 항목.** 기준선의 PIANO, Latent Bridge, Real-Time Reasoning Gym, SALMONN-duo, Emergence World, MineExplorer, MineCollab, Andy-4, Voyager 계열, TextArena는 열지 않았다. 출처가 고정된 arXiv 판이라 내용이 바뀌었을 가능성은 낮다 [추정].

### Inferences
- [추정] BALROG의 NetHack은 frontier에서도 13.2%가 최고다. 장기·비가역 계획이 여전히 가장 큰 벽이라는 기준선 결론이 오히려 더 강해졌다.
- [추정] 상위권 수치는 모두 미검증 "-Max" 설정이다. 검증된 기준으로 보면 frontier는 약 57~58%다(Gemini-3-Pro 58.1, Gemini-3.1-Pro 56.9).
- [추정] 검증된 Gemini-3-Flash 48.1%는 현재 플래너(gemini-3.8-flash) 계열의 하한 참고치로 쓸 수 있다. 다만 3.8은 측정되지 않았다.

### Gaps
- BALROG 상위 미검증 제출의 하네스, 시도 횟수, "-Max"의 의미는 페이지에 없다.
- 기준선의 다른 arXiv 항목들(위 목록)은 이번 라운드에서 다시 열지 않았다.

## 2. 구조화 API(픽셀 아님) 기반 실시간 3D·오픈월드 게임 에이전트에서 지금 무엇이 잘 되는가

### Takeaway
기준선이 정리한 패턴은 유지된다. 행동 트리·스킬·반사가 S1을 맡고, 이벤트나 문(gate)이 열릴 때 부르는 계획 모델이 S2를 맡는다. 이번에 새로 확인한 근거는 셋이다.
1. 계획 전이를 캐시하고 비동기로 재검증하는 방식이 성공률을 올리면서 지연을 줄였다(AgenticCache, MLSys 2026).
2. 재계획 여부 자체를 예산 아래의 결정으로 다루는 방식(BRACE, ICML 2026)
3. 스킬·프롬프트 자기개선은 과적합하기 쉬워서 보류 변형(held-out variant)으로 검증해야 한다(OmniGameArena IDC)

### Cited Findings
**구조화 관측이 픽셀·자연어보다 낫다**
- [new][논문 NeurIPS 2026 E&D, v3 2026-09-25] Agentick: 과제 37개, 능력 범주 6개, 관측 모달리티 5종, Gymnasium 인터페이스. — [arXiv 2605.06869](https://arxiv.org/abs/2605.06869), [HTML v3](https://arxiv.org/html/2605.06869v3), [리더보드](https://roger-creus.github.io/agentick/board/)
  - "ASCII 관측이 자연어보다 일관되게 낫다." Qwen3.5-4B + Reasoner 하네스 기준 ASCII 0.228, 자연어 0.181이다.
  - 같은 모델을 RGB 픽셀 VLM으로 쓰면 0.093이다(리더보드 2026-07-24 등록).
  - "어느 한 방식이 지배하지 않는다." PPO가 다중 에이전트 범주 1위다(0.432).
- [unchanged] BALROG, Orak, lmgame-Bench의 "텍스트 > 픽셀" 결론은 기준선 그대로다.

**실시간 동반자·공동 플레이 구조**
- [new, 놓침][논문 arXiv, 2026-01-08/09] MineNPC-Task는 Minecraft에서 기억을 쓰고 주도권을 주고받는(mixed-initiative) LLM 에이전트용 과제 모음이다. — [arXiv 2601.05215](https://arxiv.org/abs/2601.05215)
  - 숙련 플레이어 8명과 함께 플레이하며 과제를 모았다. 하위 과제는 216개다.
  - 과제는 전제조건과 의존성을 가진 매개변수 템플릿으로 만들었다.
  - 과제마다 기계가 확인하는 검증기가 있다. "월드 밖 지름길 금지(bounded-knowledge policy)" 아래서 판정한다.
  - 하네스는 계획 미리보기, 확인 질문, 기억 읽기·쓰기, 전제조건 확인, 수리 시도를 기록한다.
  - 반복된 실패: 코드 실행, 인벤토리·도구 처리, 지시 대상 해석(referencing), 내비게이션.
  - 참가자들은 과제 간 기억 유지가 더 강해야 한다고 했다. 모델은 GPT-4o다.
- [new, 놓침][논문 arXiv cs.HC, v1 2026-04-06 / v2 2026-07-07] Bounded Autonomy는 라이브 멀티플레이어 게임의 LLM 캐릭터 제어층이다. 인터페이스는 셋이다. — [arXiv 2604.04703](https://arxiv.org/abs/2604.04703)
  - 에이전트끼리: 확률적 응답 연쇄 감쇠로 말이 끝없이 이어지지 않게 한다.
  - 에이전트와 월드: 임베딩 기반 행동 grounding과 폴백
  - 플레이어와 에이전트: 'whisper'라는 부드러운 조종
  - 초록에는 수치가 없다.
- [unchanged] PUBG Ally S1/S2, PIANO의 Cognitive Controller와 Action Awareness, Mindcraft `modes.js`의 `interrupts`(기준선 참조).

**계획 캐시와 비동기 재검증**
- [new, 놓침][논문 MLSys 2026, arXiv 2026-04-27] AgenticCache. — [arXiv 2604.24039](https://arxiv.org/abs/2604.24039), [MLSys oral](https://mlsys.org/virtual/2026/oral/3806)
  - 체화 과제에는 "계획 지역성"이 있다. 다음 계획을 현재 계획으로 대부분 예측할 수 있다.
  - 에이전트는 매 단계 LLM을 부르지 않는다. 자주 나오는 계획 전이를 캐시에서 꺼낸다.
  - 백그라운드 Cache Updater가 비동기로 LLM을 불러 캐시 항목을 검증하고 다듬는다.
  - 다중 에이전트 체화 벤치마크 4개 × 모델 3개, 12개 설정 평균: 과제 성공률 +22%, 시뮬레이션 지연 −65%, 토큰 −50%.
  - 초록에는 캐시 키 설계와 벤치마크 이름이 없다.

**재계획을 예산 아래의 결정으로**
- [new, 놓침][논문 ICML 2026, arXiv 2608.01428, 검색 요약] BRACE는 재계획 트리거마다 세 가지를 결정한다. 재계획할지, 어떤 모드로 할지, 토큰 예산을 얼마로 할지다. — [arXiv 2608.01428](https://arxiv.org/pdf/2608.01428), [ICML 2026 poster](https://icml.cc/virtual/2026/poster/63603)
  - E-RECAP 모듈이 재계획 맥락을 가지치기해서 Habitat 내비게이션에서 호출당 토큰이 71~76% 줄었다.
  - SLO 위반률이 85.5%에서 4.7%로 줄었다.

**반사는 즉시, LLM은 비동기**
- [new, 놓침][논문 arXiv 2506.07223, 검색 요약] RRARA: 규칙 정책이 즉시 행동하고 LLM 반성기가 비동기로 행동을 다듬는다. 추론 지연을 시뮬레이션 프레임으로 환산하는 Time Conversion Mechanism을 둔다. — [arXiv 2506.07223](https://arxiv.org/html/2506.07223)
- [new, 놓침][논문 arXiv 2605.13360, 검색 요약] Speculative Interaction Agents: 사용자 입력과 환경 이벤트 모두에 대해 비동기 I/O와 투기적(speculative) 툴 호출로 실시간 에이전트를 만든다. — [arXiv 2605.13360](https://arxiv.org/pdf/2605.13360)
- [검색 요약] AgenticCache 논문은 "작은 모델이 제안하고 큰 모델이 검증하는" 투기적 계획(Hua et al., 2025)을 이렇게 평가한다. 되돌리기에 시간이 드는 현실 환경(되돌아가기, 조작 취소)에서는 성능이 나쁘다. — [arXiv 2604.24039](https://arxiv.org/html/2604.24039v1)

**스킬 자기개선과 과적합**
- [new, 놓침][논문 arXiv 2603.13131 v3 2026-05, 검색 요약] MineEvolve. — [arXiv](https://arxiv.org/html/2603.13131v3)
  - Monitor가 하위 목표 실행을 타입이 있는 피드백으로 바꾼다.
  - Inducer는 성공에서 재사용 스킬을, 실패·정체에서 처방(remedy)을 뽑는다.
  - Iron, Redstone, Diamond, Armor처럼 의존성이 높은 과제군에서 이득이 컸다.
- [new, 놓침][논문 arXiv 2606.09826, 2026-06-08] OmniGameArena의 IDC 방식: 툴을 쓰는 반성 LLM이 한정된 스킬 프롬프트를 여러 라운드에 걸쳐 고친다. — [arXiv](https://arxiv.org/abs/2606.09826), [HTML](https://arxiv.org/html/2606.09826v1)
  - 최고점은 보통 곡선 중간에 나온다. LastStand에서 Opus 계열은 최고 라운드보다 마지막 라운드가 0.40~0.52 낮았다.
  - Claude Opus 4.7은 원래 과제에서 +201%였지만 변형 셋 모두에서 음수였다.
  - GPT-5.5는 원래 과제 이득이 +130%로 가장 작았지만 변형 셋 모두에서 양수였다.
- [new][논문 arXiv 2610.08076, 2026-10-06] SpeedrunBench: 시도를 반복하며 반성하는 하네스(OpenCode)에서 에이전트는 경로를 새로 만들기보다 주어진 시드를 다듬었다. 긴 행동 궤적은 "잘못된 수정 하나로 전체가 깨질 수 있다". — [arXiv](https://arxiv.org/abs/2610.08076), [HTML](https://arxiv.org/html/2610.08076v1)

### Inferences
- [추정] AgenticCache는 Thorkell의 "아는 명령 → 검증된 스킬 바로 시작" 규칙을 일반화한 형태다.
  - (상황 요약, 직전 계획) → 다음 계획 전이를 캐시한다.
  - 플래너(flash)는 백그라운드에서 캐시 항목을 검증·수정하는 데만 쓴다.
  - 이렇게 하면 하루 20회 한도 안에서 호출을 "실시간 응답"이 아니라 "캐시 보강"에 쓸 수 있다.
- [추정] OmniGameArena IDC와 MineEvolve를 보면, 회고로 만든 규칙·스킬을 바로 승격하면 원래 상황에 과적합한다. 승격 전에 다른 시드나 변형(예: 해안 시드 회귀 세트)에서 월드 변화로 검증해야 한다는 레포 규칙이 맞다.
- [추정] MineNPC-Task는 공개 벤치마크 가운데 Thorkell에 가장 가깝다. 사람과 함께하는 공동 플레이, 전제조건 템플릿, 기계 검증기, 월드 밖 지름길 금지(정보 동등성과 같은 취지)를 모두 갖췄다. 과제 템플릿과 검증기 형식을 회귀 세트 설계에 참고할 만하다.

### Gaps
- AgenticCache의 캐시 키·검증 방식과 벤치마크 이름은 초록에 없다. 본문을 읽지 않았다.
- BRACE, RRARA, Speculative Interaction Agents, MineEvolve는 검색 요약으로만 확인했다.
- 3D 서바이벌(Valheim류)에서 구조화 API 에이전트를 직접 평가한 2026-09~10 논문은 찾지 못했다.

## 3. 2026 게임 벤치마크는 무엇을 말하나: 리더보드, frontier 점수, 단계 지연, 실패 유형, 모델 크기 격차

### Takeaway
2026-09~10에 나온 새 벤치마크(SpeedrunBench, Agentick v3·리더보드, AgentWorld, Game Arena)와 기준선이 놓친 OmniGameArena가 공통으로 보여 주는 것은 셋이다.
1. 턴제·정지 설정에서 frontier는 많이 올랐다(Agentick 0.63, BALROG 미검증 68%).
2. 실시간·장기·협동 설정에서는 여전히 크게 무너진다. 지연을 게임 시간에 반영하면 점수가 급락한다.
3. frontier 모델의 결정당 지연은 수 초~십수 초다.

### Cited Findings
**Agentick 리더보드** — [new][리더보드, 확인 2026-10-17] [roger-creus.github.io/agentick/board](https://roger-creus.github.io/agentick/board/)

ONS는 oracle 정규화 점수다.

| 항목 | ONS | 비고 |
|---|---|---|
| Oracle | 0.895 | 상한 |
| GPT-6 Astra | 0.634 | high, 1 seed, 2026-09-15 |
| Claude Opus 5 | 0.628 | high, 1 seed, 2026-09-16 |
| GPT-5.6 Sol / Terra / Luna | 0.578 / 0.566 / 0.553 | |
| Qwen3.5-4B SFT-250k | 0.447 | |
| GPT-5 mini | 0.309 | |
| PPO 2M | 0.287 | |
| Gemini 2.5 Flash Lite | 0.187 | |
| Random | 0.082 | |

- frontier 항목은 모두 시드 1개이고 ASCII + `markovian_reasoner` 설정이다.
- 범주별 최고(LLM): Planning 0.833(Astra), Navigation·Reasoning 0.781, Generalization 0.583, Memory 0.500, Multi-agent 0.500(Luna).
- 논문 체크리스트("27 configurations, 90,000+ episodes")와 본문("31 configurations, 108,550 episodes")이 서로 다르다. — [HTML v3](https://arxiv.org/html/2605.06869v3)

**SpeedrunBench** — [new][논문 arXiv 2610.08076, 2026-10-06, Patronus AI 등] [arXiv](https://arxiv.org/abs/2610.08076), [HTML](https://arxiv.org/html/2610.08076v1), [코드](https://github.com/patronus-ai/speedrun_bench)
- 게임 9종: Super Mario Bros., Super Mario Land, Mario Kart 64, Pokémon Red/Blue, Civilization I, Astray, SuperTux, Tuxemon, SuperTuxKart.
- 모드는 둘이다.
  - 온라인: 스크린샷을 보고 행동이나 짧은 행동 묶음을 낸다.
  - 오프라인: 프레임 단위 행동 궤적 전체를 편집하고, 다시 재생한 결과를 피드백으로 받는다. 시각이 필요 없다.
- 평가 모델: Claude Opus 5, GPT-5.6-sol, Grok 4.6, Gemini-3.7-Flash, Kimi-K3, GLM 5.3/5.2, DeepSeek-V4-Pro/Flash, Inkling-Small.
- Pokémon 온라인, 첫 배지까지 걸린 프레임. 세계기록은 약 40,435프레임이다.

  | 모델 | 프레임 | 세계기록 대비 |
  |---|---|---|
  | Opus 5 | 160,021 | 약 4배 |
  | GPT-5.6-sol | 283,474 | |
  | Grok 4.6 | 477,140 | |
  | Kimi K3 | Route 2에 도달하지 못함 | |

- 오프라인 결과.
  - 최고 평균도 세계기록보다 2배 넘게 느리다.
  - Super Mario Land 1-1에서 GLM 5.2 + 채점기는 세계기록과 3% 이내였다. 궤적 약 22만 개를 약 114시간 동안 평가했다.
  - SuperTuxKart는 세계기록의 256~261%였다.
- 실패 유형.
  - 시드가 없으면 GLM 5.2가 SuperTux 목표에 도달하지 못했다.
  - Tuxemon에서는 10개 모델 중 4개가 체육관에 가지 못했다.
  - 단계별 지연과 비용은 보고하지 않았다. Inkling-Small의 결과도 본문에 없다.

**OmniGameArena** — [new, 놓침][논문 arXiv 2606.09826, 2026-06-08] [arXiv](https://arxiv.org/abs/2606.09826), [HTML](https://arxiv.org/html/2606.09826v1)
- 새로 만든 UE5 게임 12종이다(Solo 7, PvP 3, Coop 2).
- 입력은 RGB 프레임과 텍스트이고, 출력은 키보드·마우스 행동 묶음이다.
- 두 가지 시간 규칙으로 잰다.
  - PDQ: 추론하는 동안 게임을 멈추고, 생각하는 시간을 공짜로 친다.
  - LCRT: 실제로 걸린 결정 지연을 게임 시간에 주입한다.
- 결정당 지연: GPT-5.5는 순수 모델 시간이 결정당 약 16초다. 다른 모델의 값은 본문에서 "∼44–77 s"로 깨져 보였다. 4~7초로 읽어야 하는지는 확인하지 못했다.
- LCRT를 적용하면 점수와 행동 수가 크게 준다.

  | 과제 | 모델 | PDQ → LCRT |
  |---|---|---|
  | SharedFloor (협동) | GPT-5.5 | 점수 0.368 → 0.048, 에피소드당 행동 84 → 14 |
  | MonsterShoot | GPT-5.5 | 점수 −0.408 (모델 4개 모두 하락) |
  | SoloCraft | GPT-5.5 / Opus 4.6 | 에피소드당 행동 43 → 8 / 17 |

  - 예외도 있었다. LastStand에서 Opus 4.6은 LCRT에서 오히려 +0.101 올랐다.
  - LCRT는 4개 모델에만 적용했다: Claude Opus 4.6, Claude Sonnet 4.6, GPT-5.5, GPT-5.4.
- 오픈 가중치·전용 정책.
  - Qwen3.5-397B-A17B는 협동 2종에서 모두 0.000이었다.
  - NitroGen과 Open-P2P는 대부분의 Solo 과제에서 0 근처로 무너졌다.
- 실패 유형: 협동에서 같은 아이템을 중복 추적함, LLM끼리 협응이 약함, 구멍으로 넘어감, 지연 때문에 사격 타이밍을 놓침, PvP 결과가 비이행적임.

**기타 2026-09 벤치마크**
- [new][논문 arXiv 2609.31590, 2026-09-25, 검색 요약] AgentWorld(다중 에이전트 장기 협업): 최고 모델도 과제 성공률이 52.0%였다. 실패는 소통 붕괴와 역할 혼동이다. — [arXiv](https://arxiv.org/html/2609.31590v1)
- [new][논문 arXiv 2609.31473, 약 2026-09-25, 검색 요약] Game Arena: 체스, 포커, Werewolf에서 모델끼리 맞붙는 평가다. 체화 과제는 아니다. — [arXiv](https://arxiv.org/html/2609.31473v1)

**정지 없는 설정과 실시간 설정의 차이(기준선 수치 유지)**
- [unchanged] VideoGameBench: 실시간 0.48%, Lite 1.6%. — [arXiv 2505.18134](https://arxiv.org/abs/2505.18134)
- [unchanged] System Switch: 추론 지연 중앙값 9~29초. 33게임 중 출구에 도달한 판은 없다. — [arXiv 2610.09683](https://arxiv.org/abs/2610.09683)

**단계 지연 요약**

| 출처 | 결정당 지연 | 조건 |
|---|---|---|
| OmniGameArena (2026-06) | GPT-5.5 약 16초 | 클라우드 frontier, 픽셀 |
| System Switch (2026-10) | 중앙값 9~29초 | 로컬 Qwen3.6-35B-A3B / Gemma 4 26B-A4B |
| Latent Bridge (2026-06) | 약 1.5초 | 8B thinking |
| PUBG Ally (2026-06) | 공개 수치 없음 | 2B 온디바이스 |

- [커뮤니티, 신뢰도 낮음] Gemini 3 Pro가 Pokémon Crystal을 완주했다는 보도가 있다(2025-12, 개인 하네스, 집계 사이트). 2026년 Claude Opus 5의 Pokémon 실행 결과는 찾지 못했다. — [youmind 집계](https://youmind.com/pt-PT/landing/x-viral-articles/gemini-3-pro-pokemon-benchmark)

### Inferences
- [추정] 실패 축 넷(공간, 숨은 전제조건, 체계적 탐색, knowing-doing)에 다섯째를 더해야 한다. "지연이 게임 시간에 반영되면 frontier도 급락한다"이다(OmniGameArena LCRT). frontier를 실시간 루프 안에 두면 안 된다는 기준선 결론을 정량으로 뒷받침한다.
- [추정] 협동 과제에서 "같은 아이템 중복 추적"과 "LLM끼리 협응 약함"이 반복된다(OmniGameArena, AgentWorld, 기준선 MineCollab). 리더와 토르켈이 같은 나무나 자원을 노릴 때를 위한 명시적 분담 규칙(코드)이 필요하다.

### Gaps
- OmniGameArena 다른 모델들의 정확한 지연 값은 HTML 렌더링 오류로 확인하지 못했다.
- SpeedrunBench의 비용·지연, 소형 모델(Inkling-Small) 결과는 본문에서 찾지 못했다.
- ICLR 2027 투고작(OpenReview)은 검색에서 하나도 잡히지 않았다. 인덱싱이 늦은 것으로 보인다.
- arXiv API로 2026-10 목록을 체계적으로 훑으려 했으나 503·429(요청 제한)로 실패했다. 2026-10-10~17 사이의 게임 에이전트 논문은 검색 엔진에 걸린 SpeedrunBench, System Switch 외에는 확인하지 못했다.

## 4. 소형 모델(≤8B)은 플래너로서 어떤가, 선택기·분류기로서는 어떤가

### Takeaway
2026-09 근거도 기준선과 같은 쪽을 가리킨다. 4B 모델은 zero-shot이면 랜덤 수준이다. 하네스를 붙이면 약 10배, 좁은 과제 SFT를 하면 GPT-5 mini를 넘는다. 그래도 일반화 범주와 frontier 대비로는 뒤진다. 선택기·분류기 역할에서는 보정된 확신과 구조 강제(제약 디코딩)가 효과적이다. 그러나 제약 디코딩은 "의미"(어떤 값이 맞는가)를 고치지 못한다.

### Cited Findings
**[new] Agentick: 소형 모델 사다리** (Qwen3.5-4B, ASCII 관측) — [리더보드](https://roger-creus.github.io/agentick/board/), [HTML v3](https://arxiv.org/html/2605.06869v3)

| 설정 | 전체 ONS |
|---|---|
| zero-shot | 0.023 (Random 0.082보다 낮음) |
| Reasoner 하네스 | 0.228 |
| SFT-120k | 0.354 |
| SFT-250k | 0.447 (GPT-5 mini 0.309보다 높음) |

- 일반화(Generalization) 범주에서는 순서가 뒤집힌다. GPT-5 mini 0.437이 SFT-250k 0.350보다 높다. frontier는 0.583이다.
- 더 작은 모델(Reasoner, ASCII): Qwen3.5-2B 0.133, Qwen3.5-0.8B 0.094, Qwen3-4B 0.085.
- 같은 4B를 VLM(RGB)으로 쓰면 0.093이다.
- 서빙 비용: GPT-5 mini 약 $180, Gemini 3.1 Flash Lite 약 $45, Claude Haiku 4.5 약 $65, Qwen 서빙 약 200 GPU시간.

**[unchanged] BALROG 소형 모델.** 8B급은 7.8~17.6%다. — [balrogai.com](https://balrogai.com)

**[unchanged] System Switch.** Laya base(0.4B)는 확신으로 실패를 가려내는 능력(AUROC)이 0.89로 가장 좋았다. 가장 정확한 9B는 0.60~0.61이었다. — [arXiv 2610.09683](https://arxiv.org/abs/2610.09683)

**[new][논문 arXiv 2609.23742, 2026-09-20, 단독 저자, 6쪽, 미심사] 소형 모델의 제약 디코딩.** — [arXiv](https://arxiv.org/abs/2609.23742)
- 대상: 0.6B~4B 모델 5개(3개 계열), 구조화 출력 과제 14개. Outlines, XGrammar와 native 디코딩을 비교했다.
- 스키마 유효율은 78.6~92.9%에서 제약 디코딩으로 100%가 됐다.
- 제약 디코딩이 고치는 것: 타입 강제 실패. 검색 요약에 따르면 문자열 "4.98"과 숫자 4.98 같은 경우다.
- 고치지 못하는 것: 지시 의미 실패(다단계 함수 호출 등). 그 격차는 모델 크기에 따라 달라진다.
- 원문 표현: "CD's reach ends exactly where schema conformance ends"

**[new][논문 arXiv 2609.32917, 2026-09-26, AIxSET 2026] Planner-as-Router.** 플래너가 하위 과제로 나누면서 각 하위 과제에 모델 등급(small/mid/frontier)을 함께 붙인다. — [arXiv](https://arxiv.org/abs/2609.32917)
- 모두 frontier로 보낼 때보다 비용 −44%, 정확도 −2.9점이었다.
- 차이 다수는 ±6점 신뢰구간 안이다.
- 과제는 SQL·MongoDB 기업 과제이고 게임이 아니다.

**[new][검색 요약] 소형 모델 툴 호출 미세조정.**
- 미세조정한 SLM이 ToolBench 통과율 77.55%로 ChatGPT-CoT(26.00%)를 넘었다. — [arXiv 2512.15943](https://arxiv.org/html/2512.15943v2)
- SFT 후 RL로 학습한 SLM이 다중 에이전트 라우터(에이전트 선택 + 구조화 매개변수 생성)를 맡았다. — [arXiv 2608.00030](https://arxiv.org/html/2608.00030v1)

**[new] 큰 오픈 모델도 픽셀·협동에서는 0.** OmniGameArena에서 Qwen3.5-397B-A17B가 협동 2종에서 0.000이었다. — [HTML](https://arxiv.org/html/2606.09826v1)

### Inferences
- [추정] 플래너와 선택기의 역할 분담은 기준선보다 근거가 강해졌다.
  - 4B zero-shot은 랜덤보다 낮고, SFT를 해도 일반화는 GPT-5 mini에 뒤진다. 그러니 처음 보는 요청을 맡는 플래너는 계속 클라우드 모델이어야 한다.
  - 닫힌 선택지를 고르고 확신을 내는 역할(Jev/laya)은 소형 모델이 맞다.
- [추정] 로컬 4~8B 플래너를 검토한다면 조건이 있다. Valheim 로그(성공한 계획과 검증기 통과 기록)로 SFT를 한 뒤, "자주 보는 요청군"에만 쓴다. Agentick SFT-250k 수준이 되려면 수십만 건 규모의 궤적이 필요했다.
- [추정] 지난번 `hp_below` 10.0 사고는 제약 디코딩 논문의 분류로 보면 두 성격이 섞여 있다.
  - 타입·범위 실패: 범위를 강제하는 스키마로 막을 수 있다.
  - 의미 실패: 비율인지 절대값인지를 정하는 일이다.
  - 그래서 수치 필드 자체를 없애고 열거형(`low`/`critical` 등)으로 고르게 한 뒤 코드가 숫자로 바꾸는 쪽이 의미 실패까지 막는다.

### Gaps
- Agentick의 SFT 소형 모델이 처음 보는 과제 변형에서 어떻게 되는지는 범주 점수(Generalization 0.350) 말고는 확인하지 못했다.
- 제약 디코딩 논문의 모델별 의미 정확도와 지연 오버헤드는 초록에 없다.
  - 검색 요약에 "GSM8K에서 CD 지연이 3.6~8.2배"라는 문장이 있었다. 어느 논문인지 특정하지 못해 근거로 쓰지 않는다.
- Gemini 구조화 출력이 JSON Schema의 `minimum`/`maximum`을 디코딩 단계에서 강제하는지는 이번에 확인하지 않았다(다른 조사 범위).

## 5. 플래너 호출 수와 지연을 줄이는 기법: 무엇이 근거가 있나

### Takeaway
근거가 있는 기법은 다섯이다.
1. 계획 전이 캐시와 비동기 재검증(AgenticCache: 지연 −65%, 토큰 −50%, 성공률 +22%)
2. 재계획 여부 결정과 맥락 가지치기(BRACE: 호출당 토큰 −71~76%)
3. 문 기반 호출(System Switch)
4. 실행 중 비동기 계획(AAMAS'26, RRARA, AgileThinker)
5. 구조 강제(제약 디코딩)

이 가운데 "도착한 계획을 그 시점의 관측으로 다시 검증"하는 단계는 OmniGameArena LCRT가 보여 준 급락 때문에 필수다.

### Cited Findings

| 기법 | 근거 | 수치 | 표기 |
|---|---|---|---|
| 계획 전이 캐시 + 백그라운드 LLM 검증 | [AgenticCache, MLSys 2026](https://arxiv.org/abs/2604.24039) | 성공 +22%, 지연 −65%, 토큰 −50% (12개 설정 평균) | [new, 놓침] |
| 트리거마다 재계획 여부·모드·토큰 예산 결정 | [BRACE, ICML 2026](https://arxiv.org/pdf/2608.01428) | 토큰/호출 −71~76%, SLO 위반 85.5% → 4.7% | [new, 놓침, 검색 요약] |
| 문(Unsure/Stuck/Blocked/Loop/Novelty) | [System Switch, 2026-10-07](https://arxiv.org/abs/2610.09683) | 확신 문의 이득은 AUROC에 비례(순위상관 0.87) | [unchanged] |
| 실행 중 다음 계획 계산, 단일 슬롯 버퍼, DAG 분해 | [AAMAS 2026](https://ifaamas.org/Proceedings/aamas2026/pdfs/EXAJ9853.pdf) | 상위 과제당 LLM 1회 | [unchanged, 원문 재확인 안 함] |
| 규칙이 즉시 행동 + 비동기 LLM 반성, 지연을 프레임으로 환산 | [RRARA](https://arxiv.org/html/2506.07223) | 검색 요약에 수치 없음 | [new, 놓침, 검색 요약] |
| 비동기 I/O + 투기적 툴 호출 | [Speculative Interaction Agents](https://arxiv.org/pdf/2605.13360) | 검색 요약에 수치 없음 | [new, 놓침, 검색 요약] |
| 플래너가 하위 과제별 모델 등급 지정 | [Planner-as-Router, 2026-09-26](https://arxiv.org/abs/2609.32917) | 비용 −44%, 정확도 −2.9점 | [new] |
| 제약 디코딩(구조 100%) | [arXiv 2609.23742, 2026-09-20](https://arxiv.org/abs/2609.23742) | 스키마 유효 78.6~92.9% → 100%, 의미 오류는 그대로 | [new] |
| 고정 프롬프트 앞부분으로 KV 캐시 재사용 | [PUBG Ally](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/) | 수치 없음 | [unchanged] |
| 스킬 승격 전 보류 변형 검증 | [OmniGameArena IDC](https://arxiv.org/html/2606.09826v1) | Opus 4.7 원래 과제 +201%, 변형 셋 모두 음수 | [new, 놓침] |

**계획이 낡는 문제의 정량 근거**
- [new] OmniGameArena LCRT에서 지연을 게임 시간에 반영하자 SharedFloor GPT-5.5가 0.368에서 0.048로 떨어졌다. — [HTML](https://arxiv.org/html/2606.09826v1)
- [검색 요약] AgenticCache 논문은 병렬 계획-행동의 약점을 "환경이 바뀌면 계획이 무효가 되어 재계획 오버헤드가 생긴다"로 정리했다. — [arXiv 2604.24039](https://arxiv.org/html/2604.24039v1)

**참고만 할 것(제목만 확인)**
- [검색 요약] "Rethinking Self-Evolution: A Constrained Exploration-Exploitation Process for Mitigating Skill Overfitting"는 스킬 과적합을 직접 다루는 2026-07 논문으로 보인다. 내용은 확인하지 못했다. — [arXiv 2607.26643](https://arxiv.org/pdf/2607.26643)
- [검색 요약] 진화하는 스킬 라이브러리의 생애주기를 정리한 2026-07 서베이가 있다. — [arXiv 2607.10113](https://arxiv.org/pdf/2607.10113)

### Inferences
- [추정] Thorkell에 바로 대응되는 순서(근거는 위 표)
  1. 아는 명령은 검증된 스킬로 바로 처리한다(현행).
  2. 그다음은 (상황 요약, 직전 계획) 키의 계획 전이 캐시를 본다(AgenticCache).
  3. 캐시에 없으면 문이 열렸을 때만 플래너를 부른다(System Switch, BRACE).
  4. 플래너 결과는 단일 슬롯에 넣고, 도착한 시점의 관측으로 다시 검증한다. 전제가 바뀌었으면 버린다(OmniGameArena LCRT).
  5. 하루 한도의 남은 호출은 백그라운드 캐시 검증과 회고에 쓴다.
- [추정] 플래너 출력의 수치는 "구조는 제약 디코딩·스키마, 의미는 열거형과 코드 매핑"으로 두 겹으로 막는다. 기준선의 권고와 같고, 2609.23742가 그 이유(제약 디코딩은 의미를 못 고침)를 보강한다.
- [추정] 로컬 소형 모델을 플래너 앞의 라우터로 두는 안(Planner-as-Router의 역방향)이 있다. "캐시나 스킬로 될지, 플래너가 필요할지"를 닫힌 선택으로 고르게 하는 것이다. 이것은 Jev/laya의 기존 역할 범위 안에 들어간다.

### Gaps
- 게임 에이전트에서 계획 캐시 적중률을 보고한 공개 수치는 여전히 없다. AgenticCache는 평균 효과만 초록에 있다.
- BRACE와 RRARA의 원문 수치·설정은 검색 요약으로만 확인했다.

## 6. 최근(2026-09-01~10-17) 공개된 게임용 에이전트 프레임워크·오픈소스

### Takeaway
이 기간에 "Valheim이나 3D 서바이벌용 새 에이전트 프레임워크"는 찾지 못했다. 새로 나온 것은 벤치마크와 하네스 코드다: SpeedrunBench, Agentick 리더보드 갱신, System Switch 코드. 기존 프레임워크 중에서는 mindcraft-ce의 `agent-system` 브랜치(구조화 툴 호출, RAG)만 계속 움직이고 있다.

### Cited Findings
- [new] SpeedrunBench 코드(2026-10-06, Patronus AI 등). 상용 게임 에셋은 공개하지 않는다고 밝혔다. — [GitHub patronus-ai/speedrun_bench](https://github.com/patronus-ai/speedrun_bench)
- [new] Agentick. 2026-09-15~16에 frontier 항목이 추가됐다. — [GitHub roger-creus/agentick](https://github.com/roger-creus/agentick), [리더보드](https://roger-creus.github.io/agentick/board/)
  - Gymnasium 호환이다.
  - Coding API, oracle 정책, SFT 데이터셋, 조합형 하네스를 제공한다.
- [unchanged] System Switch 코드·프롬프트·데이터·로그 공개(arXiv comments에 GitHub `system-switch` 브랜치로 명시). — [arXiv 2610.09683](https://arxiv.org/abs/2610.09683)
- [changed] mindcraft-ce의 `agent-system` 브랜치(2026-10-10 push): function calling, LanceDB RAG, XML 템플릿 툴 프롬프트, Docker, MineCollab 다중 에이전트, OpenRouter. "곧 나올 것"으로 모델·툴 제공자 저장소를 예고했다. — [GitHub](https://github.com/mindcraft-ce/mindcraft-ce)
- [unchanged] Mindcraft 본가: 2026-03-20 v0.1.4 이후 새 릴리스가 없다. — [GitHub](https://github.com/mindcraft-bots/mindcraft)
- [new, 놓침] MineNPC-Task는 과제 모음, 검증기, 로그, 하네스를 공개한다(2026-01). — [arXiv 2601.05215](https://arxiv.org/abs/2601.05215)
- [new, 놓침] AgenticCache의 코드는 GitHub에 있다고 초록에 적혀 있다. URL은 확인하지 못했다. — [arXiv 2604.24039](https://arxiv.org/abs/2604.24039)
- [unchanged] 기존 벤치마크 저장소는 비활성이다. BALROG 2026-04-09, Orak 2025-06-17, VideoGameBench 2025-05-30, GamingAgent 2025-11-16(마지막 push). — 각 GitHub 메타데이터(`gh api`, 확인 2026-10-17)

### Inferences
- [추정] 바로 쓸 만한 것은 둘이다. 새 프레임워크를 도입할 근거는 없다.
  - Agentick의 하네스 프리셋(Markovian/Reasoner) 비교 방식: Thorkell 시뮬레이터에서 빠른 결정 모델을 평가하는 틀로 쓴다.
  - MineNPC-Task의 과제·검증기 형식: 회귀 세트에 참고한다.
- [추정] mindcraft-ce가 텍스트 명령에서 구조화 툴 호출로 옮기는 흐름은 Thorkell의 타입 결정·검증기 방향과 같다.

### Gaps
- NeurIPS 2026 E&D 채택 목록에서 게임 에이전트 논문을 체계적으로 찾지 못했다. 확인한 것은 Agentick 하나다.
- ICLR 2027 OpenReview 투고작은 검색에 걸리지 않았다.
- arXiv API가 요청 제한(503·429)에 걸려 2026-10-10~17 목록을 직접 훑지 못했다. 이 기간에 놓친 논문이 있을 수 있다.
