# 비싼 게임 에이전트 행동을 싸고 빠른 정책으로 바꾸는 학습 방법 (기준일 2026-10-10)

표기: **[논문]** arXiv·학회 논문 원문 / **[공식]** 연구소·벤더 공식 블로그·문서 / **[언론]** 기사 / **[커뮤니티]** 개인 블로그·GitHub 실측 / **[추정]** 이 노트 작성자의 추론. 날짜는 arXiv 제출일 또는 게시일이다. 조사일 2026-10-11.

Thorkell 맥락 요약(과제 설명 기준): 구조화 지각(JSON) + 파라미터 행동(move_to, attack, pickup…) + 결정적 반사. 두뇌가 `decisions.jsonl`에 (상태 텍스트 → 고른 선택지, 모델 확률)을 남김. 빠른 결정은 Jev(비생성 클라우드 결정 모델), 그 로그로 Convai laya(322–421M)를 파인튜닝할 계획. 계획은 gemini-3.8-flash(무료 하루 20회). 게임은 실시간보다 빠르게 못 돌리고, 2D Python 시뮬레이터가 있음. M4 Pro 24GB, 클라우드 GPU 대여 가능.

## 1. LLM 플래너·결정기를 작은 모델로 증류하기 (게임·체화 에이전트, 2024–2026)

### Takeaway
0.5B–770M급 학생 모델이 수천 개 수준의 교사 궤적만으로 "한 단계 큰" 모델이나 표준 모방학습을 이긴다는 결과가 반복해서 나온다. 단, 대부분 텍스트 환경(ScienceWorld, ALFRED, QA/수학)에서 나온 수치이고, 3D 실시간 게임에서 LLM 결정기를 작은 모델로 증류한 공개 수치는 드물다.

### Cited Findings
- **Agent Distillation** (Kang et al., 2025-05-23, NeurIPS 2025 Spotlight) [논문]: 교사 Qwen2.5-32B-Instruct의 reason-act-observe 궤적 **약 2,000개**(HotPotQA 1,000 + MATH 2,000 문제에서 오답 궤적 제거)로 Qwen2.5 0.5B/1.5B/3B/7B 학생을 학습시켰다. LoRA rank 64, 전체 linear 층, 2 epoch, batch 8, lr 2e-4, A100 80GB 4장. 0.5B 에이전트가 CoT 증류 1.5B와 비슷하고, 1.5B가 CoT 증류 3B와 비슷하다. "first-thought prefix"는 어려운 MATH에서 도움이 되고, self-consistent action generation(여러 샘플 다수결)은 작은 모델의 잘못된 코드 행동을 크게 줄였다. — [arXiv 2505.17612](https://arxiv.org/html/2505.17612), [코드](https://github.com/Nardien/agent-distillation)
- **Sub-goal Distillation** (Hashemzadeh et al., 2024-05-04) [논문]: LLM이 오라클 경로에 하위목표를 주석으로 붙이고, 이것을 **770M** 학생의 계획 모듈(하위목표 생성) + 실행 모듈(기본 행동)로 증류한다. ScienceWorld에서 기본 행동만 따라하는 표준 모방학습보다 **절대 16.7%p** 높다. 추론 시 LLM을 호출하지 않으므로 비용이 고정된다. — [arXiv 2405.02749](https://arxiv.org/abs/2405.02749)
- **DeDer, Embodied CoT Distillation** (Choi et al., ICML 2024) [논문]: LLM 결정을 reasoning-policy와 planning-policy의 계층으로 나누어 작은 LM에 증류한다. reasoning-policy는 LLM의 embodied in-context learning과 self-verification으로 만든 데이터로 배운다. ALFRED에서 기존 언어 계획·증류 방법보다 낫다고 보고했다. — [arXiv 2412.11499](https://arxiv.org/abs/2412.11499), [PMLR](https://proceedings.mlr.press/v235/choi24d.html)
- **Distilling step-by-step** (Google, 2023) [논문/공식]: LLM의 근거(rationale)를 보조 타깃으로 함께 학습하면, 770M T5가 few-shot 540B PaLM을 데이터의 **80%만** 쓰고도 이긴다(크기 700배 이상 축소). — [Google Research 블로그](https://research.google/blog/distilling-step-by-step-outperforming-larger-language-models-with-less-training-data-and-smaller-model-sizes/), [arXiv 2305.02301](https://arxiv.org/html/2305.02301v2)
- **SOD, Step-wise On-policy Distillation** (Zhong et al., 2026-05-08) [논문]: 학생과 교사가 얼마나 다른지에 따라 단계별 증류 강도를 다시 가중한다. 학생이 분포 밖 상태에 있을 때는 교사 신호를 약하게 반영한다. 교사는 GRPO로 다듬은 Qwen3-4B, 학생은 Qwen3-0.6B/1.7B다. 궤적 **약 33K**(SFT 3K + RL 30K)를 H20 8장에서 2–3일 학습했다. 기존 on-policy distillation(OPD)보다 0.6B는 24.2%, 1.7B는 18.5% 높다(상대 개선). 수학·코드 벤치이고 체화 환경은 없다. — [arXiv 2605.07725](https://arxiv.org/html/2605.07725v1)
- **Agent Memory Distillation (AMD)** (2026-08) [논문, 검색 요약만 확인]: 교사(GPT-5-mini)의 경험을 task/subtask/function 수준의 계층 메모리로 만들어 4B·8B 학생 에이전트에 넘긴다. 가중치를 바꾸지 않는 증류다. — [arXiv 2608.07169](https://arxiv.org/abs/2608.07169)
- **The Latent Bridge** (Li & Shi, 2026-06-23) [논문]: 동결된 빠른 반응 VLM(MiniCPM-o 4.5, 9B, 15 Hz 제어 루프, 수십 ms)과 느린 추론 VLM(Qwen3-VL-8B-Thinking, 응답 약 1.5초)을 연결하는 slow-fast 구조다. 학습하는 부분은 둘 사이의 채널뿐이다. Atari 7종과 MetaDrive에서 연속 latent 채널이 텍스트 채널과 같거나 더 낫다(MsPacman +57%, RoadRunner +28%). 두 채널을 함께 쓰면 오히려 망가졌다(RoadRunner −96%). 이득의 크기는 "느린 추론이 이미 빠른 반응보다 나은가"와 강하게 상관했다(r=0.93). — [arXiv 2606.24470](https://arxiv.org/abs/2606.24470)
- **ODYSSEY** (IJCAI 2025) [논문, 검색 요약]: Minecraft Wiki에서 만든 **390k+** 지시 QA로 LLaMA-3를 파인튜닝해 Minecraft 지식 모델을 만들었다. — [IJCAI 2025 PDF](https://www.ijcai.org/proceedings/2025/0022.pdf), [arXiv 2407.15325](https://arxiv.org/pdf/2407.15325)
- **Orak** (Park et al., 2025-06-04, v3 2026-04-14) [논문]: 12개 상용 게임 벤치마크와 MCP 인터페이스를 만들고, "여러 장르의 전문가 LLM 플레이 궤적" 파인튜닝 데이터셋을 공개했다. 파인튜닝 효과 ablation도 포함했다. 구체 수치는 이번 조사에서 확인하지 못했다(PDF 10MB 초과로 열지 못함). — [arXiv 2506.03610](https://arxiv.org/abs/2506.03610)
- 고전 KD 배경 [논문, 이번 세션에서 재확인 안 한 배경 지식]: 교사의 soft probability를 temperature를 걸어 맞추는 지식 증류(Hinton et al., 2015). Jev 로그에 확률이 있으면 이 방식이 바로 적용된다. — [arXiv 1503.02531](https://arxiv.org/abs/1503.02531)

### Inferences
- [추정] laya(322–421M)는 위에서 성공한 학생 크기(0.5B, 770M)와 같은 급이다. 근거 데이터 규모로 보면 **수천 건의 깨끗한 결정 로그**에서 의미 있는 시작점이 나온다(Agent Distillation 약 2,000 궤적). 결정 하나가 짧은 "상태 → 선택지" 분류라면 궤적보다 샘플이 싸므로 수천~수만 건을 모으기 쉽다.
- [추정] `decisions.jsonl`에 Jev 확률이 있으므로 hard label(고른 선택지)만 쓰지 말고 soft target(확률 분포)으로 KD하는 편이 정보가 많다. 교사가 확신하지 못한 결정은 가중치를 낮추거나 따로 표시한다. SOD가 분포 밖 상태의 교사 신호를 약하게 한 것과 같은 생각이다.
- [추정] gemini-3.8-flash가 하루 20회로 묶여 있으므로, 플래너 출력은 증류의 주 교사가 아니라 **하위목표·근거 주석**(Sub-goal Distillation, Distilling step-by-step 방식)으로 아껴 쓰는 편이 맞다. 하루 20회면 한 달 약 600개 주석이다.
- [추정] Latent Bridge 결과는 Thorkell의 "빠른 결정 + 느린 플래너" 구조가 맞는 방향임을 뒷받침한다. 동시에 "느린 쪽이 이미 더 잘할 때만 연결이 이득"이라는 조건도 보여 준다. 플래너가 빠른 결정기보다 나은 상황인지를 먼저 측정해야 한다.

### Gaps
- 3D 실시간 게임에서 LLM 결정기를 300–500M 분류기·생성기로 증류하고 정확도·지연을 함께 보고한 공개 논문은 찾지 못했다. 대부분 텍스트 환경 또는 Atari 수준이다.
- Orak 파인튜닝 결과 수치(학생 크기, 궤적 수, 개선 폭)는 PDF를 열지 못해 확인하지 못했다.
- Convai "laya"와 "Jev"는 공개 자료로 확인되지 않았다. 검색에서는 Convai의 클라우드 NPC 플랫폼만 나왔다([Convai 블로그](https://convai.com/blog/introducing-convai)). 파라미터 수와 라이선스는 사용자 측 자료로 확인해야 한다.

## 2. 게임·에이전트 환경에서 LLM을 RL로 파인튜닝하기 (GRPO/RLVR, 2025–2026)

### Takeaway
공개된 multi-turn agent RL은 대부분 Sokoban·FrozenLake·ALFWorld·WebShop 같은 **빠른 기호 환경**에서 0.5B–7B 모델로 수백~천 스텝을 돌린다. 단일 H100으로 1.5B 1,000스텝에 약 12시간이 걸리는 규모다. 같은 게임 안 난이도 확장은 되지만 **다른 게임으로의 전이는 실패**한다는 보고가 있다. 실시간 3D 게임에서 이 루프를 직접 돌린 사례는 찾지 못했다.

### Cited Findings
- **RAGEN / StarPO** (Wang et al., 2025-04) [논문]: 궤적 수준 agent RL 프레임워크다. 주 모델은 Qwen2.5-0.5B-Instruct이고, WebShop에는 3B를 쓰고, 스케일링 실험에서 3B/7B/72B를 비교했다. H100/A100에서 100–200회 rollout-update를 돌렸다. 설정은 prompt 8개 × rollout 16개, 에피소드당 최대 5턴이다. 이 과정에서 **"Echo Trap"**이 반복해서 나타났다. 보상 분산이 먼저 급락하고, 그다음 gradient spike가 오면서 붕괴하는 현상이다. 해결책인 StarPO-S는 분산이 낮은 궤적을 거르고, critic을 넣고, gradient를 안정화한다. 세분화된 reasoning-aware 보상이 없으면 multi-turn RL에서 추론이 거의 생기지 않고, 얕은 전략이나 환각된 생각이 나온다. 매 업데이트마다 새 rollout을 쓰는 것(Online-1)이 중요하고, 초기 상태를 다양하게 하면 일반화가 좋아진다. 0.5B 학습 모델이 Sokoban/FrozenLake에서 20.70%/21.48%를 기록했다. 논문은 이것을 "파인튜닝하지 않은 대형 모델과 비슷한 수준"으로 설명한다. 기호 과제에서는 0.5B보다 큰 모델의 이득이 작았다. — [arXiv 2504.20073 v2](https://arxiv.org/html/2504.20073v2)
- **SPA, Self-Play world model SFT → PPO** (Chen et al., 2025-10-16) [논문]: 먼저 상태 관측과 다음 상태 예측을 self-play SFT(1,280 샘플)로 학습시켜 world model을 내재화한 뒤 PPO를 돌린다. Qwen2.5-1.5B-Instruct 결과는 다음과 같다(vanilla RL → SPA, Pass@1). Sokoban 25.6% → **59.8%**, FrozenLake 22.1% → **70.9%**, Sudoku 0% → **59.6%**. 모델은 Qwen2.5 0.5B/1.5B/3B, LLaMA3.2-1B, GPT-OSS-20B를 썼다. 컴퓨트는 최대 H100 8장이고, 1.5B 1,000스텝에 **단일 GPU 약 12시간**이 걸렸다. Pass@k는 초반(0–400 스텝)에 오르다가 이후 떨어졌다. 같은 게임 안의 더 어려운 설정으로는 일반화되지만, **다른 게임으로는 전이되지 않았다**. 쉬운 변형에서 배운 world model은 어려운 변형의 학습을 크게 가속했다. — [arXiv 2510.15047](https://arxiv.org/html/2510.15047v1)
- **GiGPO / verl-agent** (Feng et al., 2025-05, NeurIPS 2025) [논문]: critic 없는 group RL에 step 수준 credit assignment를 더한다. 여러 궤적에서 **반복해서 나타난 같은 환경 상태(anchor state)**를 묶어 step별 상대 advantage를 계산한다. Qwen2.5-1.5B/7B로 GRPO 대비 ALFWorld에서 12%p 이상, WebShop에서 9%p 이상 높았다. GPU 메모리와 rollout 비용은 같다. — [arXiv 2505.10978](https://arxiv.org/html/2505.10978v1), [verl-agent](https://github.com/langfengQ/verl-agent)
- **ViGaL, Play to Generalize** (Xie et al., ICLR 2026) [논문]: 7B 멀티모달 LLM을 Snake 같은 아케이드 게임에서 RL로만 학습시켰다. 풀이 데이터를 보지 않았는데도 MathVista·MMMU 같은 추론 벤치가 올랐다. "게임은 추론의 대리 과제"라는 결과이고, 게임 실력 자체를 노린 연구는 아니다. — [arXiv 2506.08011](https://arxiv.org/abs/2506.08011), [ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/1cdbce34681a3aaa0154b300706743d8-Abstract-Conference.html)
- **GROW** (Wu et al., 2026-05-18) [논문]: open-world VLM 에이전트용 GRPO다. 궤적을 state-action 샘플로 나누고 그 사이에서 advantage를 계산해, 전체 궤적을 넣을 때 생기는 긴 컨텍스트와 잡음 문제를 줄인다. Minecraft 800+ 과제에서 SOTA를 주장한다. 초록에 수치·모델 크기·컴퓨트는 없다. — [arXiv 2605.20246](https://arxiv.org/abs/2605.20246)
- 기타 2026 multi-turn RL 연구 [논문, 제목·요지만 확인]: TSR(Trajectory-Search Rollouts, 2026-02), Turn-PPO(EACL 2026 Findings, 턴 단위 advantage), AgentGym-RL(장기 결정용 multi-turn RL) 등이 있다. 모두 "GRPO를 multi-turn에 그대로 쓰면 장기 credit assignment가 약하다"는 문제를 다룬다. — [TSR](https://arxiv.org/html/2602.11767v1), [Turn-PPO](https://aclanthology.org/2026.findings-eacl.328/)

### Inferences
- [추정] 이 계열은 모두 **환경을 빠르게 많이 리셋할 수 있다**는 전제 위에 있다. 예를 들어 128 rollouts × 200 업데이트다. 실시간 Valheim 한 인스턴스(하드 규칙 3: 실게임 시나리오는 한 번에 하나)로는 불가능하다. 할 수 있는 곳은 2D 시뮬레이터뿐이다.
- [추정] SPA가 "다른 게임으로 전이 실패"를 보고했으므로, 2D 시뮬에서 RL로 다듬은 LLM 정책이 실게임에 그대로 옮겨진다고 기대하면 안 된다. 시뮬 RL은 "행동 형식·기본 전략 길들이기"로 보고, 실게임 로그로 다시 맞추는(SFT/KD) 단계가 필요하다.
- [추정] GiGPO의 anchor-state 그룹핑은 같은 상태가 반복되는 기호 환경에서 잘 맞는다. Valheim처럼 연속 상태에서는 상태를 이산화(구역·목표·인벤토리 요약)해야 같은 상태끼리 묶을 수 있다.
- [추정] 비용 감각: SPA 수치(1.5B, 1,000스텝, 단일 H100 약 12시간)를 그대로 쓰면, 시뮬레이터 기반 RL 실험 1회는 클라우드 H100 시간당 대여료 × 12시간 정도다. 시간당 가격은 이번 조사에서 확인하지 않았다.

### Gaps
- RAGEN의 총 GPU 시간은 논문 요약에서 "실험마다 다름"으로만 나왔다.
- 실시간 3D 게임(Valheim급)에서 LLM을 RL 파인튜닝하고 실게임 성능을 보고한 공개 사례는 찾지 못했다.
- GROW의 모델 크기·컴퓨트·수치는 초록에 없었다.

## 3. 사람 플레이·LLM 궤적에서 모방학습/행동복제 (3D 게임)

### Takeaway
픽셀에서 저수준 조작을 배우는 BC는 데이터가 크다. CS:GO 95시간, Lumine 1,731시간, VPT 70k시간, NitroGen 40k시간 수준이고, 컴퓨트는 H100 수천 GPU시간이 든다. 대신 **빠른 시뮬레이터 없이도 된다**(전부 오프라인 로그 학습). 사전학습 시각 인코더를 쓰면 "분 단위" 시연으로도 기본 행동을 배운 사례가 있다. Thorkell처럼 구조화 지각 + 고수준 행동이면 필요한 데이터가 크게 줄어들 가능성이 높다(추정).

### Cited Findings
- **CS:GO 대규모 BC** (Pearce & Zhu, arXiv 2021-04, NeurIPS 2021 발표 페이지 있음) [논문]: 온라인 서버 사람 플레이 **5.5M 프레임(약 95시간)**과 소량의 깨끗한 전문가 시연으로 픽셀 → 행동 네트워크를 학습했다. 내장 AI 중간 난이도와 대등하고, 사람 같은 플레이 스타일을 보였다. CS:GO는 이전 FPS 연구 대비 시스템 요구가 100배라서 on-policy 데이터를 많이 만들 수 없고, 그래서 다수의 RL 알고리즘을 쓸 수 없었다고 명시했다. — [arXiv 2104.04258](https://arxiv.org/abs/2104.04258v2), [Microsoft Research](https://www.microsoft.com/en-us/research/?p=936048)
- **Visual Encoders for Data-Efficient IL in Modern Video Games** (Schäfer et al., 2023-12, 개정 2025-06-30) [논문]: Minecraft, CS:GO, Minecraft Dungeons에서 **"수 분 분량의 시연"**만으로 이미지 기반 모방학습을 했다. 저해상도 end-to-end도 그럭저럭 되고, DINOv2 같은 사전학습 인코더가 게임에 따라 크게 낫다. 학습 비용도 줄어든다. — [arXiv 2312.02312](https://arxiv.org/abs/2312.02312)
- **VPT** (OpenAI, 2022-06-23) [논문/공식]: 계약자 키·마우스 라벨 데이터 **약 2,000시간**으로 inverse dynamics model(IDM)을 학습했다. IDM으로 인터넷 영상 **70,000시간**에 행동 라벨을 붙여 BC foundation model을 만들었다. 이후 파인튜닝·RL로 다이아몬드 도구를 만들었다(숙련자 20분, 약 24,000 행동). — [arXiv 2206.11795](https://arxiv.org/abs/2206.11795), [GitHub](https://github.com/openai/Video-Pre-Training)
- **NitroGen** (NVIDIA·MineDojo 팀, arXiv 2026-01, CVPR 2026 oral) [논문]: 게임패드 입력 오버레이가 있는 공개 영상에서 행동을 자동 추출했다. 원본 71k시간 중 55%를 남겨 1,000+ 게임 **40,000시간**을 만들었다. 추출 정확도는 조이스틱 R² 0.84, 버튼 0.96이다. 모델은 SigLIP + flow-matching DiT, **약 500M** 파라미터이고, 16스텝 action chunk를 만든다. 과거 프레임을 1장보다 많이 넣어도 이득이 없었다. 처음 보는 게임에 파인튜닝하면 scratch 대비 과제 성공률이 최대 52% 상대 개선(3D 액션 RPG 평균 25%, 전투 52%, 내비 25%, 게임 고유 과제 5%)이다. 파인튜닝 데이터는 30시간부터 전체까지 실험했다. 저자 스스로 "빠르게 반응하는 system-1 감각 모델"이라 장기 계획과 언어 지시 수행은 없다고 했다. 데이터셋·가중치·시뮬레이터를 CC BY-SA 4.0으로 공개했다. 학습 GPU 시간은 공개하지 않았다. — [arXiv 2601.02427](https://arxiv.org/html/2601.02427v1), [프로젝트](https://nitrogen.minedojo.org/), [CVPR 2026](https://openaccess.thecvf.com/content/CVPR2026/html/Magne_NitroGen_An_Open_Foundation_Model_for_Generalist_Gaming_Agents_CVPR_2026_paper.html)
- **Lumine** (2025-11) [논문]: Qwen2-VL-7B 기반으로 원신의 사람 플레이를 학습했다. 원본 2,424시간 → 사전학습 **1,731시간** → 지시 수행 **200시간** → 추론(내적 독백) **15시간**의 3단계다. 컴퓨트는 H100으로 사전학습 5,376 GPU시간(64장 3.5일), 지시 960 GPU시간, 추론 64 GPU시간, 합계 **약 6,400 GPU시간**이다. 지각은 5 Hz, 행동은 action chunk로 30 Hz이고, 첫 행동까지 약 114 ms(추론 포함 약 234 ms)다. 몬드슈타트 5시간 메인 스토리를 사람 수준 효율로 끝냈다. 파인튜닝 없이 명조(100분 미션)와 붕괴: 스타레일(5시간 1장)도 완료했다. 한계로는 움직이는 공중 표적 전투, 높은 곳 물건의 공간 추론, 200 ms 지각 지연을 들었다. — [arXiv 2511.08892](https://arxiv.org/html/2511.08892v1)
- **SIMA 2** (Google DeepMind, 2025-11-13) [공식/논문]: Gemini 기반 범용 3D 게임 에이전트다. 사람 시연으로 시작한 뒤, 새 게임에서는 Gemini가 "Task Setter"로 할 만한 과제를 내고, 별도 보상 모델이 시도를 채점한다. 이 자기 생성 경험을 다음 세대 학습에 넣어 **사람 데이터 없이** 실패하던 과제를 개선한다. Genie 3로 생성한 세계에도 일반화했다고 보고했다. — [DeepMind 블로그](https://deepmind.google/blog/sima-2-an-agent-that-plays-reasons-and-learns-with-you-in-virtual-3d-worlds/), [arXiv 2512.04797](https://arxiv.org/abs/2512.04797v1)

### Inferences
- [추정] 위 데이터 규모(95시간~40k시간)는 **픽셀 → 저수준 키 입력**을 배우는 비용이다. Thorkell은 지각이 JSON이고 행동이 파라미터화된 스킬이므로 BC 대상이 "어떤 스킬을 어떤 대상에"라는 고수준 선택으로 줄어든다. 문제 크기는 텍스트 결정 증류(1절)에 가깝다.
- [추정] 빠른 시뮬레이터가 없다는 제약은 BC/KD에는 거의 문제가 되지 않는다(전부 오프라인 학습). 제약이 걸리는 쪽은 on-policy 데이터가 필요한 RL과 DAgger식 교정이다. 사람(리더)이 실게임에서 교정하는 소량의 DAgger 데이터가 현실적인 보완책이다.
- [추정] SIMA 2의 "LLM이 과제를 내고 LLM 보상 모델이 채점 → 성공 경험으로 재학습" 루프는 Thorkell에서 gemini 쿼터 안에서 축소판으로 할 수 있다. 하루 20회를 과제 생성과 사후 채점에 쓰는 방식이다.
- [추정] NitroGen(500M, 공개 가중치)은 게임패드식 픽셀 제어용이다. Thorkell의 반사·이동 계층을 대체하는 용도로는 맞지 않는다. 규칙 5(정보 동등성)와 구조화 지각 설계와도 어긋난다.

### Gaps
- VPT 학습 컴퓨트(GPU 수·일수)는 이번에 원문으로 확인하지 못했다. 검색 결과에 "1.6B 프레임 ≈ 2,000시간"이라는 서술이 있었는데, 2,000시간 × 20fps ≈ 1.44억 프레임과 맞지 않아 인용하지 않았다.
- NitroGen의 학습 GPU 시간과 추론 지연은 논문에 없었다.
- 구조화 상태(비픽셀) + 고수준 행동으로 3D 생존 게임을 BC한 데이터량 곡선은 찾지 못했다.

## 4. 실시간(가속 불가) 게임에서 고전 RL, 단순 시뮬레이터에서의 전이, 보상 설계

### Takeaway
실시간 게임에서 RL로 성공한 사례는 **대량 병렬 인스턴스**(GT Sophy: PS4 1,000대 이상)나 수일 이상의 연속 플레이에 기대고 있다. 인스턴스 하나뿐인 취미 프로젝트에서 실게임 RL은 비현실적이다. 현실적인 경로는 단순 시뮬레이터 + LLM이 설계한 환경·보상(EnvGen, Motif)에서 작은 정책을 학습하고, 실게임 로그로 보정하는 것이다.

### Cited Findings
- **Gran Turismo Sophy** (Sony AI, Nature 2022-02) [공식]: GT 학습은 **실시간**으로 진행된다. 전용 시스템 DART로 클라우드 PS4 **1,000대 이상**을 동시에 연결해 수백 개 실험을 병렬로 돌렸다. 아무것도 모르는 상태에서 한 트랙을 주행하기까지 약 1일, 상위 5% 사람 수준까지 약 2일, 최상위 드라이버와 대등해지기까지 다시 10–12일이 걸렸다. — [Sony AI 블로그](https://ai.sony/blog/training-the-worlds-fastest-gran-turismo-racer), [NVIDIA 블로그](https://developer.nvidia.com/blog/autonomous-ai-outraces-gran-turismo-world-champs/)
- **DreamerV3 Minecraft 다이아몬드** (Hafner et al., Nature 2025-04) [언론 요약]: 사람 데이터 없이 world model 기반 RL로 다이아몬드를 찾았다. 마일스톤 12개마다 +1 보상, 사망하거나 36,000스텝(약 30분)이 지나면 리셋했다. 첫 다이아몬드까지 "약 9일"의 플레이가 필요했다는 보도가 있다. — [Gigazine](https://gigazine.net/gsc_news/en/20250403-google-deepmind-dreamerv3/), [heise](https://heise.de/-10339154)
- **Ubisoft La Forge, AAA 내비게이션 Deep RL** (Alonso et al., IJCAI 2021) [논문/공식]: SAC(entropy 계수 학습, value 네트워크 없음)를 썼다. 관측은 3D occupancy map, 2D depth map, BoxCast/RayCast, 속도, 목표 상대·절대 위치, 직전 행동이다. 보상은 "지금까지 최소 거리보다 가까워진 만큼" + 상수 + 도착 보너스의 dense 보상이다. 120 m 맵 100%, 300 m×300 m×100 m 맵 90% 성공했고, AAA 게임 Hyper Scape 엔진에서도 시험했다. 총 학습 스텝과 엔진 가속 여부는 논문에 명시되지 않았다. — [arXiv 2011.04764](https://ar5iv.labs.arxiv.org/html/2011.04764), [Ubisoft La Forge](https://ubisoft.com/en-us/studio/laforge/news/6bRtGllmfhuDqTHRS6KVLj/deep-reinforcement-learning-for-navigation-in-aaa-video-games)
- **CS:GO** [논문]: 시스템 요구 때문에 on-policy 데이터를 충분히 만들 수 없어 RL 대신 BC를 택했다(3절 참조). — [arXiv 2104.04258](https://arxiv.org/abs/2104.04258v2)
- **EnvGen** (Zala et al., COLM 2024) [논문]: LLM이 학습용 환경 설정(지형, 초기 아이템, 자원 확률)을 만들고, 에이전트 성과를 피드백 받아 약한 기술 위주로 환경을 다시 조정한다. **4M 파라미터 PPO** 에이전트가 Crafter에서 32.2%를 기록해 GPT-4 에이전트 SPRING(27.3%)을 이겼다. LLM 호출은 **4회**뿐이다(SPRING 평균 2.7K회, ELLM 5M회). — [arXiv 2403.12014](https://arxiv.org/html/2403.12014v2), [GitHub](https://www.github.com/aszala/EnvGen)
- **Motif** (Klissarov et al., ICLR 2024) [논문]: LLM에게 이벤트 캡션 쌍 중 어느 쪽이 나은지 선호를 묻고, 이것을 보상 함수로 증류한다. 환경과 직접 상호작용할 필요가 없다. NetHack에서 이 내재 보상만 최대화한 에이전트가 게임 점수를 직접 최대화한 에이전트보다 높은 점수를 냈다. 프롬프트로 행동을 조정할 수 있다. — [arXiv 2310.00166](https://ar5iv.labs.arxiv.org/html/2310.00166), [Mila](https://mila.quebec/en/article/motif/)
- **NitroGen**에도 멀티게임 평가용 시뮬레이터가 포함되어 있지만, 평가 목적이다. — [프로젝트](https://nitrogen.minedojo.org/)

### Inferences
- [추정] Valheim은 인스턴스 하나에 실시간이다. GT Sophy식 병렬화(콘솔 1,000대)도 DreamerV3식 장시간 연속 학습도 현실적이지 않다. 실게임 RL은 하지 않는 편이 맞다. 저수준 내비·전투는 지금처럼 결정적 반사·스킬(검증된 네이티브 경로)이 맡는다.
- [추정] 2D 시뮬레이터는 "싸고 빠른 RL 환경" 역할로 쓸 수 있다. 다만 SPA의 전이 실패 결과로 보아, 시뮬에서 배울 대상은 고수준 선택(언제 후퇴, 무엇을 먼저 채집)으로 한정해야 한다. 그리고 시뮬과 실게임이 같은 명령·이벤트 규약을 쓴다는 현재 원칙(AGENTS.md)이 전이의 전제다.
- [추정] EnvGen 방식(LLM 호출 몇 번으로 시뮬 설정 다양화)은 gemini 하루 20회 쿼터와 잘 맞는다. Motif 방식(LLM 선호 → 보상 모델)은 실게임 로그 캡션에 오프라인으로 적용할 수 있어, 실시간 제약을 받지 않는다.
- [추정] Ubisoft의 dense 보상("최소 거리 갱신분")은 진동하지 않는 진척 보상의 예다. Eira 교훈("자기 카운터가 아니라 월드 변화로 진척을 센다")과 같은 방향이다.

### Gaps
- 실시간 전용 게임에서 단일 인스턴스로 RL을 성공시킨 취미 규모 사례는 찾지 못했다.
- Ubisoft 내비 RL의 학습 스텝·시간·병렬 인스턴스 수는 논문에 없었다.
- DreamerV3 "9일"은 언론 요약이고, 이것이 실시간 기준인지 환경 스텝 수 기준인지 원문으로 확인하지 못했다.

## 5. 학습 없는 자기개선: 스킬 라이브러리, 성공 사례 검색, 반성·규칙 메모리

### Takeaway
가중치를 건드리지 않는 방법(스킬 코드 라이브러리, 규칙 매뉴얼, insight 메모리, 실패 교훈 메모리)은 GPT-4급 모델로 Minecraft·ALFWorld에서 큰 개선을 보고했다(Voyager 기술 트리 15.3배 빠름, AutoManual ALFWorld 97.4%). 그러나 장기 게임 벤치마크(BALROG)에서는 최상위 모델도 32% 수준이다. 장기 게임 완주 사례(Gemini의 Pokémon)도 하네스와 사람 개입에 크게 기대고 있다.

### Cited Findings
- **Voyager** (Wang et al., 2023) [논문]: 자동 커리큘럼, 실행 가능한 코드로 된 스킬 라이브러리(성공 프로그램을 벡터 DB에 저장), 환경 피드백·실행 오류·자기 검증을 쓰는 반복 프롬프팅을 결합했다. 이전 SOTA 대비 고유 아이템 **3.3배**, 이동 거리 **2.3배**, 핵심 기술 트리 도달 최대 **15.3배** 빠름. — [arXiv 2305.16291](https://www.arxiv-vanity.com/papers/2305.16291)
- **ExpeL** (Zhao et al., 2023-08, AAAI 2024) [논문]: 성공·실패 경험을 모아 자연어 insight를 추출하고, 비슷한 성공 궤적을 in-context 예시로 불러온다. 파라미터는 업데이트하지 않는다. ALFWorld 범주별(ExpeL vs ReAct)로 put 61% vs 50%, clean 87% vs 61%, cool 76% vs 71%, look 0% vs 0%였다. 원천 과제에서 쌓은 지식이 목표 과제로 전이되었다. — [arXiv 2308.10144](https://arxiv.org/html/2308.10144v3)
- **AutoManual** (Chen et al., NeurIPS 2024) [논문]: Planner가 현재 규칙으로 실행 계획 코드를 짜고, Builder가 상호작용 결과로 규칙을 갱신하며, Formulator가 규칙을 매뉴얼로 정리한다. 규칙 환각을 줄이려고 case-conditioned prompting을 쓴다. 시연 **1개**에서 시작해 ALFWorld 성공률 **97.4%**(GPT-4-turbo), **86.2%**(GPT-3.5-turbo). — [arXiv 2405.16247](https://arxiv.org/html/2405.16247v4), [GitHub](https://github.com/minghchen/automanual)
- **ReasoningBank** (Google, 2025-09, ICLR 2026) [논문/공식]: 스스로 판정한 성공과 **실패** 경험에서 일반화 가능한 추론 전략을 메모리로 뽑는다. 실패는 "예방 교훈"으로 바꾼다. 과제마다 더 많은 시도를 해서 대비 신호를 늘리는 memory-aware test-time scaling(MaTTS)도 제안한다. 웹 브라우징·SWE 벤치에서 원본 궤적 저장이나 성공 루틴만 저장하는 방식보다 낫다고 보고했다(이번에 수치는 확인 못 함). — [Google Research 블로그](https://research.google/blog/reasoningbank-enabling-agents-to-learn-from-experience/), [arXiv 2509.25140](https://arxiv.org/abs/2509.25140)
- **BALROG** (Paglieri et al., ICLR 2025) [논문/언론]: 장기 게임 벤치마크(BabyAI, Crafter, NetHack 등)에서 최고 GPT-4o가 전체 평균 **32%**, Crafter 진척 **33%**였다. NetHack에서는 의미 있는 진척이 거의 없었다(최고 개별 런은 던전 3층, 경험치 4레벨). 시각 입력을 주면 오히려 나빠지는 모델이 여럿이었다. 실패 원인은 체계적 탐색, 장기 계획, 전투 위치 선정, **알고 있는 규칙을 플레이 중에 활용하지 못함**이었다. — [arXiv 2411.13543](https://arxiv.org/html/2411.13543v1), [The Decoder](https://the-decoder.com/ai-models-stumble-in-complex-game-tests-scoring-low-across-the-board/)
- **Gemini Plays Pokémon** (2025-05-02) [언론/커뮤니티]: Gemini 2.5 Pro가 Pokémon Blue를 **106,000+ 행동, 813시간**에 완주했고, 최적화한 2회차는 406.5시간이었다. 하네스가 스크린샷, RAM 데이터, 단순화한 미니맵, Gemini 하위 에이전트(경로 찾기, 퍼즐)를 제공했다. 개발자(구글과 무관한 개인)가 탈출 아이템 사용 제한, 버그 교정 등으로 개입했다. — [TechCrunch](https://techcrunch.com/2025/05/03/googles-gemini-has-beaten-pokemon-blue-with-a-little-help), [The Decoder](https://the-decoder.com/googles-reasoning-llm-gemini-2-5-pro-beats-pokemon-blue-with-a-little-help/), [dbreunig 분석](https://www.dbreunig.com/2025/06/17/an-agentic-case-study-playing-pok%C3%A9mon-with-gemini.html)
- **AgentDistill** (2025-06) [논문]: 교사 에이전트가 만든 재사용 가능한 MCP 도구 상자(MCP-Box)를 학생에게 학습 없이 넘긴다. 학생이 PathVQA에서 52.7%로 교사(52%)와 대등했다. — [arXiv 2506.14728](https://arxiv.org/pdf/2506.14728)

### Inferences
- [추정] gemini 하루 20회 제약에서는 학습 없는 방법이 가장 효율이 높다. 이미 검증된 스킬(따라와, 기다려, 나무 N개)을 Voyager식 "검증된 스킬 라이브러리"로 늘린다. 실게임 실패 리포트는 ReasoningBank식 "실패 교훈" 규칙으로 정리해 플래너 프롬프트에 넣는다. 이렇게 하면 실게임 시간도 모델 호출도 거의 늘지 않는다.
- [추정] BALROG의 "알고 있는 규칙을 못 씀"은 메모리가 프롬프트에 있어도 쓰이지 않을 수 있다는 뜻이다. 규칙은 플래너 프롬프트에만 두지 말고, 가능한 것은 **코드 검증기·사전조건**(현재 플래너 출력 검증기와 같은 위치)으로 옮기는 편이 확실하다.
- [추정] Pokémon 사례는 장기 완주의 큰 몫이 하네스(미니맵, 경로 찾기 하위 에이전트, RAM 정보)에 있음을 보여 준다. Thorkell의 구조화 지각, 경로점 귀환, `leader_on_map` 같은 설계가 같은 역할을 한다. 다만 정보 동등성(규칙 5)을 넘는 RAM식 정보는 쓰지 않는다.
- [추정] 학습 없는 메모리에서 나온 "성공 궤적"은 그대로 1절 증류의 깨끗한 학습 데이터가 된다. 두 방법은 대체재가 아니라 파이프라인이다(메모리로 성공률을 올리고, 성공 로그를 laya로 증류).

### Gaps
- Reflexion, Agent Workflow Memory의 수치는 이번 세션에서 원문으로 확인하지 않아 넣지 않았다.
- 실시간 3D 생존 게임에서 학습 없는 메모리 방법의 효과를 정량화한 연구는 찾지 못했다. Voyager는 Mineflayer API(비시각, 코드 행동)이고, ExpeL·AutoManual은 텍스트 환경이다.
- ReasoningBank의 벤치별 개선 수치는 확인하지 못했다.

## 6. Mac(MLX LoRA/QLoRA) vs 대여 GPU 파인튜닝 처리량, 결정 모델의 캘리브레이션(ECE)

### Takeaway
MLX는 LoRA/DoRA/full과 (양자화 모델을 넣으면 자동으로) QLoRA를 지원한다. 0.8B–4B 4-bit LoRA 실측은 약 115–475 tok/s(M1 64GB), 피크 메모리 4–11GB라서 M4 Pro 24GB에서 laya급(0.3–0.4B) SFT/KD는 충분히 돌아갈 것으로 보인다(추정). RL(GRPO)과 7–8B 학습은 대여 GPU가 현실적이다. 캘리브레이션은 프롬프트만으로는 부족하고, 약 1,000개의 채점된 예시로 LoRA 학습하면 좋아진다는 근거가 있다. 결정 모델은 held-out 로그로 ECE를 재고 temperature scaling을 하는 것이 기본이다.

### Cited Findings
- **mlx-lm LORA.md** [공식]: `--fine-tune-type`은 `lora`(기본)/`dora`/`full`이다. `--model`이 양자화 모델이면 자동으로 QLoRA가 된다. 메모리 절약 수단은 batch 축소(기본 4 → 2/1), `--grad-accumulation-steps`, `--num-layers`(기본 16 → 8/4), 긴 예시 분할, `--grad-checkpoint`다. 데이터 형식은 `chat`/`tools`/`completions`/`text` JSONL을 지원한다. 문서의 유일한 수치는 M1 Max 32GB, batch 1, num-layers 4에서 WikiSQL 약 **250 tok/s**다. DPO/GRPO 언급은 없다. — [mlx-lm LORA.md](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md)
- **sciences44/mlx-lora-finetune** [커뮤니티 실측]: M1 64GB, LoRA rank 8, 16층, lr 1e-5, 600 iter, 학습 5,000 예시(Text-to-SQL) 설정이다. Qwen3.5-0.8B 4-bit는 약 **475 tok/s**, 피크 3.9GB. 2B는 약 180 tok/s, 5.9GB. 4B는 약 115 tok/s, 11.1GB. Mistral-Nemo-12B 4-bit는 약 210 tok/s, 8.2GB. 학습 시간은 600 iter에 8–15분이다(표에는 0.8B가 15분, 2B가 8분으로 나와 서로 맞지 않는다. 원문 표 그대로 옮김). — [GitHub](https://github.com/sciences44/mlx-lora-finetune)
- **M4 Pro 24GB 추론 속도** [커뮤니티]: Qwen3.5 9B 8-bit 생성 30–40 tok/s, 27B 4-bit 18–25 tok/s. 학습이 아니라 생성 속도다. — [Contra Collective](https://contracollective.com/blog/m4-m5-pro-local-ai-inference-mlx-2026), [willitrunai](https://willitrunai.com/blog/qwen-3-5-mlx-apple-silicon-guide)
- **Mac에서 RL** [커뮤니티]: `mlx-lm-lora` 패키지가 SFT, DPO, CPO, ORPO, PPO, GRPO를 지원한다고 소개되어 있다. MLX LoRA Studio는 GRPO·Online DPO·PPO 등 10개 알고리즘과 QLoRA/DoRA/QAT를 지원한다. 성능 수치는 확인하지 못했다. — [mlx-lm-lora (piwheels)](https://www.piwheels.org/project/mlx-lm-lora), [MLX LoRA Studio](https://github.com/Goekdeniz-Guelmez/MLX-LoRA-Studio)
- **대여 GPU** [공식, 벤더 자체 벤치]: Unsloth는 HF+Flash Attention 2 대비 약 2배 빠르고 VRAM을 최대 70% 줄인다고 주장한다. 예로 Llama-2 7B, A100 40GB에서 1.87배 속도, VRAM −39.3%를 든다. — [Unsloth Benchmarks](https://unsloth.ai/docs/basics/unsloth-benchmarks), [HF 블로그](https://huggingface.co/blog/unsloth-trl)
- 참고 규모 [논문]: Agent Distillation은 0.5B–7B를 LoRA r64로 A100 80GB 4장에서 학습했다. SPA는 1.5B 1,000 RL 스텝에 단일 H100 약 12시간, SOD는 0.6B/1.7B를 H20 8장에서 2–3일 걸렸다. — [2505.17612](https://arxiv.org/html/2505.17612), [2510.15047](https://arxiv.org/html/2510.15047v1), [2605.07725](https://arxiv.org/html/2605.07725v1)
- **캘리브레이션: 학습이 필요하다** (Kapoor et al., NeurIPS 2024) [논문]: 프롬프팅만으로는 LLM 캘리브레이션이 부족하다. 정답·오답이 섞인 **약 1,000개**의 채점 예시로 파인튜닝하면 기준선을 이기는 불확실성 추정이 생기고, 새 질문 유형으로도 일반화된다. 모델 특징을 통과하는 학습(LoRA)이 필요하고, 선형 probe만으로는 부족하다. — [arXiv 2406.08391](https://arxiv.org/html/2406.08391v3), [NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2024/hash/9c20f16b05f5e5e70fa07e2a4364b80e-Abstract.html)
- **정렬·LoRA와 캘리브레이션** [논문, 검색 요약]: 선호 정렬(DPO 등) 후 모델이 과신하는 경향이 보고되었다. LoRA 적응은 full 파인튜닝과 캘리브레이션이 대등하다. 적응 공간을 제한하면(예: LoRA의 A 행렬 동결) ECE가 개선되지만 정확도와 맞바꾼다. — [arXiv 2505.01997](https://arxiv.org/html/2505.01997v3), [arXiv 2603.19278 (HypeLoRA)](https://arxiv.org/html/2603.19278v2)
- **ECE와 temperature scaling 실무** [커뮤니티]: ECE는 확신도 구간별(0–10%, …) 정확도와 확신도 차이의 가중 평균이다. temperature scaling은 held-out 세트에서 NLL을 최소화하는 단일 T를 학습하고 logits를 T로 나눈다(T>1이면 과신 완화). 운영 모델 ECE는 0.05–0.20 범위라는 블로그 주장이 있다(출처 불명확, 커뮤니티 의견). — [tianpan.co](https://tianpan.co/blog/2026-04-20-llm-calibration-production-overconfidence)
- temperature scaling 원전 [논문, 이번 세션에서 재확인 안 한 배경 지식]: Guo et al., "On Calibration of Modern Neural Networks"(2017). — [arXiv 1706.04599](https://arxiv.org/abs/1706.04599)

### Inferences
- [추정] laya(322–421M)는 위 실측의 0.8B보다 작다. M4 Pro 24GB에서 MLX LoRA 또는 full 파인튜닝까지 메모리 여유가 크다. M1 0.8B 약 475 tok/s를 하한으로 잡고, 결정 샘플 1건이 약 500토큰이면 1만 건(약 500만 토큰)의 1 epoch는 약 3시간 이내다. M4 Pro가 M1보다 빠를 가능성이 높지만, M4 Pro 학습 실측은 찾지 못했다.
- [추정] 역할을 이렇게 나누는 것이 현실적이다. SFT/KD(soft label)와 캘리브레이션 실험은 Mac에서, 7–8B 학습이나 시뮬레이터 기반 GRPO는 대여 GPU(H100급, 실험당 수 시간~하루)에서 한다.
- [추정] laya가 비생성(분류·점수) 모델로 쓰인다면, 선택지별 점수의 softmax 확률에 대해 ECE를 재고 temperature scaling을 하면 된다. 이 확률을 "Jev와 불일치하거나 확신이 낮으면 플래너·반사에 넘김"이라는 게이트로 쓰려면, 학습 로그와 **다른 날·다른 세이브**에서 뽑은 held-out 세트로 캘리브레이션해야 한다(홀드아웃 시드로 튜닝하지 않는다는 Eira 교훈과 같은 원칙).
- [추정] 교사(Jev) 확률 자체도 캘리브레이션되어 있다는 보장이 없다. soft target으로 쓰기 전에, 결과(월드 변화로 검증된 성공·실패)와 비교해 Jev의 ECE를 먼저 재 보는 것이 좋다.

### Gaps
- M4 Pro(24GB)에서 MLX LoRA 학습 tok/s를 직접 잰 공개 수치는 찾지 못했다. M1/M1 Max 수치와 M4 Pro 추론 수치만 있다.
- H100/A100에서 0.5–8B LoRA·QLoRA의 tok/s 절대값(Unsloth 공식 표의 구체 숫자)은 이번 검색 결과에 없었다.
- 게임 결정 모델(선택지 분류)의 ECE를 보고한 연구는 찾지 못했다. 위 캘리브레이션 근거는 QA·분류 일반 연구다.
- 클라우드 GPU 시간당 가격(2026-10 기준)은 조사하지 않았다.
