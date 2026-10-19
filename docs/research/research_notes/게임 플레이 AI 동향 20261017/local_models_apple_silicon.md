# Apple Silicon(M4 Pro 24GB)에서 게임 두 개와 함께 돌릴 소형 로컬 모델·런타임: 2026-10-17 갱신

조사일: 2026-10-17
기준선: `../게임 플레이 AI 기술 동향 2026/local_models_apple_silicon.md`(2026-10-10 기준, 2026-10-11 작성)

갱신 표기
- [unchanged]: 기준선 내용이 지금도 맞다.
- [changed]: 그 뒤 사실이 바뀌었다.
- [new]: 새로 나왔거나 기준선이 놓쳤다.
- [corrected]: 기준선이 틀렸다.

출처 표기(기준선과 같음)
- [공식]: 개발사 카드·문서·저장소·릴리스 노트
- [커뮤니티]: 개인 벤치·이슈·큐레이션 목록
- [3자]: 언론·블로그·애그리게이터
- [추정]: 이 노트에서 계산하거나 추론한 값
- [로컬]: 이 Mac에서 잰 값
- "검색 요약"은 원문을 열지 못하고 검색 엔진 요약만 본 것이다.

이 Mac은 M4 Pro(CPU 12코어, GPU 16코어), 통합 메모리 24GiB, macOS 26.2다 [로컬, 기준선 2026-10-11].

범위: 음성(ASR, TTS, speech-to-speech. 기준선 Q4)은 이번 갱신에서 다시 확인하지 않았다. 이번에 본 역할은 타입 결정, 한국어 명령 파싱, 짧은 한국어 답, 폴백 플래너, 임베딩이다.

---

## Q0. 기준선(2026-10-10)의 핵심 주장은 지금도 맞는가

### Takeaway
대부분은 그대로다. 다만 Thorkell 설계에 영향을 주는 변화가 네 가지 있다.
1. Jev와 같은 wire(`/v1/systemone`)로 도는 **로컬 결정 모델**이 생겼다. Ollama 0.35 이상에서 Tev1 0.8B/4B, Nimble 9B, Clef-flash 9B를 쓸 수 있다.
2. Apple Foundation Models는 **Python에서 바로 부를 수 있다**(`apple-fm-sdk`). 따라서 기준선의 "Swift 전용"은 틀렸다. macOS 27의 새 온디바이스 모델은 컨텍스트가 8,192토큰이다.
3. M4 Pro에서 Qwen3.5-4B/9B 4비트를 잰 수치가 확인됐다. 최대 메모리가 4.4/6.7GiB여서, 가중치 크기로 잡은 기준선 예산보다 크다.
4. 기준선은 Kakao Kanana-2 소형(1.3B/3B, 2026-07-27)을 놓쳤다.

### Cited Findings

| # | 기준선 주장 | 상태 | 재확인 근거 |
|---|---|---|---|
| 1 | Qwen 최신 소형 dense는 Qwen3.5 0.8~9B(2026-03, Apache-2.0)다. 3.6~3.8에는 10B 미만 dense가 없다. | [unchanged] | Qwen 4(Max/Flash/Plus/27B)는 2026-09-22 Apsara에서 발표만 했다. 가중치, 날짜, 카드는 없다 — [pasqualepillitteri](https://pasqualepillitteri.it/en/news/17552/qwen-4-alibaba-apsara-en); [orcarouter](https://www.orcarouter.ai/blog/qwen-4-max-lineup-announced-apsara-2026) [3자]. 2026-10-12에도 출시 전이었다 — [yottalabs](https://www.yottalabs.ai/post/qwen-4-27b-release-date-specs-hardware-what-is-known-2026) [3자] |
| 2 | Gemma 4 출시일(03-31, MTP 04-16, 12B 06-03), EmbeddingGemma 2(10-06) | [unchanged] | 2026-10-17에 다시 연 공식 릴리스 페이지의 마지막 항목은 2026-10-06 EmbeddingGemma 2다. Gemma 4 신규 항목은 06-03 이후 없다 — [ai.google.dev releases](https://ai.google.dev/gemma/docs/releases) [공식] |
| 3 | Apple Foundation Models는 Swift 전용이라 Python 두뇌와 붙이려면 헬퍼 프로세스가 필요하다. | [corrected] | Python SDK `apple-fm-sdk`가 있다. Apache-2.0이고 요구사항은 macOS 26.0+, Xcode 26.0+, Python 3.10+다 — [GitHub apple/python-apple-fm-sdk](https://github.com/apple/python-apple-fm-sdk) [공식]. 발표는 WWDC26 session 334다 — [Apple](https://developer.apple.com/videos/play/wwdc2026/334/) [공식] |
| 4 | Apple 온디바이스 컨텍스트는 4,096토큰이다. | [changed] | WWDC26 session 241 코드 예시에서 `SystemLanguageModel().contextSize`가 `8192`로 찍힌다(새로 만든 모델) — [Apple](https://developer.apple.com/videos/play/wwdc2026/241/) [공식]. 4,096은 macOS 26 모델 값이다 — [Gigazine 2026-04-08](https://gigazine.net/gsc_news/en/20260408-apfel-mac) [3자] |
| 5 | Apple Intelligence는 한국어를 지원한다. | [unchanged] | macOS 27 지원 언어 목록에 한국어가 있다 — [Apple Support 121115 (2026-09-14)](https://support.apple.com/en-us/121115) [공식] |
| 6 | mlx-lm 서버에는 `response_format`/JSON 스키마가 없다. | [unchanged] | 이슈 #1007은 아직 열려 있다. 연결된 PR은 없고 마지막 댓글은 2026-09-21이다 — [mlx-lm #1007](https://github.com/ml-explore/mlx-lm/issues/1007) [공식 저장소]. v0.32.0~0.32.2(2026-10-15~16) 노트에도 없다 — [mlx-lm releases](https://github.com/ml-explore/mlx-lm/releases) [공식] |
| 7 | 스키마 제약, 프롬프트 캐시, 확률 출력을 한 서버에서 다 갖춘 것은 `llama-server`다. | [unchanged] (README는 다시 열지 않음) | 최신 빌드는 b11702(2026-10-17)다. 그 사이 기능 제거 흔적은 없다 — [llama.cpp releases](https://github.com/ggml-org/llama.cpp/releases) [공식] |
| 8 | Ollama의 구조화 출력은 확인하지 못했다. | [new] | v0.34.4(2026-09-23)에서 thinking 모델의 구조화 출력이 한 번에 적용되고 XGrammar가 갱신됐다 — [Ollama releases](https://github.com/ollama/ollama/releases) [공식]. MLX runner의 구조화 출력은 v0.33.2, logprobs는 v0.21.1에 들어갔다 — [frontierwisdom](https://frontierwisdom.com/ollama-v0-21-1-release/) [3자, 검색 요약] |
| 9 | Ollama 0.19는 safetensors를 MLX로, GGUF를 llama.cpp로 보낸다. | [changed] | v0.40.0부터 Apple Silicon에서는 MLX가 지원하는 아키텍처를 **기본으로 MLX에서** 돌린다. gemma4, qwen3.5, qwen3.6이 포함된다 — [Ollama v0.40.0](https://github.com/ollama/ollama/releases/tag/v0.40.0) [공식] |
| 10 | Gemma 4 MTP 체크포인트가 무엇인지 확인하지 못했다. | [new] | speculative decoding용 drafter(assistant)다. vllm-metal은 Gemma 4 MTP를 지원하고, E4B 출력 tok/s가 동시성 1에서 +20%다 — [vLLM blog 2026-09-22](https://vllm.ai/blog/2026-09-22-vllm-metal-v0-28-0) [공식]. llama.cpp는 06-07에 31B/26B MTP를, 06-08에 E2B/E4B assistant(PR #24282)를 병합했다 — [aiweekly](https://aiweekly.co/alerts/llamacpp-adds-gemma-4-e2be4b-mtp-assistant-support) [3자] |
| 11 | "M4 Pro 48GB에서 9B 49.76 / 4B 83.45 tok/s"는 원문을 확인하지 못했다. | [corrected→확인] | 원문은 Rapid-MLX README다. TTFT와 최대 메모리도 함께 있다(Q3 참고) — [Rapid-MLX](https://github.com/raullenchai/Rapid-MLX) [커뮤니티] |
| 12 | 조합 (A)에서 Qwen3.5-4B 4비트를 약 2.5~3GB + KV 0.3~0.5GB로 잡았다. | [corrected] | 실측 최대 메모리는 4.4GiB(2K 입력 → 512 출력)이고, 9B는 6.7GiB다 — [Rapid-MLX](https://github.com/raullenchai/Rapid-MLX) [커뮤니티] |
| 13 | Kanana-2는 총 32B, 활성 3B MoE다. | [corrected] | 30B-A3B 외에 소형 1.3B/3B(base, instruct)가 2026-07-27에 공개됐다 — [HF kakaocorp/kanana-2-3b-base](https://huggingface.co/kakaocorp/kanana-2-3b-base) [공식] |
| 14 | Jev는 2026-09-15 공개, 입력 100만 토큰당 0.042달러, 70~500ms다. | [unchanged] + [new] | 가격은 같다 — [OpenRouter](https://openrouter.ai/ko-KR/compare/typesafe/jev-1.13) [3자]. Jev 1.14.0이 프리뷰로 나왔다(아래 Q4) |
| 15 | laya 421M/322M, Apache-2.0, `laya-serve`는 `/v1/systemone`이다. | [unchanged] + [changed] | 런타임 0.3.20이 나왔다(체크포인트는 그대로). `laya-typed-decisions` 체크포인트가 있다 — [HF laya](https://huggingface.co/convaiinnovations/laya) [공식] |
| 16 | 결정 전용 모델은 사실상 Jev(클라우드)와 laya(오픈) 두 개다. | [changed] | OpenAI, Microsoft, Cloudflare, Together, Bespoke, Liquid 등이 9~10월에 결정 모델을 냈다(Q4) — [awesome-system-one](https://github.com/andyrewlee/awesome-system-one) [커뮤니티 큐레이션] |
| 17 | Mac에서 게임과 LLM을 같이 돌린 프레임 측정은 없다. | [unchanged] | 2026년 Mac 측정은 이번에도 찾지 못했다(Q6) |
| 18 | 2026년 한국 소형 신작(EXAONE, HyperCLOVA X SEED)은 확인하지 못했다. | [unchanged] | 2026년 EXAONE은 4.5(33B)와 도메인 모델이다. 소형 온디바이스 신작은 없다 — [opper](https://opper.ai/model-releases/lg-ai-research); [Korea Times 2026-09-14](https://www.koreatimes.co.kr/business/companies/20260914/lg-ai-research-seeks-to-address-industrial-challenges-with-expert-ai-models) [3자]. SEED도 2026년 소형 신작은 확인되지 않았다 — [hokai](https://hokai.io/hub/models/hyperclova-x) [3자] |

### Inferences
- [추정] 기준선의 큰 방향("4B급 로컬 + 클라우드 플래너, 결정은 Jev → 증류")은 유지된다. 다만 "증류해야만 로컬 결정이 가능하다"는 전제가 깨졌다. Ollama에 Jev와 같은 API를 쓰는 기성 모델이 있어서, base URL만 바꿔 바로 비교 실험을 할 수 있다(Q4, Q7).
- [추정] 메모리 예산표는 가중치가 아니라 실측 최대 메모리로 다시 짜야 한다(Q6).

### Gaps
- 기준선 Q2의 llama.cpp `server/README.md` 기능표(json_schema, n_probs, slots)는 이번에 원문을 다시 열지 않았다. 최근 릴리스 노트에 제거 흔적이 없다는 데까지만 확인했다.
- 기준선의 SiliconBench(arXiv 2609.19169), john-rocky 벤치, omlx #2264는 다시 확인하지 않았다.

---

## Q1. ≤9B 소형 모델 후보: 9~10월 신작과 후보별 사실표

### Takeaway
2026-09-01~10-17 사이에 9B 이하 범용 생성 모델의 신작은 사실상 없었다. Qwen 4는 발표만 했고, Gemma 4는 06-03 이후 신작이 없으며, Phi, SmolLM, Ministral, Llama의 소형 신작도 찾지 못했다. 한국어 소형으로는 기준선이 놓친 Kanana-2 3B/1.3B(2026-07-27)가 공개 수치가 가장 강하다. KoMT-Bench가 6.92/6.54로 Qwen3.5-2B의 5.21보다 높다. 다만 라이선스가 "온디바이스 임베드 제공"에 별도 계약을 요구한다. 범용 축은 여전히 Qwen3.5-4B/9B와 Gemma 4 E2B/E4B다.

### Cited Findings

**새로 나왔거나 놓친 모델**
- [new, 기준선 누락] Kanana-2 소형(Kakao) [공식, 자체 보고] — [HF kanana-2-3b-base](https://huggingface.co/kakaocorp/kanana-2-3b-base); [GitHub kakao/kanana-2](https://github.com/kakao/kanana-2/)
  - 공개일: 가중치와 블로그 모두 2026-07-27. 언론 보도는 07-28이다 — [EDAILY](https://en.edaily.co.kr/news/eda202607285268/) [3자].
  - 크기: 3B와 1.3B(3B에서 압축), 각각 base/instruct. 카드에 0.9B도 적혀 있지만 공개되지 않았다.
  - 컨텍스트: 32,768토큰. sliding window(1024)와 full attention을 3:1로 섞었다. 32K에서 KV 캐시가 최대 약 72.7% 줄었다고 주장한다.
  - 한국어 전용 토크나이저로 한국어 처리 효율이 30% 이상 올랐다고 주장한다 — [EDAILY](https://en.edaily.co.kr/news/eda202607285268/) [3자]
  - Instruct 한국어 점수(CoT)

    | 벤치마크 | 3B | 1.3B | Qwen3.5-2B |
    |---|---|---|---|
    | KoMT-Bench | 6.92 | 6.54 | 5.21 |
    | KMMLU | 43.32 | 42.79 | 41.75 |
    | HAERAE v1.0 | 43.75 | 44.89 | 27.84 |
    | KoSimpleQA | 22.29 | 17.81 | 3.21 |

  - Base 점수: KMMLU(5-shot) 47.92/44.17, HAE-RAE 80.66/75.34. 비교 대상 Qwen3-1.7B-Base는 43.08/55.54다.
  - 도구 호출: BFCL-v3 Live 71.94/69.64(Qwen3.5-2B 66.96), Multi-Turn 17.12/5.50
  - Instruct 범용 점수: MT-Bench 7.15/6.83, IFEval 80.96/77.63 — [braindetox 2026-08-05](https://braindetox.kr/en/posts/kakao_kanana2_open_models_2026.html) [3자, 카드 인용]
  - 런타임: Transformers 4.57.0 이상, vLLM, SGLang, Docker Model Runner. llama.cpp, Ollama, LM Studio용 양자화본 링크가 있다. MLX는 언급이 없다.
  - 라이선스는 KananaOpenLicense다 — [braindetox 2026-08-05](https://braindetox.kr/en/posts/kakao_kanana2_open_models_2026.html) [3자, 라이선스 조항 요약]
    - 자기 서비스 구축·운영(4.2)에는 별도 계약이 필요 없다.
    - API·클라우드 재판매, SI·온프레미스, **온디바이스 임베드 제공**(4.1)에는 별도 상업 라이선스가 필요하다.
    - "Powered by Kanana"를 표시하고, 파생 모델 이름 앞에 "Kanana"를 붙여야 한다.
- [new, 3자] IBM Granite 4.2(3B, 8B, 30B dense)
  - 2026-08-25 공개, Apache-2.0, 128K. 8B는 한국어를 포함한 12개 언어를 지원한다고 나온다 — [intuitionlabs](https://intuitionlabs.ai/articles/ibm-granite-4-2-model-guide); [OpenRouter granite-4.2-8b](https://openrouter.ai/ibm-granite/granite-4.2-8b) [3자]
  - IBM 공식 카드로는 확인하지 못했다.
- [new, 기준선 누락, 2025년 모델] SKT A.X 4.0 Light
  - 7B(3자 표기 7.6B), Qwen2.5 기반 한국어 대량 학습, Apache-2.0, 16K, 도구 호출 지원. 2025-07-03 공개 — [HF skt/A.X-4.0-Light](https://huggingface.co/skt/a.x-4.0-light) [공식, 검색 요약]
  - A.X K1(519B)은 공개 계획만 있다 — [SKT newsroom](https://news.sktelecom.com/en/2742) [공식, 검색 요약]
- [new, 3자] Liquid AI LFM2.5-VL-3B(3.1B 비전-언어, 2026-08-12) — [orcarouter](https://www.orcarouter.ai/blog/liquid-ai-d1-omni-600m-vs-lfm2-5-vl-3b) [3자]. 결정 모델 d1은 Q4에서 다룬다.
- [new] 예산 밖의 신작(참고용)
  - Gemma 4 12B: M4 Pro 4비트 최대 11.9GiB — [Rapid-MLX](https://github.com/raullenchai/Rapid-MLX) [커뮤니티]
  - Nemotron 3.5 Lightning: 30B-A3B — [Unsloth](https://unsloth.ai/docs/models/nemotron-3.5) [3자]. "Nemotron 3.5 Bolt"(10-15라는 3자 언급)는 확인하지 못했다.
- [unchanged] Qwen3.5-4B/9B, Gemma 4 E2B/E4B의 카드 수치(MMLU-Pro, BFCL-V4, τ2 등)는 기준선과 같다. 카드가 바뀐 흔적은 없다 — [HF Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B); [HF gemma-4-E4B-it](https://huggingface.co/google/gemma-4-E4B-it) [공식, 기준선 출처]
- [unchanged] EXAONE 4.0 1.2B(NC 라이선스)와 HyperCLOVAX-SEED 0.5B/1.5B가 여전히 각 사의 최신 소형이다(Q0 표 #18).
- 구조화 출력의 크기 하한 경고: LM Studio 문서는 "7B 미만 LLM은 구조화 출력을 못 하는 경우가 많다"고 적는다 — [LM Studio docs](https://lmstudio.ai/docs/developer/openai-compat/structured-output) [공식, unchanged]

**후보별 사실표** (속도와 메모리는 출처를 밝힌 실측만 적고, 나머지는 [추정]으로 표시한다)

| 모델 | 크기 | 라이선스 | 한국어 근거 | 구조화 출력·도구 | 메모리(4비트) | M3/M4 Pro 속도 | logprobs |
|---|---|---|---|---|---|---|---|
| Qwen3.5-4B | 4B, 262K | Apache-2.0 | 201개 언어 [공식]. 한국어 단독 점수 없음 | 도구 호출, BFCL-V4 50.3 [공식]. 스키마는 런타임 문법으로 강제 | **최대 4.4GiB**(2K→512) [커뮤니티] | M4 Pro 48GB, MLX: TTFT 0.75s(512 입력), 생성 83.45 tok/s [커뮤니티] | 런타임 의존(아래) |
| Qwen3.5-9B | 9B | Apache-2.0 | MMMLU 81.2 [공식] | BFCL-V4 66.1, τ2 79.1 [공식] | **최대 6.7GiB** [커뮤니티]. mlx-lm 최대 5.24GB(M3 Ultra) [3자] | 같은 환경 TTFT 1.37s, 49.76 tok/s [커뮤니티] | 런타임 의존 |
| Qwen3.5-2B | 2B | Apache-2.0 | KoMT 5.21, KMMLU-CoT 41.75(Kakao 측정) [공식, 경쟁사 측정] | BFCL-v3 Live 66.96 [같은 출처] | 약 1.5~2GB [추정] | M4 Pro 실측 없음 | 런타임 의존 |
| Gemma 4 E2B / E4B | 유효 2.3B / 4.5B | Apache-2.0 | 140개 이상 사전학습, 35개 이상 지원 [공식] | 네이티브 도구 사용. E4B τ2 42.2 [공식] | E4B 약 6GB(Q4, 3자) | E4B 49~57 tok/s(feasibility 문서 수치) [커뮤니티, 다시 확인 못 함] | 런타임 의존 |
| Kanana-2-3B / 1.3B | 3B / 1.3B, 32K | KananaOpenLicense(온디바이스 임베드 제공은 별도 계약) | **KoMT 6.92/6.54** [공식] | BFCL-v3 Live 71.94/69.64 [공식] | 약 2GB / 약 1GB [추정] | 실측 없음 | 런타임 의존(GGUF 경로) |
| EXAONE 4.0 1.2B | 1.2B, 64K | NC | KMMLU-Redux 40.4 [공식, 기준선] | 도구 호출. BFCL-v3 55.7 | 약 1GB [추정] | 없음 | 런타임 의존 |
| HyperCLOVAX-SEED 1.5B | 1.5B, 16K | 자체(상업 가능) | KMMLU 0.3933 [공식, 기준선] | 미기재 | 약 1GB [추정] | 없음 | 런타임 의존 |
| A.X 4.0 Light | 7B, 16K | Apache-2.0 | 한국어 대량 학습 [공식, 검색 요약] | 도구 호출 | 약 4.5~5GB [추정] | 없음 | 런타임 의존 |
| Granite 4.2 3B / 8B | 3B / 8B, 128K | Apache-2.0 [3자] | 8B가 한국어 지원 언어에 포함 [3자] | 미확인 | 약 2 / 5GB [추정] | 없음 | 런타임 의존 |
| Apple 온디바이스 모델 | 약 3B [3자] | OS 내장 | 한국어 지원 언어 [공식/3자, Q2] | `@generable` 가이드 생성, Tool [공식] | OS 상주. 앱 추가분은 미측정 | Mac 실측 없음 | 노출 안 됨(Q2) |

- logprobs 공통 사항: 오픈 웨이트 모델은 런타임이 확률을 낸다.
  - `llama-server`: `n_probs`, `top_logprobs`
  - mlx-lm 서버: `logprobs` 1~10
  - Ollama MLX runner: v0.21.1부터 [3자]
  - 출처: [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md); [mlx-lm SERVER.md](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/SERVER.md) [공식, 기준선]; [frontierwisdom](https://frontierwisdom.com/ollama-v0-21-1-release/) [3자]

### Inferences
- [추정] 한국어 짧은 답의 품질만 보면 Kanana-2-3B가 같은 크기 범용 모델보다 낫다. KoMT 1.7점 차이, KoSimpleQA 22 대 3이다. 다만 비교표는 Kakao가 고른 대상(Qwen 계열)뿐이고 독립 재현이 없다.
- [추정] Kanana 라이선스는 개인 프로젝트로 "자기 서비스"를 돌리는 데는 문제가 없어 보인다. 반면 Thorkell을 다른 사람에게 배포하면서 모델을 묶어 주면 4.1의 "온디바이스 임베드 제공"에 걸릴 수 있다. 원문 조항을 직접 읽어야 한다.
- [추정] 9B는 최대 6.7GiB여서, 그것 하나로 모델 예산(6~8GB)을 거의 다 쓴다. 로컬 폴백 플래너를 9B로 두려면 다른 로컬 모델(ASR 등)을 다 빼야 한다.
- [추정] 지금 범용 4B급에서 고를 만한 것은 Qwen3.5-4B(도구 호출·지시 수행)와 Kanana-2-3B(한국어 대화) 두 개다. 역할별로 나눠 쓰는 편이 하나로 다 하는 것보다 낫다.

### Gaps
- Qwen3.5-4B/9B, Gemma 4 E2B/E4B의 한국어 점수를 같은 조건으로 잰 독립 자료는 여전히 없다. Horangi v4 공개 결과는 frontier 모델 위주였다 — [W&B Horangi](https://wandb.ai/wandb-korea/korean-llm-leaderboard/reports/Horangi-LLM-Leaderboard-Evaluating-Korean-Language-Proficiency--Vmlldzo2OTg0MDU2) [3자]
- Kanana-2의 MLX 변환본, GGUF 품질, M4 Pro 속도 자료가 없다.
- Phi, SmolLM, Ministral, Llama의 2026-09~10 소형 신작은 검색에서 아무것도 나오지 않았다. 없다는 증거는 아니다.
- Granite 4.2의 IBM 공식 카드(한국어, 라이선스)를 확인하지 못했다.
- Gemma 4 E2B/E4B를 M4 Pro에서 잰 TTFT·최대 메모리 1차 자료를 이번에도 찾지 못했다.

---

## Q2. Apple Foundation Models(macOS 26/27): Python 호출, 가이드 생성, 한국어, 지연, 메모리, 2026년 변화

### Takeaway
Python에서 공식 SDK(`apple-fm-sdk`, macOS 26.0+)로 부를 수 있다. `@fm.generable` 가이드 생성으로 타입이 정해진 구조화 출력을 받는다. macOS 27(2026-09-14 공개)에서 바뀐 점은 다음과 같다.
- 온디바이스 모델을 새로 만들었다. 컨텍스트 8,192, 이미지 입력, 도구 호출 개선.
- PCC 모델: 32K 컨텍스트와 추론 수준 설정
- `fm` CLI가 들어갔다.

한국어는 Apple Intelligence 지원 언어에 들어 있다. 반면 Mac에서의 tok/s, TTFT, 상주 메모리, logprobs는 공식 자료가 없다. 이 Mac은 macOS 26.2라서 SDK는 쓸 수 있지만, 새 모델은 macOS 27이 필요할 가능성이 높다.

### Cited Findings
- Python SDK [공식] — [GitHub apple/python-apple-fm-sdk](https://github.com/apple/python-apple-fm-sdk); [WWDC26 334](https://developer.apple.com/videos/play/wwdc2026/334/)
  - 설치는 `pip install apple-fm-sdk`, import는 `import apple_fm_sdk as fm`다.
  - 요구사항: macOS 26.0+, Xcode 26.0+(라이선스 동의 필요), Python 3.10+, Apple Intelligence가 켜진 호환 Mac. 라이선스는 Apache-2.0이다.
  - 기능(README): 온디바이스 추론, 스트리밍, 가이드 생성(스키마와 제약), `generable` 데코레이터와 `guide` 필드 제약, 모델 설정, 배치 추론, Swift 앱에서 내보낸 transcript 처리
  - 세션 334에 나온 것
    - `@fm.generable("...")` 클래스와 `fm.guide(...)` 필드를 만들고 `session.respond(prompt, generating=Type)`로 받는다.
    - `fm.Tool` 서브클래스로 도구를 호출한다.
    - 텍스트와 이미지를 입력으로 넣는다.
  - README에는 도구, 이미지, 서버 모델, logprobs가 적혀 있지 않다. 기여는 아직 받지 않고, Releases 섹션은 비어 있다.
- `fm` CLI는 macOS 27에 기본으로 들어 있다 [공식] — [WWDC26 334](https://developer.apple.com/videos/play/wwdc2026/334/)
  - `fm respond`, `fm chat`, `fm schema object ... > schema.json`, `fm respond --schema schema.json`, `--model pcc`, `--image`, `--instructions`
  - 온디바이스 모델은 "항상 사용 가능"하다. PCC는 사용 한도가 있다.
  - 3자 정리 글(2026-06-09)은 Python SDK와 CLI를 함께 설명한다 — [blakecrosley](https://blakecrosley.com/blog/foundation-models-python-fm-cli) [3자]
- macOS 27 / iOS 27 변화 [공식] — [WWDC26 241](https://developer.apple.com/videos/play/wwdc2026/241/)
  - 온디바이스 System Language Model을 "처음부터 다시 만들었다". 논리와 도구 호출이 나아졌다고 한다.
  - 예시 코드에서 `contextSize`는 `8192`다(정식 사양표가 아니라 코드 주석).
  - 이미지 첨부를 받는다(크기·비율 무관). 큰 이미지는 토큰과 지연이 늘어난다.
  - 컨텍스트 크기와 토큰 수를 세는 API는 iOS 26.4에 들어갔다. 가드레일은 26.4에서 오탐을 줄였고, 27에서 더 고쳤다.
  - `PrivateCloudComputeLanguageModel`: 32,000토큰, 추론 수준(`.light`, `.deep`). 계정이나 API 키 없이 쓰지만 entitlement가 필요하다. 첫 다운로드 200만 미만 개발자는 비용이 없다.
  - `LanguageModel` 프로토콜이 생겼다. `MLXLanguageModel`과 `CoreAILanguageModel` 오픈소스 구현이 있다. Anthropic과 Google이 Swift 패키지를 낸다.
  - `response.usage`가 입력·캐시·출력·추론 토큰 수를 알려 준다.
  - 이 세션에는 지원 언어, 파라미터 수, 지연 수치, logprobs가 없다.
- macOS 27 일반 공개는 2026-09-14(월)다 — [MacTrast 2026-09](https://www.mactrast.com/2026/09/apple-announces-27-operating-systems-public-release-date/) [3자]
  - 가장 강한 온디바이스 모델은 RAM 12GB 이상, Mac은 M3 이상이 필요하다 — [Macworld](https://www.macworld.com/article/3139330/macos-27-mac-features-siri-apple-intelligence-release-date-compatibility.html) [3자, 검색 요약]
  - 약 30억 파라미터라는 보도가 있다 — [borncity](https://borncity.com/news/macos-27-apple-bringt-3-milliarden-ki-modell-auf-den-mac/) [3자, 제목 기준]
- 한국어
  - Apple Intelligence의 macOS 27 지원 언어에 한국어가 있다 — [Apple Support 121115 (2026-09-14)](https://support.apple.com/en-us/121115) [공식]. 이 페이지에는 Foundation Models framework의 언어 목록이 따로 없다.
  - 프레임워크 출시 때(2025) 지원 언어에 한국어가 있었다 — [natashatherobot](https://www.natashatherobot.com/p/apple-foundation-models) [3자, 보도자료 각주 인용]
  - macOS 26 온디바이스 모델: 한국어 포함 9개 언어, 최대 3B, 4,096토큰 — [Gigazine 2026-04-08](https://gigazine.net/gsc_news/en/20260408-apfel-mac) [3자]
  - 2025 기술 보고서는 15~16개 언어라고 적는다 — [Apple ML Research 2025](https://machinelearning.apple.com/research/apple-foundation-models-2025-updates) [공식, 검색 요약]
- 지연과 메모리
  - Mac 실측은 찾지 못했다.
  - Apple의 2024년 수치(iPhone 15 Pro): TTFT는 프롬프트 토큰당 약 0.6ms, 생성은 약 30 tok/s(토큰 추측 전) — [VentureBeat](https://venturebeat.com/ai/what-we-know-about-apples-on-device-ai) [3자, Apple 수치 인용, 검색 요약]
  - DeviceMark는 Apple 모델을 "OS 상주"로 분류한다. 비교한 다른 모델은 모델 데이터가 1.7~4.6GB 필요했다. iPhone 17 Pro 추정은 70~86 tok/s다(글자 수로 역산한 간접 추정) — [iThinkDiff](https://www.ithinkdiff.com/apple-foundation-model-iphone-llm-benchmark/) [3자]
  - 혼합 2/4비트, 평균 약 3.7bpw라는 분석이 있다 — [VentureBeat](https://venturebeat.com/ai/what-we-know-about-apples-on-device-ai) [3자, 검색 요약]
- logprobs와 토큰 확률: SDK README와 WWDC26 241·334 어디에도 없다. 대신 토큰 수 세기와 `usage`는 있다 [공식, 위 출처].

### Inferences
- [추정] 기준선 추정 "헬퍼 프로세스 필요"는 틀렸다. Python 두뇌가 SDK를 직접 import할 수 있다. 다만 macOS 26.2에서 SDK를 쓰면 옛 모델(4,096토큰)이 잡힐 가능성이 높다. 새 모델(8,192, 이미지)을 쓰려면 macOS 27로 올려야 할 것으로 보인다. OS 업그레이드는 사용자가 결정할 일이다.
- [추정] Thorkell에 맞는 용도
  - 한국어 명령 파싱: 닫힌 의도 목록을 `@fm.generable` 열거형으로 받는다.
  - 짧은 한국어 답
  - 둘 다 가중치 메모리를 추가로 쓰지 않는다는 점이 24GB 예산에서 가장 큰 장점이다.
- [추정] 위험 요소
  1. 가드레일: "트롤 죽여", "피 흘린다" 같은 전투 대화가 거부될 수 있다(26.4·27에서 오탐을 줄였다고 하지만 미측정).
  2. logprobs가 없어 보정된 확률을 낼 수 없다. 타입 결정(Jev 대체)에는 맞지 않는다.
  3. 추론이 ANE와 GPU 중 어디서 도는지 공개되지 않았다. 게임과 GPU를 다툴지 알 수 없다.
- [추정] PCC 모델(32K, 추론)은 무료 한도 안에서 "클라우드 플래너 보조"가 될 수 있다. 다만 entitlement가 필요하고, Python SDK에서 PCC를 쓸 수 있는지는 확인되지 않았다.

### Gaps
- macOS 26.2에서 `apple-fm-sdk`가 어떤 모델(버전, 컨텍스트)을 잡는지, 새 모델이 macOS 26.x로 백포트됐는지 확인하지 못했다.
- Mac(M4 Pro)에서 TTFT, tok/s, 상주 메모리, ANE/GPU 사용 여부, 한국어 가이드 생성 정확도를 공개한 1차 자료가 없다. 직접 재야 한다.
- Foundation Models framework 자체의 2026년 지원 언어 목록(Apple Intelligence 목록과 같은지)을 1차 자료로 확인하지 못했다.
- Python SDK가 PCC 모델이나 이미지 입력을 macOS 26에서 지원하는지 문서로 확인하지 못했다.

---

## Q3. 런타임: MLX/mlx-lm, llama.cpp, Ollama, LM Studio, vllm-metal의 최신 상태

### Takeaway
2026-10 기준으로 Apple Silicon에서 기능을 가장 많이 묶어 주는 것은 Ollama 0.40.x다.
- MLX 기본 실행
- XGrammar 구조화 출력
- MLX runner logprobs(3자)
- 자동 MTP speculative decoding
- `/v1/systemone` 결정 모델
- EmbeddingGemma 2

`llama-server`는 여전히 문법 제약, 확률, 슬롯 캐시의 기준이다. mlx-lm 서버는 아직 `response_format`이 없다. vllm-metal은 2026-09-22에 첫 정식 릴리스를 냈고, 구조화 출력과 Gemma 4 MTP를 지원한다. M4 Pro에서 4B는 TTFT 0.75s(512 입력), 생성 83 tok/s, 9B는 1.37s와 50 tok/s다.

### Cited Findings

**버전과 변화**
- [changed] Ollama [공식] — [Ollama releases](https://github.com/ollama/ollama/releases)
  - v0.34.4(09-23): thinking 모델의 구조화 출력이 한 번에 적용된다. Apple Silicon에서 Qwen 3.8 prompt 처리가 빨라졌다. XGrammar를 갱신했다.
  - v0.35.0(09-28 게시, 블로그는 09-29): `/v1/systemone` 결정 모델(Nimble, Tev1) — [v0.35.0](https://github.com/ollama/ollama/releases/tag/v0.35.0)
  - v0.35.1: 멀티모달 Clef 결정 모델
  - v0.40.0: Apple Silicon에서 지원 아키텍처를 MLX로 기본 실행한다. gemma4, qwen3.5, qwen3.6, 결정 모델(nimble, tev1, clef, clef-flash), embeddinggemma-2가 MLX에서 돈다 — [v0.40.0](https://github.com/ollama/ollama/releases/tag/v0.40.0)
    - 날짜가 어긋난다. 페이지 표기는 09-25인데 0.35.0(09-28)보다 앞서고, 09-29 블로그는 MLX 결정 모델을 "다음 할 일"로 적었다.
  - v0.40.1(10-07): MLX에 반영된 Metal residency 패치를 Ollama 쪽에서 뺐다.
  - v0.40.4(10-12): Apple silicon MLX runner에서 결정 모델을 돌린다. MLX runner의 speculative decoding 안정성이 나아졌다(rollback 뒤 recurrent state 처리).
  - v0.40.5(10-14, Latest), v0.40.6(10-16)
  - v0.32.6 노트: "MLX 엔진이 모델의 MTP head를 speculative decoding에 자동으로 쓴다(Qwen3.5)" — [terminalbytes 2026-09-20](https://terminalbytes.com/ollama-vs-llama-cpp-vs-mlx-mac-2026/) [3자, 릴리스 노트 인용]
  - Ollama는 Qwen3.5를 기본 컨텍스트 262,144토큰으로 올린다. 메모리가 빠듯하면 `num_ctx`를 설정하라고 한다 — [terminalbytes](https://terminalbytes.com/ollama-vs-llama-cpp-vs-mlx-mac-2026/) [3자]
- [unchanged + 새 버전] mlx-lm [공식] — [mlx-lm releases](https://github.com/ml-explore/mlx-lm/releases)
  - v0.32.0(10-15) 변경
    - 도구 호출 인자 파싱 수정, Qwen3 Coder 도구 호출 수정, MiniCPM5 파서 추가
    - GraniteMoeHybrid padded batch의 logprobs 수정
    - Qwen3.5 parallel head와 2비트 Hadamard 변형
    - NVFP4 MoE global scale
  - v0.32.1, v0.32.2(10-15~16)는 버그 수정이다.
  - 0.31.x의 하이라이트: 프롬프트 캐싱, BatchGenerator의 logits processor, speculative decoding 출력 수정, Gemma 4 지원
  - 날짜 충돌: PyPI 기준 0.32.0은 2026-10-01이라는 검색 요약이 있다 — [PyPI](https://pypi.org/project/mlx-lm/) [검색 요약]. GitHub 릴리스 페이지는 10-15다.
  - `response_format`은 여전히 없다(#1007 open).
    - 외부 래퍼로 Outlines를 붙이면 배치 경로에서 첫 요청 뒤 제약이 조용히 풀린다는 보고가 있다(09-21) — [#1007](https://github.com/ml-explore/mlx-lm/issues/1007) [커뮤니티]
    - 0.31.3에서 끝난 요청의 logits processor가 남는 버그 보고도 있다 — [agency-lang PR #1112](https://github.com/egonSchiele/agency-lang/pull/1112) [커뮤니티, 검색 요약]
- [unchanged + 새 빌드] llama.cpp [공식] — [llama.cpp releases](https://github.com/ggml-org/llama.cpp/releases)
  - 최신은 b11702(2026-10-17)다.
  - b11695: Mellum2.1 MTP 지원
  - b11700: Granite Switch(Decision) 지원. 일부는 같은 릴리스에서 되돌렸다. Granite-Switch는 LoRA 여러 개를 품은 Granite-4.1을 제어 토큰으로 바꿔 쓰는 PoC 아키텍처다 — [commit #25107](https://app.semanticdiff.com/gh/ggerganov/llama.cpp/commit/157b81fe6dbfec7d7ce91ef7cd9c6bc0c218d6fe) [공식 커밋, 3자 뷰어]
  - b11690: ngram 캐시를 복사하지 않고 참조로 읽는다.
  - MTP: MTP 가중치가 든 GGUF는 `--spec-type draft-mtp`로 같은 파일에서 drafter를 읽는다 — [Jetson AI Lab](https://www.jetson-ai-lab.com/tutorials/speculative-decoding) [3자]
    - Gemma 4 MTP는 06-07에, E2B/E4B assistant는 06-08에 병합됐다. E2B/E4B에서는 `llama-speculative`와 `llama-bench`가 실패한다는 보고가 있다 — [aiweekly](https://aiweekly.co/alerts/llamacpp-adds-gemma-4-e2be4b-mtp-assistant-support) [3자]
- [new] vllm-metal [공식] — [vLLM blog 2026-09-22](https://vllm.ai/blog/2026-09-22-vllm-metal-v0-28-0)
  - v0.28.0이 첫 정식 릴리스다. Homebrew로는 v0.29.0을 설치한다. 요구사항은 macOS 15+다.
  - 서빙 기능에 structured outputs가 들어 있다. 엔진(xgrammar 등)과 logprobs는 글에 없다.
  - speculative decoding은 Gemma 4 MTP, draft 모델, n-gram 세 가지다.
    - MTP는 Gemma 4 전용이고 greedy(`temperature=0`)와 `--no-async-scheduling`이 필요하다.
    - Gemma 4 E4B MTP의 출력 tok/s 변화: 동시성 1에서 +20%, 8에서 0%, 16에서 +9%
  - prefix caching을 지원한다. 하이브리드 모델의 `align` 모드는 실험적이다. 도구 호출 파싱, LoRA, GGUF를 지원한다.
  - Docker 벤치에서 Llama 3.2 1B는 llama.cpp가 vllm-metal보다 약 1.2배 빨랐다 — [Docker blog](https://www.docker.com/blog/docker-model-runner-vllm-metal-macos/) [공식, 검색 요약]
- [changed, 10월 자료 없음] LM Studio [공식, 검색 요약]
  - 0.4.0(2026-01-28): GUI 없는 데몬 `llmster`, 병렬 요청과 continuous batching — [changelog 0.4.0](https://lmstudio.ai/changelog/lmstudio-v0.4.0)
  - 0.4.2(02-06): MLX continuous batching(mlx-engine 1.0.0, 텍스트 전용) — [0.4.2](https://lmstudio.ai/changelog/lmstudio-v0.4.2)
  - 0.4.14(05-22): MTP speculative decoding 안정화 — [0.4.14](https://lmstudio.ai/changelog/lmstudio-v0.4.14)
  - 구조화 출력: GGUF는 llama.cpp 문법, MLX는 Outlines(기준선과 같음) — [LM Studio docs](https://lmstudio.ai/docs/developer/openai-compat/structured-output)
- [new] Rapid-MLX(Apache-2.0, MLX 기반 OpenAI/Anthropic 호환 서버) [커뮤니티] — [Rapid-MLX](https://github.com/raullenchai/Rapid-MLX)
  - 도구 호출 파서 27개, radix prefix 캐시(디스크 저장·복원), 양자화 KV
  - Qwen3.8-27B에서 MTP를 자동으로 켠다. M4 Pro A/B에서 13.0 → 17.2 tok/s(+32.3%)였다.
  - 구조화 출력과 logprobs는 문서에 없다.

**M4 Pro 실측** [커뮤니티] — [Rapid-MLX README](https://github.com/raullenchai/Rapid-MLX)
- 조건: M4 Pro 48GB, Rapid-MLX 0.14.1, 단일 요청, greedy, prefix 캐시 끔, speculative decoding 없음

| 모델(4비트) | 512→128 TTFT | 생성 tok/s | 2K→512 TTFT | 생성 tok/s | 최대 메모리 |
|---|---|---|---|---|---|
| qwen3.5-4b | 0.75s | 83.45 | 2.95s | 82.02 | 4.4 GiB |
| qwen3.5-9b | 1.37s | 49.76 | 5.59s | 48.68 | 6.7 GiB |
| gemma-4-12b | 2.19s | 31.87 | 9.16s | 30.92 | 11.9 GiB |
| gemma-4-26b(A4B) | 0.78s | 75.59 | 3.06s | 71.33 | 16.9 GiB |

- 48GB 모델의 GPU 코어 수는 README에 없다. 이 Mac(16코어 GPU)은 더 느릴 수 있다.

**M3 Ultra 런타임 비교, Qwen3.5-9B** [3자 실측] — [terminalbytes 2026-09-20](https://terminalbytes.com/ollama-vs-llama-cpp-vs-mlx-mac-2026/)

| 런타임 | 양자화 | 생성 tok/s | 메모리 |
|---|---|---|---|
| Ollama GGUF | Q4_K_M | 77.7 | 상주 15GB(262K 기본 컨텍스트) |
| `llama-bench` | Q4_K_M | 77.8(tg128) | – |
| Ollama MLX | NVFP4, MTP 포함 | 90.5 | 상주 9GB |
| rapid-mlx | 4비트 | 105.9 | – |
| mlx-lm 0.31.3 | 4비트 | 107.5 | 최대 5.24GB |

**기능표 갱신**

| 기능 | `llama-server` | mlx-lm 서버 | Ollama 0.40.x | vllm-metal 0.28+ | LM Studio |
|---|---|---|---|---|---|
| JSON 스키마·문법 | `json_schema`, GBNF [unchanged] | 없음 [unchanged] | `format` 스키마, XGrammar [new]. MLX runner는 0.33.2부터 [3자] | structured outputs [new] | GGUF는 문법, MLX는 Outlines [unchanged] |
| 토큰 확률 | `n_probs`, `top_logprobs` [unchanged] | `logprobs` 1~10 [unchanged] | MLX runner는 0.21.1부터 [3자] | 미확인 | 미확인 |
| speculative / MTP | draft, ngram, `draft-mtp` [changed] | `draft_model` [unchanged] | MLX에서 MTP 자동 [new] | Gemma 4 MTP, draft, n-gram [new] | MTP 안정(0.4.14) [new] |
| 프롬프트 캐시 | `cache_prompt`, 슬롯 저장 [unchanged] | `cache_prompt`, Python API [unchanged] | 미기재 | prefix caching [new] | 미기재 |
| 결정 API `/v1/systemone` | 없음 | 없음 | **있음**(0.35+) [new] | 없음 | 없음 |
| 임베딩 | `--embedding` | 별도 | embeddinggemma-2 on MLX [new] | 실험적 | 있음 |

### Inferences
- [추정] "생성 + 스키마 강제 + 확률 + 결정 API + 임베딩"을 한 로컬 서버로 묶고 싶다면 Ollama 0.40.x가 가장 가깝다. 다만 MLX 경로의 구조화 출력과 logprobs 근거는 3자 요약뿐이다. 공식 문서나 직접 호출로 확인해야 한다. 레포 규칙 7에 따라 엔진은 config로 명시하고, 실패하면 다른 엔진으로 숨어서 넘어가지 않게 한다.
- [추정] Ollama는 기본 컨텍스트(262K) 때문에 상주 메모리가 크게 늘어난다(M3 Ultra GGUF 15GB). Thorkell에서는 모델마다 `num_ctx`를 2~8K로 고정해야 게임 둘과 같이 돈다.
- [추정] 이 Mac에서 Qwen3.5-4B로 타입 결정을 생성 방식으로 하면, 상태 500토큰 기준 TTFT만 약 0.75s다. 기준선 추정(캐시 없이 1.1~1.4s/1,000토큰)과 맞는다. 600ms 마감에는 프롬프트 캐시와 1토큰 출력이 필요하다는 결론은 그대로다.
- [추정] 출력이 짧은 결정과 JSON에서는 MTP 이득이 작다. 긴 한국어 답이나 플래너 출력에서만 의미가 있다. vllm-metal의 E4B +20%는 동시성 1에서만 나왔다.

### Gaps
- Ollama 공식 문서로 MLX runner의 `format`(JSON 스키마)과 `logprobs` 지원 범위를 확인하지 못했다. 3자 요약만 있다.
- 이 Mac(M4 Pro 16코어 GPU, 24GB)에서 llama.cpp와 MLX를 같은 모델로 잰 1차 측정은 여전히 없다.
- LM Studio의 2026-06~10 릴리스 노트를 찾지 못했다.
- vllm-metal의 structured outputs 백엔드와 logprobs 지원 여부가 문서에 없다.

---

## Q4. Jev·laya와 결정 모델 생태계(2026-09 이후)

### Takeaway
기준선 이후 가장 크게 바뀐 영역이다.
- Jev 쪽: 1.14.0이 프리뷰로 나왔고(다국어 개선, 이미지·`box` 실험 기능), 단일 출처지만 TypeSafe가 8.7억 달러를 조달했다는 보도가 있다.
- 대형 회사의 호스팅 결정 API: OpenAI Decisions API(공개 베타 10-06), Microsoft-Decision-1(10-09)
- 로컬에서 Jev와 같은 API: Ollama 0.35+의 `/v1/systemone`이 Tev1 0.8B/4B, Nimble 9B, Clef/Clef-flash를 MLX로 돌린다.
- laya: 0.3.20이 나왔고, Vercel AI Gateway에서 10-31까지 무료다. 다만 3자 JevBench는 laya 기본 체크포인트를 최하위권으로 매겼다.

한국어 성능은 어느 결정 모델도 공개하지 않았다.

### Cited Findings

**Jev (TypeSafe)**
- [unchanged] 가격: 입력 100만 토큰당 0.042달러, 출력 무료 — [OpenRouter](https://openrouter.ai/ko-KR/compare/typesafe/jev-1.13) [3자]. 공개 요금표나 셀프서브 무료 등급은 없고 대기열 방식이라고 한다 — [eesel](https://www.eesel.ai/es/blog/typesafe-jev-precios) [3자, 검색 요약]
- [new] Jev 1.14.0 — [Zeli 2026-10-14](https://zeli.app/story/50095353) [3자, typesafe.ai/blog/jev-1-14 요약]; "1.14.0 in preview" — [awesome-system-one](https://github.com/andyrewlee/awesome-system-one) [커뮤니티]
  - 다국어 지원이 나아졌다.
  - 'danger zone' 실험 기능: 이미지 입력 조합, 경계 상자 타입 `box`, 더 긴 컨텍스트
  - 지연이나 가격 변화는 언급이 없다.
- [new] TypeSafe가 75억 달러 가치로 약 8.7억 달러를 조달했다(Bloomberg 10-09 보도 인용) — [letsdatascience](https://letsdatascience.com/blog/openai-jev-rival-three-weeks-typesafe-raised-870-million) [3자, **단일 출처**]
- [new] 3자 JevBench v1.7.46 — [jev-ai.pro 2026-10-16](https://jev-ai.pro/compare/jev-vs-laya) [3자. "Jev AI" 브랜드이고 TypeSafe 공식이 아니다]
  - Jev 1.13.0: 종합 71.5(API 보드 31개 중 4위), calibration 90.6, 호스팅 지연 중앙값 0.24s / p95 0.30s, 요청당 64k토큰
  - laya: 종합 0.0(오픈 웨이트 보드 162개 중 154위). CPU 측정 0.83s(raw)
  - Jev는 영어에서 가장 정확하고, 다른 언어는 정확도가 낮다고 적는다.
- 이 레포의 실측은 기준선과 같다(`jev-1.13.0`, p50 188ms / p95 292ms) [로컬, unchanged].

**laya (Convai)** — [HF convaiinnovations/laya](https://huggingface.co/convaiinnovations/laya) [공식, 벤더 측정]
- [changed] 런타임 laya 0.3.20(체크포인트는 그대로)
  - `laya-multilingual`이 `max_len=8192`를 받는다(기본 1,024).
  - `laya-serve`가 종료할 때 추론 풀을 비운다. 잘못된 bearer 헤더에는 401을 돌려준다.
  - `ONNXAgent` 동작을 맞췄다.
- 체크포인트
  - `laya`(영어, ModernBERT-large 421M, 512토큰, 약 808MB)
  - `laya-multilingual`(mmBERT-base 322M, 100개 이상 언어, 1,024토큰, 약 647MB, 약 2.2배 빠름)
  - `laya-typed-decisions`(421M, 1,024토큰)
- `laya-serve`
  - `POST /v1/systemone`, 기본 `0.0.0.0:8000`
  - Jev의 모든 질문 형태를 받고, 모르는 필드는 무시한다. 잘못된 질문에는 422를 돌려준다.
  - choice/score/noul을 지원하고, 한 호출 안의 질문을 forward pass 한 번으로 처리한다.
  - `LAYA_API_KEY`, `LAYA_DEVICE`, `LAYA_PRELOAD`를 쓴다. ONNX는 `laya[onnx]`로 쓴다.
- 지연(T4): multilingual 질문 1개 32.8ms, 10개 72.3ms. CPU는 193~464ms. Apple GPU에서 4,000토큰은 약 1.7s다. Apple Silicon의 짧은 입력 수치는 없다.
- 정확도
  - typed-decisions 파인튜닝: 0.766(Jev 0.727)
  - 기본 영어 0.362, 다국어 0.342
  - MASSIVE intent: 영어 0.783, 다른 13개 언어 0.451
  - XNLI: 영어 0.860, 다른 14개 언어 0.731
  - 51개 언어 중 45개가 "무작위의 3배 이상"이다. 한국어를 따로 적은 수치는 없다.
- 알려진 약점
  - `action.act_probability`에 쓸 만한 신호가 없다(#185).
  - noul 답이 `false:`/`true:` 라벨을 따라간다(#156).
  - score가 가장 약하다.
- [new] Vercel AI Gateway에서 2026-10-31까지 무료다(Boundless 경유). 그 뒤 표준 ID는 과금되고 `-free` ID는 중단된다 — [Vercel changelog](https://vercel.com/changelog/laya-decision-model-now-available-on-ai-gateway-free-through-october-31) [공식]
  - [corrected] "laya 무료 기간이 10-12에 끝났다"는 검색 요약은 1차 자료로 확인되지 않는다.
- 독립 시험(78건)에서 laya는 정확도 최하위(0.590)였지만, 속도는 가장 빨랐다(약 30ms 대 Jev 약 302ms) — [flowtivity](https://flowtivity.ai/blog/laya-open-source-jev-alternative/) [3자, 검색 요약, 표본 작음]

**대형 회사 호스팅 결정 API [new]**
- OpenAI Decisions API — [MarkTechPost 2026-10-09](https://www.marktechpost.com/2026/10/09/openai-decisions-api-hits-public-beta-with-10x-faster-typed-answers/); [letsdatascience](https://letsdatascience.com/news/openai-opens-decisions-api-public-beta-b69a1e40) [3자]
  - DevDay(09-29)에서 제한 프리뷰, 10-06에 공개 베타
  - GPT-6 Luna 기반. 입력 100만 토큰당 0.10달러이고 출력은 무료다.
  - 텍스트와 이미지를 받는다. Responses API보다 최대 10배 빠르다고 주장한다(OpenAI 주장).
- Microsoft-Decision-1 — [letsdatascience](https://letsdatascience.com/news/microsoft-releases-model-for-agent-decision-scoring-806746f8); [runtimewire](https://runtimewire.com/article/microsoft-decision-1-achint-srivastava-agent-workflows) [3자]
  - 2026-10-09 Foundry 공개(10-08이라는 출처도 있다 — [orcarouter](https://www.orcarouter.ai/vi/blog/microsoft-decision-1-ga-foundry-no-published-benchmarks))
  - Qwen3.5-9B를 후학습했다. 가중치는 공개하지 않고, 벤치마크 수치도 없다.
- Tom's Hardware는 "Jev류 결정 모델이 쏟아진다"는 기사를 냈다. 연구자가 TypeSafe의 표절을 주장했다는 내용이다. 본문은 열지 못했다 — [Tom's Hardware](https://www.tomshardware.com/tech-industry/artificial-intelligence/jev-like-decision-models-are-flooding-the-ai-market-after-researcher-claims-typesafe-copied-their-research-microsoft-openai-among-companies-releasing-lightweight-system-one-ai-models) [3자, 제목만]

**로컬에서 Jev와 같은 API로 도는 결정 모델 [new]**
- Ollama 블로그(2026-09-29) [공식] — [Ollama blog](https://ollama.com/blog/ollama-now-supports-jev-style-decision-models)
  - `/v1/systemone`는 TypeSafe Jev API 기반이다. choice(옵션별 `probabilities`, `confidence`), noul, score(`legend`, `probabilities`, `confidence`)를 지원한다.
  - Python 클라이언트는 `typesafe-sdk`이고 `TYPESAFE_BASE_URL`로 주소를 바꾼다.
  - 13개 공개 데이터셋, 3,880개 결정의 평균 정확도: Nimble 9B 75.7%, Tev1 4B 73.3%, Tev1 0.8B 63.5%, Jev 1.13 76.0%(Bespoke 측정)
  - 지연: Nimble은 M5 Max에서 결정당 평균 91ms(Pac-Man 데모)

| 모델 | 제작 | 크기·기반 | 라이선스 | 받는 크기 | 컨텍스트 | 언어 | 출처 |
|---|---|---|---|---|---|---|---|
| `tev1:0.8b` | Together AI | Qwen3.5-0.8B | 학습 스크립트는 MIT, 가중치는 미기재 | 812MB~1.5GB | 약 2,000토큰으로 운용(목록 표기는 256K) | **영어 외 미시험** | [Ollama tev1](https://ollama.com/library/tev1) [공식] |
| `tev1:4b` | Together AI | Qwen3.5-4B | 같음 | 4.4~4.6GB | 같음 | 같음 | 같음 |
| `nimble` | Bespoke Labs | Qwen3.5-9B 파인튜닝 | Apache-2.0(Ollama). awesome 목록은 미기재 | **9.3~9.5GB** | 프롬프트 8,192토큰 이내 | 미기재(독일어 라우팅 벤치 포함) | [Ollama nimble](https://ollama.com/library/nimble) [공식] |
| Clef-flash | Cloudflare | Qwen3.5-9B 후학습 | Apache-2.0 | 양자화본 56종 링크 | 입력 기본 16,384(`encode_record`) | 미기재 | [HF Cloudflare/clef-flash](https://huggingface.co/Cloudflare/clef-flash) [공식] |
| Clef | Cloudflare | 27B(Qwen3.8-27B) | Apache-2.0 | – | 64K | 미기재 | [letsdatascience](https://letsdatascience.com/news/cloudflare-releases-open-weight-clef-decision-models-c52886d6) [3자] |

- Nimble 세부 [공식, Ollama 페이지]
  - Bespoke 보류 세트: Nimble 90.12%, Qwen3.5-9B 기본 66.36%, Jev 93.21%
  - 공개 벤치 평균: choice 81.6%, boolean 80.2%, score 54.6%
- Clef-flash 세부 [공식, Cloudflare 내부 측정]
  - Cloudflare 내부 Decision Index 0.2.1에서 BANKING77은 90.9 대 Jev 79.7로 앞섰다.
  - GSM8K 67.3 대 79.9, BBH 68.9 대 92.9로 뒤졌다.
  - 지연 중앙값 38.8ms 대 Jev 524.1ms(H200 계열로 보임)
  - 입력은 텍스트, JSON, 이미지, 비디오이고 출력은 옵션별 logit이다.
  - Clef와 Clef-flash는 2026-10-01에 공개됐다 — [alternativeto 2026-10](https://alternativeto.net/news/2026/10/cloudflare-launches-open-source-clef-decision-models-and-rl-tuning/) [3자]
- 그 밖의 소형 오픈 결정 모델(큐레이션 목록 기준. 각 저장소는 확인하지 않음) — [awesome-system-one](https://github.com/andyrewlee/awesome-system-one) [커뮤니티]
  - Intern-Decision(Shanghai AI Lab): 0.8B/2B/4B, Qwen3.5 기반, Apache-2.0, CoreML 포트
  - Vela(KR Labs × vLLM Semantic Router): ModernBERT 0.3B~9B, Apache-2.0, ONNX와 Core ML
  - GLiNER2.5-Decide(Fastino): 340M, 1B, 다국어판, Apache-2.0
  - julia-1: 144M(mmBERT-small), CPU, GGUF
  - 도구: `laya-mlx`, `jevmlx`(Apple Silicon), `systemANE`(Neural Engine), `LLM2Jev`(prefill 전용)
- Liquid AI d1: d1-3B, d1-omni-600M(587M, 2026-10-07 업로드). LFM2.5-VL 기반이고, 수치는 모두 벤더 보고다 — [orcarouter](https://www.orcarouter.ai/blog/liquid-ai-d1-omni-600m-vs-lfm2-5-vl-3b) [3자]

### Inferences
- [추정] Thorkell의 결정 경로 선택지가 셋에서 다섯으로 늘었다.
  1. Jev 클라우드 유지(현재)
  2. Ollama `tev1:0.8b` 또는 `tev1:4b`를 `TYPESAFE_BASE_URL`로 바로 교체해 보기(학습 불필요)
  3. laya-multilingual 파인튜닝(기존 계획)
  4. Apple 쪽 경로(CoreML 결정 모델, `systemANE`). 미검증이다.
  5. 9B급 Nimble 또는 Clef-flash: 받는 크기만 9.4GB여서 24GB 예산 밖이다.
- [추정] 이 Mac에서 결정 모델의 지연은 거의 prefill 시간이다(출력 토큰 없음).
  - 근거: Qwen3.5-4B의 512토큰 TTFT 0.75s(Q3)
  - Tev1 4B: 상태 300~500토큰이면 약 0.45~0.75s다. Jev 클라우드(p50 188ms)보다 느리다.
  - Tev1 0.8B: 그 1/4~1/5 수준인 약 0.1~0.2s로 본다.
  - M5 Max의 Nimble 91ms는 옮겨 올 수 없는 수치다. M5는 TTFT가 M4보다 약 4배 빠르다(기준선 Apple ML Research 인용).
- [추정] 정확도 판단
  - 공개 13개 데이터셋 기준 Tev1 0.8B(63.5%)는 Jev(76.0%)보다 12.5%p 낮다.
  - Thorkell 결정은 선택지가 적고 상태가 짧은 편이다. 그래서 실제 격차는 Jev 로그로 다시 재야 한다.
  - Tev1은 영어 외 미시험이다. 따라서 상태 직렬화는 영어·구조화로 하고, 한국어는 리더 발화 원문에만 남기는 편이 안전하다. 정보 동등성 규칙(로컬라이즈 토큰 금지)은 그대로 지킨다.
- [추정] 한국어 의도 분류는 "choice" 질문 하나로 바꿀 수 있다(닫힌 스킬 목록). 수량은 코드나 정규식이 맡는다. 이렇게 하면 결정 모델 하나로 결정과 명령 파싱을 함께 처리하는 구성이 가능하다. laya의 MASSIVE 비영어 0.451은 파인튜닝 없이는 부족하다는 신호다.
- [추정] 3자 JevBench에서 laya가 0.0인 것은 zero-shot 기본 체크포인트를 잰 결과로 보인다. 파인튜닝 전제인 기존 계획을 뒤집는 근거는 아니다. 그래도 증류 전에 Tev1과 나란히 재 볼 이유는 된다.

### Gaps
- Jev 1.14.0의 한국어 정확도, 정식 출시일, 가격 변화는 TypeSafe 원문(typesafe.ai/blog/jev-1-14)을 직접 열지 못해 확인하지 못했다.
- Tev1·Nimble·Clef·laya의 한국어(또는 한국어가 섞인 상태) 정확도 자료가 없다.
- Ollama 결정 모델의 양자화 형식(받는 크기 4.4GB는 4B 기준 8비트로 보임 [추정])과 M4 Pro 지연 실측이 없다.
- Tev1 가중치 라이선스가 명시되지 않았다.
- TypeSafe 8.7억 달러 조달은 두 번째 출처로 확인하지 못했다.

---

## Q5. 임베딩

### Takeaway
EmbeddingGemma 2(2026-10-06)가 새 기본 후보다. 텍스트만 쓰면 270M이고, 100개 이상 언어, 768차원(MRL 512/256/128), 8,192토큰을 지원한다. Ollama 0.40.0에서 MLX로 돈다. 한국어 단독 점수는 없다.

### Cited Findings
- [new] EmbeddingGemma 2 [공식] — [HF google/embeddinggemma-2](https://huggingface.co/google/embeddinggemma-2); 출시일은 [Gemma releases](https://ai.google.dev/gemma/docs/releases)
  - 총 740M이다.
    - 텍스트 270M(transformer 130M + embedder 140M)
    - 비전 170M, 오디오 300M
  - 활성 모달리티별 크기: 텍스트 270M, 텍스트+이미지 440M, 텍스트+오디오 570M
  - 100개 이상 언어(학습 데이터는 140개 이상), 768차원, Matryoshka 512/256/128
  - 모달리티 공통 컨텍스트 8,192토큰
  - MTEB multilingual v2 Mean(Task): 61.36(768), 61.17(512), 60.41(256), 57.89(128)
  - bf16이나 fp32를 권장하고 fp16은 피하라고 한다. 카드에는 Apache-2.0과 Gemma 라이선스 링크가 함께 있다.
  - 카드가 문서화한 런타임은 sentence-transformers와 Transformers다.
  - 한국어 해설: 텍스트 전용 서비스는 270M만 올리면 된다 — [PyTorchKR](https://discuss.pytorch.kr/t/google-embeddinggemma-embeddinggemma-2/12118) [3자]
- Ollama v0.40.0에서 embeddinggemma-2가 MLX로 돈다 — [Ollama v0.40.0](https://github.com/ollama/ollama/releases/tag/v0.40.0) [공식]
- [unchanged] EmbeddingGemma(300M, 2025-09-04) — [Gemma releases](https://ai.google.dev/gemma/docs/releases) [공식]

### Inferences
- [추정] 텍스트만 bf16으로 쓰면 메모리는 약 0.55~0.7GB다(270M × 2바이트 + 런타임). 256차원으로 잘라도 MTEB 손실이 약 1점이라, 도감이나 상황 회상 kNN에는 256차원이면 충분하다.
- [추정] 정보 동등성 규칙에 따라 prefab 이름이 아니라 화면에 보이는 설명(한국어 표시명 포함)을 임베딩한다. 다만 개체 키로 쓰는 `$enemy_…` 토큰은 넣지 않는다.

### Gaps
- 한국어 검색·유사도 단독 점수(Ko-MTEB 등)가 없다.
- M4 Pro에서의 임베딩 지연 실측이 없다.
- 라이선스 표기(Apache-2.0과 Gemma 라이선스 링크)가 무엇을 뜻하는지 원문으로 정리하지 못했다.

---

## Q6. 게임 옆 GPU·메모리 경합 증거와 24GB 예산 갱신

### Takeaway
Mac에서 게임과 로컬 추론의 프레임 간섭을 잰 2026년 자료는 이번에도 없다. 남는 근거는 모바일 SoC 연구 하나다. GPU만 쓰는 prefill은 게임 프레임을 0으로 떨어뜨렸고, decode 중에는 약 46 FPS가 유지됐다. 대신 메모리 쪽은 실측이 생겼다. 4B 4비트는 최대 4.4GiB, 9B는 6.7GiB다. 또 Ollama 기본 262K 컨텍스트는 상주 메모리를 크게 키운다. 따라서 예산은 "4B 하나 + 소형 결정 모델 + 임베딩" 정도가 상한이다.

### Cited Findings
- [unchanged, 세부 보강] HeteroInfer — [arXiv 2501.14794](https://arxiv.org/abs/2501.14794) [논문, 본문은 검색 요약]
  - League of Legends: Wild Rift와 동시에 실행했다.
  - GPU 전용 기준선은 OpenCL 커널이 GPU 제출 큐를 채워서 prefill 중 FPS가 0이 됐다.
  - decode 중에는 약 46 FPS였다. GPU+NPU 분할에서는 정상 프레임이 유지됐다.
- [new, 3자] MLX의 KV 캐시가 계속 커지면 GPU 드라이버가 할당할 메모리가 바닥나 Mac이 멈춘 사례가 있다 — [Medium, Hannecke](https://medium.com/@michael.hannecke/how-my-local-coding-agent-crashed-my-mac-and-what-i-learned-about-mlx-memory-management-e0cbad01553c) [3자, 검색 요약]
- [new, 3자] Ollama Qwen3.5-9B GGUF는 기본 262K 컨텍스트로 상주 15GB였다. MLX 경로는 9GB였다(M3 Ultra) — [terminalbytes](https://terminalbytes.com/ollama-vs-llama-cpp-vs-mlx-mac-2026/)
- [new] 실측 최대 메모리: 4B 4.4GiB, 9B 6.7GiB, Gemma 4 12B 11.9GiB(M4 Pro) — [Rapid-MLX](https://github.com/raullenchai/Rapid-MLX) [커뮤니티]
- [new] Apple 온디바이스 모델은 OS 상주로 분류된다 — [iThinkDiff](https://www.ithinkdiff.com/apple-foundation-model-iphone-llm-benchmark/) [3자]. Mac에서 실제로 쓰는 메모리 수치는 없다.
- [unchanged] omlx #2264(MLX가 GPU를 100% 쓰면 UI가 끊김, not planned로 닫힘), Game Mode, Valheim 클라이언트 RSS 약 3.0~3.4GB [로컬] — 기준선 Q3 출처. 다시 확인하지 않았다.

### Inferences
- [추정] 24GiB 예산표 갱신(모델 몫 6~8GB 안전권은 기준선과 같다)

  | 조합 | 구성 | 모델 메모리 합 | 판정 |
  |---|---|---|---|
  | A′ | Qwen3.5-4B 4비트(4.4GiB 실측) + `tev1:0.8b`(약 0.8~1.5GB) + EmbeddingGemma 2 텍스트(약 0.6GB) | 약 5.8~6.5GB | 안전권. 로컬 ASR(약 2.4GiB)을 더하면 8~9GB로 넘친다 |
  | B′ | Apple 온디바이스(추가 가중치 0, 실제 몫 미측정) + `tev1:0.8b` 또는 laya-multilingual(약 0.7GB) + EmbeddingGemma 2 | 약 1.5~2.2GB + Apple 몫 | 메모리가 가장 여유롭다. 로컬 ASR까지 넣을 수 있다 |
  | C′ | Qwen3.5-9B 4비트(6.7GiB) | 6.7GiB | 이것 하나로 예산이 거의 찬다 |
  | – | `nimble` / Clef-flash 9B(받는 크기 9.4GB) | 9GB 이상 | 예산 밖 |

- [추정] 경합 완화 원칙은 기준선과 같다. 이벤트가 있을 때만 짧게 호출하고, 작은 prefill 단위로 나누고, ASR은 ANE, TTS는 CPU로 보낸다. 여기에 두 가지를 더한다.
  1. Ollama를 쓰면 모델마다 `num_ctx`를 명시한다.
  2. 결정 모델은 prefill만 하므로 짧은 GPU 버스트다. HeteroInfer의 "prefill 중 FPS 0" 결과를 보면, 결정 호출 빈도(초당 횟수)가 사람 화면 끊김에 가장 직접 영향을 줄 것이다. 실측 대상 1순위다.

### Gaps
- Mac(Metal)에서 Valheim과 MLX/llama.cpp/Apple FM을 동시에 돌린 프레임 시간 측정은 여전히 없다. 레포 규칙 3에 따라 한 번에 하나씩 직접 재야 한다.
- Apple FM 추론이 ANE와 GPU 중 어디서 도는지, 게임 GPU와 겹치는지 자료가 없다.
- Valheim 클라이언트의 `phys_footprint`(GPU 메모리 포함)는 아직 재지 않았다(기준선 갭 그대로).

---

## Q7. Thorkell 역할별 로컬 후보 정리(2026-10-17 기준)

### Takeaway
역할별 1순위는 다음과 같다.
- 타입 결정: Jev 클라우드를 유지하고, Ollama `tev1:0.8b`를 같은 API로 바로 붙여 비교한다. laya 파인튜닝은 그 결과를 보고 정한다.
- 한국어 명령 파싱: 아는 명령은 지금처럼 코드로 처리한다. 처음 보는 말은 결정 모델 choice 질문이나 Apple FM 가이드 생성으로 닫힌 의도 목록에 매핑한다.
- 짧은 한국어 답: Kanana-2-3B(라이선스 확인 필요) 또는 Apple 온디바이스 모델
- 폴백 플래너: Qwen3.5-4B(9B는 다른 로컬 모델을 다 빼야 들어간다)
- 임베딩: EmbeddingGemma 2 텍스트 270M

모든 조합은 이 Mac에서 TTFT, 메모리, 사람 프레임을 재기 전까지 가설이다.

### Cited Findings
- 결정 모델의 Jev 같은 API, 정확도, 크기: [Ollama blog 2026-09-29](https://ollama.com/blog/ollama-now-supports-jev-style-decision-models); [Ollama tev1](https://ollama.com/library/tev1); [HF laya](https://huggingface.co/convaiinnovations/laya) [공식]
- Apple FM Python SDK, 가이드 생성, 8,192 컨텍스트: [python-apple-fm-sdk](https://github.com/apple/python-apple-fm-sdk); [WWDC26 241](https://developer.apple.com/videos/play/wwdc2026/241/) [공식]
- Kanana-2 한국어 점수와 라이선스: [HF kanana-2-3b-base](https://huggingface.co/kakaocorp/kanana-2-3b-base) [공식]; [braindetox](https://braindetox.kr/en/posts/kakao_kanana2_open_models_2026.html) [3자]
- Qwen3.5-4B/9B의 M4 Pro 실측: [Rapid-MLX](https://github.com/raullenchai/Rapid-MLX) [커뮤니티]
- EmbeddingGemma 2: [HF](https://huggingface.co/google/embeddinggemma-2) [공식]
- 아는 명령을 플래너에 보내면 실게임에서 20초 늦어진 기록: 레포 `AGENTS.md` "실게임 시나리오에서 배운 것" [로컬]

### Inferences

| 역할 | 1순위 [추정] | 2순위 [추정] | 근거 | 먼저 잴 것 |
|---|---|---|---|---|
| 타입 결정(Choice/Score/Noul) | Jev 클라우드 유지 + Ollama `tev1:0.8b` 병행 비교(`TYPESAFE_BASE_URL`만 바꿈) | laya-multilingual 파인튜닝(CPU 또는 ONNX) / `tev1:4b` | Jev와 같은 API라 코드 변경이 없다. 0.8B는 약 1GB. 공개 정확도 63.5% 대 Jev 76.0% | Jev 로그 재생 일치율, M4 Pro p50/p95, 결정 호출 중 사람 p95 프레임 |
| 한국어 명령 파싱(처음 보는 말) | 결정 모델 choice(닫힌 스킬 목록) + 코드로 수량 추출 | Apple FM `@fm.generable` 열거형 / Qwen3.5-4B + JSON 스키마(`llama-server` 또는 Ollama `format`) | 출력이 1개라 빠르고, 확률로 "모르겠다"를 가를 수 있다. Apple FM은 메모리 0이지만 확률이 없다 | 한국어 발화 셋 정확도, "모르겠다" 임계값 보정 |
| 짧은 한국어 답(대사) | Kanana-2-3B instruct(KoMT 6.92) | Apple 온디바이스(macOS 27) / Qwen3.5-4B non-thinking | 한국어 공개 수치가 가장 높다. 라이선스 4.1(온디바이스 임베드 제공) 확인 필요 | 사람 평가로 자연스러움, 첫 토큰 지연, Apple 가드레일 거부율(전투 대화) |
| 폴백 플래너 | Qwen3.5-4B non-thinking + 스키마 강제(최대 4.4GiB) | Qwen3.5-9B(6.7GiB, 클라우드 음성일 때만) / Apple PCC(32K, entitlement) | Gemini 무료 등급(하루 20회) 소진 시 대체. Eira에서 1.7B는 분해에 실패했으므로 4B가 하한 | 플래너 검증기 통과율, 계획 1회 지연 |
| 임베딩 | EmbeddingGemma 2 텍스트 270M, 256차원 | EmbeddingGemma 300M | 100개 이상 언어, MRL, Ollama MLX | 한국어 회상 정확도, 지연 |
| 런타임 | Ollama 0.40.x 하나로 결정·생성·임베딩(`num_ctx` 명시) | `llama-server`(문법·확률이 꼭 필요한 경로), mlx-lm(Python 내장) | 한 서버로 묶으면 운영이 단순하다. 다만 MLX 경로의 구조화 출력과 logprobs는 3자 근거뿐 | `format`/`logprobs` 직접 호출 시험 |

- [추정] 레포 규칙 7에 맞추는 방법: Jev와 로컬 결정, Gemini와 로컬 플래너 사이의 전환은 config에서 명시적으로 고르게 한다. 장애 시 숨은 폴백을 두지 않는다. 사용자가 "Gemini 한도를 다 쓰면 로컬 플래너로"를 요청하면 그때 명시적 정책으로 만든다.
- [추정] 이번 변화로 가장 값싼 다음 실험은 Ollama 0.40.x 설치 → `tev1:0.8b`를 받고 `num_ctx`를 고정 → 기존 `thorkell contract jev`를 base URL만 바꿔 돌리는 것이다. 정확도와 지연을 Jev와 나란히 재면 된다. 실게임이 필요 없다.

### Gaps
- 위 조합 어느 것도 이 Mac에서 게임 두 개와 함께 잰 적이 없다. 모든 지연·메모리 판정은 다른 Mac(48GB M4 Pro, M3 Ultra, M5 Max)의 수치를 옮긴 추정이다.
- 결정 모델과 Apple FM의 한국어 정확도가 공개된 곳이 없다. 이 프로젝트의 Jev 로그로 직접 평가셋을 만들어야 한다.
