# Apple Silicon(M4 Pro 24GB)에서 게임 두 개와 함께 돌릴 소형 로컬 언어·비전·음성 모델 (2026-10-10 기준)

조사일: 2026-10-11. 표기는 레포 관례를 따른다.
- [공식]: 개발사 모델 카드, 블로그, 문서, 저장소
- [커뮤니티]: 개인 벤치마크, 이슈, 포럼
- [3자]: 언론, 블로그, 애그리게이터
- [추정]: 이 노트에서 계산하거나 추론한 값
- [로컬]: 이 Mac에서 직접 확인한 값

이 Mac의 사양 [로컬, 2026-10-11 `sysctl`·`system_profiler`]
- Apple M4 Pro: CPU 12코어(성능 8 + 효율 4), GPU 16코어, Metal 4
- 통합 메모리 24 GiB(`hw.memsize` 25,769,803,776), macOS 26.2(25C56)
- `iogpu.wired_limit_mb: 0`, 즉 GPU wired 한도는 기본값이다.
- M4 Pro 16코어 GPU는 M4 Pro 중 낮은 구성이다. 벤치마크 범위가 주어지면 아래쪽 값에 가깝다고 본다.

같은 레포의 `docs/research/2026-10-01-thorkell-feasibility.md` §3.3~3.9에 Gemma 4, Jev/laya, Apple Silicon 추론, 한국어 음성 스택 조사가 이미 있다. 이 노트는 그 내용을 다시 확인하고 빈칸(실측 속도, 메모리 예산, 구조화 출력 지원, 한국어 소형 모델, 결정 전용 대안)을 채운다.

---

## Q1. 2026년 10월 현재 쓸 만한 소형 오픈 웨이트 LLM(크기, 라이선스, 한국어, 도구 호출·JSON, 짧은 계획 추론)

### Takeaway
24GB에서 게임 두 개와 함께 돌릴 현실적인 후보는 Qwen3.5-4B/9B(2026-03, Apache-2.0, 201개 언어, 자체 보고 BFCL-V4 50.3/66.1)와 Gemma 4 E2B/E4B(2026-03-31, Apache-2.0, 오디오 입력 포함)다. 한국어 특화 소형 모델(EXAONE 4.0 1.2B, Kanana-1.5 2.1B/8B, HyperCLOVA X SEED 0.5B/1.5B)은 한국어 지식 점수는 높지만 라이선스(EXAONE은 비상업)나 도구 호출 근거가 약하다. 2026년 하반기 Qwen 신작(3.6/3.8)은 27B 이상이나 MoE여서 이 예산에는 들어가지 않는다.

### Cited Findings

**Qwen 계열 (Alibaba)**
- Qwen3.5 소형 시리즈(0.8B, 2B, 4B, 9B)는 2026-03-01~02에 공개됐다. 네이티브 멀티모달(이미지·비디오)이고 Apache-2.0이다. 컨텍스트는 262,144토큰, 지원 언어는 201개, thinking/non-thinking 모드가 있다 — [Qwen X 공지](https://x.com/Alibaba_Qwen/status/2028460046510965160); [MarkTechPost 2026-03-02](https://www.marktechpost.com/2026/03/02/alibaba-just-released-qwen-3-5-small-models-a-family-of-0-8b-to-9b-parameters-built-for-on-device-applications/); [The Rundown](https://www.therundown.ai/tools/qwen3-5-small) [공식/3자]
  - 날짜 불일치: HF 카드를 요약하면 "2026-02"로 나온다. 2월은 Qwen3.5 대형 open-weight가 나온 달이고, 소형은 3월 초로 보인다 — [Wikipedia Qwen](https://en.wikipedia.org/wiki/Qwen)
- Qwen3.5-4B 모델 카드 [공식, 자체 보고]
  - 기본이 thinking 모드다. `"chat_template_kwargs": {"enable_thinking": False}`로 끈다.
  - MMLU-Pro 79.1, MMMLU 76.1, IFEval 89.8, BFCL-V4 50.3, TAU2-Bench 79.9
  - 도구 호출을 지원한다(vLLM/SGLang 파서 설정 제공). 카드가 권장하는 엔진은 vLLM, SGLang, KTransformers, Transformers이고 llama.cpp, mlx-lm, Ollama는 명시하지 않는다.
  - 출처: [HF Qwen/Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B)
- Qwen3.5-9B 모델 카드 [공식, 자체 보고]
  - MMLU-Pro 82.5, MMMLU 81.2, IFEval 91.5, MMLU-ProX 76.3, INCLUDE 75.6, NOVA-63 55.9, WMT24++ 72.6
  - BFCL-V4 66.1, TAU2-Bench 79.1
  - Instruct 모드 권장 샘플링: temperature 0.7, top_p 0.8, top_k 20, presence_penalty 1.5
  - 출처: [HF Qwen/Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B)
- 2026년 Qwen 후속 [3자: Wikipedia 정리]
  - Qwen3.6(2026-04, Apache, 35B-A3B 문서화)
  - Qwen3.8-27B(2026-08-14, Apache-2.0)
  - Qwen3.8-Flash / Flash-Next(2026-08-26, 멀티모달 MoE)
  - Qwen3.8-Omni-Flash(2026-09-18, 텍스트·이미지·오디오·비디오 입력)
  - 3.6~3.8에서 10B 미만 dense 모델은 목록에 없다.
  - 출처: [Wikipedia Qwen](https://en.wikipedia.org/wiki/Qwen)
- Qwen3.8-27B는 Q4_K_M 16.5~19.5GB이고 M4 Mac mini에서 7 tok/s다 — [dev.to "Local LLM Weight Classes, September 2026" (2026-09-06)](https://dev.to/klukyanov/the-local-llm-weight-classes-september-2026-what-actually-fits-on-your-machine-128d) [3자]
  - 같은 글은 노트북급(8~16GB)으로 Qwen3 8B(Q4 약 6GB), Gemma 4 E4B(Q4 약 6GB, 128K 전체 컨텍스트에서 약 12.5GB), Phi-4-mini(약 3.5GB)를 꼽는다.
  - "모델 가중치는 총 메모리 사용량이 아니다"라고 경고한다.

**Gemma 4 (Google)**
- 공식 릴리스 페이지의 날짜 [공식]
  - Gemma 4(E2B, E4B, 31B, 26B A4B): 2026-03-31
  - Gemma 4 MTP(같은 4종): 2026-04-16
  - Gemma 4 12B Unified: 2026-06-03
  - EmbeddingGemma 2(740M): 2026-10-06
  - 출처: [ai.google.dev Gemma releases](https://ai.google.dev/gemma/docs/releases)
  - 레포 feasibility 문서는 출시일을 2026-04-02로 적었다. 공식 페이지 기준으로는 03-31이다.
- E2B는 유효 2.3B(임베딩 포함 5.1B), E4B는 유효 4.5B(임베딩 포함 8B)다 [공식]
  - 컨텍스트 128K, 입력은 텍스트·이미지·오디오, 출력은 텍스트다.
  - 사전학습 언어 140개 이상, 지원 언어 35개 이상이다.
  - Apache-2.0이다. 네이티브 도구 사용과 설정 가능한 thinking 모드가 있다.
  - E4B 점수: MMLU-Pro 69.4, MMMLU 76.6, GPQA Diamond 58.6, LiveCodeBench v6 52.0, τ2 42.2
  - 출처: [HF google/gemma-4-E4B-it](https://huggingface.co/google/gemma-4-E4B-it); [Google 블로그](https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/)
- Gemma 4 12B Unified는 11.95B, Apache-2.0, 컨텍스트 256K, encoder-free 멀티모달이고 오디오를 받는다(CoVoST 38.5) — [xigh/open-weight-models (2026-06 갱신)](https://github.com/xigh/open-weight-models) [3자 큐레이션]

**기타 범용 소형 모델** (출처는 모두 [xigh/open-weight-models](https://github.com/xigh/open-weight-models)이고 2026-06에 갱신된 [3자 큐레이션] 목록이다. 한국어 품질은 목록에 없다)

| 모델 | 크기 | 라이선스 | 비고 |
|---|---|---|---|
| Phi-4-mini | 3.8B | MIT | MATH-500 92.5 |
| Ministral 3 | 3B, 8B, 14B | Apache-2.0 | 3B는 256K. 비전·추론 지원. 8B AIME 78.7 |
| SmolLM3-3B | 3B | Apache-2.0 | 64K, `/think` 모드 |
| Llama 3.2 | 1B, 3B | Llama Community | 128K |
| LFM2.5-1.2B | 1.2B | LFM Open v1.0 | 비전·오디오·thinking 변형 |
| MiniCPM-V 4.6 | 1.2B | Apache-2.0 | 모바일 MLLM |
| Nemotron 3 Nano | 30B MoE(활성 3.5B) | Nemotron OML | 1M 컨텍스트, GPQA 73.0 |
| GLM-4.7-Flash | 30B MoE(활성 3B) | MIT | 200K |

- 다른 검색 요약에는 Nemotron 3 Nano의 4B dense 하이브리드 변형도 있다는 언급이 있다. 원문은 확인하지 못했다. 관련 항목: [Wikipedia Nemotron](https://en.wikipedia.org/wiki/Nemotron).
- Granite 4.0 Nano(350M~)는 HF에 있다 — [HF ibm-granite/granite-4.0-h-350m-base](https://huggingface.co/ibm-granite/granite-4.0-h-350m-base)
- 하이브리드 Mamba-2 계열(Nemotron-3 Nano, Granite-4.0-H, Falcon-H1)의 Apple Silicon 벤치마크가 한 저장소에 모여 있다 — [john-rocky/apple-silicon-llm-bench](https://github.com/john-rocky/apple-silicon-llm-bench) [커뮤니티]

**한국어 특화 소형 모델**

| 모델 | 출시 | 크기·컨텍스트 | 라이선스 | 한국어 점수 | 도구 호출 | 출처 |
|---|---|---|---|---|---|---|
| EXAONE 4.0 1.2B (LG) | 2025-07 | 1.2B(임베딩 제외 1.07B), 65,536토큰. 영어·한국어·스페인어 | EXAONE AI Model License 1.2 - **NC(비상업)** | non-reasoning 기준 KMMLU-Pro 37.5, KMMLU-Redux 40.4 | 지원. BFCL-v3 55.7, τ-Bench Retail 21.7. MMLU-Redux 66.9 | [HF](https://huggingface.co/LGAI-EXAONE/EXAONE-4.0-1.2B) [공식] |
| EXAONE 4.5 (LG) | 2026-04-09 | 33B(LM 31.7B + 비전 1.29B). LG 첫 오픈 웨이트 VLM | – | – | – | [HF EXAONE-4.5-33B](https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B) [공식, 검색 요약] |
| Kanana-1.5 2.1B / 8B (Kakao) | 2025-05-23 | 2.1B, 8B | **Apache-2.0(상업 가능)** | – | 1.5에서 코딩·수학·함수 호출이 개선됐다고 함 | [Kakao 보도자료](https://www.kakaocorp.com/page/detail/11654?lang=ENG); [kakao/kanana](https://github.com/kakao/kanana) [공식] |
| Kanana 1.0 Nano 2.1B / Essence 9.8B | 2025-02 기술보고서 | 2.1B, 9.8B | Nano 2.1B 컬렉션은 CC-BY-NC-4.0 | Nano KMMLU 44.80, HAE-RAE 77.09. Essence KMMLU 50.57, HAE-RAE 84.98. 비교: EXAONE-3.5-7.8B KMMLU 45.30 | – | [kakao/kanana](https://github.com/kakao/kanana) [공식] |
| HyperCLOVAX-SEED-Text-Instruct-1.5B (Naver) | 2025-04 | 1.5B, 16K | `hyperclovax-seed` 자체 라이선스 | KMMLU 0.3933, HAE-RAE 0.5674, CLIcK 0.4947, KoBEST 0.6490. 비교: Qwen2.5-1.5B 0.3696/0.5160/0.4772/0.5968, Gemma-3-1b 0.3075/0.3648/0.3724/0.5869 | 미기재 | [HF](https://huggingface.co/naver-hyperclovax/HyperCLOVAX-SEED-Text-Instruct-1.5B); 출시일은 [CLOVA 블로그 2025-04-23](https://clova.ai/en/tech-blog/sowing-the-seeds-in-the-ai-ecosystem-introducing-hyperclova-x-seed-a-commercial-open-source-ai) [공식] |

- Kanana 추가 정보
  - 같은 컬렉션의 3B와 15.7B는 KANANA LICENSE를 쓴다.
  - 검색 요약 점수는 Kanana-1.5-2.1B KMMLU 45.10, Kanana-8B 48.30이다 — [PyTorchKR landscape #861](https://github.com/PyTorchKR/landscape/issues/861) 등 [3자]
  - Kanana-2는 총 32B, 활성 3B MoE이고 에이전트용으로 최적화됐다. 2.5를 개발 중이다 — [presenc.ai](https://presenc.ai/research/korean-ai-llm-companies-2026), [agmazon 2026-07](https://agmazon.com/blog/articles/technology/202607/kanana-ai-complete-guide-en.html) [3자, 원문 수치 미확인]
- 공개된 SEED 라인은 6종이다 — [hokai.io](https://hokai.io/hub/models/hyperclova-x); [Naver](https://www.navercorp.com/en/tech/hyperclovax) [3자/공식]
  - 텍스트 0.5B, 1.5B
  - 3B vision-instruct
  - 8B Omni
  - 14B Think, 32B Think

**OS 내장 모델 (Apple Foundation Models)**
- macOS 26 이상, Apple Silicon에서 Apple Intelligence 온디바이스 LLM을 앱에서 직접 부른다 [3자 해설, 2026-06-03/07-07 갱신]
  - `@Generable` 가이드 생성으로 타입이 정해진 구조화 출력을 받는다. `@Guide`로 범위·정규식 제약을 건다. `Tool` 프로토콜로 도구를 호출한다.
  - 컨텍스트는 프롬프트와 응답을 합쳐 4,096토큰이다.
  - Swift 전용이다.
  - 출처: [blakecrosley.com](https://blakecrosley.com/blog/apple-foundation-models-framework); [natashatherobot](https://www.natashatherobot.com/p/apple-foundation-models)
- Apple Intelligence는 macOS Sequoia 15.4부터 한국어를 지원한다 — [designcompass 2025-04-02](https://designcompass.org/en/2025/04/02/apple-intelligence-korean/) [3자]

**구조화 출력의 크기 하한 경고**
- LM Studio 문서는 "7B 미만 LLM은 구조화 출력을 못 하는 경우가 많다"고 경고한다 — [LM Studio docs](https://lmstudio.ai/docs/developer/openai-compat/structured-output) [공식]

### Inferences
- [추정] 플래너 후보는 Qwen3.5-9B(non-thinking, Q4 약 5.5~6GB)가 가장 유력하다.
  - 자체 보고치이긴 하지만 BFCL-V4 66.1, τ2 79.1, MMMLU 81.2로 소형 중 도구 호출·다국어가 가장 강하다.
  - Gemma 4 E4B는 τ2 42.2로 에이전트 지표가 크게 낮다. 대신 오디오 입력이 있어 음성 이해 겸용 후보다.
- [추정] 한국어 대화 품질은 공개 점수만 보면 다음 순서로 보인다. 다만 같은 벤치마크로 나란히 잰 자료가 없어 확정할 수 없다.
  - 한국 특화 소형(Kanana, HyperCLOVA SEED)이 같은 크기의 범용 모델(Qwen2.5, Gemma 3)보다 높다.
  - 최신 Qwen3.5와 Gemma 4의 KMMLU는 찾지 못했다(Gaps 참조).
- [추정] 라이선스 결론
  - 사용자가 상업 배포를 하지 않는 개인 프로젝트라면 EXAONE NC도 쓸 수 있다.
  - 배포를 고려하면 Apache-2.0(Qwen3.5, Gemma 4, Kanana-1.5 2.1B/8B, Ministral 3, SmolLM3)이 안전하다.
- [추정] Apple Foundation Models는 다음 이유로 "타입 결정" 실험 후보다.
  - 모델이 OS에 이미 올라와 있어 앱이 따로 가중치를 들고 있지 않는다.
  - `@Generable`이 스키마 제약 디코딩을 기본으로 준다.
  - 다만 Swift 전용이라 Python 두뇌와 붙이려면 헬퍼 프로세스가 필요하다. 4K 컨텍스트와 한국어 품질도 직접 측정해야 한다.
- [추정] 짧은 계획(3~8단계 JSON)은 4B급도 스키마 제약 디코딩과 함께 쓰면 형식은 맞출 수 있다. 다만 Eira에서 1.7B가 목표 분해에 실패한 기록(AGENTS.md)을 고려하면 내용 품질은 9B 이상이나 클라우드 플래너가 낫다. 목표 분해는 9B, 수치는 코드가 맡는 분업이 맞다.

### Gaps
- Qwen3.5-4B/9B와 Gemma 4 E2B/E4B의 KMMLU·HAE-RAE·KoBEST 점수를 같은 조건으로 잰 공개 자료를 찾지 못했다. Open Ko-LLM 리더보드와 Horangi의 2026년 순위도 확인하지 못했다.
- Upstage "Solar Mini 4"(2026-09-23 출시라는 3자 언급, [morphllm](https://www.morphllm.com/best-open-source-llm))는 Upstage 쪽 자료로 확인되지 않았다. 오픈 웨이트 여부, 크기, 라이선스가 미확인이다.
- LFM2.5의 "매출 1천만 달러 미만만 상업 무료" 조건과 Galaxy S25 Ultra CPU 70 tok/s·719MB 수치는 검색 요약에만 있었다. 원문을 확인하지 못했다.
- Qwen3.8-Flash 계열의 크기와 오픈 웨이트 여부는 확인하지 못했다.
- Apple 온디바이스 모델의 크기, 양자화, Mac에서의 tok/s, 한국어 구조화 출력 품질에 대한 1차 자료를 찾지 못했다.
- Phi-5, Llama 4.x 소형, SmolLM4 같은 2026년 후속 소형 모델이 있는지 확인하지 못했다.

---

## Q2. Mac 추론 스택(MLX/mlx-lm, llama.cpp, Ollama, LM Studio): 속도, TTFT, 메모리, 구조화 출력, 프롬프트 캐시, speculative decoding

### Takeaway
M4 Pro(273 GB/s)에서 4비트 7~9B의 생성 속도는 약 40~50 tok/s, prefill은 약 360~450 tok/s(llama.cpp 기준)다. 4B급은 그 약 1.6~2배로 본다. MLX는 같은 모델에서 llama.cpp보다 생성이 빠르고(M4 Max에서 1.4~2배), 전력도 덜 쓴다. 하지만 스키마 제약 디코딩·도구 호출·프롬프트 캐시 재사용을 서버 수준에서 모두 갖춘 것은 llama.cpp `llama-server`다. mlx-lm 서버는 `logprobs`와 draft 모델은 있지만 `response_format`/JSON 스키마는 문서화되어 있지 않다.

### Cited Findings

**대역폭과 기준 속도**
- M4 Pro의 메모리 대역폭은 273 GB/s다 — [llama.cpp Apple Silicon 벤치 #4167](https://github.com/ggml-org/llama.cpp/discussions/4167) [커뮤니티 표준 벤치]
- 같은 벤치에서 Llama 2 7B 결과 [커뮤니티]

  | 칩 | 정밀도 | PP512 (t/s) | TG128 (t/s) |
  |---|---|---|---|
  | M4 Pro (GPU 16~20코어) | Q4_0 | 364~440 | 49.6~50.7 |
  | M4 Pro | Q8_0 | 367~450 | 30.5~30.7 |
  | M4 Pro | F16 | 381~464 | 17.2 |
  | M3 Pro | Q4_0 | 269~342 | 30.7 |
  | M4 Max | Q4_0 | 714~886 | 70~83 |
  | M4(기본) | Q4_0 | 221 | 24.1 |

- M4 Pro에서 7B Q4(약 4GB)의 이론 최대 생성 속도는 약 68 tok/s다 — [starmorph 가이드](https://blog.starmorph.com/blog/apple-silicon-llm-inference-optimization-guide) [3자]

**엔진 비교 (M4 Max, john-rocky 벤치, 짧은 대화 128토큰, decode 중앙값)** — [john-rocky/apple-silicon-llm-bench](https://github.com/john-rocky/apple-silicon-llm-bench) [커뮤니티, 세션·양자화 명시]

| 모델 | MLX-Swift Q4 | llama.cpp Q4_K_M | CoreML-LLM |
|---|---|---|---|
| Qwen3.5 2B | 291.9 | 149.7 | 35.0 |
| Gemma 4 E2B | 185.4 | 119.2 | 32.5 |
| Gemma 4 E4B | 113.5 | 80.5 | – |

- 같은 벤치의 다른 측정
  - Gemma 4 E2B TTFT: MLX 68ms, llama.cpp 41ms, CoreML 525ms
  - 전력: MLX PTQ 4비트 0.090 J/token(패키지 14.6W), llama.cpp Q4_K_M 0.170 J/token(20.5W)
  - 메모리: CoreML/ANE는 0.8~2B 모델에서 약 230MB를 유지했다. llama.cpp는 모델 크기에 따라 1,443~5,150MB였다.
  - Qwen3-8B(512 prefill / 1024 생성): Apple Core AI 94.1 tok/s, MLX 90.0 tok/s
- 다른 비교 [3자, 인용 수치 혼재] — [yage.ai 2026-03-31](https://yage.ai/share/mlx-apple-silicon-en-20260331.html)
  - M4 Pro, Qwen3-Coder-30B-A3B: MLX 130 tok/s 대 Ollama(llama.cpp) 43 tok/s [Reddit 인용]
  - 같은 모델의 메모리: MLX 34.7GB 대 GGUF 40GB [Reddit 인용]
  - M4 Max, Qwen3.5-35B-A3B: llama.cpp Metal 89.4 tok/s [GitHub #14861 인용]
  - llama.cpp 쪽 이슈는 Qwen3 Coder Next에서 llama.cpp 생성 속도가 MLX의 약 1/3이라고 보고한다 — [llama.cpp #19366](https://github.com/ggml-org/llama.cpp/issues/19366) [커뮤니티]
- Ollama 0.19.0(2026-03-30 발표)의 엔진 분기 [3자]
  - Apple Silicon에서 safetensors 모델은 MLX, GGUF는 llama.cpp(Metal)로 보낸다.
  - 출처: [yage.ai](https://yage.ai/share/mlx-apple-silicon-en-20260331.html); [9to5Mac 2026-03-31](https://9to5mac.com/2026/03/31/ollama-adopts-mlx-for-faster-ai-performance-on-apple-silicon-macs/); [levelup "58 → 112 tok/s"](https://levelup.gitconnected.com/ollama-mlx-nearly-doubles-llm-speed-on-your-mac-58-to-112-tok-s-and-your-old-models-get-none-of-fd1a9ec531fb)
- 2025-11 비교 연구의 처리량 순서 [논문]
  - MLX(약 230 tok/s) > MLC-LLM(약 190) > llama.cpp(약 150) > Ollama(20~40) > PyTorch MPS(7~9)
  - MLX는 GPU를 90% 이상 쓰고 CPU는 3% 미만이다.
  - 모델·칩 조건은 검색 요약에서 확인하지 못했다.
  - 출처: [arXiv 2511.05502](https://arxiv.org/pdf/2511.05502)
- SiliconBench(arXiv 2609.19169, 2026-09-12) [논문, 초록만 확인]
  - Apple Silicon 서빙 엔진 9종(vllm-metal, omlx 등)을 Qwen3, Qwen3.5, Gemma 4로 비교했다.
  - Qwen3-0.6B에서 vllm-metal은 동시성 1→16에서 처리량이 2배 이상이 됐다.
  - 출처: [arXiv 2609.19169](https://arxiv.org/abs/2609.19169)

**M4 Pro 24GB의 Qwen3.5 수치 (작성자가 [추정]이라고 밝힌 값)** — [willitrunai 2026-04-20](https://willitrunai.com/blog/qwen-3-5-mlx-apple-silicon-guide)
- 9B Q8: 약 10GB, 30~40 tok/s
- 27B 4비트: 약 18GB, 18~25 tok/s
- "macOS가 약 3.5GB를 예약한다"

**같은 레포 feasibility 문서의 기존 수치** [커뮤니티]
- Qwen3.5-9B M4 Pro: prefill 약 450, 생성 약 50 tok/s
- Gemma 4 E4B M4 Pro: 49~57 tok/s

**기능 지원 표**

| 기능 | llama.cpp `llama-server` [공식] | mlx-lm [공식] | LM Studio [공식] | Ollama |
|---|---|---|---|---|
| JSON 스키마·문법 제약 | `json_schema`, `grammar`(GBNF), `response_format` | 서버 문서에 `response_format`/스키마 없음 | GGUF는 llama.cpp 문법, MLX는 Outlines(`lmstudio-ai/mlx-engine`) | 확인 못 함 |
| 프롬프트 캐시 | `cache_prompt`(기본 켜짐), `--cache-reuse`, `/slots/{id}?action=save\|restore` | `mlx_lm.cache_prompt --prompt-cache-file`, `--max-kv-size`(회전 KV), Python API 다중 턴 캐시. `--prefill-step-size` 기본 2048 | 미기재 | 확인 못 함 |
| Speculative decoding | `--model-draft`, `--spec-draft-n-max/min`, `--spec-type`(draft-simple, ngram 계열) | 서버 `draft_model`, `num_draft_tokens`(기본 3) | 미기재 | 확인 못 함 |
| 토큰 확률 | `n_probs`, `post_sampling_probs`, `top_logprobs` | `logprobs`(1~10), `logit_bias` | – | – |
| 도구 호출 | `--jinja`, `parallel_tool_calls` | SERVER.md에 없음 | – | – |
| 멀티모달 | 이미지·오디오·비디오 입력, `--mmproj-auto` | (mlx-vlm 별도) | – | – |

- 출처: [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md); [mlx-lm README](https://github.com/ml-explore/mlx-lm); [mlx-lm SERVER.md](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/SERVER.md); [LM Studio structured output](https://lmstudio.ai/docs/developer/openai-compat/structured-output)
- MLX용 제약 디코딩 라이브러리 `llm-structured-output`이 있다. 스키마를 문법으로 바꾸지 않고 스키마로 직접 출력을 조종한다 — [PyPI llm-structured-output](https://pypi.org/project/llm-structured-output/) [공식]
- 제약 디코딩 엔진 비교: XGrammar와 llguidance는 재귀 스키마까지 처리하는 CFG 엔진으로 디코딩 오버헤드가 거의 없다. Outlines는 FSM 방식이라 재귀 스키마를 평탄화해야 한다 — [JSONSchemaBench arXiv 2501.10868](https://arxiv.org/abs/2501.10868) [논문]
- Ollama 0.19의 MLX 엔진은 2배 가까이 빨라졌다는 체감 보고가 있다 — [XDA](https://www.xda-developers.com/ollama-new-mlx-engine-local-llm-mac-twice-fast/) [3자]
- M5 대 M4(Qwen3-14B 4비트): TTFT 4.06배, 생성 1.19배 빠르다 — [Apple ML Research](https://machinelearning.apple.com/research/exploring-llms-mlx-m5) [공식, yage.ai 인용]. 이 Mac(M4 Pro)에는 해당하지 않는다.

### Inferences
- [추정] 이 Mac(M4 Pro 16코어 GPU)에서 4비트 Qwen3.5-4B의 기대치
  - 생성 약 60~80 tok/s, prefill 약 700~900 tok/s(7B 측정치를 크기로 환산)
  - 캐시 없는 1,000토큰 프롬프트의 TTFT는 약 1.1~1.4초다.
  - 시스템 프롬프트·스키마를 캐시하고 새 상태 200토큰만 넣으면 약 0.25~0.3초다.
  - 여기에 30토큰 JSON을 생성하면 0.4~0.5초가 더 걸려서 합계 약 0.7~0.8초다.
  - 결론: 600ms 마감의 타입 결정을 생성 LLM으로 맞추기는 빠듯하다. 출력 1토큰(선택지 라벨)을 `n_probs`/`logprobs`로 점수 매기면 0.3초 안팎으로 줄어든다.
- [추정] 9B는 위 값의 약 절반 속도다. 계획 1회(입력 2~4k 중 대부분 캐시, 출력 200~400토큰 JSON)는 5~12초로 본다. gemini-3.8-flash의 수초~수십 초와 비슷하고, 하루 20회 한도는 없어진다.
- [추정] 엔진 선택
  - "JSON 스키마 강제 + 프롬프트 캐시 + 확률 출력"이 한 프로세스에 다 필요하면 `llama-server`가 지금 가장 완성도가 높다.
  - 속도와 전력이 우선이면 MLX다. 다만 스키마 강제는 Outlines/`llm-structured-output`/LM Studio mlx-engine을 따로 붙여야 한다.
  - 레포 규칙 7(숨은 폴백 금지)에 맞추려면 엔진 선택을 config로 명시한다.
- [추정] speculative decoding의 이득
  - 대화처럼 긴 출력에서 생긴다. 출력이 짧은 결정·JSON 계획에서는 이득이 작다.
  - 그리고 draft 모델도 GPU 메모리와 대역폭을 쓴다. 따라서 게임 옆에서는 우선순위가 낮다.

### Gaps
- M4 Pro 24GB(16코어 GPU)에서 Qwen3.5-4B/9B와 Gemma 4 E2B/E4B를 MLX와 llama.cpp로 나란히 잰 TTFT·prefill 1차 측정을 찾지 못했다. 검색 요약에 "M4 Pro 48GB에서 9B 49.76 / 4B 83.45 tok/s(512→128)"가 있었지만 원문을 확인하지 못했다. 직접 `llama-bench`/`mlx_lm.benchmark`로 재야 한다.
- Ollama의 구조화 출력(`format` JSON 스키마)이 MLX 엔진 경로에서도 지원되는지 확인하지 못했다.
- mlx-lm 최신 버전(2026-10)에 `response_format`이 추가됐는지는 저장소 문서에서 보이지 않았다. 문서 갱신이 늦었을 수 있다.
- Gemma 4 MTP 체크포인트가 speculative decoding용 multi-token prediction 헤드인지, llama.cpp와 MLX에서 쓸 수 있는지 확인하지 못했다.

---

## Q3. 게임 두 개 옆에서 돌릴 때: GPU 경합과 24GB 메모리 예산

### Takeaway
macOS는 앱별 GPU 우선순위를 사용자가 정할 수 없다. 전체화면 게임에 Game Mode가 CPU·GPU 최우선권을 주는 정도다. MLX가 GPU를 100% 쓰면 다른 GPU 앱이 끊긴다는 보고는 있지만, Mac에서 게임 프레임 하락을 정량으로 잰 자료는 찾지 못했다. 이 Mac에서 Valheim 클라이언트 하나의 최대 RSS는 약 3.0~3.4GB다. 24GB에서 OS와 게임 둘을 빼면 모델에 안전하게 쓸 수 있는 몫은 약 6~8GB다. 4B LLM + ASR + TTS + laya 조합이 상한이고, 9B는 가능하지만 빠듯하다.

### Cited Findings
- macOS Game Mode [공식]
  - 게임에 "CPU와 GPU의 최우선 접근권"을 주고 백그라운드 작업 사용량을 낮춘다.
  - 게임이 전체화면에 들어가면 자동으로 켜지고, 종료하면 꺼진다.
  - 출처: [Apple Support 105118](https://support.apple.com/ur-in/105118); 동작 분석은 [Eclectic Light 2023-10-17](https://eclecticlight.co/2023/10/17/what-does-game-mode-do/) [3자]
- omlx 이슈 #2264 [커뮤니티]
  - MLX 추론 중 GPU가 100%가 되면서 VSCode 스크롤이 끊기고 웹앱에 키 입력 지연이 생겼다. 메모리 압박과 스왑은 없었다.
  - 다른 사용자는 M1·M5에서 GPU 100%여도 부드러웠다며 메모리 원인을 의심했다. 보고자는 반박했다.
  - 2026-10-07에 "not planned"로 닫혔고, 해결책은 없다.
  - 출처: [jundot/omlx #2264](https://github.com/jundot/omlx/issues/2264)
- 모바일 SoC의 GPU 전용 LLM 추론과 게임 동시 실행 [논문]
  - 검색 요약(본문 인용)에 따르면 GPU 전용 기준선은 GPU 제출 큐를 포화시켜 게임 프레임을 0까지 떨어뜨렸다. GPU+NPU 이기종 방식(HeteroInfer)은 게임 프레임에 영향이 없었고 prefill은 0.5~2.2%만 줄었다.
  - 초록은 "다른 앱과의 간섭이 무시할 만하다"고만 적는다. 이 노트에서 본문 수치는 직접 확인하지 못했다.
  - 출처: [arXiv 2501.14794](https://arxiv.org/abs/2501.14794)
- 레포 feasibility 문서도 "게임과 모델이 GPU를 같이 쓰면 프레임이 떨어진다"는 판단 아래 ASR은 Neural Engine, TTS는 CPU로 나누자고 제안했다 [커뮤니티/추정] (`docs/research/2026-10-01-thorkell-feasibility.md` §3.7)
- CoreML/ANE 경로는 0.8~2B LLM에서 약 230MB만 썼지만 decode가 32~35 tok/s로 느렸다(M4 Max) — [john-rocky bench](https://github.com/john-rocky/apple-silicon-llm-bench) [커뮤니티]
- Metal GPU 메모리 한도 [3자]
  - 24GB M4 Pro의 기본 `recommendedMaxWorkingSetSize`는 약 17.76 GiB(약 74%)다.
  - `iogpu.wired_limit_mb`로 올릴 수 있지만 Apple이 문서화하지 않은 sysctl이다.
  - 한도를 올리기보다 KV 캐시를 양자화하라는 조언이 있다(`-ctk q4_0 -ctv q4_0`).
  - 출처: [bestllmfor](https://bestllmfor.com/guide/optimiser-mac-silicon-llm/); [localaimaster](https://localaimaster.com/blog/mac-memory-pressure-local-llm); [MLX memory API](https://www.mintlify.com/ml-explore/mlx/api/memory)
- 이 Mac은 `iogpu.wired_limit_mb: 0`(기본값)이다 [로컬]
- Valheim 클라이언트 실측 [로컬]
  - 출처: `artifacts/native/*/report.json`. `ps -o rss`로 1초 간격 샘플링했다. 2026-10-02 실게임 시나리오 약 50회(peer, primitives, rehearsal).
  - 호스트 클라이언트 최대 RSS: 중앙값 3,051MB, 최대 3,447MB. 최대값은 사람 백업 월드를 쓴 rehearsal이다.
  - 봇 클라이언트 최대 RSS: 중앙값 3,031MB, 최대 3,068MB
  - 둘 다 x86_64 Rosetta, Metal 그래픽이다.
  - 주의
    - 짧은 시나리오(수 분)와 작은 월드 기준이다.
    - RSS는 Metal 버퍼 같은 GPU 할당을 다 포함하지 않을 수 있다. `phys_footprint`로 다시 재야 한다.
- Valheim 공식 사양은 RAM 최소 8GB, 권장 16GB다 — [sysrqmts](https://sysrqmts.com/de/games/valheim) [3자]
  - 서버 메모리는 플레이어 수보다 월드 크기를 따라간다 — [connecthosting](https://connecthosting.net/blog/how-much-ram-valheim-dedicated-server) [3자]
- macOS는 약 3.5GB를 예약한다. 24GB에서 27B를 돌리려면 브라우저·Docker·IDE를 닫으라는 조언이 있다 — [willitrunai](https://willitrunai.com/blog/qwen-3-5-mlx-apple-silicon-guide) [3자, 추정치]
- Gemma 4 E4B는 Q4 약 6GB이고 128K 컨텍스트를 다 쓰면 약 12.5GB다. "가중치 ≠ 총 메모리"다 — [dev.to 2026-09-06](https://dev.to/klukyanov/the-local-llm-weight-classes-september-2026-what-actually-fits-on-your-machine-128d) [3자]
- 레포 feasibility 문서의 목표 [추정]: 클라이언트 두 개와 큰 월드에서 총 RSS 16GB 이하, 사람 p95 프레임 1.25배 이하, 스왑 증가 없음.

### Inferences
- [추정] 24GiB 예산표

  | 항목 | 예산 | 근거 |
  |---|---|---|
  | macOS, WindowServer, Steam, 브라우저 최소 | 약 4.5~5.5GB | 예약 3.5GB + Steam·기타 |
  | Valheim 클라이언트 2개 | 약 6.5~8GB | 실측 각 3.0~3.4GB. 월드가 커지면 늘어날 여유를 둠 |
  | Python 두뇌, 브리지 | 약 0.5~1GB | – |
  | **모델에 쓸 몫** | **약 6~8GB(스왑 없는 안전권). 최대 약 10GB** | – |

- [추정] 이 예산 안에서 고를 수 있는 조합
  - (A) Qwen3.5-4B 4비트(약 2.5~3GB) + KV 4K(약 0.3~0.5GB) + laya-multilingual 322M(fp16 약 0.7GB) + Whisper turbo/Qwen3-ASR(1.9~2.4GiB) + Supertonic(약 0.3GB) = 약 6~7GB
  - (B) 9B 4비트(약 5.5~6GB)를 넣으려면 ASR과 TTS를 클라우드에 남겨야 한다.
  - 27B와 35B-A3B는 예산을 넘는다.
- [추정] GPU 경합 대응
  - 사람 클라이언트를 전체화면으로 두면 Game Mode가 그 프로세스를 우선한다. 봇 클라이언트와 모델은 백그라운드로 밀린다.
  - 봇 클라이언트도 GPU를 쓰므로 렌더 해상도와 프레임 상한을 낮춰 두는 편이 좋다.
  - LLM은 상시로 돌리지 말고 이벤트가 있을 때만 짧게 돌린다. prefill 한 번은 GPU를 100% 쓰는 수백 ms 버스트다.
  - ASR은 ANE(WhisperKit/CoreML), TTS는 CPU(Supertonic ONNX)로 보내 GPU를 비운다.
  - 이 원칙들은 실측(사람 p95 프레임)으로 확인해야 한다.
- [추정] MLX/llama.cpp에는 GPU 사용률 상한 설정이 없다(omlx 이슈에도 해결책 없음). 경합은 호출 빈도, 배치 크기(`--prefill-step-size`를 작게), 모델 크기로만 조절할 수 있다.

### Gaps
- Mac에서 Metal 게임과 MLX/llama.cpp를 동시에 돌렸을 때의 프레임 시간 측정(1차 자료)을 찾지 못했다. 이 레포에서 직접 재야 한다(레포 규칙 3에 따라 한 번에 하나씩).
- Game Mode가 Rosetta x86_64 게임에도 똑같이 적용되는지, 창 모드 두 클라이언트 중 하나만 전체화면일 때 어떻게 동작하는지 확인하지 못했다.
- Valheim 클라이언트의 `phys_footprint`(GPU 메모리 포함)와 오래 탐험한 월드에서의 증가 폭은 측정하지 못했다.

---

## Q4. 한국어 로컬 음성: ASR, TTS, speech-to-speech와 Mac 지연

### Takeaway
ASR은 Qwen3-ASR-1.7B(MLX 8비트)가 Whisper large-v3-turbo보다 한국어 CER이 낮고(3.54% 대 4.25%) 3.7배 빠르다(Mac 측정). 단 4비트로 줄이면 한국어가 크게 무너진다. TTS는 Supertonic 3(99M, CPU, 31개 언어)와 Qwen3-TTS(0.6B/1.7B, 10개 언어)가 한국어 로컬 후보다. 한국어로 쓸 수 있는 로컬 speech-to-speech 모델(HyperCLOVA X SEED 8B Omni)은 GPU 약 48GB가 필요해서 이 Mac에서는 쓸 수 없다. 현실적인 답은 VAD → ASR → LLM → TTS 파이프라인이다.

### Cited Findings

**ASR**
- Qwen3-ASR 1.7B 대 Whisper large-v3-turbo [3자 블로그 실측, 2026-08-25] — [whispernotes](https://whispernotes.app/blog/qwen3-asr-vs-whisper)
  - 환경: M5 MacBook Air 32GB, macOS 27.0. Qwen3-ASR은 MLX 8비트, Whisper는 whisper.cpp Metal.
  - 한국어 FLEURS CER: Qwen3-ASR 3.54%, Whisper 4.25%
  - 실시간 대비 속도(중앙값): Qwen3-ASR 9.6배, Whisper 2.6배
  - 최대 프로세스 메모리: Qwen3-ASR 2.43 GiB, Whisper 1.87 GiB
- 양자화 영향과 스트리밍 [3자, 검색 요약, 원문 표 미확인] — [soniqo benchmarks](https://soniqo.audio/benchmarks); [mstar PR #318](https://github.com/mstar-project/mstar/pull/318)
  - Qwen3-ASR 4비트의 한국어 WER은 19.95, 8비트는 6.89였다.
  - Qwen3-ASR 0.6B 스트리밍의 부분 결과 지연은 단일 세션에서 p50 54ms, p95 95ms였다.
- Qwen3-ASR을 MLX로 Mac에서 실시간 전사하는 런타임 사례가 있다 — [epidemiology.tech](https://epidemiology.tech/al-ml-dl/qwen3-asr-mlx-runtime-for-realtime-transcription-on-mac/) [3자]
- WhisperKit(arXiv 2507.10860, 2025-07-14) [논문, 영어 기준]
  - 온디바이스에서 가설당 지연 0.46초, WER 2.2%다.
  - gpt-4o-transcribe, Deepgram nova-3, Fireworks large-v3-turbo와 견줘 지연은 가장 낮은 값과 같고 정확도는 가장 높았다.
  - 출처: [arXiv 2507.10860](https://arxiv.org/html/2507.10860v1)
- 한국어로 파인튜닝한 whisper-large-v3-turbo(Zeroth-KO)는 자체 평가셋에서 CER 6.60%다 — [HF o0dimplz0o](https://huggingface.co/o0dimplz0o/Whisper-Large-v3-turbo-STT-Zeroth-KO-v2) [커뮤니티]
- SenseVoice Small은 중국어·일본어·한국어·광둥어 전용 엔진이고 MLX로 Apple GPU에서 돈다 — [whispernotes SenseVoice](https://whispernotes.app/blog/sensevoice-fastest-cjk-transcription) [3자]
- 저비트 Whisper로 한국어 ASR을 다룬 사례가 있다 — [ENERZAi](https://enerzai.com/resources/blog/small-models-big-heat-conquering-korean-asr-with-low-bit-whisper) [3자]

**TTS**
- Supertonic 3 (Supertone, 2026-04-29) [공식] — [GitHub supertone-inc/supertonic](https://github.com/supertone-inc/supertonic)
  - 31개 언어에 한국어(`ko`)가 들어 있다.
  - 공개 ONNX 자산 기준 약 99M 파라미터다. ONNX Runtime으로 CPU에서 돌고 GPU가 필요 없다.
  - 출력은 44.1kHz 16비트다.
  - 코드는 MIT, 모델은 OpenRAIL-M이다.
  - Raspberry Pi에서 평균 RTF 0.3이다. 내장 목소리 복제는 없다.
  - Voice Builder 서비스는 2026-08-31에 종료됐다.
  - feasibility 문서는 저장소가 2026-09-09에 아카이브됐다고 기록했다.
  - 다른 자료는 약 305MB ONNX 자산이라고 적었다 — [pinggy](https://pinggy.io/blog/best_open_source_self_hosted_text_to_speech_models/) [3자]
- Qwen3-TTS (2026-01-22) [공식/3자] — [Qwen 블로그](https://qwen.ai/blog?id=qwen3tts-0115); [openvoxai](https://openvoxai.com/blog/best-free-local-tts-models-2026)
  - 10개 언어에 한국어가 들어 있다.
  - 0.6B와 1.7B, 각각 Base / CustomVoice / VoiceDesign이 있다.
- CosyVoice2는 한국어를 포함한 9개 언어와 다언어 zero-shot 복제를 지원한다. 코드와 가중치 모두 Apache-2.0이다 — [pinggy](https://pinggy.io/blog/best_open_source_self_hosted_text_to_speech_models/) [3자]
- 한국어를 지원하는 로컬 TTS 목록 — [HeeJayC/Awesome-Korean-TTS-Local-](https://github.com/HeeJayC/Awesome-Korean-TTS-Local-) [커뮤니티]
- 이미 정리된 항목 (레포 feasibility §3.7)
  - Kokoro-82M, Kyutai TTS, Sesame CSM은 한국어를 지원하지 않는다.
  - Qwen3-TTS를 Mac에서 쓰는 경로는 mlx-audio 또는 Argmax TTSKit(CoreML, 청크당 약 80ms)다.

**Speech-to-speech / 옴니**
- HyperCLOVA X SEED 8B Omni [공식]
  - 8B dense, "Any-to-Any-Korean-First"
  - 입력은 텍스트·이미지·비디오·음성, 출력은 텍스트·이미지·음성이다.
  - 전용 라이선스(HyperCLOVA X SEED 8B Omni Model License)다.
  - 권장 하드웨어는 A100 80GB 3~4장, 구성요소 합계 VRAM 약 48GB다.
  - 런타임은 Transformers(`trust_remote_code`), vLLM, SGLang, OmniServe다.
  - 출처: [HF HyperCLOVAX-SEED-Omni-8B](https://huggingface.co/naver-hyperclovax/HyperCLOVAX-SEED-Omni-8B); [CLOVA 블로그 2026-01-14](https://clova.ai/en/tech-blog/hyperclova-x-omni-koreas-flagship-ai-on-the-road-to-omnimodality)
- Qwen3.8-Omni-Flash(2026-09-18)는 텍스트·이미지·오디오·비디오를 받는다 — [Wikipedia Qwen](https://en.wikipedia.org/wiki/Qwen) [3자]. 오픈 웨이트 여부와 크기는 확인하지 못했다.
- Gemma 4 E2B/E4B는 오디오 입력을 받는다(출력은 텍스트) — [HF gemma-4-E4B-it](https://huggingface.co/google/gemma-4-E4B-it) [공식]
- 레포 feasibility §3.7 정리
  - Moshi와 PersonaPlex는 영어만 된다.
  - Raon-Speech-9B는 CC BY-NC 4.0이고 CUDA가 필요하다.
  - Qwen3-Omni-30B-A3B는 BF16 기준 약 79GB가 필요하다.
  - 한국어 로컬 full-duplex 오픈 모델은 사실상 없다.
  - Pipecat `macos-local-voice-agents`는 영어로 음성→음성 800ms 미만이다.

### Inferences
- [추정] 이 Mac의 로컬 한국어 음성 파이프라인 후보
  - Silero VAD + Smart Turn(CPU)
  - → Qwen3-ASR-0.6B/1.7B MLX 8비트(GPU, 약 2.4GiB) 또는 WhisperKit turbo(ANE)
  - → Qwen3.5-4B(non-thinking, 스트리밍)
  - → Supertonic 3(CPU)
  - 게임과 GPU를 덜 다투려면 ASR을 ANE 경로(WhisperKit 또는 Apple SpeechAnalyzer)에 둔다. 한국어 정확도는 Qwen3-ASR 8비트가 낫다. 둘 중 무엇을 고를지는 실측해서 정한다.
- [추정] 지연 예산(말 끝 → 첫 소리)
  - 턴 감지 약 0.2~0.5초
  - ASR 확정 약 0.1~0.3초(9.6배 실시간이면 3초 발화를 약 0.3초에 처리)
  - LLM TTFT 약 0.3~0.6초(캐시 사용)
  - TTS 첫 청크 약 0.1~0.2초
  - 합계 약 0.8~1.5초다. gemini-3.8-live의 TTFA 1.18초(feasibility §3.8)와 비슷한 수준이다.
  - 대신 대화 품질은 4B 모델 수준으로 떨어진다.
- [추정] Qwen3-ASR은 4비트로 줄이지 말고 8비트 이상으로 쓴다. 한국어 WER이 6.89에서 19.95로 무너진다.
- [추정] 음성 정체성
  - Supertonic은 프리셋 음성만 있어 Thorkell 고유 목소리를 만들 수 없다.
  - 목소리 설계가 필요하면 Qwen3-TTS VoiceDesign/CustomVoice가 맞다. 대신 GPU와 메모리를 더 쓴다.

### Gaps
- M4 Pro에서 Qwen3-TTS 0.6B/1.7B(mlx-audio)와 Supertonic 3의 한국어 첫 청크 지연·RTF 1차 측정을 찾지 못했다.
- Qwen3-ASR 0.6B의 한국어 CER과 Mac MLX 스트리밍 지연 원문을 확인하지 못했다(검색 요약만 있음).
- Apple SpeechAnalyzer(macOS 26)의 한국어 정확도 수치를 이번에 다시 확인하지 못했다.
- Gemma 4 E4B 오디오 입력의 한국어 인식 정확도를 공개한 자료를 찾지 못했다.

---

## Q5. 결정 전용 모델: Jev·laya 현황과 대안(인코더 분류기, 임베딩+kNN, 소형 LLM 로짓 점수)

### Takeaway
Jev(클라우드, 2026-09-15)와 laya(Apache-2.0, 322~421M 인코더)는 "상태 + 타입 질문 → 확률 붙은 선택" 하나의 forward pass라서 생성 LLM보다 한 자릿수 이상 빠르다. 다만 laya는 zero-shot 정확도가 낮아(0.362) 도메인 데이터로 파인튜닝해야 한다. 선택지가 20개 이하이고 라벨 데이터가 있으면 파인튜닝한 인코더가 zero-shot LLM보다 정확하면서 10~100배 싸고 빠르다는 연구가 일관된다. 라벨이 없는 새 상황, 선택지가 많은 경우, 계산이 필요한 경우는 LLM(또는 코드)이 맡아야 한다.

### Cited Findings
- Jev (TypeSafe AI) [3자 보도, 벤더 주장 포함] — [letsdatascience](https://letsdatascience.com/news/typesafe-ai-launches-jev-decision-model-889a38c0); [NYU Shanghai RITS](https://rits.shanghai.nyu.edu/ai/typesafe-jev-system-one-model); [YourStory](https://yourstory.com/ai-story/what-is-jev-typesafe-ai-decision-model)
  - 2026-09-15에 DCVC 주도 시드 4,000만 달러와 함께 공개됐다.
  - 상태를 타입 질문으로 평가해 제한된 선택, 순서 점수, 예/아니오 확률을 신뢰도와 함께 병렬로 낸다.
  - RLCD(보정된 결정을 위한 강화학습)로 학습했다.
  - 70~500ms, 입력 10억 토큰당 42달러, 출력은 무료다.
- 이 레포의 실측(2026-10-02, `thorkell contract jev`): `jev-1.13.0`, `threat_response` 10회, p50 188ms / p95 292ms, 오류 0 [로컬] (`docs/research/2026-10-02-api-costs-and-keys.md` §7)
- laya (Convai Innovations) [공식, 벤더 측정] — [HF convaiinnovations/laya](https://huggingface.co/convaiinnovations/laya)
  - 영어 체크포인트: 421M(ModernBERT-large 395M + 결정 헤드)
  - 다국어 체크포인트: mmBERT-base 322M
  - 결정 헤드는 처음부터 학습한 transformer 2층, 선택지 마커 점수기, act/escalate 헤드다.
  - 지연: T4 GPU에서 영어 39.5ms, 다국어 32.8ms. CPU에서 193~464ms. Apple GPU에서 4,000토큰 입력은 약 1.7초다.
  - typed-decisions 정확도는 laya 0.766, Jev 0.727이고 laya가 7.8배 빠르다.
  - 77개 라벨 과제에서는 Jev 0.870, laya 0.425로 크게 진다.
  - 선택지가 20개를 넘으면 설정을 바꾸지 않는 한 어렵다.
  - temperature 보정 후 ECE는 0.081이다.
  - `pip install laya`, `laya[serve]`
- laya 보도 [3자]: Apache-2.0, 100개 이상 언어, 단일 질문 중앙값 32.8ms, Jev 공개치 236~276ms보다 6~8배 빠르다 — [alphasignal](https://alphasignal.ai/news/convai-innovations-laya-beats-closed-decision-models-at-32-8-ms); [gradually.ai](https://www.gradually.ai/ki-modelle/laya/)
- 레포 feasibility §3.4 정리 [공식/커뮤니티]
  - laya zero-shot 정확도 0.362
  - M3 Max MLX에서 7.4~13.4ms [커뮤니티]
  - `laya-serve`가 Jev wire protocol(`POST /v1/systemone`)을 구현해서, 교체는 base URL 변경으로 끝난다.
  - Jevstiller(Jev 응답 증류 프록시 캐시): CPU 중앙값 16ms, Jev와 일치율 99.45% [커뮤니티]
  - OpenJev 0.8B를 쓰는 `open-valheim-bot`이 있다 [커뮤니티]
- 인코더 대 LLM [논문]
  - 파인튜닝한 BERT 계열 인코더는 IMDB, SST-2, AG News, DBPedia에서 zero/few-shot LLM과 같거나 더 좋은 macro F1을 냈다. 비용과 지연은 1~2자릿수 낮았다 — [arXiv 2602.06370](https://arxiv.org/html/2602.06370)
  - 파인튜닝한 RoBERTa, DeBERTa-v3, ELECTRA 등이 zero-shot GPT-3.5/4, Claude Opus를 텍스트 분류에서 일관되게 크게 앞섰다(적당한 양의 학습 데이터가 있을 때) — [arXiv 2406.08660](https://arxiv.org/abs/2406.08660)
  - 더 작은 모델을 파인튜닝하는 편이 큰 LLM의 few-shot보다 여전히 낫다 — [arXiv 2403.17661](https://arxiv.org/html/2403.17661v2)
- 소형 LLM 로짓 점수용 기능 [공식]
  - llama.cpp `n_probs`/`post_sampling_probs`/`top_logprobs`, `grammar`로 라벨 토큰 제한
  - mlx-lm 서버 `logprobs`(1~10)와 `logit_bias`
  - 출처: [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md); [mlx-lm SERVER.md](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/SERVER.md)
- 임베딩 후보: EmbeddingGemma(300M, 2025-09-04), EmbeddingGemma 2(740M, 2026-10-06) — [Gemma releases](https://ai.google.dev/gemma/docs/releases) [공식]

### Inferences
- [추정] 언제 결정 전용 모델(인코더)이 생성 LLM을 이기는가

  | 조건 | 결정 전용(laya, 파인튜닝 인코더) | 생성 LLM(4~9B) |
  |---|---|---|
  | 선택지 | 20개 이하 닫힌 집합 | 열린 집합, 77개처럼 많을 때, 새 선택지 |
  | 상태 크기 | 512~1,024토큰 이하로 직렬화한 상태 | 긴 맥락·대화 이력 |
  | 데이터 | Jev·플래너 로그로 라벨 수백~수천 개 | 라벨 없음(zero-shot) |
  | 지연 | 10~40ms(GPU), 0.2~0.5초(CPU) | 캐시가 있어도 0.3~0.8초 |
  | 보정된 확률 | 임계값 설계에 유리(ECE 0.081 주장) | logprob은 보정이 약함 |

- [추정] 이 프로젝트의 단계
  1. 지금처럼 Jev로 결정 로그를 쌓는다.
  2. laya-multilingual을 그 로그로 파인튜닝하고 temperature로 보정한다.
  3. `laya-serve`로 base URL만 바꾼다.
  - 게임 옆 GPU 경합을 피하려면 laya를 CPU에서 돌린다. 짧은 상태 기준 193~464ms로 600ms 마감에 들어간다. 또는 CoreML/ANE로 변환한다(미검증).
- [추정] 소형 LLM 로짓 점수(선택지마다 단일 라벨 토큰, 출력 1토큰)
  - 라벨 없이도 바로 쓸 수 있는 중간 단계다.
  - 프롬프트 캐시가 있으면 prefill 증분 + 1 forward로 약 0.2~0.4초(4B, M4 Pro)로 본다.
  - 다만 확률 보정과 한국어 상태 설명의 영향을 따로 재야 한다.
- [추정] 임베딩 + kNN
  - "이 상황은 예전의 어떤 상황과 비슷한가"(위협 유형 회상, 도감 매칭)처럼 선택지가 데이터에서 오는 문제에 맞다.
  - EmbeddingGemma 300M급은 수 ms~수십 ms다. 단 정보 동등성 규칙에 따라 prefab 이름이 아니라 화면 정보로 임베딩해야 한다.
- [추정] Jev와 laya 모두 산술과 개수 세기에 약하다(feasibility §3.4). 수량 판단은 코드(`craftgraph.feasible_max`)가 하고, 모델은 코드가 계산한 후보 중에서 고르게 한다.

### Gaps
- laya-multilingual의 한국어 정확도, Jev의 한국어 상태 처리 성능을 공개한 자료가 없다.
- laya를 Apple Silicon CPU(M4 Pro)에서 잰 1차 지연 수치는 없다. T4와 CPU 일반 수치만 있다.
- 게임 행동 선택 같은 도메인에서 인코더 분류기와 소형 LLM 로짓 점수를 직접 비교한 연구를 찾지 못했다. 위 논문들은 일반 텍스트 분류 벤치마크다.
