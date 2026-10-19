# Thorkell 역할별 클라우드 모델 선택지, 가격, 한도, 지연 (2026-10-10 기준)

조사일: 2026-10-11(KST). 모든 웹 페이지는 이 날 가져왔다. 페이지에 갱신일이 있으면 같이 적었다.
표기 규칙: **[공식]** 제공사 문서·가격표, **[제3자]** 블로그·집계 사이트·독립 측정, **[추정]** 이 노트에서 계산한 값.
가격은 모두 USD, 100만 토큰(1M) 단위. 계산 가정은 마지막 절에 적었다.

---

## 1. Gemini API (2026-10): 무료 등급 한도, Tier 1, 학습 사용 여부, Batch·캐싱 할인

### Takeaway
gemini-3.8-flash 무료 등급은 하루 20회(RPD)라서 플래너(시간당 30~120회)로는 10~40분 만에 바닥난다. 결제 계정을 연결하면(Tier 1) 2026년 말까지 프로모션가 $0.75/$3.75로 쓸 수 있고, 2027-01-01부터 두 배($1.50/$7.50)가 된다. 무료 등급 데이터는 제품 개선에 쓰이고 유료는 쓰이지 않는다.

### Cited Findings
- **[공식]** gemini-3.8-flash 유료(Standard) 가격: 입력 "$0.75 through December 31, 2026. $1.50 starting January 1, 2027", 출력 "$3.75 … / $7.50 starting January 1, 2027". 컨텍스트 캐싱 $0.075(2026)/$0.15(2027), 캐시 저장 $0.50/1M 토큰·시간(2026)/$1.00(2027). 페이지 갱신일 2026-10-09 — [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- **[공식]** gemini-3.8-flash Batch는 50% 할인: 입력 $0.375(2026)/$0.75(2027), 출력 $1.875/$3.75 — [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- **[공식]** gemini-3.8-flash Flex: 입력 $0.375/출력 $1.875(2026), $0.75/$3.75(2027). Priority: 입력 $1.35/출력 $6.75(2026), $2.70/$13.50(2027) — [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- **[공식]** "Used to improve our products": 무료 등급 Yes, 유료 등급 No — [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- **[공식]** Google Search grounding: 월 5,000건 무료(Gemini 3 이상 모델 공유), 이후 1,000건당 $14 — [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing). 무료 등급에서는 grounding을 쓸 수 없다는 제3자 설명도 있다 — [ofox.ai, 2026-09-03/09-14](https://ofox.ai/blog/gemini-3-8-flash-api-pricing-2026/)
- **[공식]** 무료 등급("Free of charge")이 있는 모델: Gemini 3.8 Flash, Gemini 3.8 Live, Gemini 3.5 Flash-Lite, Gemini 3.1 Flash-Lite, Gemini 2.5 Flash, 2.5 Flash-Lite, 2.5 Flash Native Audio, Gemma 4, Gemini 3.8 Flash TTS, Gemini 3.8 Flash-Lite TTS — [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- **[공식]** Flash-Lite 계열 유료가: Gemini 3.5 Flash-Lite 입력 $0.30/출력 $2.50(Batch·Flex $0.15/$1.25, Priority $0.54/$4.50). Gemini 3.1 Flash-Lite 입력 $0.25(텍스트·이미지·비디오)/$0.50(오디오), 출력 $1.50(Batch·Flex $0.125/$0.75, Priority $0.45/$2.70). 텍스트용 "3.8 Flash-Lite"는 가격표에 없고 TTS 모델만 있다 — [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- **[공식]** Gemini 3.1 Pro Preview: 입력 $2.00(≤200k)/$4.00, 출력 $12.00/$18.00 — [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- **[공식]** 등급 조건: Tier 1 = 활성 결제 계정 연결(결제 상한 $250), Tier 2 = $100 결제 + 첫 결제 후 3일(상한 $2,000), Tier 3 = $1,000 결제 + 30일(상한 $20,000~$100,000+). 10분 롤링 지출 한도: Tier 1 $10, Tier 2 $50, Tier 3 $200. 페이지 갱신일 2026-10-09 — [Gemini API Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- **[공식]** 레이트 리밋 문서는 모델별 RPM/TPM/RPD 표를 더 이상 싣지 않고 "View your active rate limits in AI Studio"로 안내한다 — [Gemini API Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- **[제3자·사용자 보고]** gemini-3.8-flash 무료 등급 20 RPD("very restrictive"), Flash-Lite는 500 RPD(어느 Flash-Lite인지 미기재). 2026-09-03 게시, Google 직원 답변 없음 — [Google AI Developers Forum](https://discuss.ai.google.dev/t/gemini-3-8-flash-free-tier-20-rpd-is-too-limited-for-practical-evaluation/180609). 사용자가 직접 받은 429 "limit: 20 requests per day"와 일치한다.
- **[제3자, 상충]** 일부 가이드는 3.8 Flash 무료 등급을 10~15 RPM, 1,500 RPD로 적는다. 공식 근거가 없고 위 포럼·사용자 429와 맞지 않는다 — [apidog](https://apidog.com/blog/how-to-use-gemini-3-8-flash-for-free/), [yingtu.ai](https://yingtu.ai/en/blog/google-gemini-api-free-tier-limits-2026)
- **[제3자]** Tier 1에서도 2.5 Flash-Lite가 5,000 RPD로 막힌다는 포럼 글(2026-03-18)이 있다 — [Google AI Developers Forum 관련 글 목록](https://discuss.ai.google.dev/t/gemini-3-8-flash-free-tier-20-rpd-is-too-limited-for-practical-evaluation/180609)
- **[제3자]** gemini-3.8-flash thinking 수준은 low/medium/high 세 단계이고 기본값은 medium이다. minimal은 지원하지 않는다 — [ofox.ai](https://ofox.ai/blog/gemini-3-8-flash-api-pricing-2026/)

### Inferences
- **[추정]** 무료 20 RPD로는 플래너를 하루 한 세션도 못 돌린다(시간당 30회면 40분, 120회면 10분). 결제 연결(Tier 1)이 사실상 필수이고, Thorkell 사용량은 Tier 1 지출 상한($10/10분, $250 결제 상한) 근처에도 가지 않는다(아래 비용표 참고: 시간당 $1 미만).
- thinking을 끌 수 없어(minimal 미지원) gemini-3.8-flash 플래너의 지연 하한은 "low" 수준이다. 사용자가 잰 2.2초가 이 하한 근처일 가능성이 높다.
- Flex는 Standard의 절반 가격이다. 다만 Flex의 지연·가용성 보장은 이번에 확인하지 못했으므로 실시간 플래너에 쓰기 전에 실측이 필요하다.
- 2027-01-01 가격 두 배 인상은 장기 비용 계획에서 반드시 반영해야 한다.

### Gaps
- 프로젝트별 RPM/TPM/RPD 실제 수치(무료·Tier 1)는 공식 문서에 없고 AI Studio 콘솔에서만 보인다. 3.8 Flash Tier 1 RPM/RPD, 3.5/3.1 Flash-Lite 무료 RPD 공식값을 찾지 못했다.
- Flex 등급의 지연 특성(대기열, 타임아웃) 공식 설명을 확인하지 못했다.
- 한국에서 무료 등급을 쓸 수 있는지(지역 제한) 이번에 확인하지 않았다. 사용자가 이미 무료 키로 429를 받은 것으로 보아 사용은 가능한 것으로 보인다.

---

## 2. 저지연 JSON 플래너 대안: OpenAI, Anthropic, xAI, Mistral, DeepSeek, Qwen, 고속 추론 제공사(Groq, Cerebras 등)

### Takeaway
값만 보면 Claude Haiku 5.5($0.10/$0.50, JSON 스키마 GA)와 gpt-5-nano($0.05/$0.40)가 gemini-3.8-flash보다 4~10배 싸고, 속도만 보면 Groq·Cerebras의 gpt-oss-120b(초당 500~3,000토큰, JSON Schema 모드)가 가장 빠르다. 하지만 이 모델들을 "thinking 낮게" 두었을 때 한국어 품질과 TTFT를 같은 조건으로 잰 공개 자료는 없다. 결정 전에 Thorkell 플래너 프롬프트로 직접 재야 한다.

### Cited Findings
**OpenAI**
- **[공식]** 소형 모델 가격(입력/캐시 입력/출력): gpt-5-nano $0.05/$0.005/$0.40, gpt-5-mini $0.25/$0.025/$2.00, gpt-5.4-nano $0.20/$0.02/$1.25, gpt-5.4-mini $0.75/$0.075/$4.50, gpt-5.6-luna $0.20/$0.02/$1.20(짧은 컨텍스트; 긴 컨텍스트 $0.40/$0.04/$1.80), gpt-5.6-terra $2/$0.20/$12, gpt-5.6-sol $4/$0.40/$20, gpt-5.5 $5/$0.50/$30. Batch·Flex는 50% 할인(예: gpt-5.6-luna $0.10/$0.01/$0.60) — [OpenAI API Pricing](https://developers.openai.com/api/docs/pricing)
- **[공식]** 사용 등급: Free(허용 지역 사용자, 월 $100 상한), Build($5 충전, 월 $500), Launch($100 충전, 월 $5,000), Grow($500 충전, 월 $200,000). Build 등급 Luna 5,000 RPM / 2M TPM, Astra·Sol·Terra 5,000 RPM / 1M TPM. Free 등급의 모델별 한도와 무상 토큰 여부는 문서에 없다 — [OpenAI Rate limits](https://developers.openai.com/api/docs/guides/rate-limits)
- **[공식]** Structured Outputs(strict JSON schema)는 gpt-4o-mini, gpt-4o-2024-08-06 "and later models"에서 지원하고, 새 프로젝트 권장 모델로 `gpt-6-astra`를 든다. 스키마 첫 요청에는 추가 지연이 있고 같은 스키마의 다음 요청부터는 없다 — [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)

**Anthropic**
- **[공식]** Claude Haiku 5.5(`claude-haiku-5-5`): 입력 $0.10/출력 $0.50(프롬프트 ≤100K), $0.50/$2.50(>100K). 캐시 읽기 $0.01, 캐시 쓰기 $0.125. Batch 50% 할인 — [Claude Pricing](https://claude.com/pricing), [Models overview](https://platform.claude.com/docs/en/about-claude/models/overview)
- **[공식]** Haiku 5.5는 현 라인업에서 "Fastest", 용도는 "high-volume, latency-sensitive tasks such as classification, extraction, and routing". Adaptive thinking, 기본 effort `medium`, 1M 컨텍스트, 출시 후 은퇴는 2027-10-07 이후 — [Models overview](https://platform.claude.com/docs/en/about-claude/models/overview)
- **[공식]** Structured outputs는 GA이고 `claude-haiku-5-5`를 지원한다. 파라미터는 `output_config.format`(type `json_schema`). 스키마별 첫 요청에 문법 컴파일 지연이 있고 컴파일 결과는 마지막 사용 후 24시간 캐시된다. 숫자 제약(`minimum`/`maximum`)과 문자열 길이 제약은 지원하지 않는다 — [Claude Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- **[공식]** 레이트 리밋(Start 등급): Haiku 5.5 1,000 RPM, 2M ITPM, 400K OTPM. 캐시 읽기 토큰은 ITPM에 세지 않는다. 신규 조직은 이보다 낮은 Evaluation 등급에서 시작할 수 있다. 무료 등급은 없다 — [Claude Rate limits](https://platform.claude.com/docs/en/api/rate-limits)

**xAI, Mistral, DeepSeek, Qwen**
- **[제3자]** Grok 4.1 Fast $0.20/$0.50, Grok 4.7(2026-09-21 출시) $2.00/$6.00 — [morphllm Grok API Pricing](https://www.morphllm.com/grok-api-pricing) 외 검색 요약. 공식 docs.x.ai는 확인하지 못했다.
- **[공식]** DeepSeek: `deepseek-flash` 입력(캐시 적중) $0.003~0.006, 입력(미적중) $0.15~0.30, 출력 $0.60~1.20. `deepseek-v4-pro` $0.66~1.32/$1.98~3.96. 피크(01:00~04:00, 06:00~10:00 UTC 평일)에는 두 배. JSON output·tool call 지원, 동시성 한도 Flash 2,500 — [DeepSeek Pricing](https://api-docs.deepseek.com/quick_start/pricing)
- **[제3자]** Qwen3.8-Flash(Alibaba Cloud Model Studio 국제 엔드포인트) $0.15~0.16/$0.47, qwen3.8-max $2/$6, 신규 모델마다 90일간 1M 무료 토큰 — [runtimewire](https://runtimewire.com/article/alibaba-qwen3-8-flash-api-qwencloud-pricing), [morphllm Qwen API](https://www.morphllm.com/qwen-api)

**고속 추론 제공사**
- **[공식]** Groq gpt-oss-120b: 입력 $0.15/캐시 $0.075/출력 $0.60, 약 500 tps, 131K 컨텍스트, JSON Object 모드·JSON Schema 모드·tool use·reasoning 지원, MMMLU(다국어) 평균 81.3% — [Groq GPT-OSS 120B](https://console.groq.com/docs/model/openai/gpt-oss-120b)
- **[공식]** Groq gpt-oss-20b 약 1,000 T/s, $0.075/$0.30. Llama 3.1 8B 560 T/s, Llama 3.3 70B 280 T/s. Qwen3.8-27B는 Preview — [Groq Models](https://console.groq.com/docs/models)
- **[공식, 탭 표기 모호]** Groq 레이트 리밋 표: gpt-oss-20b·gpt-oss-120b·qwen3.8-27b 모두 30 RPM, 1K RPD, 8K TPM, 200K TPD. 가져온 페이지가 "Developer plan"으로 표기했지만 수치는 무료 플랜 수준이라 어느 플랜인지 불분명하다 — [Groq Rate Limits](https://console.groq.com/docs/rate-limits)
- **[공식]** Cerebras: gpt-oss-120b 약 3,000 tok/s, qwen-3.8-27b 약 1,850 tok/s. 무료 체험 5 RPM, 30K TPM(비캐시), 1M TPD. 종량제(Developer) gpt-oss-120b 1,000 RPM, 1M TPM(비캐시); qwen-3.8-27b 300 RPM — [Cerebras Models](https://inference-docs.cerebras.ai/models/overview), [Cerebras Rate Limits](https://inference-docs.cerebras.ai/support/rate-limits)
- **[제3자]** Cerebras gpt-oss-120b 종량제 $0.35/$0.75(2026-08 기준, 이전 발표가 $0.25/$0.69) — [morphllm Cerebras Pricing](https://www.morphllm.com/cerebras-pricing), [cloudprice](https://cloudprice.net/models/cerebras/gpt-oss-120b). 공식 가격표는 JS 렌더링이라 가져오지 못했다.

**지연 측정(독립)**
- **[제3자, Artificial Analysis]** 리더보드(조사일 기준): Gemini 3.8 Flash(high) 125 tok/s, TTFT 27.18초 / Gemini 3.5 Flash-Lite 365 tok/s, 8.96초 / Claude Haiku 5.5(high) 174 tok/s, 22.65초 / DeepSeek V4.1 Flash(max) 217 tok/s, 1.16초 / Mistral Small 4 158 tok/s, 0.77초 / gpt-oss-120b(high) 184 tok/s, 0.89초 / gpt-oss-20b(high) 175 tok/s, 0.75초 — [Artificial Analysis Leaderboard](https://artificialanalysis.ai/leaderboards/models)
- **[제3자, Artificial Analysis]** Gemini 3.8 Flash(high) 단독 페이지: 127.9 tok/s, TTFT 23.70초, 지능 지수 41(227개 중 50위), 평가 중 출력 토큰 170M(중앙값 82M)으로 "very verbose" — [AA Gemini 3.8 Flash](https://artificialanalysis.ai/models/gemini-3-8-flash)
- **[제3자]** 2026-03 토론토 서버 스트리밍 측정(중간 길이 프롬프트): Claude Haiku 4.5 TTFT 약 597ms, Gemini 2.5 Flash 약 450ms, GPT-4.1 Mini 약 2,400ms. 표본이 작아 P99 보장에는 못 쓴다고 저자가 밝힘 — [kunalganglani.com](https://www.kunalganglani.com/blog/llm-api-latency-benchmarks-2026.md)

**한국어**
- **[제3자]** KMMLU(2026-07 스냅샷): Claude Sonnet 4.6 85%, GPT-5.4 83.65%, Solar Pro 2 80.1%, HyperCLOVA X 78.4%. KMMLU-Hard: GPT-5.4 72.8%, GPT-5 mini 60.6%, GPT-5 nano 51.7% — [benchlm Korean Benchmarks](https://benchlm.ai/leaderboards/korean-benchmarks), [benchlm KMMLU-Hard](https://benchlm.ai/benchmarks/kmmluHard)

### Inferences
- AA의 TTFT는 reasoning 높음/최대 설정이라 thinking 시간이 포함된다(Gemini 3.8 Flash high 23.7초, Haiku 5.5 high 22.65초). Thorkell처럼 thinking을 낮추거나 끄는 경우와는 다르다. 사용자의 gemini-3.8-flash low 실측 2.2초가 더 의미 있는 기준이다.
- 비용·속도·JSON 강제를 함께 보면 플래너 후보는 세 갈래다.
  1. **Claude Haiku 5.5**: 가장 싸고(플래너 호출당 약 $0.00055 [추정]) JSON 스키마 GA. 다만 effort를 낮춘 TTFT는 직접 재야 한다.
  2. **Groq gpt-oss-120b**: $0.15/$0.60, 500 tps, JSON Schema 모드. 무료 플랜 1K RPD로 하루 테스트 정도는 된다. 한국어 품질은 MMMLU 81.3% 외 근거가 약하다.
  3. **gpt-5.6-luna / gpt-5.4-nano**: $0.20 입력대, Structured Outputs. Build 등급($5 충전) 5,000 RPM.
- KMMLU는 지식 시험이라 "짧은 한국어 대사 이해 → 행동 JSON" 능력을 직접 재지 않는다. 현재 후보 모델(Haiku 5.5, 3.8 Flash, luna, gpt-oss)은 표에 없다.
- DeepSeek 피크 시간(01:00~04:00, 06:00~10:00 UTC)은 KST 10:00~13:00, 15:00~19:00 평일이다. 저녁 플레이 시간대는 대체로 할인 시간이다.

### Gaps
- gpt-6-astra(OpenAI 권장 모델)의 가격, Astra/Sol/Terra/Luna와 모델 ID 매핑을 확인하지 못했다.
- gpt-5.x nano/mini/luna, Haiku 5.5(effort low), gemini-3.8-flash(low)를 같은 조건으로 잰 TTFT 자료가 없다. 한국(서울)에서 잰 지연 자료도 없다.
- xAI·Mistral 공식 가격 페이지를 직접 확인하지 못했다(제3자·AA 값만 있음). SambaNova, Fireworks, Together는 이번에 조사하지 못했다.
- Cerebras·Groq 공식 가격표는 JS 렌더링 페이지라 직접 확인하지 못했다(Groq는 모델 페이지 가격만 공식 확인).
- Haiku 5.5·luna·gpt-oss의 한국어 대화 품질 공개 평가를 찾지 못했다.

---

## 3. OpenRouter: 무료 모델과 한도, 수수료, 라우팅 지연

### Takeaway
OpenRouter 무료(`:free`) 모델은 분당 20회, 하루 50회(누적 $10 이상 충전 시 1,000회)라 플래너 상시 운용에는 부족하다. 유료 모델은 제공사 가격을 그대로 받지만 충전 수수료 5.5%가 붙고, 직접 호출보다 지연이 40ms(공식)~200ms 이상(독립 측정) 늘어난다.

### Cited Findings
- **[공식]** 무료 모델 한도: 20 RPM, 누적 충전 $10 미만 50 RPD, $10 이상 1,000 RPD. 무료 모델 ID는 `:free`로 끝난다. 유료 모델에는 플랫폼 차원의 요청 상한이 없다 — [OpenRouter Limits](https://openrouter.ai/docs/api-reference/limits)
- **[공식]** 충전 수수료 Stripe 5.5%(최소 $0.80), 암호화폐 5%. BYOK는 월 $25,000 무료 사용분 초과 시 5%. 추론 가격은 마크업 없이 제공사 가격 그대로. 프롬프트·응답 기본 무로깅 — [OpenRouter FAQ](https://openrouter.ai/docs/faq)
- **[공식]** 일반적인 운영 조건에서 약 40ms 지연이 추가된다(Cloudflare Workers 엣지). 엣지 캐시가 차가울 때나 잔액이 적을 때는 지연이 늘어난다 — [OpenRouter Latency and Performance](https://openrouter.ai/docs/features/latency-and-performance)
- **[제3자]** 실측 추가 지연 80~250ms. 6개 게이트웨이 벤치마크에서 OpenRouter의 TTFT 오버헤드 중앙값은 GPT-4 246ms, Claude 207ms — [Enterprise DNA](https://enterprisedna.co/resources/blog/practitioner-openrouter-vs-direct), [edgee.ai](https://www.edgee.ai/blog/posts/i-benchmarked-six-ai-gateways-including-ours)

### Inferences
- **[추정]** 무료 1,000 RPD로는 플래너 시간당 120회 기준 8시간 남짓을 버틴다. 하지만 무료 모델 목록은 자주 바뀌고 지연이 더해지므로 실서비스 플래너용으로는 맞지 않는다. 여러 제공사 모델을 빠르게 비교하는 실험용으로는 쓸 만하다.
- Jev처럼 p50 188ms인 빠른 결정 경로에 OpenRouter를 끼우면 지연이 2배 가까이 될 수 있다. 빠른 결정은 직접 호출이 맞다.

### Gaps
- 2026-10 현재 `:free` 모델 목록과 그중 한국어·JSON 스키마를 잘 지원하는 모델은 확인하지 못했다.
- 서울 기준 OpenRouter 오버헤드 실측은 없다.

---

## 4. 실시간 음성 대안 (Gemini Live, OpenAI Realtime, ElevenLabs, Hume, Azure, 국내 음성 API)

### Takeaway
분당 단가는 Gemini 3.8 Live가 가장 싸다(오디오 입력 $0.005/분, 출력 $0.018/분, 무료 등급 있음). OpenAI gpt-realtime-2.1은 대략 분당 $0.04~0.10, mini는 그 1/3 수준이다(제3자 추정). ElevenLabs Agents는 플랫폼 요금만 $0.08/분이다. 한국어 음성 대 음성(speech-to-speech)을 tool call과 함께 제공하는 국내(Naver/Kakao) API는 찾지 못했다. CLOVA Voice는 TTS뿐이다.

### Cited Findings
**Gemini Live**
- **[공식]** Gemini 3.8 Live 유료: 입력 텍스트 $0.75, 오디오 $3.00(= $0.005/분); 출력 텍스트 $4.50, 오디오 $12.00(= $0.018/분). 무료 등급 "Free of charge". 이전 세대 Gemini 2.5 Flash Native Audio: 입력 오디오 $3.00, 출력 오디오 $12.00 — [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- **[공식]** 모델 ID `gemini-3.8-live`, 안정판(2026-09 갱신). 입력 131,072 / 출력 65,536 토큰. Function calling은 비동기가 기본(동기 blocking 선택 가능), interleaved thinking, Search grounding 지원. Structured outputs·캐싱·Batch는 미지원. Affective dialog 제거, proactive audio 상시 켜짐. 언어 옵션 24개(한국어 포함) — [Gemini 3.8 Live 모델 페이지](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live)
- **[공식, 상충]** 검색 요약은 같은 모델 페이지를 인용해 "97 languages detected and switched on the fly", GA 2026-09-15, 비동기(`NON_BLOCKING`) 기본이라고 했다. 직접 가져온 페이지에서는 24개 언어로 읽혔다 — [Gemini 3.8 Live 모델 페이지](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live)
- **[공식]** Live API 세션 한도: 오디오만 약 15분, 오디오+비디오 약 2분, 연결 약 10분 후 종료 예고, 세션 컨텍스트 128k. 컨텍스트 압축과 세션 재개로 연장한다. ko-KR 지원. 입력 16kHz 16bit PCM, 출력 24kHz. Gemini Developer API의 동시 세션 수는 사용 등급에 따른다(Agent Platform/Vertex는 Firebase 프로젝트당 1,000 동시 세션). 갱신일 2026-10-09 — [Firebase AI Logic Live API limits](https://firebase.google.com/docs/ai-logic/live-api/limits-and-specs)
- **[공식]** Live API 개요 페이지는 "70 supported languages", function calling·Google Search 통합을 적는다. 갱신일 2026-10-06 — [Gemini Live API](https://ai.google.dev/gemini-api/docs/live)

**OpenAI Realtime**
- **[공식]** gpt-realtime-2.1: 오디오 입력 $32 / 캐시 $0.40 / 출력 $64, 텍스트 $4/$0.40/$24. gpt-realtime-2.1-mini: 오디오 $10/$0.30/$20, 텍스트 $0.60/$0.06/$2.40. 이전 gpt-realtime·gpt-realtime-mini도 오디오 단가는 같다. 전사: gpt-live-transcribe·gpt-realtime-whisper $0.017/분, gpt-transcribe $0.0045/분, gpt-realtime-translate $0.034/분. gpt-4o-mini-tts 오디오 출력 $12/1M — [OpenAI API Pricing](https://developers.openai.com/api/docs/pricing)
- **[제3자]** gpt-realtime-2.1 실사용 분당 $0.04~0.10(VAD·캐싱 사용 시), mini는 약 1/3. 단일 분당 단가는 대화 양상과 캐싱에 따라 달라서 정할 수 없다. 2026-07-09 게시(한국어) — [aireiter](https://aireiter.com/ko/blog/openai-realtime-api-pricing)
- **[제3자]** gpt-realtime-mini는 시스템 프롬프트가 없으면 분당 약 $0.16, 1,000단어 시스템 프롬프트면 약 $0.33(컨텍스트 누적 재과금 영향) — [eesel.ai](https://www.eesel.ai/blog/gpt-realtime-mini-pricing)

**기타**
- **[제3자]** ElevenLabs Agents: 모든 플랜에서 통화 분당 $0.08, 텍스트 메시지당 $0.003, 동시성 초과 burst $0.16/분. LLM 비용은 별도(분당 $0.0005 GPT-5 Nano ~ $0.0446 GPT-5.5) — [happyrobot ElevenLabs Pricing](https://www.happyrobot.ai/hub/elevenlabs-pricing), [getmacha](https://www.getmacha.com/blog/elevenlabs-agents-pricing-explained)
- **[제3자]** Hume: 2026-06부터 EVI 4 mini $0.035~0.02/분, EVI 3 초과분 $0.07~0.04/분, 유료 플랜 월 $3~$500 — [costbench Hume](https://www.costbench.com/software/voice-apis/hume-ai/), [toolradar](https://toolradar.com/tools/hume-ai/pricing)
- **[공식]** Azure Voice Live는 선택한 LLM에 따라 요금 등급이 정해진다. 분당 단가는 가져온 페이지에서 표시되지 않았다 — [Azure Speech pricing](https://azure.microsoft.com/pricing/details/speech/)
- **[공식]** Naver CLOVA Voice는 RESTful TTS API(문서 2026-07 갱신)다. 실시간 대화·tool call API는 아니다 — [Ncloud CLOVA Voice 문서](https://api.ncloud-docs.com/docs/ai-naver-clovavoice.md)
- **[제3자]** 한국어 실시간 STT는 Soniox, Gladia, AssemblyAI가 제공한다(파이프라인 구성용) — [Soniox Korean](https://soniox.com/speech-to-text/use-cases/voice-agents/korean), [Gladia Korean](https://www.gladia.io/product/languages/korean), [AssemblyAI Korean](https://www.assemblyai.com/languages/korean)

### Inferences
- **[추정]** 오디오 단가 비교(분당, 출력 기준): Gemini 3.8 Live $0.018 대 OpenAI gpt-realtime-2.1 오디오 출력 $64/1M. 출력 오디오가 분당 약 1,200토큰이라고 가정하면 OpenAI는 분당 약 $0.077이라 Gemini가 4배 이상 싸다. 이 토큰 비율 가정은 이번에 공식 확인하지 못했다.
- Gemini 3.8 Live는 structured outputs를 지원하지 않는다. 그러니 음성 쪽 tool call 인자는 플래너·검증기를 거쳐야 하고, 기존 "검증기가 단위까지 확인" 규칙을 음성 경로에도 그대로 적용해야 한다.
- function calling 기본값이 비동기(NON_BLOCKING)다. 몸 동작 결과를 기다렸다가 말해야 하는 경우(예: "나무 10개 다 했어")에는 blocking으로 명시하거나 결과 주입 시점을 설계해야 한다.
- 세션 한도(오디오 15분, 연결 약 10분) 때문에 "세션 전체 음성"을 하려면 세션 재개와 컨텍스트 압축을 반드시 구현해야 한다.
- ElevenLabs·Hume은 Korean 대화 품질과 게임 tool call 통합을 확인하지 못했고, 분당 단가도 Gemini Live보다 높다. 국내 업체는 TTS·STT 부품만 있어서, 쓰려면 STT→LLM→TTS 파이프라인을 직접 조립해야 한다(지연 증가).

### Gaps
- Gemini Live가 턴마다 누적 컨텍스트를 다시 과금하는지(3.8 Live 기준) 확인하지 못했다. 분당 단가만으로 계산한 비용은 하한일 수 있다.
- Gemini 3.8 Live 무료 등급의 동시 세션 수·일일 한도, 2027년 가격 변동 여부를 확인하지 못했다.
- 한국어 음성 품질(자연스러움, 인식률)을 모델별로 비교한 공개 평가를 찾지 못했다. gpt-realtime-2.1의 공식 지연·한국어 주장은 OpenAI 발표 페이지가 403이라 확인하지 못했다.
- Kakao의 음성 대화 API는 찾지 못했다.

---

## 5. Jev (TypeSafe AI): 가격, 한도, 제공 경로, 비슷한 결정 모델 API

### Takeaway
Jev는 입력 $0.042/1M, 출력 무료이고 무료 등급은 없다. 2026-09-15 공개 출시했고 아직 early access(대기자 명단) 성격이 남아 있다. 공식 RPM은 공개되지 않았다. OpenRouter 제공 여부는 출처끼리 엇갈린다. 숫자만 돌려주는 같은 형태의 상용 결정 API는 찾지 못했다.

### Cited Findings
- **[제3자]** 입력 $0.042/1M, 출력은 텍스트를 생성하지 않으므로 무료. 질문 형식은 예/아니오(0~1 신뢰도), 객관식(확률 분포), 수치 점수 세 가지. 2026-09-15 공개 출시, DCVC 주도 $40M 시드, 창업자 Diogo Almeida(전 OpenAI) 외. Simon Willison은 감사 가능성 부족("black box" 회귀)을 지적. 게시 2026-09-23 — [AI Weekly](https://aiweekly.co/alerts/typesafe-ais-jev-outputs-numbers-not-text-at-0042m-input)
- **[제3자]** 요청 예산 약 32,000토큰(약 150,000자), 선택지 최대 255개, RPM 미공개, 무료 등급·체험 크레딧 없음. 상태는 early-access 대기자 명단과 브라우저 playground, 모델 ID `jev-latest`, 제공 경로 Cloudflare AI·Vercel·TypeSafe AI이며 OpenRouter나 공개 API는 아니라고 함. 내부 벤치마크 정확도 67.8%(비공개 비교 대상 74.1%), 독립 벤치마크 없음. 2026-09-22 갱신 — [Layer3 Labs Jev limits](https://www.layer3labs.io/guides/jev-limits)
- **[제3자, 상충]** cloudprice는 `openrouter/typesafe/jev-1.13` ID와 32K 컨텍스트를 적고 Jev를 "evaluation model … text output"으로 설명한다 — [cloudprice jev-1.13](https://cloudprice.net/models/typesafe-jev-1-13). 2026-10-11에 `https://openrouter.ai/typesafe/jev-1.13`은 404였다.
- **[제3자]** Jev 출시 후 며칠 만에 jevchat, jev-2048 등 커뮤니티 프로젝트와 오픈 웨이트 대안 "Kev"가 나왔다 — [AI Weekly](https://aiweekly.co/alerts/typesafe-ais-jev-outputs-numbers-not-text-at-0042m-input)
- **[공식, 비교 기준]** OpenAI gpt-5-nano $0.05/$0.40 — [OpenAI API Pricing](https://developers.openai.com/api/docs/pricing)

### Inferences
- **[추정]** Thorkell에서 잰 p50 188ms / p95 292ms는 공개된 어떤 범용 LLM TTFT(AA 최상위 약 0.4~0.8초)보다 빠르다. 위험 상황 반사 결정에서 Jev를 대체할 클라우드 범용 모델은 현재 없다.
- 대체가 필요하면 후보는 Groq gpt-oss-20b(1,000 T/s, $0.075/$0.30, JSON Schema 모드)나 Cerebras(약 3,000 tok/s)에 enum 스키마를 거는 방식이다. 다만 TTFT·네트워크 왕복을 합친 p95가 300ms 안에 들어오는지는 실측해야 하고, Groq 무료 1K RPD는 위험 상황에서 분당 수십 회 호출하면 금방 끝난다.
- 무료 등급이 없고 RPM이 공개되지 않았으므로, 위험 시 버스트(분당 수십 회)에서 429가 나는지 시나리오로 확인해야 한다.

### Gaps
- TypeSafe 공식 문서(typesafe.ai)의 가격·RPM·지연을 직접 확인하지 못했다. 검색 요약에 "1,200 RPM, 250,000 tokens/s", "공식 70~500ms, 독립 측정 중앙값 0.32초"라는 문구가 있었으나 원 페이지를 특정하지 못해 미검증으로 둔다.
- Jev의 한국어 입력 품질 자료는 없다(Thorkell은 정보 동등성 규칙상 결정 질문을 영어로 구성할 수도 있다).
- jev-1.13.0 버전별 차이와 OpenRouter 등재 여부는 확정하지 못했다.

---

## 6. Thorkell 사용 패턴의 시간당 비용 추정 (2~3개 구성)

### Takeaway
**[추정]** 현재 구성(gemini-3.8-flash 플래너 + Jev + Gemini 3.8 Live)을 유료 Tier 1으로 돌리면 2026년 프로모션가 기준 시간당 약 $0.33~1.09, 2027년 가격 기준 약 $0.46~1.58이다. 플래너를 Haiku 5.5나 Groq gpt-oss-120b로 바꾸면 시간당 약 $0.23~0.68로 내려간다. 비용의 대부분은 음성이 차지하고, 음성을 OpenAI Realtime으로 바꾸면 비용이 커진다.

### Cited Findings
가격 근거(위 절과 같음): [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing), [OpenAI API Pricing](https://developers.openai.com/api/docs/pricing), [Claude Pricing](https://claude.com/pricing), [Groq GPT-OSS 120B](https://console.groq.com/docs/model/openai/gpt-oss-120b), [DeepSeek Pricing](https://api-docs.deepseek.com/quick_start/pricing), [AI Weekly (Jev)](https://aiweekly.co/alerts/typesafe-ais-jev-outputs-numbers-not-text-at-0042m-input), [aireiter (Realtime 분당)](https://aireiter.com/ko/blog/openai-realtime-api-pricing), [happyrobot (ElevenLabs)](https://www.happyrobot.ai/hub/elevenlabs-pricing)

**계산 가정 [추정]**
- 플래너 1회: 입력 3,000토큰(시스템 + 세계 요약 + 스키마), 출력 500토큰(JSON 약 300 + low thinking 약 200). 시간당 30~120회. 캐싱 할인은 넣지 않음.
- 빠른 결정(Jev) 1회: 입력 1,500토큰, 출력 무료. 시간당 600~1,800회(분당 10~30회, 상한은 한 시간 내내 위험한 경우).
- 음성(Gemini 3.8 Live): 하한 = VAD로 사용자 발화 15분 입력 + 토르켈 발화 5분 출력, 상한 = 마이크 60분 상시 스트리밍 + 토르켈 발화 10분. 텍스트·tool call·컨텍스트 토큰은 제외했으므로 하한값이다.

**플래너 호출당·시간당 비용 [추정]**

| 플래너 모델 | 가격(입력/출력) | 호출당 | 30회/h | 120회/h |
|---|---|---|---|---|
| gemini-3.8-flash (2026) | $0.75 / $3.75 | $0.0041 | $0.12 | $0.50 |
| gemini-3.8-flash (2027~) | $1.50 / $7.50 | $0.0083 | $0.25 | $0.99 |
| gemini-3.8-flash Flex (2026) | $0.375 / $1.875 | $0.0021 | $0.06 | $0.25 |
| gemini-3.5-flash-lite | $0.30 / $2.50 | $0.0022 | $0.06 | $0.26 |
| gemini-3.1-flash-lite | $0.25 / $1.50 | $0.0015 | $0.05 | $0.18 |
| gpt-5.4-mini | $0.75 / $4.50 | $0.0045 | $0.14 | $0.54 |
| gpt-5.4-nano | $0.20 / $1.25 | $0.0012 | $0.04 | $0.15 |
| gpt-5.6-luna | $0.20 / $1.20 | $0.0012 | $0.04 | $0.14 |
| gpt-5-nano | $0.05 / $0.40 | $0.00035 | $0.01 | $0.04 |
| Claude Haiku 5.5 | $0.10 / $0.50 | $0.00055 | $0.02 | $0.07 |
| Groq gpt-oss-120b | $0.15 / $0.60 | $0.00075 | $0.02 | $0.09 |
| Cerebras gpt-oss-120b (제3자 가격) | $0.35 / $0.75 | $0.0014 | $0.04 | $0.17 |
| DeepSeek flash (할인/피크) | $0.15~0.30 / $0.60~1.20 | $0.00075~0.0015 | $0.02~0.05 | $0.09~0.18 |
| Qwen3.8-Flash (제3자 가격) | $0.16 / $0.47 | $0.0007 | $0.02 | $0.09 |

**빠른 결정·음성 시간당 비용 [추정]**
- Jev: 600회 × 1,500 = 0.9M토큰 → $0.04/h, 1,800회 → 2.7M토큰 → $0.11/h.
- (대안) gpt-5-nano를 같은 패턴으로 쓰면(출력 20토큰) 1,800회 기준 약 $0.15/h. Groq gpt-oss-20b(출력 50토큰)는 약 $0.23/h.
- Gemini 3.8 Live: 하한 15분 × $0.005 + 5분 × $0.018 = $0.17/h, 상한 60분 × $0.005 + 10분 × $0.018 = $0.48/h.
- OpenAI gpt-realtime-2.1: 대화 20분/h × 분당 $0.04~0.10 = $0.80~2.00/h. 2.1-mini(약 1/3)는 $0.27~0.67/h.
- ElevenLabs Agents: 20분 × $0.08 = $1.60/h + LLM 비용.

**구성별 합계 [추정, 시간당]**

| 구성 | 플래너 | 빠른 결정 | 음성 | 합계 |
|---|---|---|---|---|
| A. 현재 구성, Gemini 유료 Tier 1 (2026 가격) | gemini-3.8-flash $0.12~0.50 | Jev $0.04~0.11 | Gemini 3.8 Live $0.17~0.48 | **$0.33~1.09** |
| A'. 같은 구성, 2027 가격 | $0.25~0.99 | $0.04~0.11 | $0.17~0.48 (변동 미확인) | **$0.46~1.58** |
| B. 저가 플래너 | Haiku 5.5 $0.02~0.07 또는 Groq gpt-oss-120b $0.02~0.09 | Jev $0.04~0.11 | Gemini 3.8 Live $0.17~0.48 | **$0.23~0.68** |
| C. OpenAI 음성 | gpt-5.6-luna $0.04~0.14 | Jev $0.04~0.11 | gpt-realtime-2.1-mini $0.27~0.67 | **$0.35~0.92** |
| C'. OpenAI 풀 음성 | gpt-5.6-luna $0.04~0.14 | Jev $0.04~0.11 | gpt-realtime-2.1 $0.80~2.00 | **$0.88~2.25** |

### Inferences
- 어느 구성이든 시간당 $2를 넘기 어렵다. 비용보다 **무료 등급 한도(20 RPD)**와 **지연**이 실제 제약이다.
- 가장 적은 변경으로 문제를 푸는 길은 Gemini 키에 결제를 연결하는 것이다(Tier 1, 모델·코드 그대로, 시간당 $0.5 안팎). 덤으로 데이터가 학습에 쓰이지 않게 된다.
- 플래너 비용을 더 줄이거나 2027년 가격 인상에 대비하려면, Thorkell의 플래너 프롬프트·스키마로 Haiku 5.5(effort low), gpt-5.6-luna, Groq gpt-oss-120b, gemini-3.1-flash-lite를 A/B로 재야 한다. 기준은 한국어 대사 해석 정확도, 검증기 통과율, p50/p95 지연이다. 이 결정은 공개 벤치마크만으로는 내릴 수 없다.
- 음성은 Gemini 3.8 Live가 가장 싸므로 유지하는 것이 합리적이다. 비용 계산에 컨텍스트 재과금이 빠져 있으니, 실제 청구액은 첫 한 시간 플레이 후 콘솔 사용량으로 보정해야 한다.

### Gaps
- 플래너 입력·출력 토큰 수는 가정값이다. 실제 Thorkell 프롬프트 크기를 로그에서 재면 표를 바로 보정할 수 있다.
- 음성 비용의 컨텍스트 재과금, tool call 텍스트 토큰, 2027년 Live 가격 변동을 반영하지 못했다.
- 원화 환산, 한국 부가세(해외 디지털 서비스 VAT 10%) 적용 여부는 조사하지 않았다.
