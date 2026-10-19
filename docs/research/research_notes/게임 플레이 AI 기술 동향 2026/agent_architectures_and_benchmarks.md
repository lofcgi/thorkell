# 개방형·서바이벌 게임 LLM 에이전트 아키텍처와 게임 벤치마크 근거 (기준일 2026-10-10, 조사일 2026-10-11)

표기: [논문] 동료심사 논문 또는 arXiv 프리프린트(구분해서 적음), [공식 블로그] 개발사·벤더 엔지니어링 글, [코드] GitHub 저장소·README·소스, [모델 카드] HF 카드, [리더보드] 벤치마크 사이트 표, [집계] 2차 집계 사이트, [이전 조사] 이 레포 `docs/research/2026-10-01-thorkell-feasibility.md`에서 2026-10-01에 확인한 출처, [추정] 이 노트 작성자의 추론.

## 1. 계층형·이중 시스템(System 1 / System 2) 설계: 무엇이 있고 어떻게 나누는가

### Takeaway
2024~2026년의 실용 사례는 모두 "틱 단위로 도는 결정적 실행층(행동 트리·스킬·모드) + 이벤트 때만 부르는 언어 모델층"으로 나눈다. 2026년 연구는 여기서 더 나아가 "느린 모델을 언제 부를지 정하는 문(gate)"과 "느린 모델이 생각하는 동안 낡아 버리는 계획"을 핵심 문제로 다룬다.

### Cited Findings
**PUBG Ally (KRAFTON + NVIDIA ACE)**
- [공식 블로그, 2026-06-25] System 1인 행동 트리가 이동·조준·즉각 전투를 게임 틱 단위로 처리하고 SLM 추론을 기다리지 않는다. System 2인 SLM은 의도 파악, 협동, 발화, 행동 명령 생성을 맡는다. — [NVIDIA Developer Blog](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)
  - SLM은 Mistral-NeMo-Minitron-2B(2B)이고, 양자화해 온디바이스로 돌린다. 총 VRAM 8GB GPU까지 지원하고, ASR과 TTS도 온디바이스다.
  - 클라우드를 쓰지 않은 이유: 네트워크 지연과 추론 지연이 합쳐져 분대 교신용으로는 너무 느렸다.
- [공식 블로그, 2026-06-25] SLM은 이벤트 구동 루프로 돈다. 플레이어가 말하거나 게임 이벤트가 생길 때만 실행된다. — [NVIDIA Developer Blog](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)
  - 지시문과 게임 맥락은 고정하고 실시간 정보만 바꿔 KV 캐시를 재사용하도록 프롬프트를 짰다.
- [공식 블로그, 2026-06-25] 범위를 좁혀서 문제를 풀 만하게 만들었다. 같은 출처.
  - 맵 하나(Sanhok), 모드 하나(AI Duo), 고정된 아이템 분류 체계만 다룬다.
  - 큰 교사 모델에게 결정적인 PUBG 사양을 시스템 프롬프트로 주고, 그 행동(용어, 툴 호출 규율)을 2B 학생 모델에 증류했다.
  - 영어·한국어·중국어를 지원한다.
- [공식 블로그, 2026-06-25] 공개된 지연 수치(ms)는 없다. "수백 ms가 교신의 쓸모를 가른다"는 서술만 있다. 같은 출처.
  - 베타 기간을 이 블로그는 2026-06-17~30으로 적었다. 이전 조사는 06-17~07-01로 기록해서 하루 차이가 난다.

**Project Sid / PIANO (Altera)**
- [논문 arXiv, 2024-10-31] PIANO는 여러 모듈을 서로 다른 시간 척도에서 동시에 돌린다. 모듈은 기억, Action Awareness, 목표 생성, 사회 인식, Talking, Skill Execution 등이다. — [arXiv 2411.00114](https://arxiv.org/html/2411.00114v1)
  - Cognitive Controller(CC)는 정보 병목으로서 상위 결정을 내리고, 그 결정을 말하기·행동 모듈에 방송해 말과 행동이 일치하게 한다.
- [논문 arXiv, 2024-10-31] 결과와 한계. 같은 출처.
  - 사용 모델은 GPT-4o다. 이전 모델로는 이 결과가 나오지 않았다고 썼다.
  - 25개 에이전트가 30분에 평균 17종의 고유 아이템을 얻었다. 49개 에이전트로 4시간을 돌리면 약 320종(전체 약 1,000종의 1/3)에서 포화됐다.
  - 한계로 시각과 공간 추론이 없다는 점을 스스로 밝혔다.

**병렬 계획-행동 (Li et al., AAMAS 2026)**
- [논문 AAMAS 2026, arXiv v1 2025-03] 계획 스레드와 행동 스레드가 공유 액션 버퍼로만 소통한다. — [AAMAS 2026 PDF](https://ifaamas.org/Proceedings/aamas2026/pdfs/EXAJ9853.pdf), [arXiv 2503.03505](https://arxiv.org/abs/2503.03505v1)
  - 버퍼는 **단일 슬롯 큐**다. 새 제안이 들어오면 이전 것을 덮어쓴다.
  - LLM이 새 행동과 함께 interrupt 플래그를 낸다. 플래그가 true면 행동 스레드는 진행 중인 스킬을 즉시 끊고 버퍼의 최신 행동을 가져간다.
  - 행동 스레드는 선점을 스스로 판단하지 않는다.
- [논문 AAMAS 2026] 지연 분석: 행동 시간(t_act)이 계획 시간(t_plan)보다 길면 계획 지연이 행동 뒤에 숨는다. 같은 출처.
  - "몇 분짜리 스킬을 재귀 분해로 자동화하고, LLM 추론은 보통 몇 초"라고 썼다.
- [논문 AAMAS 2026] 전제조건 DAG로 재귀 분해한다. 같은 출처.
  - 순차 추론으로는 임계 경로 길이 d에 대해 LLM 호출이 최소 d+1번 필요하다. 이 방식은 상위 과제당 LLM 호출 1번이면 된다.
  - 저자들은 이것이 "오류 전파도 줄인다"고 주장한다.
- [논문 AAMAS 2026] 실험 조건과 관찰. 같은 출처.
  - 모델: Qwen-Plus, 멀티모달 실험은 Qwen-VL-Plus. 서버는 LLM 호출 중에도 멈추지 않았다.
  - 텍스트 관측을 VLM 관측으로 바꾸면 응답 지연이 늘고 관측 정확도가 약간 떨어졌다.

**Mindcraft와 MineCollab**
- [코드, 확인 2026-10-11] Mindcraft는 `mindcraft-bots/mindcraft`로 옮겨 계속 개발 중이다. — [GitHub mindcraft-bots/mindcraft](https://github.com/mindcraft-bots/mindcraft), [`src/agent/modes.js`](https://github.com/mindcraft-bots/mindcraft/blob/develop/src/agent/modes.js)
  - 상태: develop 브랜치 마지막 push 2026-10-03, 별 5,872개.
  - 릴리스: v0.1.4(2026-03-20), v0.1.3(2025-09-20), v0.1.2(2025-09-07, UI·AI 음성·ToolUse).
  - `modes.js`의 모드:
    - `self_preservation`(익사·화염·저체력 대응), `unstuck`, `cowardice`, `self_defense`: `interrupts: ['all']`
    - `hunting`, `item_collecting`, `torch_placing`, `elbow_room`: `followPlayer`만 끊는다.
- [코드] 코드 실행 기능은 기본으로 꺼져 있다. 켜려면 `allow_insecure_coding`을 설정해야 한다. README는 "코딩을 켠 채 공개 서버에 연결하지 말라"고 경고한다. Ollama로 미세조정한 로컬 모델(`sweaterdog/andy-4:micro-q8_0`)도 지원한다. — [GitHub README](https://github.com/mindcraft-bots/mindcraft)
- [코드, 확인 2026-10-11] 커뮤니티 갈래 `mindcraft-ce` 조직이 따로 있다. — [GitHub org mindcraft-ce](https://github.com/mindcraft-ce)
  - 본 저장소 마지막 push 2026-10-10, 별 141개.
  - Windows GUI 설치기와 분산 추론 풀 클라이언트(`andyapi-client-*`)가 있다.
  - 본가와 기능이 어떻게 다른지는 확인하지 못했다.
- [모델 카드, 2025-05] Andy-4는 Mindcraft 전용으로 미세조정한 8B 모델이다. — [HF Sweaterdog/Andy-4](https://huggingface.co/Sweaterdog/Andy-4)
  - DeepSeek-R1-LLaMA 8B 기반이다. 425.5M 토큰(대화 62,149개)으로 RTX 3090 한 장에서 약 3주 학습했다.
  - Q4_K_M 기준 6~8GB VRAM이 필요하다.
  - 큰 모델과의 정량 비교는 없다.
- [논문 arXiv, 2025-04-24] MineCollab은 Mindcraft 위에 47개 매개변수 도구를 두고 협업 과제를 평가한다. — [arXiv 2504.17950](https://arxiv.org/html/2504.17950)
  - 상세한 계획을 말로 주고받게 하면 성능이 최대 약 15% 떨어진다.
  - 저자 결론: 효율적인 자연어 소통이 협업의 "주된 병목"이다.

**코드 스킬 라이브러리 계열과 MLLM 계열**
- [논문 arXiv, 2023-05] Voyager는 GPT-4 블랙박스 호출로 동작한다. — [arXiv 2305.16291](https://arxiv.org/abs/2305.16291)
  - 구성: 자동 커리큘럼, 실행 가능한 코드 스킬 라이브러리, 반복 프롬프팅(환경 피드백, 실행 오류, 자기검증).
  - 성과(초록): 고유 아이템 3.3배, 이동 거리 2.3배, 기술 트리 마일스톤 최대 15.3배 빠름.
- [논문 arXiv, 2024-07, IJCAI'25] ODYSSEY는 기본 스킬 40개와 조합 스킬 183개를 쓴다. Minecraft 위키 QA 390k+로 LLaMA-3 8B·70B를 미세조정해 MineMA를 만들었다. — [arXiv 2407.15325](https://arxiv.org/abs/2407.15325)
- [논문 arXiv, 2023-05] GITM은 목표를 하위 목표, 구조화 액션 순으로 분해하고 텍스트 지식·기억을 쓴다. ObtainDiamond 성공률이 +47.5%p 올랐다. — [arXiv 2305.17144](https://arxiv.org/abs/2305.17144)
- [논문 arXiv, 2023-11] JARVIS-1은 멀티모달 기억을 붙인 계획기다. — [arXiv 2311.05997](https://arxiv.org/abs/2311.05997)
  - 200개 이상의 과제를 수행한다.
  - 장기 과제 다이아몬드 곡괭이 완료율 12.5%로, 기존 기록의 최대 5배다.
- [논문 arXiv, 2024-08] Optimus-1은 계층적 지식 그래프(HDKG)와 경험 풀(AMEP)을 쓴다. 기존 에이전트보다 최대 30% 개선됐다. — [arXiv 2408.03615](https://arxiv.org/abs/2408.03615)
- [논문 arXiv, 2024-03] Cradle은 스크린샷을 입력받아 키보드·마우스 코드를 출력한다. RDR2, Stardew Valley 등에서 실험했다. — [arXiv 2403.03186](https://arxiv.org/abs/2403.03186)
  - 실시간 게임은 추론하는 동안 일시정지해야 했다 [이전 조사].

**픽셀 범용 에이전트 (2025-10~2026-01, 이전 조사에서 출처 확인)**
- [논문/공식, 이전 조사] Lumine(ByteDance Seed, 2025-11-11): 7B, 5Hz로 관측하고 30Hz로 키보드·마우스를 낸다. 필요할 때만 추론한다. 가중치는 공개하지 않았다. — [arXiv 2511.08892](https://arxiv.org/abs/2511.08892)
- [논문/공식, 이전 조사] Game-TARS(2025-10-27): 결정적인 순간에만 추론한다(Sparse Thinking). — [arXiv 2510.23691](https://arxiv.org/abs/2510.23691)
- [논문/공식, 이전 조사] SIMA 2(2025-11-13): Gemini 기반이다. 학습 환경에 Valheim이 들어 있다. — [DeepMind blog](https://deepmind.google/blog/sima-2-an-agent-that-plays-reasons-and-learns-with-you-in-virtual-3d-worlds/), [arXiv 2512.04797](https://arxiv.org/abs/2512.04797)
- [논문/공식, 이전 조사] NitroGen(2025-12): README가 "빠른 반응용 system-1 모델이며 장기 계획은 못 한다"고 밝힌다. — [nitrogen.minedojo.org](https://nitrogen.minedojo.org/)

**2025-11~2026-10 이중 시스템 연구**
- [논문 arXiv 프리프린트, 2026-10-07, 독립 연구자 단독 저자, 미심사] "System Switch"는 Doom에서 빠른 typed-decision 행위자와 느린 추론 VLM을 붙여 실험했다. 느린 모델은 문이 열릴 때만 넘겨받고, 게임은 멈추지 않는다. — [arXiv 2610.09683](https://arxiv.org/html/2610.09683)
  - typed-decision 모델은 선택·점수·예/아니오를 한 번의 forward로, 보정된 확률과 함께 답한다. llama.cpp `/v1/systemone` 인터페이스로 묶었다.
  - 다룬 모델: Julia-1, Laya, Kev, Lev, Clef-Flash, OpenJev, Strands Decider, CLM(0.15B~9B, zero-shot).
  - 느린 모델: Qwen3.6-35B-A3B, Gemma 4 26B-A4B.
  - 이 논문의 Laya·OpenJev가 Thorkell이 쓰는 Jev·laya와 같은 계열인지는 확인하지 못했다.
- [논문 arXiv, 2025-11-07] Real-Time Reasoning Gym은 에이전트가 생각하는 동안에도 환경이 바뀌는 상황을 다룬다. — [arXiv 2511.04898](https://arxiv.org/abs/2511.04898)
  - 반응형(짧은 추론)과 계획형(긴 추론)을 동시에 돌리는 AgileThinker가 단일 방식보다 낫다.
  - 그 차이는 난이도와 시간 압박이 클수록 커진다.
- [논문 arXiv, 2026-06-23] Latent Bridge는 얼린 모델 두 개를 붙이고 둘 사이 통신 채널만 학습한다. — [arXiv 2606.24470](https://arxiv.org/abs/2606.24470)
  - 빠른 쪽은 MiniCPM-o 4.5, 느린 쪽은 Qwen3-VL-8B-Thinking(약 1.5초)이다.
  - Atari 7종과 MetaDrive에서 fast-only 대비 MsPacman +57%, RoadRunner +28%였다.
  - 느린 추론이 원래 더 나은 영역에서만 도움이 됐다. Latent와 Text 채널의 이득 상관은 r=0.93이었다.
- [논문 arXiv, 2026-09-28, 검색 요약으로만 확인] SALMONN-duo는 상시 켜진 빠른 전이중 음성 LLM(System 1)과 비동기로 도는 느린 LLM 에이전트(System 2)를 짝지었다. — [arXiv 2609.34247](https://arxiv.org/abs/2609.34247)
- [논문 arXiv, 2024-10] Talker-Reasoner(DeepMind)는 빠르게 대화하는 Talker와 느리게 계획·믿음을 갱신하는 Reasoner로 나눈다. — [arXiv 2410.08328](https://arxiv.org/abs/2410.08328)
- [논문 arXiv, 2023-05] SwiftSage는 작은 빠른 모델과 큰 느린 LLM을 상황에 따라 전환한다. — [arXiv 2305.17390](https://arxiv.org/abs/2305.17390)

### Inferences
- [추정] Thorkell의 현재 층 구조는 PUBG Ally와 거의 같은 모양이다. Body 반사·스킬이 행동 트리, Jev/laya가 빠른 타입 결정, flash가 System 2에 해당한다. 사례에 비춰 구조 자체를 바꿀 근거는 없다.
- [추정] 두 부분은 바로 가져올 수 있다.
  - AAMAS'26의 단일 슬롯 버퍼: 최신 제안만 남기고 덮어쓰는 방식.
  - DAG 재귀 분해: 상위 목표당 LLM 호출 1번.
- [추정] interrupt 판단은 AAMAS처럼 LLM에 맡기지 않는다. 몸(반사)과 Jev가 해야 한다.
  - Thorkell의 플래너 지연은 수 초~수십 초다. System Switch가 보고한 9~29초 지연에서는 LLM이 낸 interrupt가 이미 낡은 상태에 근거한다.
- [추정] PUBG Ally가 "맵 하나, 모드 하나, 고정 분류"로 성공한 것은 범위를 닫을수록 작은 모델로도 된다는 증거다. Valheim은 범위가 넓으니 마일스톤마다 닫힌 하위 범위를 정의하는 편이 맞다.

### Gaps
- PUBG Ally의 실제 지연(ms), 이벤트당 SLM 호출 빈도, 툴 호출 스키마 검증 방식은 공개되지 않았다.
- `mindcraft-ce`가 본가와 어떤 기능(인터럽트, 기억 등)이 다른지는 README를 읽지 않아 확인하지 못했다.
- System Switch는 단독 저자 프리프린트이고 Doom 한 맵, 33게임 규모다. 일반화 근거로는 약하다.

## 2. 인터럽트, 장기 과제, 기억·회고, 말과 행동의 일관성은 어떻게 다루는가

### Takeaway
인터럽트는 "코드 반사가 즉시 끊고, 언어 모델은 다음 의도만 단일 슬롯에 넣는" 방식으로 수렴하고 있다. 장기 과제는 frontier 모델도 숨은 전제조건이 여러 단계로 엮이면 급격히 실패한다. 말과 행동의 일관성은 결정을 한곳에 모으는 병목과 월드 근거 진척 검증으로 지킨다.

### Cited Findings
**인터럽트**
- [코드] Mindcraft 모드는 `interrupts` 목록으로 선점 범위를 선언한다. 생존·자기방어·끼임 탈출은 `all`이고, 유휴 행동(사냥, 줍기, 횃불 설치)은 `followPlayer`만 끊는다. — [`modes.js`](https://github.com/mindcraft-bots/mindcraft/blob/develop/src/agent/modes.js)
- [논문 AAMAS 2026] 계획 스레드가 상시 감시하며 새 행동과 interrupt 플래그를 낸다. 행동 스레드는 플래그가 없으면 현재 스킬을 끝까지 하면서 주기적으로 버퍼를 확인한다. — [AAMAS 2026 PDF](https://ifaamas.org/Proceedings/aamas2026/pdfs/EXAJ9853.pdf)
- [공식 블로그] PUBG Ally의 행동 트리는 언어 모델 추론에 막히지 않는다. — [NVIDIA](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)
- [논문 프리프린트, 2026-10] System Switch는 느린 모델을 부르는 문 다섯 가지를 비교했다. — [arXiv 2610.09683](https://arxiv.org/html/2610.09683)

  | 문 | 조건 |
  |---|---|
  | Unsure | 확신이 임계값 아래인 결정이 3번 연속 |
  | Stuck | 5초 동안 48 단위 미만 이동, 적 없음 |
  | Blocked | 최근 명령 6개 중 3개 실행 실패 |
  | Loop | 15초 동안 같은 명령이 80% 이상 |
  | Novelty | 15초 동안 새 128 단위 칸에 도달하지 못함 |

**장기 과제**
- [논문 arXiv, 2026-05-29, EMNLP 2026 Main] MineExplorer(Minecraft 탐색 벤치마크): 강한 모델도 단일 홉 과제는 풀지만, 숨은 전제조건을 긴 궤적에 걸쳐 맞춰야 하면 성능이 급락한다. "더 큰 모델이나 thinking 모드가 일관되게 성능을 올리지는 않는다." — [arXiv 2605.30931](https://arxiv.org/abs/2605.30931)
- [논문 ICLR 2025] BALROG에서 확인된 장기 과제 약점. — [arXiv 2411.13543v2](https://arxiv.org/html/2411.13543v2)
  - Boxoban 퍼즐(되돌릴 수 없는 다단계 계획)에서 성공 궤적이 하나도 없었다.
  - TextWorld에서는 방을 다시 돌아다니며 중요한 곳을 놓쳤다. 체계적 탐색이 없다.
  - 논문 시점 NetHack 최고는 o1의 1.57% 진척이었다.
- [논문 arXiv, 2026-09-15] Emergence World는 10개 에이전트 세계 8개를 16일 연속으로 돌렸다(LLM 호출 85만 회 이상, 약 500억 토큰). — [arXiv 2609.17320](https://arxiv.org/abs/2609.17320)
  - 반복되는 도구 오류, 목표 표류, 사적으로는 반대하면서 동조하는 현상이 보고됐다.
  - 위협을 인지하고도 오염된 내용을 영구 기억에 써서 최대 46시간 뒤에 그에 따라 행동했다.
- [논문 AAMAS 2026] 전제조건 DAG로 재귀 분해하면 순차 추론보다 LLM 호출이 크게 줄어든다. 저자들은 오류 전파도 줄어든다고 주장한다. — [AAMAS 2026 PDF](https://ifaamas.org/Proceedings/aamas2026/pdfs/EXAJ9853.pdf)

**기억·회고**
- [논문] PIANO는 작업·단기·장기 기억을 둔다. Action Awareness 모듈은 기대한 결과와 관측한 결과를 비교한다. 이 모듈을 빼면 성능이 크게 떨어져, 환각이 연쇄로 번지는 것을 막는 역할이 확인됐다. — [arXiv 2411.00114](https://arxiv.org/html/2411.00114v1)
- [공식 블로그] PUBG Ally의 시스템 프롬프트는 "툴 결과가 현재 매치의 유일한 진실"이라고 정한다. — [NVIDIA](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)
  - 교사 모델이 "이전 턴을 회상하지 말고 도구로 다시 관측하는 습관"을 시연했고, 학생 모델이 이를 익혔다.
  - 장기 기억(이름, 선호 무기, 매치 기록)은 매치를 넘어 유지된다. 예: 첫 매치에서 Beryl을 찾아 달라고 하면 다음 매치부터 묻지 않아도 찾았다.
- [논문 ICLR 2026] Orak: 반사·계획 모듈은 GPT-4o의 평균 순위를 3.4에서 2.2로 올렸다. LLaMA-3.2-3B는 6.4에서 6.1로 거의 변화가 없었다. 작은 모델은 모듈의 복잡도를 감당하지 못한다. — [arXiv 2506.03610v2](https://arxiv.org/html/2506.03610v2)
- [논문 ICLR 2026] lmgame-Bench: 기억 모듈은 2048 같은 시간적 계획에서 약한 모델일수록 더 큰 도움이 됐다. — [arXiv 2505.15146v2](https://arxiv.org/html/2505.15146v2)
- [논문] Optimus-1은 경험 풀(AMEP)로, JARVIS-1은 멀티모달 기억으로 자기개선한다. — [Optimus-1](https://arxiv.org/abs/2408.03615), [JARVIS-1](https://arxiv.org/abs/2311.05997)

**말과 행동의 일관성**
- [논문] PIANO는 "말과 다른 행동을 한다"는 문제를 정면으로 겨냥한다. Cognitive Controller를 병목으로 두고 결정을 Talking과 Skill 모듈에 함께 방송한다. — [arXiv 2411.00114](https://arxiv.org/html/2411.00114v1)
- [공식 블로그] PUBG Ally는 자동 점검에 "말-행동 일관성"을 넣었다. 프로토콜 준수, 툴 사용과 함께 확인한 뒤 A/B 플레이테스트와 1,000명 이상 실사용자 검증을 거쳤다. — [NVIDIA](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)
- [논문] MineCollab에서 상세 계획을 말로 주고받으면 성능이 최대 약 15% 떨어졌다. 실패 유형: 소통된 계획 오해·무시, 자원 경쟁, 앞선 진척 파괴(완성한 구조물 부수기). — [arXiv 2504.17950](https://arxiv.org/html/2504.17950)
- [논문 ICLR 2025] BALROG의 "knowing-doing gap": 모델은 물어보면 "던전 출구로 나가면 즉사"라고 답하면서 실제 플레이에서는 그 행동을 반복했다. 썩은 음식도 같은 식이었다. — [arXiv 2411.13543v2](https://arxiv.org/html/2411.13543v2)
- [논문 프리프린트] System Switch에서 느린 모델은 상태에 "닫힌 문"으로만 나와 잠겼는지 모르는 문을 두고 25번의 생각 중 17번 "열쇠가 필요하다"고 결론냈다. 부분 관측이 환각을 부른다. — [arXiv 2610.09683](https://arxiv.org/html/2610.09683)

### Inferences
- [추정] 인터럽트 설계는 셋으로 나누면 맞다. 레포의 "즉시 명령, 반사 선점, 두뇌 인계" 규칙과 같은 방향이다.
  - 몸의 모드: Mindcraft처럼 `interrupts` 범위를 선언한다.
  - 두뇌의 빠른 결정: Jev가 재개 또는 교체를 판단한다.
  - 느린 계획: 단일 슬롯 버퍼에 다음 의도만 넣는다.
- [추정] 장기 과제(보스 대비 등)는 frontier 모델에게 맡겨도 숨은 전제조건 조율에서 무너진다는 증거가 반복된다(MineExplorer, BALROG). 전제조건은 코드의 의존성 그래프(craftgraph)가 들고, 모델은 그래프 위에서 무엇을 할지만 고르게 하는 편이 안전하다.
- [추정] 회고와 기억 쓰기는 Emergence World처럼 오염될 수 있다. 사용자에게 들은 사실을 경험으로 검증하는 기존 설계(`told` → verified/refuted)가 이 위험에 대한 직접적인 방어다.
- [추정] PUBG Ally가 "회상하지 말고 다시 관측"을 증류로 심은 것은 Thorkell 플래너 프롬프트에도 그대로 적용할 수 있다. 수치(HP 비율 등)는 매번 관측 도구 값으로 다시 채우게 한다.

### Gaps
- 인터럽트 정책을 서로 비교한 정량 연구(모드 vs LLM 플래그 vs 확신 문)는 Doom 한 편 외에 찾지 못했다.
- 게임 동반자에서 "말-행동 불일치율"을 수치로 보고한 공개 자료는 찾지 못했다. PUBG Ally도 점검 항목만 밝히고 수치는 없다.

## 3. 2026년 기준 게임 벤치마크: 어떤 모델이 앞서고, 소형 오픈 모델은 어떤가, 실패 유형은 무엇인가

### Takeaway
2026-09 BALROG LLM 리더보드에서 최상위 frontier 모델은 평균 60~68%까지 올라왔다. 8B급 오픈 모델은 여전히 8~18%에 머문다. 픽셀만으로 1990년대 게임을 끝까지 하는 과제는 2025년 기준 1% 미만이다. 소형 모델은 zero-shot으로는 거의 0이지만, 좁은 게임에서 미세조정하면 크게 오른다.

### Cited Findings
**BALROG**
- [리더보드, 조회 2026-10-11] LLM 리더보드 상위. — [balrogai.com](https://balrogai.com)
  - 1위 GPT-6-Astra-Max: 평균 68.3%(BabyAI 100%, Crafter 100%, NetHack 65%), 2026-09-18 등록
  - 2위 Claude-Opus-5-Max: 63.4%(NetHack 37.5%), 2026-09-20 등록
  - 3위 GPT-5.6-Sol-Max: 60.0%(NetHack 42.5%)
- [리더보드] 같은 표의 소형 오픈 모델: Llama-3.1-8B 15.1%, Llama-3.2-11B 16.8%, Qwen-2.5-7B 7.8%, Mistral-Nemo(12B) 17.6%. — [balrogai.com](https://balrogai.com)
- [리더보드] VLM 리더보드는 2025-04 이후 갱신되지 않았다. — [balrogai.com](https://balrogai.com)
  - 1위 Gemini-2.5-Pro-Exp-03-25 35.7%, 2위 Claude-3.5-Sonnet 35.5%
  - Qwen2-VL-7B 4.4%, Qwen2-VL-72B 12.2%
- [논문 ICLR 2025] 논문 시점 기록. — [arXiv 2411.13543v2](https://arxiv.org/html/2411.13543v2)
  - NetHack 최고는 o1의 1.57%였다. 리더보드의 NetHack 65%와 차이가 매우 크니 해당 제출의 조건(하네스, 시도 횟수)을 확인해야 한다.
  - 크기별 평균: Llama 3.2 1B 6.65%, 3B 10.13%, 11B 16.82%

**Orak (KRAFTON 등)**
- [논문 ICLR 2026, arXiv v1 2025-06-04 / v3 2026-04-14] 12개 게임을 MCP 기반 플러그앤플레이 인터페이스로 묶었다. — [arXiv 2506.03610v2](https://arxiv.org/html/2506.03610v2), [GitHub krafton-ai/Orak](https://github.com/krafton-ai/Orak)
  - 게임: Street Fighter III, Super Mario, Ace Attorney, Her Story, Pokémon Red, Darkest Dungeon, Minecraft, Stardew Valley, StarCraft II, Slay the Spire, Baba Is You, 2048
  - 평균 순위: Gemini-2.5-pro 3.5, GPT-5·GPT-4o 3.6, o3-mini 4.0, Claude-3.7 5.1, LLaMA-3.3-70B 7.3
  - 가장 작은 오픈 모델은 복잡한 게임에서 거의 0점이었다.
- [논문 ICLR 2026] 전문가 궤적으로 미세조정한 효과. 점수 정의는 게임마다 다르다. — [arXiv 2506.03610v2](https://arxiv.org/html/2506.03610v2)
  - LLaMA-3.2-1B, 학습한 게임 안: Street Fighter III 0.0→42.0, Darkest Dungeon 0.0→93.4
  - LLaMA-3.2-3B, 게임 밖 일반화: Math500 0.0→8.4, WebShop-Hard 0.0→12.6

**lmgame-Bench**
- [논문 ICLR 2026, arXiv 2505.15146] 하네스(지각·기억·추론 모듈) 효과. — [arXiv 2505.15146v2](https://arxiv.org/html/2505.15146v2)
  - 하네스 없이는 Sokoban과 Ace Attorney에서 모델의 75% 이상이 랜덤 수준이었다.
  - 하네스를 켜면 실행의 86.7%가 랜덤 기준을 넘었다.
- [논문 ICLR 2026] 게임 RL의 전이 효과. 같은 출처.
  - Qwen2.5-7B-Instruct를 게임으로 RL(RAGEN)했더니 Blocksworld가 10% 이상, WebShop이 6% 이상 올랐다.
  - 수학(GSM8K)과 코딩(BIRD)으로는 전이되지 않았다.
- [리더보드, 조회 2026-10-11] 평균 정규화 점수. — [HF Space lmgame-Bench](https://lmgame-lmgame-bench.hf.space)
  - o3 66.17, gpt-5-thinking-high 56.63, o1 38.42, grok-4 37.79, gpt-oss-120b 36.14, gpt-oss-20b 35.27, claude-opus-4 35.02
  - 표기된 갱신일은 2025-06-07이다. 그런데 그 뒤에 나온 gpt-5와 gpt-oss가 들어 있어 표기가 실제와 맞지 않는다. 2026년 최신 모델은 없다.

**VideoGameBench**
- [논문 arXiv, v1 2025-05-23 / v3 2026-05-14] 1990년대 게임 10종을 화면과 목표 설명만 주고 실시간으로 플레이한다. — [arXiv 2505.18134](https://arxiv.org/abs/2505.18134v2)
  - 최고 Gemini 2.5 Pro: 실시간 0.48%, 게임을 멈추고 기다리는 Lite 1.6%
  - GPT-4o 0.09%, Claude 3.7 Sonnet 0%
  - 실패 유형: 추론 지연, knowing-doing gap, 공간·시각 오류, 기억 관리
  - 2026년 모델 결과는 찾지 못했다.

**Minecraft 계열**
- [논문 EMNLP 2026] MineExplorer는 앞 절에서 다뤘다. 숨은 전제조건 다단계 과제에서 급락하고, 스케일과 thinking의 이득이 일관되지 않다. — [arXiv 2605.30931](https://arxiv.org/abs/2605.30931)
- [논문 NeurIPS 2025 D&B] MineAnyBuild는 공간 계획 과제 4,000개로 구성된다. MLLM 에이전트는 공간 오해와 "구현 격차(계획은 맞는데 실행이 틀림)"를 보였다. — [arXiv 2505.20148v3](https://arxiv.org/html/2505.20148v3)
- [논문] MineCollab 성공률. — [arXiv 2504.17950](https://arxiv.org/html/2504.17950)

  | 모델 | crafting | cooking | construction |
  |---|---|---|---|
  | Claude 3.5 Sonnet | 0.47 | 0.64 | 0.36 |
  | GPT-4o | 0.17 | 0.40 | 0.31 |
  | LLaMA 3.3-70B | 0.16 | 0.36 | 0.19 |
  | LLaMA 3-8B | 0.00 | 0.01 | 0.00 |
  | LLaMA 3-8B-SFT | 0.28 | 0.18 | 0.20 |

  - 8B-SFT는 LLaMA-70B로 만든 시행 2,000건으로 미세조정했다.
  - 모든 모델이 4~5명 협업에서 무너졌다.

**TextArena**
- [집계, 신뢰도 낮음] 57개 이상의 경쟁형 텍스트 게임을 TrueSkill로 평가한다. — [arXiv 2504.11442](https://alphaxiv.org/abs/2504.11442)
  - 집계 사이트는 "2026-05-29 기준 Balanced Subset 1위 Claude 3.5 Sonnet, 3위 Ministral 8B"라고 전한다. — [benchmarklist.com](https://benchmarklist.com/benchmarks/textarena_balanced_subset/)
  - 원 리더보드를 직접 확인하지 못했고 모델 목록이 오래된 것으로 보여 근거로 쓰기 어렵다.

**소형 typed-decision 모델 (Doom, 프리프린트)**
- [논문 프리프린트, 2026-10-07] 오프라인 결과. — [arXiv 2610.09683](https://arxiv.org/html/2610.09683)
  - zero-shot 정확도는 0.14~0.60이었다.
  - 확신이 낮은 30%를 추론 모델에 넘기면 Laya base(0.4B)가 0.56에서 0.75로 올랐다.
  - 확신으로 실패를 가려내는 능력(AUROC)은 Laya base가 0.89로 가장 좋았다. 가장 정확했던 Kev 9B와 Strands는 0.60~0.61로 확신이 거의 쓸모없었다.
- [논문 프리프린트] 실전(폐루프) 결과. 같은 출처.
  - 33게임 중 출구에 도달한 변형은 없었다.
  - 추론 지연 중앙값은 9~29초였다.
  - 사망 수는 추론을 쓰면 게임당 1.3~2.0, 고정 규칙 대조군은 2.7이었다.
  - 탐색 범위는 고정 "explore" 규칙도 추론과 비슷했다.

### Inferences
- [추정] 8B 이하 오픈 모델을 zero-shot 범용 플래너로 쓰는 안은 증거로 지지되지 않는다(BALROG 8~18%, MineCollab 8B 0~1%, Orak 소형 거의 0). gemini-3.8-flash를 로컬 8B로 바꾸면 계획 품질이 크게 떨어질 가능성이 높다.
- [추정] 반대로 소형 모델은 좁은 결정·좁은 게임에서 미세조정이나 증류를 하면 쓸 만해진다(Orak 1B, MineCollab 8B-SFT, PUBG Ally 2B, Andy-4 8B). Thorkell의 Jev/laya처럼 "닫힌 선택지 + 확률"로 문제를 바꾸는 것이 소형 모델이 이기는 영역이다.
- [추정] 벤치마크가 반복해서 보여 주는 실패 축은 넷이다. Valheim 동반자에게도 그대로 해당한다.
  - 공간 추론
  - 숨은 전제조건이 있는 장기 계획
  - 체계적 탐색
  - 아는 것을 행동으로 옮기기(knowing-doing)

### Gaps
- BALROG 2026-09 상위 제출(GPT-6-Astra-Max 등)의 하네스, 시도 횟수, 검증 여부는 확인하지 못했다. NetHack 65%는 논문 시점보다 수십 배 높은 수치라 재확인이 필요하다.
- Qwen3·Gemma 3/4 같은 2025~2026 소형 모델이 BALROG·Orak·lmgame-Bench에 올라간 결과는 찾지 못했다.
- MCU(Minecraft 자동 평가 벤치마크)의 수치는 수집하지 못했다.
- 수치·단위 오류(예: HP 비율 대신 절대값)를 직접 측정한 게임 벤치마크는 찾지 못했다. 가장 가까운 근거는 lmgame-Bench의 "게임 RL이 수학으로 전이되지 않음"과 BALROG의 knowing-doing gap이다.

## 4. 무엇을 코드·규칙·템플릿으로 대체할 수 있고 무엇에 강한 모델이 필요한가 (구조화 지각 vs 픽셀 포함)

### Takeaway
틱 단위 반응, 전제조건 해소, 진척 판정, 탐색 기본값은 코드가 모델보다 빠르고 정확하다는 증거가 여러 출처에서 겹친다. 강한 모델의 이득은 처음 보는 지시 해석, 다중 모듈 하네스 활용, 개방형 목표 분해에 몰린다. 지각은 구조화 텍스트가 픽셀보다 일관되게 낫다.

### Cited Findings
**코드·규칙이 맡는 부분**
- [공식 블로그] PUBG Ally는 이동·조준·즉각 전투를 행동 트리에 두고, 언어 모델은 의도·협동·발화만 맡는다. — [NVIDIA](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)
- [논문 AAMAS 2026] 전제조건 해소는 DAG 코드가 하고, LLM은 상위 과제만 고른다(상위 과제당 호출 1번). — [AAMAS 2026 PDF](https://ifaamas.org/Proceedings/aamas2026/pdfs/EXAJ9853.pdf)
- [코드] Mindcraft는 생존, 방어, 끼임, 줍기를 규칙 모드로 처리한다. — [`modes.js`](https://github.com/mindcraft-bots/mindcraft/blob/develop/src/agent/modes.js)
- [논문] Voyager는 검증을 통과한 행동을 코드 스킬로 저장해 재사용한다. 다시 계획할 필요를 줄인다. — [arXiv 2305.16291](https://arxiv.org/abs/2305.16291)
- [논문 프리프린트] System Switch에서는 계획을 끝까지 지키는 것(commitment) 자체가 이득의 대부분이었다. 고정 탐색 규칙이 추론 모델과 비슷한 범위를 탐색했다. 다만 사망은 규칙 대조군이 더 많았다(2.7 대 1.3~2.0). — [arXiv 2610.09683](https://arxiv.org/html/2610.09683)
- [논문] PIANO의 Action Awareness는 기대 결과와 관측 결과를 비교하는 단순한 점검이다. 빼면 성능이 크게 떨어진다. — [arXiv 2411.00114](https://arxiv.org/html/2411.00114v1)

**강한 모델이 필요한 부분**
- [논문 ICLR 2026] Orak: 반사·계획 모듈은 GPT-4o에만 이득이고 LLaMA-3.2-3B에는 거의 효과가 없다. 복잡한 하네스를 쓰려면 모델 역량이 필요하다. — [arXiv 2506.03610v2](https://arxiv.org/html/2506.03610v2)
- [논문] PIANO의 문명 시뮬레이션은 GPT-4o 이상이 필요했다. — [arXiv 2411.00114](https://arxiv.org/html/2411.00114v1)
- [논문] MineCollab에서 zero-shot 8B는 거의 0이고 70B·frontier는 0.16~0.64였다. — [arXiv 2504.17950](https://arxiv.org/html/2504.17950)
- [논문 EMNLP 2026] 숨은 전제조건 탐색에서는 큰 모델·thinking도 일관된 이득이 없다. 모델 크기만으로는 풀리지 않는다. — [arXiv 2605.30931](https://arxiv.org/abs/2605.30931)

**소형 모델을 좁은 범위에 맞추기**
- [공식 블로그] PUBG Ally는 범위를 닫고 교사 모델을 2B 학생 모델에 증류했다. — [NVIDIA](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)
- [논문] Orak은 1B 모델을 게임 궤적으로 미세조정했다. — [arXiv 2506.03610v2](https://arxiv.org/html/2506.03610v2)
- [논문] MineCollab은 8B를 SFT했다. — [arXiv 2504.17950](https://arxiv.org/html/2504.17950)
- [모델 카드] Andy-4는 8B를 RTX 3090 한 장으로 학습했다. — [Andy-4](https://huggingface.co/Sweaterdog/Andy-4)

**구조화 지각 vs 픽셀**
- [논문 ICLR 2025] BALROG: 시각 입력을 더하면 대부분 모델의 성능이 떨어졌다. 예외는 Claude 3.5 Sonnet(32.64→35.48%)뿐이었다. — [arXiv 2411.13543v2](https://arxiv.org/html/2411.13543v2)
  - GPT-4o: 32.34 → 22.56%
  - Llama 3.2 90B: 27.29 → 20.99%
- [논문 ICLR 2026] Orak: 텍스트만 넣는 쪽이 이미지만 넣는 쪽보다 크게 앞섰다. — [arXiv 2506.03610v2](https://arxiv.org/html/2506.03610v2)
  - 텍스트와 이미지를 함께 넣는 효과는 엇갈렸다. 액션 게임에는 도움이 됐다.
  - 서사 게임에는 해가 됐다. GPT-4o의 Ace Attorney 점수가 31.8점 떨어졌다.
- [논문 ICLR 2026] lmgame-Bench: 게임 백엔드에서 화면 배치를 텍스트 표로 바꿔 주는 지각 모듈이 Sokoban 같은 공간 과제에서 특히 효과가 컸다. — [arXiv 2505.15146v2](https://arxiv.org/html/2505.15146v2)
- [논문 AAMAS 2026] VLM 관측으로 바꾸면 지연이 늘고 관측 정확도가 약간 떨어졌다. — [AAMAS 2026 PDF](https://ifaamas.org/Proceedings/aamas2026/pdfs/EXAJ9853.pdf)
- [논문] 픽셀만 쓰는 VideoGameBench의 frontier 최고 기록은 0.48%(실시간)다. — [arXiv 2505.18134](https://arxiv.org/abs/2505.18134v2)
- [논문/공식, 이전 조사] 픽셀 범용 에이전트(Lumine, Game-TARS, SIMA 2, NitroGen)는 대규모 학습이 필요하다. 가중치를 공개하지 않았거나 비상업·Windows 전용이다. — [Lumine](https://arxiv.org/abs/2511.08892), [NitroGen](https://nitrogen.minedojo.org/)

### Inferences
- [추정] 정보 동등성을 지키는 구조화 텍스트·JSON 지각은 성능 면에서도 옳은 선택이다. Thorkell처럼 BepInEx로 엔티티 이름, 거리, 인벤토리를 보내는 방식이다. 픽셀 경로는 지연과 정확도 모두 손해다.
- [추정] Thorkell에서 강한 모델이 정말 필요한 곳은 넷으로 좁혀진다.
  1. 처음 보는 자유 발화를 목표로 바꾸기
  2. 수량·우선순위 판단의 근거 고르기. 숫자 자체는 코드가 계산한다.
  3. 실패 회고에서 규칙 후보 뽑기. 오프라인·배치로 한다.
  4. 자기 의제(보스 대비 같은 장기 목표) 고르기. 전제조건은 DAG가 해소한다.
- [추정] 나머지는 코드·템플릿·Jev 계열로 충분하다는 것이 사례들의 공통 결론이다. 반사, 이동, 채집 루프, 전제조건 해소, 진척 판정, 탐색 기본값, 알려진 명령 처리가 여기에 든다.
- [추정] 로컬 소형 모델(M4 Pro 24GB에서 8B Q4 약 6~8GB)은 두 경우에만 대체재가 될 수 있다. "닫힌 선택지 결정"과 "짧은 잡담"이다. 플래너를 대체하려면 PUBG Ally처럼 범위를 닫고 증류 데이터를 만들어야 한다.
  - Valheim 클라이언트 두 개와 메모리를 나눠 써야 한다는 점도 제약이다.

### Gaps
- Valheim이나 비슷한 3D 서바이벌 게임에서 구조화 텍스트와 픽셀을 직접 비교한 연구는 찾지 못했다.
- Andy-4 등 Mindcraft 전용 소형 모델을 frontier 모델과 같은 과제로 비교한 공개 수치는 없다.

## 5. 동반자 봇을 위한 실전 교훈과 Thorkell에 맞는 패턴 (지연 예산, 플래너 호출 빈도, 계획 캐시·템플릿, 계획 검증)

### Takeaway
느린 모델은 "이벤트나 문(gate)이 열릴 때만, 상위 목표당 한 번, 행동이 진행되는 동안 뒤에서" 부른다. 결과는 단일 슬롯에 넣고, 단위와 범위를 코드로 검증한 뒤에만 실행한다. 이것이 2024~2026 사례들이 수렴한 패턴이고, 하루 20회 무료 한도와 수 초~수십 초 지연이라는 Thorkell의 제약과도 맞는다.

### Cited Findings
**지연 예산**
- [공식 블로그] PUBG Ally는 클라우드 왕복 지연이 교신에 너무 느려 전부 로컬로 돌렸다. 블로그는 수백 ms가 교신의 쓸모를 가른다고 서술한다. — [NVIDIA](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)
- [논문 프리프린트] System Switch의 추론 지연은 중앙값 9~29초(최대 32초)였다. 계획이 9~29초 전 프레임에 적용되는 "낡은 정보"가 첫째 실패 원인이었다. — [arXiv 2610.09683](https://arxiv.org/html/2610.09683)
  - 폐루프 성능을 제한한 것은 추론 모델의 품질이 아니라 지연과 관측 가능성이었다.
  - Gemma 4는 600문항 중 199개(33%)에서 4,000토큰 추론 상한 안에 답하지 못했다.
- [논문] Latent Bridge의 느린 모델(8B thinking)은 약 1.5초가 걸렸고, 빠른 모델은 수 ms였다. — [arXiv 2606.24470](https://arxiv.org/abs/2606.24470)
- [논문 AAMAS 2026] 행동이 계획보다 길면 계획 지연은 숨는다. 몇 분짜리 스킬 대 몇 초짜리 추론이다. — [AAMAS 2026 PDF](https://ifaamas.org/Proceedings/aamas2026/pdfs/EXAJ9853.pdf)
- [논문] VideoGameBench는 frontier 모델의 추론 지연을 실시간 설정의 주요 한계로 꼽았다. — [arXiv 2505.18134](https://arxiv.org/abs/2505.18134v2)

**플래너 호출 빈도**
- [공식 블로그] PUBG Ally는 이벤트 구동으로, 발화나 게임 이벤트가 있을 때만 SLM을 부른다. — [NVIDIA](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)
- [논문 프리프린트] System Switch는 문 다섯 가지로 호출한다(Unsure, Stuck, Blocked, Loop, Novelty). 확신 문이 무작위로 넘기는 것보다 나은 것은 행위자의 확신이 "틀릴 답"이 아니라 "실패할 상황의 종류"를 가려낼 때뿐이다. 오프라인 이득과 AUROC의 순위 상관은 0.87이었다. — [arXiv 2610.09683](https://arxiv.org/html/2610.09683)
- [논문 AAMAS 2026] DAG 분해로 상위 과제당 LLM 호출이 1번이다. — [AAMAS 2026 PDF](https://ifaamas.org/Proceedings/aamas2026/pdfs/EXAJ9853.pdf)
- [논문] MineCollab의 대화 관리자는 환경 행동이 끝날 수 있도록 에이전트 응답을 늦춘다. — [arXiv 2504.17950](https://arxiv.org/html/2504.17950)

**계획 캐시·템플릿**
- [논문] Voyager는 검증된 스킬 코드를 라이브러리에 저장하고 검색해 재사용한다. — [arXiv 2305.16291](https://arxiv.org/abs/2305.16291)
- [논문 AAMAS 2026] 새 스킬은 전제조건 DAG를 갱신하는 것만으로 추가된다. — [AAMAS 2026 PDF](https://ifaamas.org/Proceedings/aamas2026/pdfs/EXAJ9853.pdf)
- [공식 블로그] PUBG Ally는 고정 아이템 분류와 "큐레이션한 무기·부착물·아이템·규칙 사전"을 툴 결과로 준다. 프롬프트 앞부분을 고정해 KV 캐시를 재사용한다. — [NVIDIA](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)
- [논문] MineCollab은 임베딩 유사도로 few-shot 예시를 검색한다(RAG). — [arXiv 2504.17950](https://arxiv.org/html/2504.17950)

**계획 검증**
- [공식 블로그] PUBG Ally는 출시 전에 자동 점검(프로토콜 준수, 툴 사용, 말-행동 일관성), A/B 플레이테스트, 1,000명 이상 실사용자 검증을 거쳤다. 팀의 조언: "빠른 프로토타입을 많은 실사용자 앞에 놓고 반복하라." — [NVIDIA](https://developer.nvidia.com/blog/how-krafton-built-pubg-ally-a-co-playable-character-powered-by-nvidia-ace/)
- [논문] Voyager의 자기검증과 PIANO의 Action Awareness는 진척을 관측으로 확인한다. — [Voyager](https://arxiv.org/abs/2305.16291), [PIANO](https://arxiv.org/html/2411.00114v1)
- [논문 프리프린트] 부분 관측 상태(문이 잠겼는지 모름)에서 느린 모델은 그럴듯한 전제("열쇠가 필요")를 지어냈다. 일반 지식을 주면 맵이 다른데도 과하게 적용했다. — [arXiv 2610.09683](https://arxiv.org/html/2610.09683)

### Inferences
- [추정] Thorkell에 맞는 패턴 목록. 근거는 위 인용들이다.

  | 패턴 | 출처 | Thorkell 적용 |
  |---|---|---|
  | S1 행동 트리 / S2 이벤트 구동 모델 | PUBG Ally | Body 반사·스킬 + 이벤트 때만 플래너 |
  | 단일 슬롯 의도 버퍼 | AAMAS'26 | 최신 계획만 유지. interrupt는 몸·Jev가 판단 |
  | DAG 재귀 분해 | AAMAS'26, GITM | craftgraph가 전제조건 해소. 상위 목표당 플래너 1회 |
  | 검증된 스킬 템플릿 우선 | Voyager | 아는 명령은 즉시 스킬. 성공한 계획은 (목표, 상황 요약) 키로 캐시 |
  | 문(gate) 기반 호출 | System Switch | stuck / blocked / loop / novelty / 낮은 확신일 때만 플래너 |
  | 결정 병목 + 행동 인식 | PIANO | 말은 단일 Decision 기록에서만. 진척은 월드 변화로 |
  | 관측 도구가 유일한 진실 | PUBG Ally | 플래너 출력의 수치는 관측값으로 다시 채우고 단위를 검증 |
  | 구조화 텍스트 지각 | BALROG, Orak, lmgame-Bench | 현행 유지. 픽셀 경로는 추가하지 않음 |

- [추정] 지난번 단위 사고(`hp_below` 10.0)는 두 겹으로 막는 게 맞다. 위 증거(knowing-doing gap, 부분 관측 환각, 수학 비전이)를 보면 모델은 숫자와 단위를 안정적으로 지키지 못한다.
  - 스키마 단계: 비율 필드는 0~1 타입으로 강제한다(기존 검증기와 같은 방향).
  - 해석 단계: "체력 X% 이하" 같은 조건은 모델이 숫자를 내지 않고 열거형 수준(low/critical)만 고르게 한다. 숫자는 코드가 매핑한다.
- [추정] 하루 20회 무료 한도 계산. 근거는 문 기반 호출, 템플릿 우선, 실패 시 재시도를 1회로 제한하는 설정이다.
  - 처음 보는 발화: 세션당 수 회
  - 실패·정체 회고: 세션당 1~3회
  - 자기 의제 갱신: 하루 1~2회
  - 이렇게 하면 한 세션(1~2시간)을 20회 안에 맞출 수 있다. 이 수치는 실측이 아니라 설계 목표다.
- [추정] 지연 대책: 플래너가 수 초~수십 초 걸리는 동안 몸은 계속 행동하고, 결과가 오면 그때의 관측으로 다시 검증한다. System Switch의 낡은 정보 실패가 이 단계를 거치는 이유다.
  - 행동 중에는 "생각 중" 같은 비언어 신호나 짧은 발화를 Live 층이 낸다.
  - 결과가 도착했을 때 전제가 바뀌었으면(대상이 사라짐, HP 급변) 버린다.
- [추정] 강한 모델이 정말 필요한 범위는 4절의 네 가지다. 그중 회고와 자기 의제는 실시간이 아니므로 하루 한도 안에서 배치로 몰아 처리할 수 있다.

### Gaps
- 게임 동반자에서 "플래너 호출 빈도 대 사용자 만족"을 수치로 보고한 공개 자료는 찾지 못했다. PUBG Ally도 빈도를 밝히지 않았다.
- 계획 캐시의 적중률이나 재사용률을 게임 에이전트에서 측정한 공개 수치는 찾지 못했다. Voyager는 스킬 재사용의 효과를 전체 성능으로만 보고한다.
- 하루 호출 수 추정은 Thorkell 실사용 로그로 확인해야 한다. 이 노트의 숫자는 설계 가정이다.
