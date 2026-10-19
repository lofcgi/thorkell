# 게임 에이전트 학습 방법 — Thorkell에 쓸 수 있는 것 (기준일 2026-10-17, 기준선 2026-10-10 갱신)

기준선: `docs/research/research_notes/게임 플레이 AI 기술 동향 2026/learning_methods.md`(2026-10-10). 조사일 2026-10-17.
상태 태그: **[unchanged]** 기준선과 같음 / **[changed]** 버전·수치·지위가 바뀜 / **[new]** 기준선에 없던 것(2026-09-01 이후 우선, 그 전 것은 "기준선 누락"이라고 적음) / **[corrected]** 기준선(또는 레포 feasibility 문서)의 서술이 틀렸거나 오해 소지가 있었음.
출처 등급: **[논문]** arXiv·학회 원문(초록 또는 본문을 직접 열어 봄) / **[공식]** 연구소·벤더 문서 / **[벤더 주장]** 벤더 자체 측정 / **[커뮤니티]** 개인 블로그·GitHub / **[검색 요약만]** 검색 결과 요약만 봤고 원문을 열지 않음 / **[추정]** 이 노트 작성자의 추론·계산.
기준선 논문의 버전 재확인은 2026-10-17 arXiv API(`export.arxiv.org/api/query?id_list=…`)로 했다. 결과에 "API 2026-10-17"이라고 적는다.
Thorkell 맥락: 구조화 지각(JSON) + 파라미터 행동, 월드 변화로 진척 검증. 빠른 타입 결정은 Jev(`jev-1.13.0` 고정, `brain/thorkell/config.py:54`) → laya 증류. 승격 게이트는 Jev 일치율 ≥95%, ECE ≤0.05, p95 ≤50 ms. 플래너는 gemini-3.8-flash(무료 하루 20회). 실게임은 Rosetta, 클라이언트 둘, 한 번에 하나라서 느리다. 같은 규약의 2D 시뮬레이터가 있다. M4 Pro 24GB.

## 1. 자기 경험에서 배우는 에이전트(시험 시간 학습·자기진화): 2026년에 새로 나온 것과 게임 근거

### Takeaway
2026-10-06~10-14에 게임이나 게임형 환경 근거를 가진 결과가 연달아 나왔다. 셋 다 기준선의 "회고 → 규칙" 가정을 조정한다.
- Learn2Play Bench: 낯선 규칙의 게임에서는 **원본 기록을 보존하는 메모리가 요약 규칙(Reflexion·ReasoningBank·EvoTest)보다 낫다**.
- Randomized Block Curation: **에이전트가 스스로 고른 교훈은 불안정하다**. 교훈 블록을 무작위로 켜고 끈 A/B 결과로 고르면 평균 +12.8점이다.
- Memento 3: 규칙서를 **실행 가능한 코드 world model로 컴파일하고 리플레이로 검증**하면 ARC-AGI-3 공개 25게임을 모두 깬다.

3D 실시간 게임에서 정량 근거는 여전히 없다.

### Cited Findings
- **[new] Learn2Play Bench** (Li, …, Hooi, arXiv 2610.08215, 2026-10-06) [논문]
  - 설정: 새로 설계한 텍스트 게임 20개(고정 10, 재셔플 10, 도전 5 + 일반 15)다. 게임당 3 trial이고, 일반 게임은 5 에피소드, 도전 게임은 10 에피소드를 돈다. 가중치 갱신 없이 반복 시도에서 배우는지를 잰다.
  - 백본 11개를 비교했다. 자기진화 방법은 Kimi K3, Opus 5, GPT-5 Mini로 비교했다.
  - Kimi K3 기준으로 **Memory(전체 기록 그대로)**가 네 지표에서 모두 최고였다: Max 63.3, Mean 48.0, LG +16.9, LS +4.69.
    - Reflexion: Max 61.6, LS +3.35
    - ReasoningBank: Max 59.9, LS +2.59
    - EvoTest: Max 62.4, LS +1.01
  - 백본 3개 평균 LS: Memory +3.04, Reflexion +2.42, EvoTest +1.71.
  - 저자 해석: "preserving evidence can matter more than compressing it." 요약은 불완전한 증거를 지나치게 넓은 규칙으로 만든다.
  - 재셔플 인스턴스로 옮기면 학습 기울기가 떨어진다: Opus 5 4.10→3.51, Sonnet 5 4.90→2.23, Gemini 3.7 Flash 4.49→2.34. 예외는 Qwen 3.8 Max(3.16→3.57)다.
  - 사람과 비교:
    - 사람 Top-1 Max는 84.3, 참가자 평균은 43.6이다(게임당 21–30명).
    - 점수가 떨어진 다음 에피소드에서 개인 최고를 새로 낸 비율은 사람 33%, 에이전트 22%다.
    - 같은 행동을 연속으로 되풀이하는 정도(유사도)는 사람 0.54, 에이전트 0.66이다. 에이전트가 더 반복한다.
  - 하네스만 바꿔도 성능이 오른다. Opus 5는 OpenCode 74.5 → Claude Code 81.8이다.
  - 출처: [arXiv abs](https://arxiv.org/abs/2610.08215v1), [HTML](https://arxiv.org/html/2610.08215)
- **[new] Memento 3** (Zhao, …, Bou-Ammar, Wang, arXiv 2610.11794, 2026-10-08) [논문]
  - 동결된 LLM이 자연어 규칙서(수정 가능한 가설)를 유지한다. 루프는 관찰 → 회고 → 규칙 수정 → 코드로 컴파일 → 검증이다.
  - 새 코드는 두 조건을 모두 통과해야 채택한다: LLM이 규칙서에 충실하다고 판정하고, 관찰된 전이를 칸 단위로 정확히 재현해야 한다(cell-exact replay).
  - ARC-AGI-3 공개 25게임의 모든 레벨을 깼다. RHAE는 100.0이고, 사람 행동 수의 44%만 썼다.
  - Pong에서는 학습된 제어기가 LLM 호출 없이 3판 모두 21:0으로 이겼다.
  - LLM 이름과 비용은 초록에 없다.
  - 출처: [arXiv](https://arxiv.org/abs/2610.11794v1)
- **[new] Reliable Memory from Unstable Growth / Randomized Block Curation(RBC)** (Pham, …, Luu, arXiv 2610.18427, 2026-10-13) [논문]
  - 에이전트가 스스로 쓴 playbook은 같은 절차에서도 결과가 크게 갈린다. 도움이 되기도 하고, playbook이 없을 때보다 **최대 69.6점 낮아지기도** 한다.
  - RBC는 교훈을 블록으로 묶고 연습 과제에서 무작위로 넣거나 뺀다. 성공률 차이로 각 블록의 효과를 추정해 유익한 블록만 남긴다.
  - 평균 성공률: RBC 66.9, 전체 playbook 55.5, playbook 없음 54.1, 에이전트 자기 판단 53.8.
  - 범위는 메모리 시스템 2개(ACE, Dynamic Cheatsheet), 모델 3개, 벤치 3개다.
  - 출처: [arXiv](https://arxiv.org/abs/2610.18427)
- **[new] EvoWeave** (Zhu et al., NJIT·CUHK-SZ, arXiv 2610.19381, 2026-10-14) [논문]
  - 경험을 "추상 상태 사이의 operation 간선"으로 저장한다. 간선에는 입출력 계약과 출처가 붙는다.
  - 백본 3개 평균(ALFWorld 점수): EvoWeave 70.96, ExpeL 69.70, AWM 66.96, ReasoningBank 66.76, A-MEM 64.33, Mem0 62.14.
  - 저자는 유의성을 주장하지 않는다. 일부 차이는 표준편차보다 작다고 스스로 밝혔다.
  - 출처: [arXiv HTML](https://arxiv.org/html/2610.19381v1)
- **[new, 기준선 누락 2026-07] AutoMem** (Wu, …, Yeung-Levy, arXiv 2607.01224, 2026-07-01) [논문]
  - 강한 LLM이 전체 궤적을 보고 메모리 구조를 반복 수정한다. 좋은 메모리 결정은 모델 학습 신호로 쓴다.
  - Crafter·MiniHack·NetHack에서 메모리 최적화만으로 기본 에이전트 성능이 약 2–4배 올랐다. 32B 오픈 모델이 Claude Opus 4.5, Gemini 3.1 Pro Thinking과 경쟁 수준이 됐다.
  - 게임별 수치와 컴퓨트는 초록에 없다.
  - 출처: [arXiv](https://arxiv.org/abs/2607.01224)
- **[new, 기준선 누락 2026-05] PEAM** (Guo et al., arXiv 2605.27762, v2 2026-06-01) [논문]
  - Minecraft에서 느린 LLM과 빠른 파라미터 모듈(멀티모달 MoE-LoRA, 범주별 분리 어댑터)을 짝짓는다.
  - 실패-교정 궤적 쌍을 BC + 대조 학습 목표로 학습한다.
  - "어떤 경험을 내재화할지"를 점수로 고르고, "언제 할지"를 자기 촉발 통합으로 정한다.
  - 장기 과제 성능이 오르고 망각이 줄었다고 주장한다. 초록에 수치는 없다.
  - 출처: [arXiv](https://arxiv.org/abs/2605.27762)
- **[new, 기준선 누락 2026-06] MemoPilot / From Player to Master** (Cai, …, Tang, Sun, arXiv 2606.08656, 2026-06-07) [논문]
  - 동결 LLM 옆의 메모리 갱신기를 multi-turn GRPO로 학습한다. 턴별 보상과 턴 단위 advantage를 쓴다.
  - 가위바위보에서 Elo 1590, Limit Texas Hold'em에서 Elo 1762로 1위다. 모델 크기는 초록에 없다.
  - 출처: [arXiv](https://arxiv.org/abs/2606.08656)
- **[new, 기준선 누락 2025-10] EvoTest / J-TTL** [검색 요약만]
  - Jericho 인터랙티브 픽션 게임을 연속 에피소드로 플레이하는 test-time learning 벤치다.
  - 프롬프트 진화·메모리·RL 기준선보다 낫다고 보고했다. 단, 위 Learn2Play에서는 EvoTest가 단순 Memory보다 낮았다.
  - 출처: [arXiv 2510.13220](https://arxiv.org/html/2510.13220)
- **[new, 검색 요약만] 기타 2026 게임·체화 메모리 연구**
  - HiMeco(2610.20312): 실패 후 회고로 라운드 사이에 메모리를 갱신하는 체화 공간지능 에이전트, 파라미터 동결 — [arXiv](https://arxiv.org/abs/2610.20312v1)
  - MemoWM(2610.10778): world model로 경험 저장량을 MIRIX 대비 53.9% 줄임 — [arXiv](https://arxiv.org/abs/2610.10778)
  - Echo(2604.05533): Minecraft 경험 전이와 유추 추론 — [arXiv](https://arxiv.org/pdf/2604.05533)
  - XENON(2505.24157): Minecraft에서 성공·실패로 계획 지식을 고침. LLM 자기 교정에 의존하지 않음 — [arXiv](https://arxiv.org/html/2505.24157v2)
  - AgentOdyssey(2606.24893): test-time 지속학습용 장기 텍스트 게임 생성 — [arXiv](https://arxiv.org/pdf/2606.24893)
- **[changed: 기준선 공백 채움] ReasoningBank** — arXiv v2 2026-03-16, ICLR 2026 채택(API 2026-10-17). Google 블로그(2026-04-21), Gemini-2.5-Flash + ReAct 기준:
  - 메모리 없음 대비 WebArena 성공률 +8.3%, SWE-Bench-Verified +4.6%, 과제당 약 3스텝 절약.
  - MaTTS(k=5)는 ReasoningBank 단독보다 WebArena +3%, 0.4스텝 적음.
  - 단, 위 Learn2Play(낯선 규칙 게임)에서는 단순 Memory보다 낮았다.
  - 출처: [블로그](https://research.google/blog/reasoningbank-enabling-agents-to-learn-from-experience/), [arXiv](https://arxiv.org/abs/2509.25140)
- **[new: 기준선 공백 채움] Agent Workflow Memory** (arXiv 2409.07429, v1 2024-09-11, 학회 표기 없음) [논문]
  - 기준선 대비 상대 성공률 개선: Mind2Web +24.6%, WebArena +51.1%.
  - 온라인 AWM은 학습-평가 차이가 커질수록 기준선을 8.9–14.0점(절대) 앞선다.
  - 출처: [arXiv](https://arxiv.org/abs/2409.07429)
- **[new: 기준선 공백 채움, 배경] Reflexion** (arXiv 2303.11366, v4 2023-10-10): 초록 수치는 HumanEval pass@1 91%(GPT-4 80%)뿐이다. ALFWorld 수치는 초록에 없다 — [arXiv](https://arxiv.org/abs/2303.11366)
- **[unchanged]** 아래 항목은 이번에 원문을 다시 열지 않았다. 2026-10-17 검색에서 반박하거나 대체하는 자료는 나오지 않았다.
  - Voyager(15.3배), ExpeL(ALFWorld 범주별 수치), AutoManual(97.4%), BALROG(GPT-4o 32%), Gemini Plays Pokémon, AgentDistill. 수치와 출처는 기준선 5절에 있다.
  - EvoWeave 표(2026-10-14)에서 ExpeL이 ALFWorld 최강 기준선(69.70)으로 다시 확인됐다.
- **[unchanged]** Agent Memory Distillation(AMD): v1 2026-08-07, 상태 "Under review"(API 2026-10-17) — [arXiv](https://arxiv.org/abs/2608.07169)

### Inferences
- [추정] Thorkell 회고 루프에 대한 수정 제안. 근거는 Learn2Play, RBC, Memento 3다.
  1. 회고가 만든 규칙만 남기지 않는다. 그 규칙의 근거 에피소드(이벤트·결과 evidence)를 SQLite에 원본 그대로 보존하고, 규칙은 근거 링크가 달린 "가설"로 둔다.
  2. 규칙 채택을 LLM 자기 판단에 맡기지 않는다. 규칙 블록 on/off A/B로 정한다. 실게임은 느리므로 A/B는 2D 시뮬 회귀 시드에서 먼저 하고, 실게임은 확인용으로만 쓴다.
  3. 검증할 수 있는 규칙(전제조건, 약점·내성)은 코드 술어나 검증기로 컴파일한다. 기준선의 "규칙을 코드 검증기로 옮긴다"는 추정을 Memento 3가 강화한다.
- [추정] 약점·내성 학습은 지금 방식이 맞다. `damage_dealt.on_target` 증거를 세서 갱신하는 방식이 Memento 3의 "리플레이 재현으로만 채택"과 같은 원리다. 추가로 증거 수가 적은 규칙은 "잠정"으로 표시하고, 반례가 나오면 바로 내린다.
- [추정] 비용. 이 계열은 가중치 학습이 없어서 Mac 부담이 0이다. 비용은 LLM 호출이다.
  - gemini flash가 하루 20회이므로 회고는 목표당 1회 이하로 한다.
  - A/B 평가는 LLM 호출 없이 실행 결과만 있으면 되므로 쿼터를 쓰지 않는다.
  - 원본 기록 보존은 프롬프트 토큰을 늘린다. 검색으로 관련 에피소드만 넣어야 한다(Learn2Play는 하네스 차이가 비용에도 크게 영향을 준다고 보고했다).
- [추정] AutoMem, PEAM, MemoPilot처럼 메모리 관리자나 스킬을 가중치로 내재화하는 단계는 32B·GRPO·MoE-LoRA 규모다. 지금 Thorkell에는 과하다. "반복 성공 계획 → 스킬 승격"은 Voyager식 코드 스킬과 검증된 네이티브 경로로 충분하다. 가중치로 내재화할 대상은 laya 결정 하나로 한정한다.
- [추정] 호기심 실험은 Learn2Play의 사람-에이전트 차이(에이전트가 더 반복하고, 실패 뒤에 개선하는 비율이 낮음)를 겨냥할 수 있다. 실험 선택 기준을 "같은 행동 반복 페널티 + 가설 판별력"으로 둔다.

### Gaps
- Learn2Play의 에피소드당 비용 표는 페이지에서 잘려 확인하지 못했다.
- Memento 3의 LLM 종류·비용, PEAM의 수치·모델 크기, AutoMem의 게임별 수치는 초록에 없었다.
- 실시간 3D 생존 게임에서 메모리·회고 방법의 효과를 정량화한 연구는 이번에도 찾지 못했다. 근거는 모두 텍스트 게임, ARC-AGI-3, Minecraft(API), 웹·코드 환경이다.
- 2609.16679 "AI for Games in the Foundation Model Era" 서베이는 검색 결과에 참고문헌만 나와서 내용을 확인하지 못했다.

## 2. 클라우드 결정 모델 → 작은 로컬 분류기 증류와 캘리브레이션 실무

### Takeaway
2026-09~10에 공개된 실무 사례 두 개(Jevstiller, laya)의 레시피가 같은 방향으로 모인다.
- 교사의 **전체 확률분포를 soft target으로** 쓴다.
- held-out 데이터로 **(질문 타입 × 선택지 수)별 temperature**를 맞춘다.
- "로컬에서 답할지"는 **유한표본 보수 경계(Clopper–Pearson) + OOD 거리 게이트 + 항상 교사로 보내는 감사 샘플**로 정한다.

"일치율"은 정확도가 아니다. 교사(Jev)도 월드 변화 결과로 따로 채점해야 한다. 그리고 laya가 Jev보다 보정이 좋다는 서술은 조건부다([corrected]).

### Cited Findings
- **[changed] Jevstiller** (Apache-2.0, alpha, v0.4.0 2026-09-27, 마지막 push 2026-10-03) [커뮤니티]
  - 학생 모델: 동결 문장 인코더(bge-small/base/large)에 numpy 로지스틱 회귀 한 층을 얹는다. Jev의 **전체 확률분포**로 학습하고, 검증 조각으로 조기 종료한다. 메모리는 인코더 포함 약 300 MB다.
  - 라우팅:
    - 임베딩 kNN 거리로 처음 보는 입력은 무조건 Jev로 보낸다.
    - 신뢰도 임계값은 held-out IID 보정 세트에서 Clopper–Pearson 경계로 "가장 엄격한 것부터" 시험해 고른다.
    - 이 임계값은 "로컬 답 중 Jev와 다른 비율"을 95% 신뢰로 예산 안에 묶는다. `target_agreement=0.98`이면 예산은 2%다.
    - 무작위 2%는 항상 Jev로 보내 감사한다. 계약이 깨지면 전부 Jev로 돌린다.
  - 학습은 "수 초"이고, 새 후보는 라이브 트래픽에 그림자로 붙여 본 뒤 승격한다. Banking77에서는 약 5,000건부터 대부분을 맡았고, 프록시 데모에서는 5,000건 중 약 4,000건 뒤에 넘겨받았다.
  - 지연: 로컬 CPU p50 약 15–16 ms, p99 약 50 ms. Jev는 p50 약 300 ms다.
  - 리플레이 결과(bge-small, CPU, 목표 98%, held-out 2,000행):

    | 과제 | 로컬 처리 | Jev 일치 |
    |---|---|---|
    | Banking77 | 71.9% | 99.50% |
    | CLINC150 | 69.0% | 99.65% |
    | AG News | 80.2% | 99.40% |
    | TweetEval 감성 | 22.2% | 98.70% |

  - 무작위 분할 100번 중 예산 초과는 1번이었다. 점추정 규칙은 과제당 20번 중 6–12번 초과했다.
  - 스스로 밝힌 한계: "Jev가 틀리면 학생도 똑같이 틀린다." 클래스 목록이 바뀌는 과제, 수천 건을 모으기 어려운 과제에는 맞지 않는다.
  - 기준선(feasibility)의 "99.45%"는 2026-09-25 라이브 런 수치이고, 최신 표는 99.50%다.
  - 출처: [GitHub](https://github.com/tomerglick57/Jevstiller), [PyPI](https://pypi.org/project/jevstiller/)
- **[new] Jev 1.14.0 예고** (TypeSafe 블로그, 바이라인 2026-10-14) [공식]
  - `jev-latest`가 "일주일 뒤" `jev-1.14.0`으로 바뀐다. 변화는 "작고 미묘한 개선"이고, 다국어 개선이 가장 크다고 했다. 수치는 공개하지 않았다.
  - `jev-1.13.0`은 "당분간" 유지된다. 폐기 60일 전에 공지할 예정이다.
  - 사용자 질의로 학습하지 않는다고 했다. Jev 출력으로 다른 모델을 학습시키는 것(증류)의 허용 여부는 언급하지 않았다.
  - 출처: [TypeSafe 블로그](https://typesafe.ai/blog/jev-1-14)
- **[corrected] laya와 Jev의 ECE 비교** [벤더 주장, laya PyPI 0.4.8, 2026-10-17 확인]
  - 기준선과 feasibility는 "laya 측은 Jev의 ECE를 0.246이라고 주장"만 적었다. PyPI 본문에는 두 수치가 같이 있다.
    - 헤드라인 비교: laya 0.081(temperature 보정 후) 대 Jev 0.246.
    - typed-decisions 행: `laya-typed-decisions` ECE 0.213 대 Jev 1.13.0 **0.144**. 이 행에서는 Jev가 더 잘 보정됐고, 본문은 temperature 맞춤으로 이 차이를 메운다고 설명한다.
  - 배포 상태 그대로는 과신한다. (타입, 선택지 수)마다 temperature를 맞추면 평균 ECE가 바뀐다.
    - `laya`: 0.466 → 0.081
    - `laya-multilingual`: 0.314 → 0.106
  - `laya-multilingual`은 맞춘 temperature 없이 배포된다.
  - 노트북의 보정 샘플은 학습 항목에서 뽑는다. 그래서 개선을 주장하기 전에 별도 held-out으로 평가하라고 PyPI가 스스로 경고한다.
  - 출처: [PyPI laya](https://pypi.org/project/laya/)
- **[new] LLM 점수 + 말로 한 확신도 → soft target → BERT** (arXiv 2605.11954 v2, 사회과학 측정) [검색 요약만]
  - LLM이 점수와 말로 된 확신도를 함께 내게 하고, 이를 점수 클래스 위의 soft target으로 바꿔 BERT를 학습한다.
  - 데이터셋 평균 ECE 0.408 → 0.228, Brier 0.376 → 0.248. FOMC에서는 Brier가 오히려 나빠졌다.
  - 출처: [arXiv](https://arxiv.org/html/2605.11954v2)
- **[new, 검색 요약만]** From Clicks to Intent(2606.26277): LLM 의도 라벨을 고정 임베딩 위의 경량 분류기로 증류했다. 라벨 품질 하락은 7%였다 — [arXiv](https://arxiv.org/html/2606.26277)
- **[unchanged]** Agent Distillation: v2 2025-11-05, NeurIPS 2025 Spotlight(API 2026-10-17). 현재 제목은 "Distilling LLM Agent into Small Models with Retrieval and Code Tools"다 — [arXiv](https://arxiv.org/abs/2505.17612)
- **[changed] SOD** (arXiv 2605.07725): v2 2026-08-03, v3 2026-08-18.
  - v3 초록은 "2위 기준선 대비 최대 20.86%", 0.6B 학생 AIME 2025 26.13%만 적는다.
  - 기준선이 v1에서 인용한 "OPD 대비 0.6B 24.2%, 1.7B 18.5%"는 v3 초록에서 확인되지 않는다. 인용하려면 v3 본문 표로 다시 확인해야 한다.
  - 출처: [arXiv v3](https://arxiv.org/abs/2605.07725v3)
- **[unchanged]** Latent Bridge: v1만 있음(2026-06-23, API 2026-10-17) — [arXiv](https://arxiv.org/abs/2606.24470)
- **[unchanged]** Kapoor et al.(약 1,000개 채점 예시로 LoRA 학습해야 보정이 생김): v3, NeurIPS 2024 camera ready(API 2026-10-17) — [arXiv](https://arxiv.org/abs/2406.08391)
- **[unchanged, 재확인 안 함]** Sub-goal Distillation, DeDer, Distilling step-by-step, Hinton KD, 2505.01997, HypeLoRA. 기준선 1·6절 참조.
- **[배경, 이번 세션 원문 재확인 안 함]**
  - temperature scaling은 held-out NLL을 최소화하는 단일 T다(Guo et al. 2017) — [arXiv 1706.04599](https://arxiv.org/abs/1706.04599)
  - 구간(binned) ECE 추정량은 표본이 적으면 편향되므로 편향 보정 추정량을 제안한 연구가 있다(Kumar et al. 2019) — [arXiv 1909.10155](https://arxiv.org/abs/1909.10155)
- **Jev 단가(기준선 노트 인용, 재확인 안 함)** [3자]: 입력 1M 토큰당 $0.042, 출력 무료, 분당 1,200건 — [letsdatascience](https://letsdatascience.com/news/typesafe-ai-launches-jev-decision-model-889a38c0)

### Inferences
- [추정, 계산] **승격 게이트 "Jev 일치율 ≥95%"의 표본 수.** 일치율 하한을 Clopper–Pearson 단측 95%로 0.95 이상 보이려면 held-out 결정이 질문 타입마다 다음만큼 필요하다(이 노트에서 이항분포로 직접 계산).

  | 관측 일치율 | 필요한 n |
  |---|---|
  | 99% | 약 100 |
  | 98% | 약 160 |
  | 97% | 약 340 |
  | 96% | 약 1,260 |

  점추정 95%로 승격하면 Jevstiller 실험처럼 예산 초과가 흔하다(20번 중 6–12번). 게이트는 하한으로 걸어야 한다.
- [추정, 시뮬레이션] **"ECE ≤0.05" 게이트의 잡음 바닥.** 완벽히 보정된 모델이라도 표본 오차만으로 15구간 ECE가 다음처럼 나온다(확신도 0.5–1.0 분포, 200회 반복 시뮬레이션).

  | n | ECE 평균 | ECE p95 |
  |---|---|---|
  | 200 | 0.046 | 0.071 |
  | 500 | 0.031 | 0.050 |
  | 1,000 | 0.021 | 0.032 |
  | 2,000 | 0.015 | 0.022 |

  따라서 ECE ≤0.05를 의미 있게 판정하려면 **평가 단위(질문 타입)마다 held-out 약 1,000건 이상**이 필요하다. 그보다 적으면 편향 보정 ECE나 신뢰구간(부트스트랩)을 같이 보고한다.
- [추정] **보정 단위.** laya처럼 (질문 타입, 선택지 수)마다 temperature를 맞추면, 단위가 늘어날수록 단위당 표본이 줄어든다. laya의 `min_bucket_n`이 그 하한이다. Thorkell 질문 타입(`threat_response`, `prep_check` 등)이 적을 때는 타입별 하나로 시작한다.
- [추정] **p95 ≤50 ms 게이트.**
  - laya 공개 지연: T4에서 1질문 32.8–39.5 ms, 10질문 배치 72.3–158.6 ms. 기준선 노트 기준 CPU 193–464 ms, M3 Max MLX 7.4–13.4 ms[커뮤니티].
  - 그래서 laya를 CPU에서 돌리면 게이트에 못 든다. MPS에서는 들어갈 가능성이 높지만, 게임과 GPU를 같이 쓸 때의 p95는 직접 재야 한다.
  - Jevstiller식(bge-small + 로지스틱 회귀)은 CPU p99 약 50 ms라서 GPU 경합 없이 게이트에 든다.
- [추정] **두 단계 권장.**
  1. 먼저 Jevstiller식 "동결 인코더 + 선형 헤드 + CP 임계값 + kNN OOD + 2% 감사"를 Thorkell 질문 타입별로 붙인다. 학습은 수 초이고 Mac 부담이 없다. 확신이 높은 결정만 로컬로 답하고 나머지는 Jev에 넘기는 선택적 증류다.
  2. 데이터가 타입당 수천 건 쌓이면 laya-multilingual 파인튜닝으로 넘어간다. 기준은 로컬 처리 비율과 정확도가 1단계보다 나은지다.
- [추정] **교사 고정과 표류 측정.**
  - config가 `jev-1.13.0`으로 고정되어 있어서, 2026-10-21 전후의 `jev-latest` 전환은 Thorkell 라벨에 영향을 주지 않는다.
  - 1.14로 바꿀 때는 기존 held-out 상태를 1.14로 다시 라벨링해 1.13 대비 일치율(교사 표류)을 먼저 잰다.
  - `decisions.jsonl` 각 행에 교사 모델 버전을 남긴다.
- [추정] **데이터를 싸게 모으는 법.** Jev 라벨링은 싸다. 상태 1건이 1K 토큰이면 5,000건은 5M 토큰, 약 $0.21이고, 분당 1,200건이면 몇 분이면 된다.
  - 그래서 2D 시뮬레이터 상태를 대량으로 Jev에 라벨링해 사전학습하고, 실게임 상태로 보정·평가하는 혼합이 현실적이다.
  - 단, 시뮬 상태 분포와 실게임 상태 분포가 다르므로 승격 게이트는 **실게임 held-out만으로** 판정한다.
- [추정] **soft target 가중.** Jev 확률을 soft target으로 쓰되, 월드 변화로 결과가 검증된 결정(성공·실패)으로 Jev의 정확도와 ECE를 먼저 재 본다. Jev가 틀린 것으로 확인된 결정은 결과 라벨로 덮어쓰거나 가중치를 낮춘다. Jevstiller가 밝힌 "교사 오류 복제"를 줄이는 방법이다.
- [추정] 정보 동등성(규칙 5): 학생 입력은 Jev에 보낸 직렬화 상태와 같아야 한다. prefab 이름이나 `$enemy_` 토큰이 학생 학습 데이터에도 들어가지 않게 같은 직렬화기(`world/serialize.py`)를 쓴다.

### Gaps
- 게임 행동 선택 도메인에서 증류 학생의 ECE와 일치율을 보고한 공개 연구는 여전히 없다. 근거는 텍스트 분류(Banking77 등)와 벤더 벤치다.
- Jev 출력으로 학생을 학습시키는 것에 대한 TypeSafe 약관 조항은 확인하지 못했다(블로그는 언급하지 않음).
- Jev 1.14.0의 정확도·ECE·지연 수치는 공개되지 않았다.
- 2605.11954, 2606.26277은 검색 요약만 봤다.

## 3. laya 학습·보정 도구 업데이트 (laya.train, laya.calibrate, evals 게이트)

### Takeaway
laya는 2026-09-18 0.1.0 이후 한 달 사이에 0.4.8(2026-10-15)까지 왔다. 2026-10-07~10-15 사이에 학습·보정·평가 게이트 쪽이 크게 바뀌었다.
- `laya-train --eval`, abstention 임계값 맞춤, 전후 비교 `train_report.json`이 생겼다.
- `calibrate`는 일주일에 버그 수정이 3번 들어갔다.
- Jev 신뢰도 공식(`jev_confidence`)이 공개됐다.
- 선택지가 많을 때 쓰는 토너먼트 방식이 생겼다.
- Apple M5 Pro MPS 벤치 문서가 추가됐다.

Jev 로그를 바로 증류하는 전용 명령은 여전히 없다. Apple Silicon 학습은 MLX가 아니라 PyTorch MPS 경로다.

### Cited Findings
- **[new] 릴리스 이력** (PyPI 2026-10-17 확인) [공식]
  - 0.1.0–0.1.6: 2026-09-18
  - 0.3.23: 2026-10-01
  - 0.3.29 / 0.4.0: 2026-10-07
  - 0.4.1: 10-08
  - 0.4.2: 10-10
  - 0.4.3: 10-11
  - 0.4.4–0.4.6: 10-12
  - 0.4.7: 10-14
  - 0.4.8: 10-15
  - 출처: [PyPI](https://pypi.org/project/laya/), [GitHub releases](https://github.com/NandhaKishorM/laya/releases)
- **[new] 학습** [공식]
  - v0.3.29: "feat(train): add --eval, abstention threshold fitting, and before/after train_report.json". 파인튜닝 예측이 클래스 사전분포로 무너지면 경고한다.
  - v0.4.1: 실행 전에 optimizer 업데이트 예산을 출력한다.
  - 출처: [GitHub releases](https://github.com/NandhaKishorM/laya/releases)
- **[new] 학습 레시피와 규모** [공식, PyPI 본문]
  - Kaggle 2×T4(DDP) 노트북이 데이터셋 구축 → **RLCD 학습** → temperature 맞춤 → 평가 → Hub 업로드를 한다. 약 30k 질문 4 epoch에 "roughly 4-5 hours"가 걸린다.
  - Apple Silicon용 `notebooks/laya_finetune_typed_decisions_mps.py`는 PyTorch MPS(CPU 폴백), 단일 프로세스다. 16 GB MacBook 예시는 `--micro-batch 1 --grad-accum 32`이고, MPS 학습 시간은 적혀 있지 않다.
  - 인코더와 결정 헤드에 gradient checkpointing을 켠다.
  - `option_layout="parallel"`은 선택지 순서를 섞어도 같은 답을 내는 비율이 100%(정확도 0.764)다. sequential은 91.7%다.
  - typed-decisions 벤치는 400 사례, 2,000 결정이다.
  - 출처: [PyPI](https://pypi.org/project/laya/)
- **[new] 보정·게이트** [공식]
  - 0.3.29: `--min-confidence` 게이트는 답을 덮어쓰지 않고 표시만 한다. 배포된 보정 수준은 "not calibrated"라고 문서에 명시했다.
  - 0.4.3: `jev_confidence`(서빙 `x_jev_confidence`의 공식)를 공개했다. abstention 컷은 선택지 수에 따라 달라지지 않는 값이 아니라고 문서에 적었다.
  - 0.4.4: 학생의 abstention을 그것을 쓴 게이트에서 읽도록 고쳤다.
  - 0.4.5: 표본 수가 들쭉날쭉한 구간에서 맞춤이 1.0으로 사라지는 문제를 고쳤다.
  - 0.4.7: checkpoint가 bool temperature를 싣고 오면 조용히 로드하지 않고 보고한다.
  - 0.4.8: `bins`·`min_bucket_n`을 양의 정수로 읽는다. 아무것도 판정하지 않는 게이트(예: `--max ece=inf`)와 유한하지 않은 게이트 파라미터를 거부한다. 음수 확률의 Jev 신뢰도를 거부한다.
  - 로드할 때 temperature를 [0.5, 5.0]으로 자른다.
  - 출처: [GitHub releases](https://github.com/NandhaKishorM/laya/releases), [PyPI](https://pypi.org/project/laya/)
- **[new] 서빙** [공식]
  - 0.4.3: 선택지가 많으면 `LAYA_TOURNAMENT_GROUP`으로 소거 토너먼트를 한다. 0.4.7부터 batch 엔드포인트에도 적용된다.
  - 0.4.1: `LAYA_EXTRA_MODELS`로 checkpoint를 추가 등록한다.
  - 0.4.8: `laya-go`(Go 클라이언트)를 추가했다.
  - 출처: [GitHub releases](https://github.com/NandhaKishorM/laya/releases)
- **[corrected] 체크포인트 컨텍스트**: `laya-multilingual`은 1,024(최대 8,192)다. feasibility 표는 "–"였다. 디바이스 순서는 CUDA → MPS → XPU → CPU이고, MLX는 언급이 없다 — [PyPI](https://pypi.org/project/laya/)
- **[new] Apple Silicon 벤치**: v0.4.7에 "docs(benchmarks): MPS fp16 autocast against fp32 on an Apple M5 Pro"가 추가됐다. 수치는 이번에 열어 보지 못했다 — [GitHub releases](https://github.com/NandhaKishorM/laya/releases)
- **[unchanged]** 영어 laya 421M, multilingual 322M, zero-shot 0.362/0.352, typed-decisions 0.766 대 Jev 0.727, Banking77 0.425 대 Jev 0.870 — [PyPI](https://pypi.org/project/laya/)

### Inferences
- [추정] **버전 고정.** laya는 하루 단위로 바뀌고, 보정 코드에 일주일 동안 버그 수정이 3번 있었다. 두뇌 venv와 분리한 laya venv에서 정확한 버전(예: `laya==0.4.8`)을 고정한다. 업그레이드할 때마다 같은 held-out으로 보정과 ECE를 다시 잰다.
- [추정] **선택지 순서 불변성.** Thorkell의 선택지 순서는 상황마다 바뀔 수 있으므로 `option_layout="parallel"`로 학습한다(순서를 섞었을 때 같은 답 100% 대 91.7%). 선택지가 20개를 넘는 질문은 토너먼트를 믿기 전에 따로 평가한다.
- [추정] **Mac 학습 시간.**
  - 벤더 수치(2×T4, 30k 질문 × 4 epoch ≈ 4–5시간)를 비례로 옮기면, Thorkell 결정 5k건 × 4 epoch는 2×T4에서 약 40–50분이다.
  - M4 Pro MPS가 2×T4와 같은 자릿수거나 2–3배 느리다고 보면 **약 1–2.5시간**이다(미측정 가정).
  - v0.4.1의 "optimizer 업데이트 예산 출력"과 M5 Pro 벤치 문서로 시작 전에 가늠한다.
  - 학습 중에는 게임을 끈다(24GB 공유).
- [추정] **승격 게이트 구현.** laya evals의 `--max ece`와 `--min-confidence` 게이트, 그리고 `train_report.json` 전후 비교를 Thorkell 승격 게이트(일치율 하한, ECE, p95)에 그대로 연결할 수 있다. 일치율 하한(Clopper–Pearson)은 laya 게이트에 없으므로 Thorkell 쪽에서 계산한다.

### Gaps
- M4 Pro나 M5 Pro MPS에서의 laya 학습 시간과 추론 p95 수치는 이번에 열어 보지 못했다(v0.4.7 문서).
- RLCD 학습 목적함수의 세부(정확한 scoring rule)는 PyPI 요약 수준만 확인했다.
- laya-multilingual의 한국어 정확도는 여전히 공개되지 않았다(PyPI는 51개 언어 중 48개가 "무작위의 3배 초과"라고만 적음).

## 4. Apple Silicon 학습: MLX·mlx-lm 변화, 새 도구, 속도·메모리, 24GB 최대 모델

### Takeaway
2026-09~10에 MLX 0.32.3(9-29)·0.32.4(10-14)와 mlx-lm 0.32.0–0.32.2(10-01~10-16)가 나왔다. 하지만 mlx-lm의 LoRA 학습 기능(LORA.md)은 실질적으로 그대로다.
- 바뀐 것은 커널, 메모리(M5 이전 칩의 SDPA 메모리 감소), VJP(gated delta net 등 하이브리드 모델 학습), 모델 지원이다.
- Apple 2026-10-15 글의 M5 Neural Accelerator 이득은 M4 Pro에는 해당하지 않는다.
- M4 Pro 학습 tok/s 실측은 여전히 공개되지 않았다.
- 24GB에서 학습 가능한 최대 크기는 커뮤니티 추정으로 LoRA 7–8B, QLoRA 8–14B다.
- laya 학습은 PyTorch MPS 경로라서 MLX 변화와 무관하다.

### Cited Findings
- **[new] MLX 코어 릴리스** [공식]
  - v0.32.4(10-14): 1-bit affine 양자화(Metal), SDPA·gated delta net VJP, **M5 이전 칩의 SDPA D512 Metal 메모리 감소**.
  - v0.32.3(09-29): gated delta net Metal 커널, SGD·Adafactor가 호출자 배열을 바꾸던 버그 수정, SDPA D256/D512 메모리 감소.
  - 학습 속도를 높였다는 명시 항목은 적다. 대부분 자동미분 정확성 수정이다.
  - 출처: [GitHub releases](https://github.com/ml-explore/mlx/releases)
- **[changed] mlx-lm 릴리스** [공식]
  - 0.32.0: 새 모델(Muse-Spark-Open NVFP4 등), Qwen 3.5 parallel head, NVFP4 MoE global scale.
  - 0.32.1 / 0.32.2: 템플릿·마스크 수정.
  - 날짜 충돌: PyPI는 0.32.0 = **2026-10-01**, 0.32.1 = 10-15, 0.32.2 = 10-16이다. GitHub 릴리스 페이지는 0.32.0을 "15 Oct"로 표기한다. 태그 게시와 PyPI 업로드 시점이 다른 것으로 보인다.
  - 2026-01 이후 릴리스 노트에 LoRA/DoRA/full/GRPO/DPO 항목이 없다.
  - 출처: [GitHub releases](https://github.com/ml-explore/mlx-lm/releases), [PyPI](https://pypi.org/project/mlx-lm/)
- **[unchanged] mlx-lm LORA.md** (2026-10-17 확인) [공식]
  - `--fine-tune-type lora|dora|full`, 양자화 모델이면 QLoRA, `--mask-prompt`, `--grad-checkpoint`, `--num-layers`(기본 16), `--report-to wandb|swanlab`, YAML 설정, GGUF 내보내기.
  - DPO·GRPO·증류는 없다. 유일한 수치는 여전히 M1 Max 32GB 약 250 tok/s다.
  - 출처: [LORA.md](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md)
- **[new] Apple ML Research, 2026-10-15** [공식]
  - "Local and Distributed Large LLM Inference with MLX and RDMA on Mac Studio": RDMA over Thunderbolt 5용 `jaccl` 백엔드(macOS 26.2), `mlx.launch`, `mlx_lm.benchmark`.
  - M5 GPU Neural Accelerator는 TTFT를 M3 Ultra 대비 최대 4.6배 줄인다. decode 1.6배는 대역폭 덕이다.
  - 학습(LoRA)은 다루지 않았다.
  - 출처: [Apple](https://machinelearning.apple.com/research/mlx-distributed-inference)
- **[new, 상충] Unsloth의 Mac 지원** [공식]
  - 요구사항 문서는 "Mac: Training, MLX and GGUF inference are ALL supported"(Unsloth Studio)라고 쓴다.
  - 같은 문서의 Unsloth Core 절은 "Apple/Silicon/MLX is in the works"라고 쓴다.
  - Mac용 방법·모델·메모리 수치는 없다.
  - 출처: [Unsloth docs](https://unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements)
- **[new, 기준선 누락] mlx-tune** (0.6.0, PyPI 2026-06-23) [커뮤니티]: Unsloth 호환 API로 MLX 위에서 SFT·DPO·GRPO·비전·임베딩 파인튜닝을 한다. 성능 수치는 확인하지 못했다 — [PyPI](https://pypi.org/project/mlx-tune/), [GitHub](https://github.com/ARahim3/mlx-tune)
- **[unchanged]** mlx-lm-lora(SFT/DPO/GRPO 등)와 MLX LoRA Studio는 awesome-mlx 목록에 여전히 있다 — [awesome-mlx](https://github.com/raullenchai/awesome-mlx)
- **[new] 24GB에서 학습 가능한 크기** (InsiderLLM 가이드, 게시 2026-02-26, 갱신 2026-09-24) [커뮤니티, 근거 미기재 추정치]
  - 용량별 상한:

    | 메모리 | LoRA | QLoRA |
    |---|---|---|
    | 16GB | 3–7B | 7–8B |
    | **24GB** | **7–8B** | **8–14B** |
    | 32GB | 8–14B | 14–32B(빠듯) |

  - 모델별 메모리: Llama 3.1 8B는 LoRA 약 14GB, QLoRA 약 7GB. Qwen 2.5 14B는 QLoRA 약 12GB. 같은 글 안에서 14B LoRA 메모리 수치가 서로 맞지 않는다.
  - 8B LoRA 학습 속도("rough numbers"): M1 Max 약 250, M3 Max 약 320, M4 Max 약 380 tok/s. M4 Pro는 표에 없다.
  - 출처: [InsiderLLM](https://insiderllm.com/guides/fine-tuning-mac-lora-mlx/)
- **[new] 측정 주의** [커뮤니티, 검색 요약만]: mlx-lm 로그의 학습 Tokens/sec가 마스크된(학습 대상) 토큰만 센다는 보고가 있다. 표시 0.6 tok/s가 실제 처리량 약 39 tok/s였다 — [블로그](https://vincentvandeth.nl/blog/lora-fine-tuning-mlx-lm-qwen35-mac-mini)
- **[unchanged]** sciences44 M1 64GB 실측(0.8B 4-bit 약 475 tok/s, 피크 3.9GB; 4B 약 115 tok/s, 11.1GB). 기준선 6절 — [GitHub](https://github.com/sciences44/mlx-lora-finetune)

### Inferences
- [추정] **Thorkell에 필요한 학습은 대부분 작다.**
  - laya(322–421M)는 PyTorch MPS로 학습한다. 3절 추정으로 5k 결정이면 약 1–2.5시간이다.
  - Jevstiller식 선형 헤드는 CPU에서 수 초다.
  - 둘 다 MLX가 필요 없다.
- [추정] **MLX가 필요한 경우**는 생성형 소형 모델(0.8–4B)에 플래너 출력이나 회고 규칙을 증류할 때다.
  - 기준선 수치(M1에서 0.8B 약 475 tok/s, 4B 약 115 tok/s)를 하한으로 잡는다. 플래너 증류 데이터는 gemini 쿼터 때문에 월 약 600건 × 1–2K 토큰 ≈ 1M 토큰 수준이다.
  - 이 규모면 4B QLoRA 1 epoch가 약 2.5시간 이내다(115 tok/s 기준, 마스크 토큰 계산 주의).
- [추정] **24GB 상한.** 게임을 끄면 QLoRA 8B는 무난하고, 14B는 짧은 시퀀스와 grad-checkpoint로 가능성이 있다(커뮤니티 추정). 게임을 켜 두면(클라이언트당 약 3–3.4GB, 기준선 로컬 모델 노트) 학습은 하지 않는 편이 맞다.
- [추정] **Mac에서의 GRPO**(mlx-tune, mlx-lm-lora)는 기능은 있지만 속도 근거가 없다. 0.5B급 시뮬 실험 시험용으로만 쓰고, 본 실험은 대여 GPU에서 한다(5절).
- [추정] M4 Pro 실측은 `mlx_lm.lora`로 고정 모델·시퀀스 길이·batch를 정하고 처리 토큰 수 기준으로 직접 재는 것이 가장 빠르다. 공개 수치를 기다릴 이유가 없다.

### Gaps
- M4 Pro(24GB)에서 MLX LoRA 학습 tok/s를 잰 공개 1차 수치는 이번에도 없다.
- Unsloth Studio의 Mac 학습이 어떤 방법·모델을 지원하는지 문서가 서로 맞지 않는다.
- mlx-tune과 mlx-lm-lora의 GRPO 속도와 메모리 수치는 없다.

## 5. LLM 에이전트 RL(GRPO·agentic RL)과 빠른 시뮬레이터 없이 가능한 것

### Takeaway
공개 agentic RL은 여전히 빠른 환경을 전제한다. 예를 들어 2026-09 환경 생성 논문은 스텝당 64 prompt × 16 rollout을 쓴다. 기준선의 "실게임 RL 불가, 2D 시뮬은 대여 GPU" 결론은 그대로다.

새로 의미 있는 것은 두 가지다.
- **시뮬레이터·검증기 없이 원본 로그 한 묶음으로 하는 오프라인 학습(AgentBrew, 2026-09-05)**: 실게임 로그를 학습에 쓰는 경로다.
- **메모리 갱신기만 RL로 학습(MemoPilot)**: 정책 모델은 동결한다.

SPA는 EMNLP 2026 Findings에 채택되며 제목이 바뀌었다.

### Cited Findings
- **[changed] SPA**: v2 2026-09-09, "Accepted to Findings of EMNLP 2026"(API 2026-10-17). 현재 제목은 "Why Do LLM Agents Fail in Exploring New Environments? A World-Modeling Perspective"이고, 방법 이름은 그대로 SPA다.
  - v2 초록: Sokoban 25.6% → 59.8%(Qwen2.5-1.5B), 3B 미만 모델이 20B 기준선을 넘음.
  - FrozenLake·Sudoku 수치와 컴퓨트(단일 H100 약 12시간)는 v1 본문 기준이다. v2에서 다시 확인하지 않았다.
  - 출처: [arXiv v2](https://arxiv.org/abs/2510.15047v2)
- **[unchanged]** API 2026-10-17 기준:
  - RAGEN: v2 2025-05-26 — [arXiv](https://arxiv.org/abs/2504.20073)
  - GiGPO: v3 2025-10-28, NeurIPS 2025 — [arXiv](https://arxiv.org/abs/2505.10978)
  - GROW: v2 2026-05-21 — [arXiv](https://arxiv.org/abs/2605.20246)
  - 수치는 기준선 2절과 같다. ViGaL, TSR, Turn-PPO는 재확인하지 않았다.
- **[new] AgentBrew** (Lyu, …, An, arXiv 2609.05837, 2026-09-05) [논문]
  - 원본 상호작용 궤적 한 묶음에서 품질 필터·과제 검증기·on-policy rollout 없이 도구 사용 정책을 학습한다.
  - 두 구성 요소:
    - 회고적 과제 추론: 각 궤적의 실제 결과에 맞는 지시를 다시 만든다.
    - PMI 기반 행동별 credit: 궤적이 추론된 지시에 대해 가진 정보를 행동별로 나눠 학습 가중치로 쓴다.
  - Qwen3-32B가 GitHub·Notion·PostgreSQL MCP에서 평균 +8.7 Acc / +9.7 Score를 얻었다. Qwen3-235B는 +2.3/+4.4, rejection sampling은 +5.9/+10.3이다.
  - 데이터량과 컴퓨트는 초록에 없다.
  - 출처: [arXiv](https://arxiv.org/abs/2609.05837)
- **[new, 기준선 누락 2026-06] MemoPilot**: 메모리 갱신을 multi-turn GRPO로 학습한다. 정책 LLM은 동결한다. 1절 참조 — [arXiv](https://arxiv.org/abs/2606.08656)
- **[new, 검색 요약만] Verifiable Hidden Dynamics Play** (arXiv 2609.27321): 해결된 메커니즘에서 게임형 agentic RL 환경을 생성한다. GRPO로 스텝당 64 prompt × 16 rollout(18회 과샘플)을 쓴다 — [arXiv](https://arxiv.org/pdf/2609.27321)
- **[new, 검색 요약만]**
  - EnvRL(2606.17680): GRPO로 Qwen2.5-1.5B ALFWorld 72.8% → 77.4% — [alphaXiv](https://www.alphaxiv.org/abs/2606.17680)
  - GEM(ICLR 2026): 게임 위주 agentic LLM gym, GRPO/PPO/REINFORCE 비교 — [arXiv](https://arxiv.org/pdf/2510.01051)
  - "Decoupling KL and Trajectories"(2605.16826): SFT·DAgger·오프라인 RL·OPD를 증류 관점에서 통합(제목만 확인) — [arXiv](https://arxiv.org/pdf/2605.16826)

### Inferences
- [추정, 계산] **실게임 GRPO가 왜 안 되는가.** 64 × 16 = 1,024 rollout/스텝이다. 실게임 에피소드가 5분이면 스텝 하나에 약 85시간이 든다. 한 번에 한 시나리오만 돌릴 수 있다(하드 규칙 3). 결론은 기준선과 같다.
- [추정] **2D 시뮬 GRPO.**
  - 시뮬 1 에피소드가 수 초이고 정책이 0.5–1.5B 생성 모델이면, 기준선의 SPA 규모(1.5B, 1,000스텝, 단일 H100 약 12시간)가 참고점이다.
  - Mac에서는 0.5B 소규모 동작 확인만 한다(4절).
  - laya 같은 비생성 분류기는 GRPO 대상이 아니다. 분류기는 증류·보정으로 다룬다.
- [추정] **시뮬레이터 없는 학습 경로(새 권장).** AgentBrew식 오프라인 학습을 Thorkell 로그에 적용한다.
  1. 실게임 에피소드 로그에서 "실제로 일어난 결과"로 목표를 다시 붙인다(hindsight 재라벨링, 예: "나무 3개를 모았다").
  2. 월드 변화로 검증된 진척 이벤트로 행동별 가중치를 준다(PMI 대신 쓰는 단순 대체).
  3. 가중 SFT/KD를 한다.

  on-policy rollout이 필요 없어서 실게임 시간 제약을 받지 않는다. 단 32B 규모 결과이므로, Thorkell에서는 플래너 출력 증류(4B 이하)나 laya 라벨 가중에 축소해서 쓴다.
- [추정] **보상 설계.** Thorkell은 이미 "월드 변화로 진척"을 센다. 이것이 RLVR의 검증 가능한 보상과 같은 구조라서, 시뮬 RL에서도 같은 진척 판정 코드를 보상으로 쓰면 sim-to-real 차이가 줄어든다.

### Gaps
- 실시간 3D 게임에서 LLM을 RL로 파인튜닝하고 실게임 성능을 보고한 공개 사례는 이번에도 찾지 못했다.
- AgentBrew의 데이터량과 컴퓨트는 초록에 없었다.
- 2609.27321, EnvRL, GEM은 검색 요약만 봤다.

## 6. 사람 플레이·영상 모방학습

### Takeaway
2026-09-01~10-17 사이에 게임 모방학습의 큰 새 결과는 찾지 못했다. NitroGen, Lumine, SIMA 2는 arXiv 버전 변화가 없다(API 2026-10-17). Thorkell에 맞는 모방학습은 여전히 "픽셀 → 키 입력"이 아니라 리더의 고수준 선택과 교정을 라벨로 쓰는 것이다.

### Cited Findings
- **[unchanged]** 수치는 기준선 3절과 같다.
  - NitroGen: v1 2026-01-04(API 2026-10-17). HF 가중치 공개 — [arXiv](https://arxiv.org/abs/2601.02427), [HF](https://huggingface.co/nvidia/NitroGen)
  - Lumine: v1 2025-11-12(API) — [arXiv](https://arxiv.org/abs/2511.08892)
  - SIMA 2: v1 2025-12-04(API) — [arXiv](https://arxiv.org/abs/2512.04797)
  - VPT, CS:GO BC, Visual Encoders(Schäfer)는 재확인하지 않았다.
- **[new, 기준선 누락 2025-08, 검색 요약만] Pixels to Play(P2P0.1)**: 픽셀에서 사람 같은 행동을 내는 3D 게임 foundation model이다. 저자 스스로 "비교적 단순한 3D 타이틀"을 다룬다고 밝혔다 — [arXiv](https://arxiv.org/pdf/2508.14295)
- **[new, 검색 요약만]** CS2 1인칭 영상, 프레임 정렬 행동이 있는 멀티게임 FPS 데이터셋 등 게임 플레이 데이터셋 모음이 있다 — [HF collection](https://huggingface.co/collections/davanstrien/video-game-gameplay-datasets-for-agent-training)
- **[new, 모방학습 인접] PEAM**: 실패-교정 궤적 쌍을 BC + 대조 목표로 학습한다(1절) — [arXiv](https://arxiv.org/abs/2605.27762)
- **[unchanged] Orak**: v3 2026-04-14(API). 파인튜닝 수치는 이번에도 확인하지 못했다 — [arXiv](https://arxiv.org/abs/2506.03610)

### Inferences
- [추정] **Thorkell식 모방학습.**
  - (a) 호스트 플러그인이 리더의 고수준 행동(무엇을 치고, 무엇을 줍고, 어디로 가는지)을 구조화 이벤트로 남긴다. 같은 상태 직렬화로 "리더라면 이 상황에서 이것을 골랐다"는 라벨을 만든다.
  - (b) 리더의 채팅 교정("아니 그거 말고 …")을 DAgger식 교정 라벨로 저장한다.
  - 둘 다 오프라인이라 실게임을 추가로 돌릴 필요가 없다. 데이터는 플레이 시간에 비례해 자연히 쌓인다.
- [추정] PEAM의 "실패-교정 쌍"은 Thorkell에서 바로 만들 수 있다. 실패한 결정과 그 뒤 성공한 결정을 같은 상태 키로 묶으면 된다. laya 학습에서는 대조 쌍이나 하드 네거티브로 쓴다.
- [추정] 정보 동등성(규칙 5): 리더 행동 로그를 라벨로 쓸 때도 학생 입력은 봇이 볼 수 있는 상태여야 한다. 리더 화면에만 보이는 정보로 라벨을 만들면 학생이 따라 할 수 없는 라벨이 섞인다.

### Gaps
- 구조화 상태(비픽셀) + 고수준 행동으로 3D 생존 게임을 모방학습한 데이터량 곡선은 이번에도 찾지 못했다.
- 2026-09~10 게임 모방학습 신규 논문은 검색 색인에서 찾지 못했다. 색인 지연일 수 있다.

## 7. 2D 시뮬레이터의 sim-to-real 활용

### Takeaway
2026년에 "foundation model 에이전트의 sim-to-real 간극"을 MDP 네 요소(관측·행동·전이·보상)로 나누어 보자는 틀(KDD 2026 Blue Sky)과, 상태 정렬 + 행동 번역으로 재학습 없이 옮기는 틀(사이버 RL, 2026-10)이 나왔다. 둘 다 "잘 정렬된 환경에서만 zero-shot이 된다"는 쪽이다.
- Thorkell 시뮬은 행동·이벤트 규약을 공유하므로 **행동 간극은 작다**.
- 남는 것은 **전이(물리·내비·전투)와 관측 분포** 간극이다.
- Learn2Play와 SPA는 같은 게임 안에서도 인스턴스가 바뀌면 배운 것이 줄어든다는 증거다.

### Cited Findings
- **[new] The Sim-to-Real Gap of Foundation Model Agents: A Unified MDP Perspective** (Liu et al., arXiv 2606.07017, 2026-06-05, KDD 2026 Blue Sky) [논문]
  - 간극을 Observation·Action·Transition·Reward로 구조화한다.
  - 다국어 도구 호출에서 관측 간극 때문에 의미는 맞지만 실행할 수 없는 행동이 나오는 예를 든다.
  - 권고: domain randomization 등 로보틱스 기법 도입, 공통 용어, 표준 스트레스 테스트 벤치.
  - 정량 결과는 없다.
  - 출처: [arXiv](https://arxiv.org/abs/2606.07017)
- **[new, 검색 요약만] Crossing the Cyber Divide** (arXiv 2610.00759, 2026-10): RL 정책의 sim-to-sim·sim-to-real 전이를 같은 정렬 문제로 본다. 상태 정렬과 행동 번역을 분리해 재학습 없이 옮긴다. zero-shot 전이는 밀접하게 정렬된 환경에서만 됐다 — [arXiv](https://arxiv.org/abs/2610.00759)
- **[new, 검색 요약만]** Mind the Sim2Real Gap in User Simulation(2603.11245): 모델 능력이 높다고 시뮬레이션이 더 충실해지지는 않는다 — [arXiv](https://arxiv.org/pdf/2603.11245)
- **[new] 인스턴스 전이 감소**: Learn2Play에서 재셔플 인스턴스의 학습 기울기가 0.59–2.67 떨어졌다(1절) — [arXiv](https://arxiv.org/html/2610.08215)
- **[changed] SPA**: 같은 게임 안 난이도 확장은 되지만 다른 게임으로는 전이되지 않는다는 기준선 결론은 v1 본문 기준이다. v2(EMNLP 2026 Findings) 본문에서 다시 확인하지 않았다 — [arXiv v2](https://arxiv.org/abs/2510.15047v2)
- **[unchanged]** EnvGen(LLM 4회 호출로 Crafter 환경 조정, 4M PPO 32.2%)과 Motif(LLM 선호 → 보상)는 기준선 4절 그대로다(재확인 안 함).

### Inferences
- [추정] **시뮬에서 배울 것과 배우지 않을 것.**
  - 배울 것: 고수준 선택 정책(언제 후퇴, 무엇을 먼저), 규칙 가설의 1차 선별(RBC식 A/B), 호기심 실험 후보 거르기, laya 사전학습용 Jev 라벨 상태.
  - 배우지 않을 것: 내비게이션, 전투 타이밍, 손 닿는 거리. 이것들은 실게임 네이티브 스킬과 반사가 맡는다(Eira 교훈: 해안 내비 정체가 최다 실패).
- [추정] **간극 측정.**
  1. 실게임 결정 로그의 상태를 시뮬 직렬화와 같은 스키마로 비교한다. 필드 분포(위협 수, 체력 비율, 거리 구간)의 차이를 잰다(관측 간극).
  2. 같은 고수준 계획을 시뮬과 실게임에서 실행해 성공·소요 시간 차이를 잰다(전이 간극). 회귀 세트의 해안 시드를 꼭 넣는다.
  3. 시뮬 파라미터(적 속도, 지형 막힘 확률, 채집 시간)를 무작위화해서, 시뮬에서 배운 선택이 특정 시뮬 값에 과적합되지 않게 한다.
- [추정] **보정은 실게임에서만 한다.** temperature, abstention 임계값, 승격 게이트는 실게임 held-out으로만 맞추고 판정한다. 시뮬 데이터로 맞춘 보정은 분포가 달라 그대로 옮겨지지 않는다.
- [추정] AGENTS.md의 "몸의 동작 규칙을 바꾸면 시뮬도 같이 바꾼다"는 원칙이 행동 간극을 0에 가깝게 유지하는 장치다. 위 논문들의 "정렬된 환경에서만 zero-shot" 결과가 이 원칙을 뒷받침한다.

### Gaps
- 단순 2D 시뮬에서 배운 LLM·분류기 정책을 3D 실시간 게임으로 옮기고 성능을 보고한 공개 사례는 찾지 못했다.
- 2610.00759, 2603.11245는 검색 요약만 봤다.

## 8. 학습된 행동의 평가 방법 (홀드아웃 시드, 회귀 세트, 승격 게이트)

### Takeaway
2026 근거는 다음 다섯 가지로 모인다.
- multi-turn 에이전트는 single-turn보다 시드 분산이 크다.
- 같은 시드로 짝지은 비교가 분산을 줄인다.
- 메모리·학습 효과는 "같은 인스턴스 반복"과 "재셔플 인스턴스"를 나눠서 재야 한다(Learn2Play).
- 규칙·교훈의 효과는 무작위 on/off로 재야 한다(RBC).
- 로컬 대체는 보수 경계, 상시 감사, 여러 번의 무작위 분할로 검증해야 한다(Jevstiller).

### Cited Findings
- **[new, 검색 요약만]** 도구 호출 에이전트를 10개 시드로 돌리면 multi-turn 결과가 최대 약 3% 흔들렸다. 논문들은 흔히 단일 실행만 보고한다 — [arXiv 2606.00135](https://arxiv.org/pdf/2606.00135)
- **[new, 검색 요약만]** 시드 단위 결과가 양의 상관이면 같은 시드로 짝지은 비교가 분산을 엄격히 줄인다(다중 에이전트 경제 시뮬) — [arXiv 2512.24145](https://arxiv.org/abs/2512.24145)
- **[new, 커뮤니티, 검색 요약만]** ReAct HotpotQA 소규모 연구: 정답 분산의 84–100%가 문항 차이에서 온다. 300문항 × 3회면 3점 차이를 검정력 약 0.9로 잡는다 — [GitHub agent-eval-variance](https://github.com/V1cissitudes/agent-eval-variance)
- **[new, 검색 요약만]** LLM 파인튜닝 논문의 50% 이상이 시드를 잘못 다룰 가능성이 있었고, 24편은 고정 시드 하나만 썼다 — [IJCNLP 2025](https://aclanthology.org/2025.ijcnlp-short.3.pdf)
- **[new] Learn2Play 평가 설계**
  - 지표: Max, Mean, 학습 이득(LG), 학습 기울기(LS).
  - 고정 인스턴스와 재셔플 인스턴스를 나눠서 잰다.
  - 사람 기준선은 게임당 21–30명이다.
  - "점수 하락 후 개인 최고 갱신률" 같은 행동 지표도 쓴다.
  - 출처: [arXiv](https://arxiv.org/html/2610.08215)
- **[new] RBC**: 교훈 블록을 무작위로 포함하거나 빼서 효과를 추정한다. 마지막에는 정리한 playbook, 전체 playbook, 빈 playbook 중 새 연습 에피소드에서 가장 좋은 것을 고른다 — [arXiv](https://arxiv.org/abs/2610.18427)
- **[new] EvoWeave**: 저자가 유의성 주장을 하지 않고, 일부 차이가 표준편차보다 작다고 명시했다. 메모리 방법 간 1–2점 차이는 잡음 범위일 수 있다 — [arXiv](https://arxiv.org/html/2610.19381v1)
- **[new] Jevstiller 검증 방식**: held-out 2,000행, 무작위 분할 100번(예산 초과 1번), 상시 2% 감사 — [GitHub](https://github.com/tomerglick57/Jevstiller)
- **[new] laya evals 게이트**: `--max ece`, `--min-confidence`, 기준선 차감, 무의미하거나 유한하지 않은 게이트 거부(0.4.8) — [GitHub releases](https://github.com/NandhaKishorM/laya/releases)
- **[unchanged]** 기준선의 "홀드아웃 시드로 튜닝하지 않는다"(Eira 교훈), BALROG의 장기 게임 평가는 그대로다.

### Inferences
- [추정] **Thorkell 회귀 세트 구성.**
  - (a) 시뮬 회귀 시드 고정 세트를 둔다. 해안·물가 시드를 꼭 넣는다. 비교할 두 정책은 **같은 시드로 짝지어** 돌린다.
  - (b) 실게임 시나리오 세트(talk, primitives, 채집 N개, 위협 대응)를 정기적으로 돈다. 실게임은 비싸므로 승격 후보가 시뮬 회귀를 통과했을 때만 돌린다.
  - (c) 튜닝에 한 번도 쓰지 않는 홀드아웃 시드와 홀드아웃 실게임 세이브를 따로 둔다.
- [추정] **결정 모델 승격 게이트**(2절 계산 반영). 질문 타입마다 다음을 모두 만족해야 승격한다.
  - 실게임 held-out에서 Jev 일치율 Clopper–Pearson 하한 ≥0.95. 관측 97%면 약 340건, 96%면 약 1,260건이 필요하다.
  - ECE ≤0.05. 타입당 약 1,000건 이상 또는 부트스트랩 상한으로 판정한다.
  - 게임을 켠 상태의 p95 ≤50 ms.
  - 승격 뒤에도 Jevstiller처럼 2% 감사 트래픽을 Jev로 보내 일치율 하락을 감시한다.
- [추정] **학습 루프 평가.** 회고 규칙과 호기심 실험의 효과는 Learn2Play처럼 "같은 시드 반복"과 "새 시드"로 나눠 보고한다. 규칙 채택은 RBC식 on/off 비교로 한다. 결과는 기존 report·evidence에 싣는다(BepInEx 로그 끝부분 유실 교훈).
- [추정] **표본 감각.** 실게임 시나리오 1회의 성공·실패는 이항 결과라 분산이 크다. 성공률 10%p 차이를 검정력 0.8로 보려면 조건당 수백 회가 필요하다. 그래서 실게임 A/B는 사실상 불가능하다. 실게임은 "회귀 없음 확인"용으로 쓰고, 효과 크기 추정은 시뮬과 결정 단위 held-out에서 한다.

### Gaps
- LLM 게임 에이전트 평가의 시드 분산을 체계적으로 다룬 2026 논문은 찾지 못했다. 근거는 도구 호출 벤치, 경제 시뮬, 커뮤니티 소규모 연구다.
- 2606.00135, 2512.24145, agent-eval-variance는 검색 요약만 봤다.
