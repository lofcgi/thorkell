# 범용 게임 에이전트·게임 파운데이션 모델·월드 모델 (2026-10-17 갱신)

조사일: 2026-10-17. 기준선은 `../게임 플레이 AI 기술 동향 2026/game_foundation_models.md`(2026-10-10 기준, 2026-10-11 작성)다.

표기
- 갱신 상태: **[unchanged]** 기준선과 같음 / **[changed]** 상태가 바뀜 / **[new]** 기준선에 없던 항목(기준선이 놓친 2026 상반기 항목 포함) / **[corrected]** 기준선의 사실이나 빈칸을 고침
- 출처 종류: [공식] 논문·모델 카드·공식 레포·연구실 블로그 / [보도] 언론 / [커뮤니티] 개인 레포·블로그 / [추정] 이 노트 작성자의 판단
- 1차 자료 확인 방법: arXiv 초록 페이지와 API, Hugging Face API(`/api/models`, 모델 카드 원문, LICENSE 원문), GitHub API(`gh api`)를 2026-10-17에 직접 조회했다. 웹 검색 요약만으로 확인한 것은 그렇다고 적었다.
- 주의: 일반 웹 검색 색인은 최근 몇 주를 잘 반영하지 못했다. "발표를 찾지 못했다"는 결론은 arXiv·HF·GitHub 직접 조회와 웹 검색을 함께 해서 내렸지만, 블로그만으로 나온 발표는 놓쳤을 수 있다.

## 1. 범용 게임 에이전트의 현재 상태: SIMA 2, Lumine, Game-TARS, NitroGen, Open-P2P와 2026-09~10 신규

### Takeaway
기준선 이후 닫힌 대형 에이전트(SIMA 2, Game-TARS, Lumine)는 그대로 비공개다. 새로 나온 것은 세 갈래다.
- 공개 VLM을 게임 조작으로 후학습: Tencent ARC의 **Player-1**(9B·35B-A3B, 2026-10-14, 가중치는 "준비 중")
- 월드-액션 모델: **GameWAM**(6B, 가중치 공개)
- **API·도구 기반 동료 에이전트**: 실서비스에 들어간 **PUBG Ally**(2B 온디바이스 SLM + 행동 트리), Gemini 4 Argon 4개 팀이 Mineflayer로 Minecraft 엔딩까지 간 결과

픽셀로 처음 보는 3D 게임을 잘 하는 공개 모델은 여전히 없다. 2026-10 벤치마크(PlaySuite, GameBoyWorlds)도 "지각-행동 격차"를 다시 확인했다.

### Cited Findings

**기준선 항목 재확인**

- **SIMA 2 [unchanged]** (재확인 2026-10-17)
  - [공식] 블로그는 여전히 "limited research preview"이고 "small cohort of academics and game developers"에게만 조기 접근을 준다. 2025-11-13 이후 갱신 문구, 신청 경로, API는 없다. — [DeepMind blog](https://deepmind.google/blog/sima-2-an-agent-that-plays-reasons-and-learns-with-you-in-virtual-3d-worlds/)
  - [공식] arXiv 2512.04797은 v1(2025-12-04)뿐이다. — [arXiv 2512.04797](https://arxiv.org/abs/2512.04797)
  - [보도] 2026-09~10 기간의 SIMA 관련 발표(SIMA 3 포함)는 웹 검색에서 찾지 못했다. — [TechCrunch 2025-11-13](https://techcrunch.com/2025/11/13/googles-sima-2-agent-uses-gemini-to-reason-and-act-in-virtual-worlds/)
  - [공식][보충] 블로그 감사의 글의 파트너 게임 목록이 기준선의 학습 환경 목록보다 넓다. Valheim, Satisfactory, Goat Simulator 3, Hydroneer, No Man's Sky, Space Engineers, Wobbly Life, Eco, ASKA, The Gunk, SteamWorld Build, Road 96, Teardown이다. — [DeepMind blog](https://deepmind.google/blog/sima-2-an-agent-that-plays-reasons-and-learns-with-you-in-virtual-3d-worlds/)
- **Game-TARS [unchanged]** (재확인 2026-10-17)
  - [공식] arXiv 2510.23691은 v1(2025-10-27)뿐이다. — [arXiv 2510.23691](https://arxiv.org/abs/2510.23691)
  - [공식] 가중치와 코드 공개는 없다. 근거는 다음과 같다.
    - ByteDance-Seed의 HF 모델 목록과 GitHub 조직 목록에 Game-TARS가 없다. — [HF ByteDance-Seed](https://huggingface.co/ByteDance-Seed), [GitHub ByteDance-Seed](https://github.com/ByteDance-Seed)
    - UI-TARS-2 가중치도 없다. HF에 있는 것은 UI-TARS-1.5-7B(Apache 2.0)와 UI-TARS-2B-SFT 계열뿐이다. — [HF UI-TARS-1.5-7B](https://huggingface.co/ByteDance-Seed/UI-TARS-1.5-7B)
- **Lumine [changed: 공식 공개는 없고 커뮤니티 재현 시도만 생김]**
  - [공식] 프로젝트 페이지에는 기술 보고서 링크만 있다. 가중치, 코드, 데이터 공개 문구와 GitHub·HF 링크가 없다. arXiv는 v1(2025-11-12)뿐이다. — [lumine-ai.org](https://www.lumine-ai.org/), [arXiv 2511.08892](https://arxiv.org/abs/2511.08892)
  - [커뮤니티] 재현 시도가 있다.
    - `koboshchan/Lumine`: 설명이 "Attempt to recreate Lumine"이다. 2026-02-18에 만들었고, 마지막 push는 2026-03-10이다. — [GitHub koboshchan/Lumine](https://github.com/koboshchan/Lumine)
    - 같은 저자가 7B 체크포인트를 MIT로 올렸다(2026-02~03). 원신 플레이 데이터셋을 쓴다. — [HF koboshchan/Lumine-Agent-Pretrain-VL-7B](https://huggingface.co/koboshchan/Lumine-Agent-Pretrain-VL-7B)
    - AntimLabs는 이름만 빌린 다른 시도를 올렸다. Qwen3.5-2B 기반 "Lumine" LoRA·IFT(2026-03~04)와, Elden Ring용 Pi0.5식 flow-matching 행동 디코더 `Pi-Lumine-4B`(Qwen3.5-4B 동결, 학습 파라미터 약 64M, 패드 20차원 × 6스텝, Apache 2.0)다. — [HF AntimLabs/Pi-Lumine-4B-FlowMatching](https://huggingface.co/AntimLabs/Pi-Lumine-4B-FlowMatching)
    - 이 재현물들의 성능 보고는 찾지 못했다.
- **NitroGen [corrected: 라이선스 원문 확인] [changed: 생태계]**
  - [공식] HF `LICENSE` 원문(2026-10-17 열람)은 "NVIDIA License"다. 3.3조 원문: "The Work and any derivative works thereof only may be used or intended for use non-commercially … for non-commercial research purposes only." 따라서 **비상업 연구 전용**이 원문으로 확인됐다. 기준선에서는 미확인이었다. 파생물에도 같은 제한이 붙는다(3.2조). — [HF nvidia/NitroGen LICENSE](https://huggingface.co/nvidia/NitroGen/blob/main/LICENSE)
  - [공식] 라이선스 표기는 층마다 다르다. 논문 문서는 CC BY-SA 4.0이고, GitHub 레포 라이선스 필드는 NOASSERTION이다. — [arXiv 2601.02427](https://arxiv.org/abs/2601.02427), [GitHub MineDojo/NitroGen](https://github.com/MineDojo/NitroGen)
  - [공식] 공식 갱신은 없다. HF 마지막 수정은 2026-02-05, GitHub 마지막 push는 2026-01-25, arXiv는 v1(2026-01-04)뿐이다. — [HF nvidia/NitroGen](https://huggingface.co/nvidia/NitroGen)
  - [커뮤니티] 미세조정본이 생겼다: Sonic 3(2026-07), Pizza Tower(2026-03). — [HF BotGoesBrrr/nitrogen-sonic3-ft](https://huggingface.co/BotGoesBrrr/nitrogen-sonic3-ft), [HF subbonan/nitrogen-pizza-tower-finetune](https://huggingface.co/subbonan/nitrogen-pizza-tower-finetune)
  - [커뮤니티] FP8/NVFP4 양자화 ONNX(DiT 약 466MB, 2026-06)도 올라왔다. NVIDIA GPU용이며, 같은 NVIDIA 라이선스를 따른다고 적혀 있다. — [HF syseeker-at-nv/nitrogen-quant](https://huggingface.co/syseeker-at-nv/nitrogen-quant)
- **Open-P2P [unchanged]** (재확인 2026-10-17)
  - [공식] 갱신이 없다. HF `elefantai/open-p2p`(MIT)의 마지막 수정은 2026-01-10이고, GitHub(MIT)의 마지막 push는 2026-02-06이다. Elefant AI가 HF에 올린 다른 모델은 없다. — [HF elefantai/open-p2p](https://huggingface.co/elefantai/open-p2p), [GitHub elefant-ai/open-p2p](https://github.com/elefant-ai/open-p2p)
  - [공식] 실시간 플레이는 Windows와 Recap이 필요하다. 문서는 GPU 2장 구성이나 Moonlight 스트리밍으로 게임 PC와 추론 PC를 나누는 대안을 제시한다. 요구사항은 "< 50 ms" 종단 지연이다. 학습과 오프라인 추론은 Linux에서 한다. — [GitHub README](https://github.com/elefant-ai/open-p2p)
  - [공식] arXiv의 논문 문서 라이선스는 여전히 CC BY-NC-ND 4.0이다. 마지막 버전은 2026-01-28이다. — [arXiv 2601.04575](https://arxiv.org/abs/2601.04575)
- **JARVIS-VLA [corrected: 라이선스]**
  - [공식] HF 카드 라이선스는 MIT다. 기준선에서는 "확인 못 함"이었다. 반면 GitHub 레포에는 라이선스 필드가 없다. — [HF CraftJarvis/JarvisVLA-Qwen2-VL-7B](https://huggingface.co/CraftJarvis/JarvisVLA-Qwen2-VL-7B), [GitHub CraftJarvis/JarvisVLA](https://github.com/CraftJarvis/JarvisVLA)
  - [커뮤니티] GGUF 양자화본이 있다(2026-08-24). — [HF mradermacher/JarvisVLA-Qwen2-VL-7B-GGUF](https://huggingface.co/mradermacher/JarvisVLA-Qwen2-VL-7B-GGUF)
- **ROCKET-3 [new: 기준선 누락, 2025 논문]**
  - [공식] Minecraft에서 크로스뷰 목표로 조건화한 다중 과제 RL 시각운동 정책이다.
  - 체크포인트는 약 750MB이고 MIT다. HF 저장소는 2025-10-24에 만들었고 카드는 2026-09-28에 갱신했다.
  - 카드는 "zero-shot transfer to unseen 3D environments"를 연구 주제로 든다. — [HF CraftJarvis/ROCKET-3-1.5x](https://huggingface.co/CraftJarvis/ROCKET-3-1.5x), [arXiv 2507.23698](https://arxiv.org/abs/2507.23698)

**2026-09-01 ~ 2026-10-17 신규 에이전트**

- **Player-1 (Tencent ARC 외, arXiv 2610.20584, 2026-10-14) [new]**
  - [공식] 학습 방식: 컴퓨터 사용 모델을 게임 궤적 6,044개로 SFT한 뒤, 합성 2D/3D 환경 16종(Player-1-Gym, 검증 가능한 보상)에서 PPO로 학습한다. — [arXiv 2610.20584](https://arxiv.org/abs/2610.20584)
  - [공식] 백본과 학습 비용:
    - Player-1-9B는 Qwen3.5-9B, Player-1-35B-A3B는 Qwen3.5-35B-A3B에서 시작했다.
    - 행동 공간은 상대 포인터 이동, 지속 입력, 복합 입력을 추가했다. 제어 스텝은 200ms 격자다.
    - SFT는 H200 32장으로 약 24시간, RL 200스텝은 H200 64장으로 약 36시간 걸렸다. — [arXiv HTML](https://arxiv.org/html/2610.20584v1)
  - [공식] 결과:

    | 벤치마크 | Player-1-35B-A3B | Player-1-9B | 비교 대상 |
    |---|---|---|---|
    | MineDojo-300 성공률 | 41.04% | 38.33% | GameWAM 12.63%, JARVIS-VLA 6.71% |
    | ViZDoom-10 | 0.7236 | 0.6922 | — |
    | GameWorld 성공/진척 | 17.25% / 38.79% | — | NitroGen 8.82% / 23.41% |

    처음 보는 상용 3D 게임은 **Watch Dogs 2 정성 사례만** 있고 수치가 없다. — [arXiv HTML](https://arxiv.org/html/2610.20584v1)
  - [공식] 공개 상태:
    - GitHub 레포는 MIT이고 2026-10-10에 만들었다.
    - 릴리스 계획에 "Model checkpoints: Player-1-9B and Player-1-35B-A3B"가 **체크되지 않은 채** 남아 있다. 즉 2026-10-17 현재 가중치는 미공개다.
    - 추론 하드웨어와 지연은 본문에 없다. — [GitHub TencentARC/Player-1](https://github.com/TencentARC/Player-1), [project page](https://player-1-project.github.io/)
- **GameWAM (arXiv 2608.26200, v1 2026-08-25, v2 2026-09-10) [new]**
  - [공식] 미래 영상과 키보드·마우스 궤적을 함께 생성하는 "world action model"이다. "block-cycle control"로 동작한다. — [arXiv 2608.26200](https://arxiv.org/abs/2608.26200)
  - [공식] 가중치는 Apache 2.0(2026-09-09)이다.
    - 구성: Wan2.2-TI2V-5B 비디오 전문가 5.0B + ActionDiT 행동 전문가 1.0B.
    - Minecraft와 ViZDoom 체크포인트가 각 12.2GB다. 학습에 H200 8장을 썼다.
    - 16스텝을 예측하고 8스텝을 실행한다.
    - **픽셀 외에 구조화 상태도 입력으로 받는다.** Minecraft는 15차원, ViZDoom은 위치·각도·체력 4차원이다. — [HF yunncheng/gamewam-models](https://huggingface.co/yunncheng/gamewam-models), [GitHub yunncheng/GameWAM](https://github.com/yunncheng/GameWAM)
- **PUBG Ally / Ally Duo (KRAFTON, arXiv 2609.29837, v1 2026-09-24, v2 2026-09-25) [new]**
  - [공식] 구조:
    - System 2: 온디바이스 2B 학생 모델이다. 영어는 Mistral-NeMo-Minitron-2B, 한국어는 kanana-1.5-2.1b, 중국어는 Qwen3-1.7B를 쓴다.
    - 교사와 증류: Gemma 4 31B 교사(GEPA로 프롬프트 최적화)가 데이터를 만들고, 8B 중간 교사를 거쳐 2B로 증류했다.
    - System 1: 매 틱 평가하는 행동 트리다. 이동, 전투, 복구를 맡고 우선순위 선점을 한다.
    - 게임 접근: 픽셀이 아니라 도구 16개로 한다(관찰 7, 지식·기억 2, 행동 실행 2, 말하기 3, 루프 제어 1, 안전 1).
    - 컨텍스트 예산은 약 5,000토큰이다. — [arXiv HTML v2](https://arxiv.org/html/2609.29837v2)
  - [공식] 성능과 운영:
    - 음성 한 번 주고받기: 온디바이스 약 1.6초, 클라우드 구성 약 3.4초.
    - 요구 사양: VRAM 8GB 이상 소비자 GPU, 언어 모델 추론은 한 번에 하나.
    - 데이터: 세션 38,956개를 실사용자 데이터로 반복 학습했다.
    - 추천 순응답: +25.1%p.
    - 운영에서 배운 것: 자발적 발화가 너무 잦으면 플레이를 방해해서 쿨다운을 넣었다. — [arXiv HTML v2](https://arxiv.org/html/2609.29837v2)
  - [보도] 배포:
    - 2026-06-17 PC 업데이트 42.1로 2인 아케이드 모드 "Ally Duo" 베타가 열렸다(캐릭터 이름 Ella, 맵 Sanhok). 종료일은 6-30과 7-1로 보도가 엇갈린다.
    - NVIDIA ACE 기반 온디바이스 SLM을 쓰고, 음성 인식은 NVIDIA Parakeet, 음성 합성은 KRAFTON 자체 TTS다.
    - **RTX GPU 전용**이다. — [Seoul Economic Daily 2026-06-17](https://en.sedaily.com/technology/2026/06/17/krafton-unveils-ally-duo-mode-to-play-pubg-with-ai-teammate), [TweakTown](https://www.tweaktown.com/news/112250/pubgs-new-ally-duo-game-mode-pairs-you-with-an-ai-teammate-powered-by-nvidia-ace/index.html), [allthings.how](https://allthings.how/pubg-ally-duo-how-to-play-with-ella-the-rtx-only-ai-teammate/) (웹 검색 요약으로 확인)
- **"A team of Gemini 4 Argon agents beats Minecraft" (arXiv 2610.22319, 2026-10-15) [new]**
  - [공식] Gemini 4 Argon 에이전트 4개가 Mineflayer(JavaScript API)로 플레이했다.
    - 픽셀 입력은 쓰지 않았다. 원문은 "Rather than seeing pixels or pressing keys, an agent acts by writing and running a short JavaScript program"이다.
    - 게임 내 채팅(승리 전 229건)과 공유 메모리로 협업했다.
    - Easy 난이도에서 27시간 14분 만에 엔더 드래곤을 잡았다. 프로그램 2,783개를 썼고, 605번 죽었다.
  - [공식] 비용과 한계:
    - 모델 호출 약 24,000회, 입력 약 13.5억 토큰(91% 캐시), 출력 약 1,600만 토큰.
    - 비용은 출시 할인가로 약 520달러, 정가로 약 1,040달러라고 추정했다.
    - 프로그램 실행 시간의 중앙값은 33.5초다.
    - 저자들은 Mineflayer가 사람이 못 보는 정보(바위 뒤 블록, 드래곤 내부 상태)를 준다는 점, 1회 실행이라는 점을 한계로 밝혔다. — [arXiv HTML](https://arxiv.org/html/2610.22319v1)
  - [보도] Gemini 4 Argon은 2026-09-30에 발표된 유료 API 모델이다. 가격은 보도마다 다르다. — [HPCwire 2026-10-14](https://www.hpcwire.com/bigdatawire/2026/10/14/gemini-4-argon-arrives-with-big-claims-for-ai-agents-and-scientific-discovery/), [Gemini API docs](https://ai.google.dev/gemini-api/docs/models/gemini-4-argon)
- **EvolvingBrain (arXiv 2610.20786, 2026-10-14) [new]**
  - [공식] 궤적에서 Domain, Plan, Action/Trap 스킬을 계층으로 뽑아 자기진화한다. VAB-Minecraft와 DiscoveryWorld에서 성공률이 올랐다.
  - 코드는 camera-ready 때 공개할 예정이다. — [arXiv 2610.20786](https://arxiv.org/abs/2610.20786)

**벤치마크와 설계 근거 (2026-06~10)**

- [공식] **PlaySuite** (arXiv 2610.07127, 2026-10-05, CC BY 4.0)
  - itch.io와 PyWeek의 오픈소스 게임 5천 종 이상에서 공개 모델 14개를 평가했다.
  - 최고 무기억 점수가 0~4 척도에서 0.84(itch.io, Qwen3-Omni-30B-A3B)였다. UI-TARS-1.5-7B는 0.71이었다.
  - 논문은 이를 "perception-action gap"이라고 부른다.
  - 게임을 멈추고 평가했으며, 상호작용은 0.33Hz였다. 실시간 반응은 재지 않았다. NitroGen과 Open-P2P는 평가 대상이 아니다. — [arXiv 2610.07127](https://arxiv.org/abs/2610.07127), [HTML](https://arxiv.org/html/2610.07127v1)
- [공식] **GameBoyWorlds** (arXiv 2609.32093, 2026-09-25)
  - 프런티어 모델이 처음 보는 게임 과제 500개 중 50% 미만을 끝냈다.
  - 팬메이드 포켓몬 두 작품에서는 첫 주요 마일스톤에도 도달하지 못했다. — [arXiv 2609.32093](https://arxiv.org/abs/2609.32093)
- [공식] **SpeedrunBench** (arXiv 2610.08076, 2026-10-06)
  - 단순 플랫포머에서는 세계기록에 근접했지만, 길고 복잡한 게임에서는 사람에게 뒤졌다. — [arXiv 2610.08076](https://arxiv.org/abs/2610.08076)
- [공식] **The Latent Bridge** (arXiv 2606.24470, 2026-06-23) [new: 기준선 누락]
  - 추론형 VLM인 Qwen3-VL-8B-Thinking은 응답 하나에 약 1.5초가 걸려 15Hz 제어 루프에 못 들어간다.
  - 그래서 반응형 9B 모델(MiniCPM-o 4.5)과 묶고, 두 모델 사이 채널만 학습했다.
  - 학습한 latent 채널은 텍스트 채널보다 같거나 나았다(MsPacman +57%).
  - "느린 추론이 빠른 반응보다 이미 나을 때만" 도움이 된다(r=0.93). — [arXiv 2606.24470](https://arxiv.org/abs/2606.24470)
- [공식] **GPTNT** (arXiv 2606.28514, TMLR 2026-09-02 채택)
  - Keep Talking and Nobody Explodes에서 정보가 비대칭인 두 에이전트가 실시간·비동기로 소통하며 협업하는 벤치마크다. — [arXiv 2606.28514](https://arxiv.org/abs/2606.28514)
- [공식] **AAArena** (arXiv 2610.12341, 2026-10-08)
  - 에이전트가 게임 정책 코드를 고쳐 가며 경쟁한다. "Opus5.5 with Claude Code"가 12종 중 6종에서 금메달을 받았다. — [arXiv 2610.12341](https://arxiv.org/abs/2610.12341)
- [공식] **Compiled Agency [changed: 제목·내용 개정]**
  - v2(2026-09-26)에서 제목이 "Compiled Agency: Coding Agents as Game AI Researchers -- from a Roguelike to StarCraft II and Civilization"으로 바뀌었다.
  - develop-freeze-evaluate 프로토콜 "Gauntlet"을 도입했다.
  - 환경에 접근할 수 있으면 홀드아웃 성공률이 10~78%p 오른다고 보고했다. — [arXiv 2609.18996](https://arxiv.org/abs/2609.18996)
- [공식] **OmniGameArena(2606.09826)와 GameWorld(2604.07429) [unchanged]**: 둘 다 v1 그대로다(재확인 2026-10-17). — [arXiv 2606.09826](https://arxiv.org/abs/2606.09826), [arXiv 2604.07429](https://arxiv.org/abs/2604.07429)
- [공식] **AI for Games in the Foundation Model Era** (서베이, arXiv 2609.16679, 2026-09-15, 120쪽)
  - 제어 방식, 규칙, 엔진 인터페이스, 상태 표현이 게임마다 달라서 전이가 제한적이라고 정리했다. — [arXiv 2609.16679](https://arxiv.org/abs/2609.16679)

### Inferences
- [추정] 2026-09~10의 가장 큰 변화는 "픽셀 범용 에이전트"보다 **"도구·상태 API + 결정적 하위 제어 + 작은 온디바이스 모델" 구조가 상용 동료 AI로 검증된 것**이다(PUBG Ally). Thorkell의 Body(구조화 지각·결정적 반사)와 Brain(빠른 결정 + 드문 플래너) 분리와 같은 구조다.
- [추정] PUBG Ally의 증류 경로(대형 교사 → 8B → 2B, 실사용 로그로 반복 학습)는 Thorkell이 Jev/laya를 쓰는 방식에 바로 참고할 수 있다.
  - Gemini 플래너 출력과 실게임 로그로 작은 결정 모델을 미세조정하면 하루 20회 한도의 영향을 줄일 수 있다.
  - 다만 PUBG Ally의 지연 수치(음성 1.6초)는 RTX GPU 기준이다. M4 Pro에서 Valheim 두 개와 같이 돌릴 때의 값은 아니다.
- [추정] Gemini 4 Argon Minecraft 결과는 장기 과제를 코드와 API로 풀 수 있다는 증거다. 다만 Thorkell 제약에는 두 가지가 맞지 않는다.
  - 호출 약 24,000회는 무료 등급 하루 20회와 세 자릿수 이상 차이 난다.
  - Mineflayer는 바위 뒤 블록까지 보여 준다. Thorkell은 하드 규칙 5(정보 동등성)로 이런 정보를 막고 있으므로 결과를 그대로 옮길 수 없다.
- [추정] Player-1은 공개 VLM(Qwen3.5) 기반이라 가중치가 나오면 맥에서 양자화해 볼 수 있는 첫 "게임 조작 특화" 9B가 될 수 있다. 그래도 MineDojo-300 38%이고 Valheim 결과가 없으며 출력이 키·마우스다. Thorkell의 타입 결과 코드 체계를 우회하므로 실행 경로 후보는 아니다.

### Gaps
- Player-1 가중치 공개 날짜, 추론 지연, 하드웨어 요구는 확인하지 못했다(레포에 "preparing"만 있음).
- PUBG Ally 본문의 System 1 틱 주기(Hz)와 ASR·TTS 모델명(부록 H)을 읽지 못했다. 보도는 Parakeet과 자체 TTS라고 했다.
- GameWAM의 추론 지연, 하드웨어, 처음 보는 게임 성능은 초록과 카드에 없다.
- Optimus-3, UI-TARS-2, Game-TARS의 공개 여부를 HF·GitHub 외 경로(신청 양식, 기업 API)로는 확인하지 못했다.
- Gemini 4 Argon의 정식 가격과 무료 등급 여부는 보도마다 다르다. 이 노트의 범위 밖이다.

## 2. 월드 모델: 소비자 하드웨어에서 에이전트 학습·계획에 쓸 수 있는가

### Takeaway
2026-09~10에 **NVIDIA 소비자 GPU에서 실시간으로 도는 공개 월드 모델이 크게 늘었다.**
- Matrix-Game 4.0: RTX 5070 Ti에서 58 FPS
- Waypoint-1.5: RTX 30 시리즈 이상
- MIRA: GPU 1장에서 20 FPS
- Zing-0.5, Astronex-World, SolarWM, WorldPlay2, Multics

하지만 대부분 **콘텐츠 생성기나 뉴럴 렌더러**다. Valheim 같은 특정 게임의 규칙을 정확히 흉내 내는 시뮬레이터가 아니다. 에이전트 학습에 쓴 사례는 구조화 상태 월드 모델(MOBA Dyna 루프)과 연구실 단위(Dreamer 4, SIMA 2 + Genie 3)에 머문다. Genie 3과 Project Genie는 새 발표를 찾지 못했다.

### Cited Findings

**기준선 항목 재확인**
- **Genie 3 / Project Genie [unchanged]**
  - [보도] 2026-09~10 사이 Genie 새 버전이나 API 발표를 찾지 못했다.
  - 마지막 확인 사항은 2026-01-29 Ultra 구독자 공개와 2026-05 글로벌 확대(출처 하나)다.
  - "2026-09 프리뷰"를 언급한 블로그가 하나 있지만 날짜 메타데이터가 서로 맞지 않아 신뢰하기 어렵다. — [AI Stack Current, 2026-09-01 갱신](https://www.aistackcurrent.com/models/genie-3/), [buildmind.ai](https://buildmind.ai/blog/project-genie-infinite-interactive-worlds-2026/)
- **Muse / WHAM [unchanged]**
  - [보도] 2026년 새 버전은 찾지 못했다. HF `microsoft/wham`의 마지막 수정은 2025-12-17이다. — [HF microsoft/wham](https://huggingface.co/microsoft/wham), [the-decoder](https://the-decoder.com/microsofts-new-ai-model-muse-can-generate-gameplay-and-might-preserve-classic-games/)
- **Matrix-Game 3.0 [corrected]**
  - [공식] 가중치 라이선스는 HF에서 Apache 2.0이다. 레포 코드는 MIT다. 기준선은 MIT로만 적었다. — [HF Skywork/Matrix-Game-3.0](https://huggingface.co/Skywork/Matrix-Game-3.0), [GitHub SkyworkAI/Matrix-Game](https://github.com/SkyworkAI/Matrix-Game)
  - [커뮤니티] 기준선의 GPU 사양 빈칸: MLX 이식본 README는 원본이 A100/H100에서 Flash Attention, 다중 GPU 병렬(8장, Ulysses), DMD로 40fps를 낸다고 적었다. — [GitHub dgrauet/Matrix-Game-mlx](https://github.com/dgrauet/Matrix-Game-mlx)
- **Dreamer 4 [unchanged + 보충]**
  - [커뮤니티] 공식 코드는 여전히 찾지 못했다.
  - 비공식 구현은 있다: `nicklashansen/dreamer4`(MIT, 2026-07 push), `lucidrains/dreamer4`(2026-10-14 push), `edwhu/dreamer4-jax`.
  - CoinRun을 GPU 1장으로 처음부터 학습한 사례(2026-08)도 있다. — [GitHub nicklashansen/dreamer4](https://github.com/nicklashansen/dreamer4), [GitHub RajatDandekar/dreamer4-coinrun](https://github.com/RajatDandekar/dreamer4-coinrun)
- **Hunyuan-GameCraft / HY-WorldPlay [corrected: 지역 제한]**
  - [공식] 두 라이선스 모두 "THIS LICENSE AGREEMENT DOES NOT APPLY IN THE EUROPEAN UNION, UNITED KINGDOM AND SOUTH KOREA"로 시작한다. 정의상 Territory에서 EU, 영국, **한국**을 뺀다.
    - 대상: Hunyuan-GameCraft-1.0 GitHub LICENSE, HY-WorldPlay(HY-World 1.5) HF License.txt.
    - 한국 사용자는 라이선스 범위 밖이다. — [HF tencent/HY-WorldPlay License.txt](https://huggingface.co/tencent/HY-WorldPlay/blob/main/License.txt), [GitHub Hunyuan-GameCraft-1.0](https://github.com/Tencent-Hunyuan/Hunyuan-GameCraft-1.0)
  - [공식] Hunyuan-GameCraft-2는 프로젝트 페이지 레포만 있고 가중치 저장소는 찾지 못했다. — [GitHub search 결과: Hunyuan-GameCraft-2.github.io](https://github.com/Hunyuan-GameCraft-2/Hunyuan-GameCraft-2.github.io)

**신규 (기준선 누락분 포함)**
- **Matrix-Game 4.0 (Skywork, 2026-10-15) [new]**
  - [공식] 성격: 실행 가능한 게임 엔진이 게임플레이, 물리, 입력을 정한다. 모델은 low-poly RGB를 실사풍으로 다시 그리는 **장면 특화 인과 비디오 렌더러**다.
  - [공식] 구성: 장면은 중세 성, 고대 이집트, 도시 레이싱 3종이다. 장면마다 5.0B(BF16)이고 출력은 480×864다. 가중치와 게임 에셋은 Apache 2.0이다.
  - [공식] 한계(카드 원문): "There is no guaranteed frame rate, consumer-GPU memory fit", "Neural output does not change collision or gameplay". — [HF Skywork/Matrix-Game-4.0](https://huggingface.co/Skywork/Matrix-Game-4.0)
  - [공식] 2026-10-16 레포 뉴스: SageAttention과 고정 프롬프트 조건에서 RTX 5080은 67 FPS, RTX 5070 Ti는 58 FPS(864×480, 정상 상태, 영상 I/O 제외)다. 같은 날 RTX 5090 최적화와 기술 보고서도 나왔다. — [GitHub SkyworkAI/Matrix-Game](https://github.com/SkyworkAI/Matrix-Game)
- **Matrix-Game 3.5 (arXiv 2608.29910, 2026-08-30) [new]**
  - [공식] 기하 인식 patch memory와 정적·동적 분리 표현을 쓴다.
  - 5B distilled 가중치(1인칭)를 Apache 2.0으로 공개했다. 저장소는 Riemann-Dynamics 조직이고 2026-07에 올렸다. — [arXiv 2608.29910](https://arxiv.org/abs/2608.29910), [HF RiemannDynamics/Matrix-Game-3.5-Distilled](https://huggingface.co/RiemannDynamics/Matrix-Game-3.5-Distilled), [GitHub](https://github.com/Riemann-Dynamics/Matrix-Game-3.5)
- **Waypoint-1.5 (Overworld; 가중치 2026-04, 논문 arXiv 2609.37107 2026-09-29) [new]**
  - [공식] 학습 데이터는 게임 수백 종의 제어 정렬 영상 10만 시간이다. 입력은 키보드·마우스 전체다. — [arXiv 2609.37107](https://arxiv.org/abs/2609.37107)
  - [공식] 1B 카드: 1.2B 파라미터, 512프레임 컨텍스트, Apache 2.0.
    - RTX 5090에서 56 FPS, w8a8 양자화로 72 FPS.
    - 지원 GPU는 데스크톱 RTX 30 시리즈 이상이다.
    - 360P 변형은 노트북 GPU용이고 Apple Silicon은 "(soon)"이다. — [HF Overworld/Waypoint-1.5-1B](https://huggingface.co/Overworld/Waypoint-1.5-1B), [HF Overworld/Waypoint-1.5-1B-360P](https://huggingface.co/Overworld/Waypoint-1.5-1B-360P)
  - [공식] 실행 환경:
    - 데스크톱 클라이언트 Biome(GPL-3.0)은 Windows와 Linux만 배포하고 "NVIDIA GPU with 16GB+ VRAM"을 요구한다.
    - 추론 라이브러리 world_engine(GPL-3.0) README는 "Apple Silicon" 백엔드를 언급하지만, 양자화 방식은 모두 NVIDIA 전용이다. — [GitHub Overworldai/Biome](https://github.com/Overworldai/Biome), [GitHub Overworldai/world_engine](https://github.com/Overworldai/world_engine)
  - [공식] 같은 회사가 키보드·마우스 역동역학 모델(IDM) Owl IDM v4(MIT, 128×128, WASD/Space/Shift/Ctrl + 마우스, FPS 데이터 학습)도 공개했다. — [HF Overworld/owl-idm-4](https://huggingface.co/Overworld/owl-idm-4)
- **MIRA (General Intuition + Kyutai, Epic Games 협업; 코드 레포 2026-07-05 생성) [new] / General Intuition API [changed]**
  - [공식] 4인 Rocket League 경기를 모델 안에서 플레이하는 멀티플레이 월드 모델이다. 공개 봇 데이터 약 1만 시간으로 학습했다.
  - "single GPU" 20 FPS이고 NVIDIA GPU가 필요하다. 코드는 Apache 2.0이다. — [generalintuition.com](https://www.generalintuition.com/), [GitHub mira-wm/mira](https://github.com/mira-wm/mira)
  - [공식] 상업 API는 "small number of partners"에게만 열었고 대기자 명단을 받는다. 가격과 모델명은 공개하지 않았다. 기준선의 "2026 여름 API 개방" 계획은 **제한 파트너 단계**로 확인된다. — [generalintuition.com](https://www.generalintuition.com/)
- **기타 공개 실시간 월드 모델 (2026-09) [new]**
  - [공식] Zing-0.5 (2609.17909, 2026-09-15)
    - 5B 모델이고, 키보드와 온라인 텍스트로 동시에 조종한다.
    - 832×480 24 FPS, 스트림 1분당 약 0.009달러(서버 임대 추정).
    - 가중치는 Apache 2.0이고, H100 80GB에서 검증했다. — [arXiv 2609.17909](https://arxiv.org/abs/2609.17909), [HF seedleap/zing-0.5](https://huggingface.co/seedleap/zing-0.5)
  - [공식] Astronex-World 1.0 (2609.20034, 2026-09-17): 5B, 832×480 24fps. 인과 모델이 L20 48GB 한 장에서 실시간으로 스트리밍한다. 학습 5단계를 모두 L20 두 장으로 했다. — [arXiv 2609.20034](https://arxiv.org/abs/2609.20034)
  - [공식] SolarWM (2609.02886, 2026-09-02): 클립 143만 개, 5B~33B 모델 4종. 데이터, 레시피, 가중치를 공개했다. — [arXiv 2609.02886](https://arxiv.org/abs/2609.02886)
  - [공식] WorldPlay2 (2609.35560, 2026-09-28)
    - HF `aejion/WorldPlay2-*` 가중치는 CC BY-NC 4.0이다.
    - 저자는 HY-WorldPlay 계열과 겹친다. 올린 계정의 소속은 확인하지 못했다. — [arXiv 2609.35560](https://arxiv.org/abs/2609.35560), [HF aejion/WorldPlay2-Fast](https://huggingface.co/aejion/WorldPlay2-Fast)
  - [공식] Multics (Tencent ARC, 2610.17201, 2026-10-12): 4인 멀티플레이 영상 생성 모델이다. 가중치는 Apache 2.0이고 6~10인으로 확장된다. — [arXiv 2610.17201](https://arxiv.org/abs/2610.17201), [HF TencentARC/Multics](https://huggingface.co/TencentARC/Multics)
  - [공식] Esports World Model Dataset (2610.16166, 2026-10-12): StarCraft II, Dota 2, CS2의 플레이어 시점 약 4,880시간이다. 렌더 영상, 게임 고유 행동, 구조화 상태가 시각 정렬돼 있다. — [arXiv 2610.16166](https://arxiv.org/abs/2610.16166)
- **에이전트 학습에 월드 모델을 쓴 신규 사례 [new]**
  - [공식] "Learning in Dreams, Winning in Reality" (2610.08033, 2026-10-06)
    - 10영웅 MOBA를 **구조화 다중 에이전트 월드 모델**로 배웠다. 픽셀이 아니다.
    - 그 안에서만 정책을 학습하고 실게임 결과를 다시 넣는 Dyna 루프를 돌렸다.
    - radiant 진영에서 실게임 내장 AI 상대로 70.2%를 이겼다(600판 중 421판). 꿈 학습만 했을 때는 0%였다. dire 진영에서는 0승이었다. — [arXiv 2610.08033](https://arxiv.org/abs/2610.08033)
  - [공식] "Pixels to Keys" (2609.37907, NVIDIA 연구진, ECCV 2026 워크숍)
    - 역동역학 모델(IDM)을 Trackmania와 Cyberpunk 2077에서 분석했다.
    - 메커닉마다 정확도가 고르지 않았다. 카메라 움직임, 지연 효과, 키 빈도 불균형이 원인이다. — [arXiv 2609.37907](https://arxiv.org/abs/2609.37907)

### Inferences
- [추정] 2026-10 기준으로 공개 월드 모델은 "NVIDIA 소비자 GPU 한 장에서 실시간"까지 왔다. Thorkell에 쓸모가 없다는 기준선 결론은 그대로다. 이유는 세 가지다.
  1. 어떤 모델도 Valheim으로 학습하지 않았다. 행동 결과(피해, 인벤토리, 구조물)를 정확히 모사한다는 보장이 없다. Matrix-Game 4.0 카드도 "collision or gameplay"를 바꾸지 못한다고 명시한다.
  2. M4 Pro에서는 실시간이 안 된다(3절).
  3. Thorkell은 실게임 클론 런타임과 Body와 같은 규약의 2D 시뮬레이터를 이미 갖고 있다.
- [추정] 장기적으로 참고할 만한 것은 **구조화 상태 월드 모델 + Dyna 루프**(MOBA 사례)다. Thorkell의 NDJSON 이벤트 로그를 학습 데이터로 쓰는 방향과 맞는다. 다만 연구 단계이고, 현재 우선순위(플래너 호출 절감, 빠른 결정)와는 거리가 있다.
- [추정] 라이선스 측면에서, 한국에서 쓰는 Thorkell은 Tencent Hunyuan 계열(GameCraft, HY-WorldPlay)을 쓸 수 없다. NitroGen은 비상업 연구에만 쓸 수 있다. Apache와 MIT인 것은 Matrix-Game 3.x·4.0, Waypoint-1.5, Zing-0.5, GameWAM, Multics, Open-P2P, MIRA 코드다.

### Gaps
- Matrix-Game 4.0 기술 보고서 본문과 MIRA 정식 발표일은 확인하지 못했다. MIRA는 보도 URL 날짜상 2026-06-25~30으로 보인다.
- Waypoint-1.5 360P의 Apple Silicon 지원 날짜는 "soon"뿐이다.
- Astronex-World와 SolarWM 가중치의 라이선스는 HF 카드로 확인하지 못했다(arXiv 문서 라이선스만 확인).
- Genie 3의 2026-09~10 상태는 웹 색인 한계로 확정하지 못했다.

## 3. Apple Silicon(MLX/CoreML)에서 돌아가는 게임 에이전트·VLA·월드 모델

### Takeaway
2026-10-17 현재 MLX로 이식된 것은 다음과 같다.
- 월드 모델: Matrix-Game 3.0·4.0. 2026-10-16 이식이지만 실시간과는 거리가 멀다.
- 범용 GUI 에이전트: UI-TARS 양자화본.
- 로보틱스 VLA: smolvla, pi0 이식본.

**키보드·마우스 게임 정책(NitroGen, Open-P2P, Player-1, GameWAM, Lumine 재현물)의 MLX/CoreML 이식은 HF 검색에서 찾지 못했다.** NVIDIA ACE(PUBG Ally) 같은 온디바이스 동료 스택도 RTX 전용이다.

### Cited Findings
- **Matrix-Game-mlx [new]**
  - [커뮤니티] Matrix-Game 4.0 MLX 변환(2026-10-16), M2 Pro 32GB 실측:

    | 프리셋 | 4프레임 청크당 시간 | 최대 메모리 |
    |---|---|---|
    | 품질 | 약 27~38초 | 24.4GB |
    | 실시간(TAEHV, 1스텝) | 약 3.5~3.6초 | 약 15GB |

    장면 DiT 하나가 9.32GB다. — [HF dgrauet/matrix-game-4.0-mlx](https://huggingface.co/dgrauet/matrix-game-4.0-mlx), [GitHub dgrauet/Matrix-Game-mlx](https://github.com/dgrauet/Matrix-Game-mlx)
  - [커뮤니티] Matrix-Game 3.0 MLX: README 원문은 "This MLX port does not achieve real-time performance on Apple Silicon"이다.

    | 기계 | 해상도 | 2초 클립 생성 시간 |
    |---|---|---|
    | M2 Pro 32GB | 480p | 약 3분 |
    | M2 Pro 32GB | 720p | 약 7분 |
    | M4 Max 64GB 이상 | 720p | 약 15분(전체 VAE) |

    가중치 묶음은 DiT 12GB와 T5 10.6GB 등이다. — [GitHub dgrauet/Matrix-Game-mlx](https://github.com/dgrauet/Matrix-Game-mlx), [HF dgrauet/matrix-game-3.0-mlx](https://huggingface.co/dgrauet/matrix-game-3.0-mlx)
- **UI-TARS MLX [corrected]**
  - [커뮤니티] 기준선은 "MLX 변환 가능성 [추정]"이라고 했다. 실제로는 2025-04-25부터 변환본이 있었다.
    - `mlx-community/UI-TARS-1.5-7B-4bit/6bit/8bit`(Apache 2.0)
    - 2B 4bit MLX(2026-09-08) — [HF mlx-community/UI-TARS-1.5-7B-4bit](https://huggingface.co/mlx-community/UI-TARS-1.5-7B-4bit), [HF wi-fi2/ui_tars_2b_mlx_4bit](https://huggingface.co/wi-fi2/ui_tars_2b_mlx_4bit)
  - [공식] 참고로 UI-TARS-1.5-7B는 PlaySuite 무기억 0.71/4로 공개 VLM과 비슷한 수준이었다. — [arXiv HTML 2610.07127](https://arxiv.org/html/2610.07127v1)
- **로보틱스 VLA MLX [new]**: [커뮤니티] `tokimoa/smolvla-mlx`, `tokimoa/pi0-mlx`(Apache 2.0, 2026-07-29), `mohan007/pi05-mlx-4bit`(2026-05). 게임용 가중치는 아니다. — [HF tokimoa/smolvla-mlx](https://huggingface.co/tokimoa/smolvla-mlx), [HF tokimoa/pi0-mlx](https://huggingface.co/tokimoa/pi0-mlx)
- **GGUF(llama.cpp, Metal) [new]**: [커뮤니티] JarvisVLA-Qwen2-VL-7B GGUF(2026-08-24)가 있다. Minecraft 전용이다. — [HF mradermacher/JarvisVLA-Qwen2-VL-7B-GGUF](https://huggingface.co/mradermacher/JarvisVLA-Qwen2-VL-7B-GGUF)
- **이식본을 찾지 못한 것**: [공식/조회] HF 검색 "nitrogen mlx", "waypoint mlx", "openvla mlx", "gr00t mlx"는 결과가 0이었다. NitroGen과 Open-P2P 계열 저장소에 MLX/CoreML 변형은 없다(조회 2026-10-17). — [HF nvidia/NitroGen](https://huggingface.co/nvidia/NitroGen), [HF elefantai/open-p2p](https://huggingface.co/elefantai/open-p2p)
- **NVIDIA 전용 경로**
  - [보도] PUBG Ally Duo는 RTX 전용이다. — [allthings.how](https://allthings.how/pubg-ally-duo-how-to-play-with-ella-the-rtx-only-ai-teammate/)
  - [보도] NVIDIA ACE 온디바이스 SLM(Nemotron-4 4B, 2024)은 GeForce RTX를 대상으로 하며 macOS 언급이 없다. — [NVIDIA blog](https://blogs.nvidia.com/blog/ai-decoded-gamescom-ace-nemotron-instruct)
  - [공식] Waypoint와 Biome은 NVIDIA 16GB 이상을 요구하고, Apple Silicon은 "soon"이다. — [GitHub Overworldai/Biome](https://github.com/Overworldai/Biome)

### Inferences
- [추정] M4 Pro 24GB는 M2 Pro 32GB보다 GPU가 빠르지만 메모리가 작다. Matrix-Game 4.0 실시간 프리셋(최대 약 15GB, 청크당 약 3.5초, 대략 1fps)을 Valheim 두 개(Rosetta)와 같이 돌리기는 어렵다.
- [추정] 맥에서 "게임 화면을 보는" 모델로 현실적인 후보는 일반 VLM과 GUI 에이전트의 4bit MLX(UI-TARS 2B/7B, Qwen3.x-VL)다. 지연은 초 단위다. Player-1 가중치가 나오면 9B 4bit(약 5~6GB 추정)도 후보에 들어간다. 모두 실시간 제어가 아니라 가끔 묻는 보조 지각 용도다.
- [추정] 이 범위의 결론: Apple Silicon에서 실시간 게임 정책을 돌릴 공개 스택은 아직 없다. 맥 로컬 추론의 실익은 텍스트 결정 모델(laya 등)에 있다. 이는 `local_models_apple_silicon.md` 범위다.

### Gaps
- UI-TARS MLX 변환본과 Player-1의 M4 Pro 실측 지연, Valheim 동시 실행 시 프레임 영향은 공개 자료가 없다. 직접 재야 한다.
- CoreML로 변환한 게임 정책은 검색 범위(HF 키워드)에서 찾지 못했다. Apple 개발자 포럼 등은 조사하지 않았다.

## 4. Valheim을 직접 다룬 증거·주장

### Takeaway
Valheim이 학습에 들어갔다고 공식 확인된 범용 에이전트는 **여전히 SIMA 2 하나**이고, 단독 수치는 없다[unchanged]. 2026에는 **Thorkell과 같은 "BepInEx 플러그인 + 외부 LLM" 오픈소스 시도가 여러 개** 생겼다[new]. 픽셀 모델로 Valheim을 플레이했다는 공개 결과는 찾지 못했다.

### Cited Findings
- [공식] SIMA 2 [unchanged]
  - 논문의 학습 환경과 블로그의 파트너 목록에 Valheim이 있다. 블로그는 2025-11-13 그대로다. — [DeepMind blog](https://deepmind.google/blog/sima-2-an-agent-that-plays-reasons-and-learns-with-you-in-virtual-3d-worlds/), [arXiv 2512.04797](https://arxiv.org/html/2512.04797)
  - arXiv API 초록 검색 "all:Valheim"은 0건이었다(2026-10-17). 다만 초록 검색이라 본문 언급은 잡지 못한다. — [arXiv API](https://export.arxiv.org/api/query?search_query=all:Valheim)
- [보도/2차] Valheim 1.0 정식판은 2026-09-09에 나왔다. PS5와 Switch 2 버전이 함께 나왔다. SIMA 2(2025)는 그전 얼리액세스 빌드로 학습했다. — [Wikipedia: Valheim](https://en.wikipedia.org/wiki/Valheim)
- [커뮤니티] Valheim LLM 브리지 프로젝트 [new]. 모두 구조화 API 방식이고 공개된 성능 결과는 없다.

  | 프로젝트 | 생성일 / 마지막 push | 라이선스 | 구조 |
  |---|---|---|---|
  | `Dahuchsi/ValheimAI` | 2026-09-29 | — | 두 번째 Steam 계정으로 AI 동료를 접속시킨다. BepInEx 플러그인이 localhost WebSocket으로 상태를 내보내고, 컨트롤러가 플래너/LLM을 부른다. "The LLM chooses high-level goals. Deterministic local code executes movement…" Windows 전용, 초기 스캐폴드. |
  | `itenev/valheim-ai-agent` | 2026-03-02 / 2026-04-17 | Apache 2.0 | mineflayer에서 착안. BepInEx가 상태를 JSON으로 내고 WebSocket(25500)으로 Python과 Claude/GPT-4o를 잇는다. Linux에서 시험. |
  | `jneb802/ValBridgeServer` | 2026-01~02 | MIT | GABP/MCP로 Claude Code에 도구를 준다. 체력, 위치, 콘솔 명령, prefab, Unity 검사. |
  | `myrcutio/ValheimMCP` | 2026-05-29 / 2026-09-25 | MIT | 콘솔 명령 HTTP 엔드포인트. 인증 없음, 루프백만. |
  | `ValAgentBridge`, `tmac1973/ModTestBridge` | 2026-10 | — | 모드 테스트 자동화용. |

  — [GitHub Dahuchsi/ValheimAI](https://github.com/Dahuchsi/ValheimAI), [GitHub itenev/valheim-ai-agent](https://github.com/itenev/valheim-ai-agent), [GitHub jneb802/ValBridgeServer](https://github.com/jneb802/ValBridgeServer), [GitHub myrcutio/ValheimMCP](https://github.com/myrcutio/ValheimMCP), [GitHub tmac1973/ModTestBridge](https://github.com/tmac1973/ModTestBridge)
- [커뮤니티] 그 밖의 Valheim 관련 시도:
  - AIRI(오픈소스 AI 캐릭터) 이슈 #1097 "game playing ai support Valheim (like Minecraft)": 2026-03-04에 열렸고, 2026-03-26 이후 진척이 없다. — [GitHub moeru-ai/airi#1097](https://github.com/moeru-ai/airi/issues/1097)
  - Nexus의 "Tutorial AI" 모드(동료 Aruana): 나무를 하고, 광맥을 캐고, 방어한다. 검색 요약상 Valheim 1.0.7 대응이고 2026-10-07에 갱신됐다. 페이지는 403이라 직접 확인하지 못했다. — [Nexus Mods 3312](https://www.nexusmods.com/valheim/mods/3312)

### Inferences
- [추정] 오픈소스 Valheim 봇들은 Thorkell과 같은 결론("LLM은 목표, 결정적 코드가 실행")에 도달했다. 하지만 공개된 것은 모두 초기 스캐폴드이거나 개발 도구다.
- [추정] 일부는 Thorkell이 금지한 것을 그대로 노출한다(prefab 이름, 콘솔 치트 명령, `spawn`, `god`). 정보 동등성과 결과 검증 면에서 Thorkell보다 약하다. 코드를 참고할 가치는 낮다. 다만 같은 계정 두 프로세스, 루프백 같은 문제를 어떻게 풀었는지는 비교해 볼 만하다.
- [추정] Valheim 1.0(2026-09-09) 이후 Thorkell이 1.0.16을 대상으로 한다는 점은 버전 게이트 규칙(하드 규칙 6)과 맞는다. SIMA 2 학습분은 얼리액세스 빌드이므로 Thorkell이 활용할 여지는 없다.

### Gaps
- SIMA 2의 Valheim 단독 성공률은 여전히 비공개다.
- `Dahuchsi/ValheimAI` README가 선행작으로 든 `valheim-ai-agent`, ValheimMCP, ValBridgeServer 외에 실제 동작 데모(영상, 수치)가 있는 Valheim 에이전트는 찾지 못했다.
- Tutorial AI(Aruana) 모드의 구현 방식(NPC인지 진짜 플레이어인지, 규칙 기반인지)은 확인하지 못했다.

## 5. 종합 팩트 시트와 Thorkell(플러그인 Body)에 붙이는 방법

### Takeaway
2026-10-17 기준으로도 Thorkell의 **실행 경로에 픽셀 게임 모델이나 월드 모델을 넣을 근거는 없다**[unchanged]. 대신 이번 기간의 새 자료 두 가지가 지금 구조를 지지한다.
- PUBG Ally: 상용 서비스에서 도구 API, 행동 트리, 증류한 2B 온디바이스 모델로 동료 AI를 운영했다.
- Latent Bridge: 느린 모델은 빠른 모델보다 이미 나을 때만 도움이 된다.

바로 쓸 만한 것은 PUBG Ally의 증류·운영 패턴이다. 맥에서 시험해 볼 수 있는 것은 UI-TARS와 (공개되면) Player-1의 MLX 4bit를 "가끔 화면 보기" 보조로 쓰는 정도다.

### Cited Findings

| 시스템 (상태) | 공개 | 라이선스 | OS / GPU | 하드웨어 | 지연·제어율 | 처음 보는 3D 게임 | 출처 |
|---|---|---|---|---|---|---|---|
| SIMA 2 [unchanged] | 비공개, 연구 프리뷰 | — | — | 미공개 | 미공개 | ASKA 약 40% | [blog](https://deepmind.google/blog/sima-2-an-agent-that-plays-reasons-and-learns-with-you-in-virtual-3d-worlds/) |
| Game-TARS [unchanged] | 비공개 | — | — | 미공개 | Sparse-Thinking | 웹 3D 게임에서 처음 하는 사람 수준 | [arXiv](https://arxiv.org/abs/2510.23691) |
| Lumine [changed] | 공식 비공개, 커뮤니티 재현(MIT 7B) | — | — | H20 4장(논문) | 5Hz 지각, 30Hz 행동 | 명조·스타레일 zero-shot | [arXiv](https://arxiv.org/abs/2511.08892), [재현](https://github.com/koboshchan/Lumine) |
| Player-1 [new] | 코드 MIT, 가중치 준비 중 | 미정 | 미기재 | 학습 H200 32~64장 | 200ms 격자 | Watch Dogs 2 정성 사례만 | [arXiv](https://arxiv.org/abs/2610.20584), [GitHub](https://github.com/TencentARC/Player-1) |
| GameWAM [new] | 가중치 공개 | Apache 2.0 | CUDA(학습 H200) | 6B, 체크포인트 12.2GB | 16 예측 / 8 실행 | Minecraft·ViZDoom 전용 | [HF](https://huggingface.co/yunncheng/gamewam-models) |
| NitroGen [corrected] | 가중치 공개 | NVIDIA License, **비상업 연구 전용**(3.3조) | 추론 Linux 가능, 게임 Windows, 패드만 | 493M | 동기 추론 | 미세조정 후 최대 52% 상대 개선. PlaySuite·OmniGameArena에서 약함 | [LICENSE](https://huggingface.co/nvidia/NitroGen/blob/main/LICENSE) |
| Open-P2P [unchanged] | 가중치 공개 | MIT (논문 CC BY-NC-ND) | Windows + Recap, GPU 2장 또는 Moonlight | 150M~1.2B | <50ms 필요 | Roblox, DOOM, Quake | [GitHub](https://github.com/elefant-ai/open-p2p) |
| UI-TARS-1.5-7B [corrected] | 가중치 공개, MLX 4·6·8bit | Apache 2.0 | **macOS MLX 가능** | 약 8B | 초 단위 [추정] | PlaySuite 0.71/4 | [HF MLX](https://huggingface.co/mlx-community/UI-TARS-1.5-7B-4bit) |
| JARVIS-VLA [corrected] | 가중치 공개, GGUF | MIT | llama.cpp 가능 [추정] | 7B | — | Minecraft 전용 | [HF](https://huggingface.co/CraftJarvis/JarvisVLA-Qwen2-VL-7B) |
| ROCKET-3 [new] | 체크포인트 공개 | MIT | PyTorch | 약 750MB | — | 처음 보는 3D 환경 전이를 연구 주제로 다룸 | [HF](https://huggingface.co/CraftJarvis/ROCKET-3-1.5x) |
| PUBG Ally [new] | 상용(게임 내장), 비공개 | — | Windows, **RTX 전용** | VRAM 8GB 이상, 2B SLM | 음성 왕복 1.6초(온디바이스) | PUBG 전용(도구 API) | [arXiv](https://arxiv.org/html/2609.29837v2) |
| Gemini 4 Argon × Mineflayer [new] | 유료 API | 상용 | 클라우드 | 에이전트당 클라우드 머신 | 프로그램 중앙값 33.5초 | Minecraft 완주 1회(API, 정보 우위 있음) | [arXiv](https://arxiv.org/html/2610.22319v1) |
| Matrix-Game 4.0 [new] | 가중치 공개 | Apache 2.0 | CUDA, MLX 이식(오프라인) | 장면당 5B | 5070 Ti 58 FPS / M2 Pro 청크당 약 3.5초 | 장면 특화 렌더러 | [GitHub](https://github.com/SkyworkAI/Matrix-Game), [MLX](https://huggingface.co/dgrauet/matrix-game-4.0-mlx) |
| Waypoint-1.5 [new] | 가중치 공개 | Apache 2.0 (엔진·클라이언트 GPL-3.0) | NVIDIA RTX 30 이상, Apple "soon" | 1.2B | 5090에서 56~72 FPS | 생성 세계(에이전트 아님) | [HF](https://huggingface.co/Overworld/Waypoint-1.5-1B) |
| MIRA [new] | 코드 공개 | Apache 2.0 | NVIDIA | GPU 1장 | 20 FPS | Rocket League 전용 | [GitHub](https://github.com/mira-wm/mira) |
| HY-WorldPlay / GameCraft [corrected] | 가중치 공개 | Tencent 커뮤니티 라이선스, **한국·EU·영국 제외** | CUDA | — | — | — | [License](https://huggingface.co/tencent/HY-WorldPlay/blob/main/License.txt) |

**플러그인 Body와 결합하는 관점의 근거**
- [공식] PUBG Ally의 결합 방식은 다음과 같다. Thorkell과 1:1로 대응한다.
  - 도구 그룹: 관찰, 행동 실행, 말하기, 기억, 안전.
  - 행동 실행 전 `check_action_availability`로 확인한다.
  - System 1 행동 트리가 우선순위로 선점한다.
  - 관찰 결과는 다음 루프로 넘기지 않고, 짧은 계획만 넘긴다. — [arXiv HTML v2](https://arxiv.org/html/2609.29837v2)
- [공식] GameWAM은 픽셀과 함께 구조화 상태(위치, 각도, 체력)를 입력으로 받는다. 플러그인이 주는 구조화 지각을 정책 입력에 섞는 것이 연구에서도 쓰인다는 근거다. — [HF yunncheng/gamewam-models](https://huggingface.co/yunncheng/gamewam-models)
- [공식] Latent Bridge: 느린 추론이 빠른 반응을 이기는 과제에서만 느린 모델과 빠른 모델 결합이 이득이다(r=0.93). — [arXiv 2606.24470](https://arxiv.org/abs/2606.24470)
- [공식] Gemini 4 Argon Minecraft: 1회 완주에 모델 호출 약 24,000회, 비용 약 520~1,040달러가 들었다. — [arXiv HTML](https://arxiv.org/html/2610.22319v1)

### Inferences
- [추정] **결합 방식별 판단**

  | 방식 | 판단 | 이유 |
  |---|---|---|
  | 픽셀 정책을 Body의 입력 주입으로 연결 (Open-P2P, NitroGen, Player-1, GameWAM) | 비추천 [unchanged] | Valheim 데이터가 없고, Windows·NVIDIA 기준이며, 타입 결과 코드와 월드 변화 검증을 우회한다. NitroGen은 비상업 라이선스다. |
  | VLM(UI-TARS MLX, 공개 후 Player-1)을 "화면 질의" 도구로 Brain에 추가 | 선택적 실험 | 정보 동등성은 자연히 지켜진다. 초 단위 지연이므로 반사나 전투에는 쓰지 않는다. M4 Pro에서 Valheim 두 개와 같이 돌릴 때의 실측이 먼저다. |
  | PUBG Ally식 증류: 플래너(Gemini) 출력과 실게임 로그를 교사 데이터로 Jev/laya 등 소형 결정 모델 미세조정 | **가장 실익이 큼** | 무료 등급 20회/일과 플래너 지연을 직접 줄인다. 증류와 학습의 세부는 `learning_methods.md` 범위다. |
  | PUBG Ally 운영 패턴 차용 | 바로 적용 가능 | 자발적 발화 쿨다운, 약 5k 토큰 컨텍스트 예산, 관찰은 매 루프 새로 읽고 계획만 이월, 안전 입력 가림 처리 |
  | 월드 모델로 상상 학습 | 보류 [unchanged] | 맥에서 실시간이 아니고 Valheim으로 학습한 것이 없다. 구조화 상태 Dyna 루프는 장기 연구 후보다. |
  | LLM이 코드를 써서 스킬을 만드는 방식 (Argon Minecraft, Compiled Agency) | 오프라인 개발 도구로만 | 실시간 경로에 넣으면 호출 수가 무료 등급과 맞지 않는다. 스킬 코드는 개발 때 만들고 검증해서 Body에 고정하는 현재 방식이 맞다. |

- [추정] 기준선의 요약 판단("범용 게임 에이전트·파운데이션 모델을 실행 경로에 넣을 이유는 없다")은 유지한다. 2026-10-17 기준으로 바뀐 것은 근거가 늘었다는 점이다. 같은 구조가 상용 서비스(PUBG Ally)와 연구(Latent Bridge, GameWAM의 상태 입력) 양쪽에서 확인됐다.

### Gaps
- PUBG Ally 방식의 2B 증류 모델을 M4 Pro 24GB에서 Valheim 두 개와 같이 돌린 지연 수치는 없다. PUBG 수치는 RTX 기준이다.
- Player-1 가중치가 실제로 나올지와 그 라이선스는 미정이다.
- 이 노트는 API·클라우드 비용 비교, 로컬 텍스트 LLM 성능, 학습 방법은 다루지 않는다. 같은 폴더의 `cloud_options_costs.md`, `local_models_apple_silicon.md`, `learning_methods.md`가 그 범위다.
