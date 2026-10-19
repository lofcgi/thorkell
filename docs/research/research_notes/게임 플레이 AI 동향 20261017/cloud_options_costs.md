# Thorkell 역할별 클라우드 모델: 가격, 한도, 지연 갱신 (2026-10-17 기준)

- 기준 문서: `../게임 플레이 AI 기술 동향 2026/cloud_options_costs.md`(2026-10-10 기준, 2026-10-11 조사)
- 조사일: 2026-10-17. 아래 웹 페이지는 모두 이날 가져왔고, 페이지에 갱신일이 있으면 같이 적었다.
- 출처 표기
  - **[공식]**: 제공사 문서·가격표
  - **[제3자]**: 블로그·집계 사이트·독립 측정
  - **[커뮤니티]**: 포럼 글
  - **[추정]**: 이 노트에서 계산한 값
- 변경 표기
  - **[unchanged]**: 기준 문서와 같음
  - **[changed]**: 값이 바뀜
  - **[new]**: 기준 이후 새로 생겼거나 기준 문서가 놓친 것
  - **[corrected]**: 기준 문서의 판단을 바로잡음
- 가격 단위: 따로 적지 않으면 USD / 100만 토큰(1M).

**이번 라운드의 큰 변화 (요약)**

1. **[new] Gemini Live 누적 컨텍스트 재과금.** 포럼 답변 근거로, 턴마다 세션 컨텍스트 전체가 다시 과금된다. 3.8 Live는 캐싱도 안 된다. 기준 문서처럼 분당 단가만으로 계산하면 음성 비용을 5~15배 낮게 잡는다. 대화가 많으면 음성만으로 $2/h 상한에 닿는다(7절).
2. **[corrected] Gemini Flex는 실시간 플래너에 못 쓴다.** 목표 지연이 1~15분이고, 부하가 걸리면 먼저 밀려난다(sheddable).
3. **[new] 새 모델·API**
   - OpenAI `gpt-6-luna`(2026-09-22): $0.10/$0.50. reasoning `none`이 가능하고 AA TTFT는 0.94초다.
   - OpenAI `gpt-live-1`(API 2026-09-10): $0.05/분.
   - Gemini 4 Argon(2026-10-13 GA): 유료 전용.
4. **[new] 결정 API 경쟁자 셋.** OpenAI Decisions API(2026-10-06 베타), Cloudflare Clef/Clef-flash(2026-10-01, Jev 호환 API), Microsoft Decision-1($0.042, Foundry). Jev는 1.14.0(약 2026-10-14)이 나왔다.
5. **[new] Gemini 결제 세부.** 선불(Prepay)은 최소 $5이고, 잔액이 0이 되면 HTTP 402로 멈춘다. AI Studio에 프로젝트 지출 상한(실험 기능)이 있다.
6. **[changed] AA 측정이 추론 수준별로 나뉘었다.** Haiku 5.5 low의 TTFT는 6.85초다. 기준 문서가 "가장 싼 플래너"로 꼽은 Haiku 5.5는 thinking을 켜 두면 빠르지 않다.

---

## 1. Gemini API: gemini-3.8-flash·flash-lite 가격, 무료/Tier 1 한도, 결제 켜기, 지출 상한, 최근 변경

### Takeaway
gemini-3.8-flash 가격과 등급 구조는 기준과 같다.
- 2026년 말까지 $0.75/$3.75, 2027-01-01부터 $1.50/$7.50이다.
- Tier 1은 결제 계정을 연결하면 된다. 결제 상한은 월 $250, 10분 롤링 지출 한도는 $10이다.

새로 확인한 것은 결제를 켜는 절차(선불 최소 $5)와 지출을 막는 장치 세 가지다.
1. 선불 잔액이 0이 되면 402로 멈춘다.
2. 등급 월 상한에 닿으면 다음 달 1일까지 멈춘다.
3. 프로젝트 지출 상한(실험 기능)이 있다. 다만 약 10분 과금 지연 동안 초과될 수 있다.

무료 등급 모델별 RPM/RPD 공식 수치는 여전히 문서에 없고 AI Studio에서만 보인다.

### Cited Findings
**가격 (페이지 갱신 2026-10-16)**
- **[unchanged][공식] gemini-3.8-flash 유료 Standard**
  - 입력 $0.75 → $1.50(2027-01-01부터), 출력 $3.75 → $7.50
  - 캐싱 $0.075 → $0.15, 캐시 저장 $0.50 → $1.00/1M·h
  - Batch·Flex 입력 $0.375, 출력 $1.875
  - Priority 입력 $1.35, 출력 $6.75
  - 무료 등급: 입력·출력·캐싱 무료, Search grounding 불가
  - "Used to improve our products": 무료 Yes, 유료 No
  - 출처: [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing) (접속 2026-10-17)
- **[unchanged][공식] Flash-Lite 계열**
  - Gemini 3.5 Flash-Lite: $0.30/$2.50. 캐싱 $0.03 + 저장 $1.00/1M·h. Batch·Flex $0.15/$1.25. Priority $0.54/$4.50.
  - Gemini 3.1 Flash-Lite: 입력 $0.25(오디오 $0.50), 출력 $1.50. Batch·Flex $0.125/$0.75. Priority $0.45/$2.70.
  - 둘 다 무료 등급이 있다.
  - 텍스트용 "3.8 Flash-Lite"는 여전히 없다. `gemini-3.8-flash-lite-tts`(TTS)만 있다.
  - 출처: [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing) (접속 2026-10-17)
- **[new][공식] Gemini 3.6 Flash.** 가격표에 "previous generation Flash"로 올라 있고, 3.8 Flash와 같은 가격이다($0.75/$3.75 → 2027 $1.50/$7.50) — [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing) (접속 2026-10-17)
- **[new][공식] Gemini 4 Argon (`gemini-4-argon`)**
  - 2026-10-13 GA. 용도는 "complex coding, agentic, math, and science"다.
  - 무료 등급 없음.
  - 입력 $2.00(2026-11-30까지) → $4.00(2026-12-01부터). 출력(thinking 포함) $10.00 → $20.00.
  - 캐싱은 암묵적 캐싱만 된다($0.10 → $0.20).
  - 출처: [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing), [Gemini API Changelog](https://ai.google.dev/gemini-api/docs/changelog) (접속 2026-10-17)

**변경 이력 (2026-09-01~10-17, 페이지 갱신 2026-10-14)**
- **[new][공식]** 2026-10-08: `gemini-3.7-flash` 폐기, 요청이 3.8 Flash로 자동 전환된다. `gemini-3.5-flash` 폐기, 3.6 Flash로 전환된다.
- **[new][공식]** 2026-09-18: 2.5 계열 모델 접근을 "이전에 쓴 사용자"로 제한했다. 폐기는 아니다. 기준 문서의 무료 모델 목록에 있던 2.5 Flash 계열은 새 프로젝트에서 못 쓸 수 있다.
- **[new][공식]** 2026-09-22: Gemini 3.8 Flash TTS·3.8 Flash-Lite TTS GA. Voices 엔드포인트와 Voice design/replication이 나왔다.
- 2026-09-01~10-17 사이 가격·레이트 리밋 변경 항목은 없다.
- 출처: [Gemini API Changelog](https://ai.google.dev/gemini-api/docs/changelog) (접속 2026-10-17)

**레이트 리밋 (페이지 갱신 2026-10-15)**
- **[unchanged][공식] 등급 조건과 결제 상한**
  - Tier 1: 활성 결제 계정 연결, 상한 $250
  - Tier 2: 누적 $100 + 첫 결제 후 3일, 상한 $2,000
  - Tier 3: 누적 $1,000 + 30일, 상한 $20,000~$100,000+
- **[unchanged][공식] 10분 롤링 지출 한도.** Tier 1 $10, Tier 2 $50, Tier 3 $200. 넘으면 `429 RESOURCE_EXHAUSTED`.
- **[unchanged][공식]** 모델별 RPM/TPM/RPD 표는 문서에 없고 AI Studio(`aistudio.google.com/rate-limit`)에서만 보인다.
- **[new][공식] 한도 적용 방식**
  - 한도는 API 키가 아니라 **프로젝트 단위**다.
  - RPD는 **태평양 시간 자정**에 초기화된다.
  - 무료 → Tier 1 승급은 "almost immediately", 이후 승급은 약 10분 안에 반영된다.
  - Priority 추론은 등급별 표준 한도의 0.3배가 기본이다.
  - "Specified rate limits are not guaranteed"라고 적혀 있다.
- 출처: [Gemini API Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits) (접속 2026-10-17)
- **[new][공식] Batch 대기열 토큰 한도.** gemini-3.8-flash Tier 1은 3,000,000이다. 3.5/3.1 Flash-Lite Tier 1은 10,000,000이다 — [Gemini API Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits) (접속 2026-10-17)
- **[unchanged][커뮤니티] 무료 20 RPD.** gemini-3.8-flash 무료 등급 20 RPD는 여전히 포럼 글(2026-09-03)과 사용자 429 메시지 말고는 근거가 없다. 15 RPM/1,500 RPD라는 제3자 값은 공식 근거 없이 계속 돌고 있다 — [Google AI Developers Forum](https://discuss.ai.google.dev/t/gemini-3-8-flash-free-tier-20-rpd-is-too-limited-for-practical-evaluation/180609), [usagebox (2026-10, 검색 요약)](https://usagebox.com/articles/gemini-3-8-flash-pricing-free-tier-2026), [freellm.net (검색 요약)](https://freellm.net/models/google-gemini/gemini-3-8-flash) (접속 2026-10-17)

**결제 켜기와 지출 상한 (페이지 갱신 2026-09-28)**
- **[new][공식] 결제 켜는 절차**
  1. AI Studio의 API keys 또는 Projects 화면에서 Billing Tier 열의 **Set up billing**을 누른다.
  2. Cloud Billing 계정을 고르거나 새로 만든다.
  3. 선불(Prepay, 최소 $5, 1회 최대 $5,000)과 후불(Postpay) 중 하나를 고른다. 선불에서 후불로는 못 바꾼다. 후불에서 선불로는 바꿀 수 있다.
  - 출처: [Gemini API Billing](https://ai.google.dev/gemini-api/docs/billing) (접속 2026-10-17)
- **[new][공식] 멈추는 방식**
  - **선불 잔액 $0**: 연결된 모든 프로젝트 키가 HTTP 402로 실패한다.
  - **등급 월 상한 도달**: 연결된 모든 프로젝트가 다음 달 1일까지 멈춘다.
  - **프로젝트 지출 상한(experimental)**: AI Studio Spend 페이지에서 편집자·소유자가 설정한다. 약 10분 과금 지연 동안 초과될 수 있다고 경고한다. 하드 스톱인지 알림인지는 명확하지 않다.
  - **자동 충전 월 한도**: 자동 충전만 끄고 서비스는 막지 않는다.
  - 출처: [Gemini API Billing](https://ai.google.dev/gemini-api/docs/billing) (접속 2026-10-17)
- **[new][공식] 크레딧·환불 조건**
  - 선불 크레딧은 12개월 뒤 만료되고, 원칙적으로 환불되지 않는다.
  - 2026-03-02 이후 만든 계정은 Google Cloud Welcome 크레딧을 Gemini API에 쓸 수 없다.
  - 2026-03부터 $300 무료 체험에서 Gemini API 비용은 빠진다.
  - 출처: [Gemini API Billing](https://ai.google.dev/gemini-api/docs/billing) (접속 2026-10-17)

**Flex 지연 (기준 문서의 Gap)**
- **[corrected][공식, 검색 요약] Flex 특성**
  - Flex는 Standard의 절반 가격이다. 대신 "variable latency and best-effort availability"이고, 비교표 목표 지연은 **1~15분**이다.
  - 부하가 걸리면 밀려날 수 있다(sheddable).
  - 켜는 법: `service_tier: "flex"`. 응답 헤더 `x-gemini-service-tier`로 어느 등급이 처리했는지 확인한다.
  - 출처: [Flex inference 문서](https://ai.google.dev/gemini-api/docs/flex-inference), [Google 블로그: Flex and Priority inference](https://blog.google/innovation-and-ai/technology/developers-tools/introducing-flex-and-priority-inference/) (검색 결과 요약, 2026-10-17. 문서 원문 `/docs/flex`는 404였다)

### Inferences
- **[추정]** 결제를 연결하면 Tier 1으로 바로 올라간다. 무료 20 RPD 문제는 모델·코드를 바꾸지 않고 풀린다. 이 길이 여전히 가장 적은 변경이다.
- **[추정]** 선불 $5~10을 충전하고 자동 충전을 꺼 두면, 잔액 0에서 402로 멈추므로 사실상 하드 상한이 된다.
  - 프로젝트 지출 상한(실험)은 10분 지연이 있어 보조 수단으로만 믿는다.
  - Thorkell 자체의 $2/h 상한 가드는 계속 필요하다.
  - 402와 429(10분 $10 한도)를 구분해 말로 알리는 처리가 `ModelError` 경로에 있어야 한다.
- **[추정]** 무료 RPD는 태평양 자정에 초기화된다. 지금(PDT)은 KST 16:00이고, 2026-11-01 PST 전환 뒤에는 KST 17:00이다.
- **[corrected]** 기준 문서는 플래너 비용을 줄이는 길로 "Flex(절반 가격)"를 들었지만, 목표 지연 1~15분이라 실시간 플래너에는 못 쓴다. 회고·학습 같은 비실시간 작업에만 맞다.
- Gemini 4 Argon은 플래너 용도로 비싸고(3.8 Flash의 2.7배, 12월부터 5.3배) 무료 등급도 없다. Thorkell에는 해당 없음.

### Gaps
- gemini-3.8-flash의 무료·Tier 1 RPM/TPM/RPD 공식 수치는 여전히 공개 문서에 없다. AI Studio 화면 캡처로만 확인할 수 있다.
- 프로젝트 지출 상한(실험)이 넘었을 때 하드 스톱인지 공식 문서로 확정하지 못했다.
- Flex 문서 원문을 직접 열지 못했다(URL 404). 검색 결과 요약으로만 확인했다.

---

## 2. Gemini Live API: gemini-3.8-live 가격, 세션 한도, 컨텍스트 압축, 오디오 토큰, 누적 재과금

### Takeaway
gemini-3.8-live 단가는 기준과 같다. 오디오 입력 $3.00(= $0.005/분), 출력 $12.00(= $0.018/분)이고 무료 등급이 있으며, 2027년 가격 변경 공지는 없다.

기준 문서가 Gap으로 둔 "누적 컨텍스트 재과금"은 포럼 답변 근거로 사실로 보인다.
- 턴마다 세션 컨텍스트 전체가 다시 과금된다.
- 3.8 Live는 명시적·암묵적 캐싱을 모두 지원하지 않는다.
- 슬라이딩 윈도 압축을 써도 system_instruction은 매 턴 과금된다.

오디오는 공식적으로 초당 25토큰이다.

### Cited Findings
- **[unchanged][공식] 가격 (페이지 갱신 2026-10-16)**
  - 적용 모델: Gemini 3.8 Live, 3.8 Live Extended Thinking, 3.1 Flash Live Preview
  - 입력: 텍스트 $0.75, 오디오 $3.00(= $0.005/분), 이미지·비디오 $1.00(= $0.002/분)
  - 출력: 텍스트 $4.50, 오디오 $12.00(= $0.018/분)
  - 무료 등급: 입력·출력 무료
  - Search grounding: 월 5,000건 무료, 이후 1,000건당 $14
  - 캐싱·Batch·Flex·Priority는 없고, 날짜별 가격 변경도 적혀 있지 않다
  - 출처: [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing) (접속 2026-10-17)
- **[new][공식] 오디오 토큰 비율.** "Audio tokens correspond to 25 tokens per second of audio". TTS·Transcribe·Live Translate 각주에 있다. 3.8 Live 분당 단가($3.00 × 1,500토큰/분 ≈ $0.0045 ≈ $0.005)와도 맞는다 — [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing) (접속 2026-10-17)
- **[unchanged][공식] 모델 사양 (페이지 갱신 2026-09-15)**
  - 모델 ID `gemini-3.8-live`, Stable. 입력 131,072, 출력 65,536 토큰.
  - Function calling은 `NON_BLOCKING`이 기본이고 `BLOCKING`을 선택할 수 있다.
  - thinking은 지원하지만 `thinking_level`은 지원하지 않는다(넣지 말 것).
  - Structured outputs·캐싱·Batch는 미지원이다.
  - 출처: [Gemini 3.8 Live 모델 페이지](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live) (접속 2026-10-17)
- **[new][공식] Extended Thinking 변형.** 2026-09-15에 `gemini-3.8-live`와 `gemini-3.8-live-extended-thinking`이 함께 GA됐다 — [Gemini API Changelog](https://ai.google.dev/gemini-api/docs/changelog) (접속 2026-10-17)
- **[unchanged][공식] 세션 한도 (페이지 갱신 2026-09-15)**
  - 압축 없이 오디오만 15분, 오디오+비디오 2분.
  - 연결 수명 약 10분. 종료 전에 `GoAway`(`timeLeft` 포함)가 온다.
  - 압축은 `contextWindowCompression`(슬라이딩 윈도, 트리거 토큰)으로 켠다. 문서에 기본값은 없다.
  - 출처: [Live API session management](https://ai.google.dev/gemini-api/docs/live-session) (접속 2026-10-17)
- **[new][공식] 세션 재개 토큰**은 마지막 세션이 끝난 뒤 2시간 동안 유효하다 — [Live API session management](https://ai.google.dev/gemini-api/docs/live-session) (접속 2026-10-17)
- **[unchanged][공식] Firebase 문서 (페이지 갱신 2026-10-13)**
  - 세션 컨텍스트 128k 토큰.
  - ko-KR 지원(모든 오디오 생성 모델).
  - 연결 종료 약 60초 전에 going-away 알림이 온다.
  - Developer API 동시 세션 수는 사용 등급에 따른다. Agent Platform(구 Vertex)은 Firebase 프로젝트당 1,000개다.
  - 출처: [Firebase AI Logic Live API limits](https://firebase.google.com/docs/ai-logic/live-api/limits-and-specs) (접속 2026-10-17)
- **[unchanged][공식]** Live API 개요는 "70 supported languages"라고 적는다(페이지 갱신 2026-10-06) — [Gemini Live API](https://ai.google.dev/gemini-api/docs/live) (접속 2026-10-17)

**누적 재과금 (기준 문서의 Gap)**
- **[new][커뮤니티, 답변자 소속 미표시] 3.8 Live 캐싱 미지원 답변 (2026-10-08)**
  - "Neither explicit nor implicit context caching is supported for `gemini-3.8-live`."
  - 활성 세션 컨텍스트(system instruction, tool 선언 포함)는 표준 텍스트 입력 요금으로 과금된다.
  - 슬라이딩 윈도는 오래된 턴을 지운다. 하지만 "system_instruction is always preserved … and remains billed on each turn."
  - 대량 사용자에게는 Enterprise 플랜(볼륨 할인)을 안내했다.
  - 출처: [Forum: Context caching or cached-input pricing for the Gemini Live API](https://discuss.ai.google.dev/t/title-context-caching-or-cached-input-pricing-for-the-gemini-live-api-native-audio/186850) (2026-10-05 질문, 10-08 답변; 접속 2026-10-17)
- **[new][커뮤니티] 누적 promptTokenCount 대조 (2026-07-02 질문, 07-07 답변)**
  - 질문자는 턴마다 커지는 누적 `promptTokenCount`를 실제 청구액과 대조했다.
    - 모든 턴의 스냅숏을 합하면 청구액과 약 3% 안에서 맞았다.
    - 마지막 스냅숏만 쓰면 약 8.6배 낮았다.
  - 답변: "Gemini Live re-bills the entire cumulative context on every single turn." 이전 턴의 원시 오디오 토큰을 그대로 들고 있기 때문이라고 설명했다.
  - 표본: 5.6분 20턴에서 최종 프롬프트 약 160k, 7.1분 29턴에서 약 261k.
  - 공식 문서 링크는 없다.
  - 출처: [Forum: Does Gemini Live native audio bill cumulative prompt tokens on every turn?](https://discuss.ai.google.dev/t/does-gemini-live-native-audio-bill-cumulative-prompt-tokens-on-every-turn-cost-seems-to-scale-with-turn-count-not-call-duration/173248) (접속 2026-10-17)
- **[new][제3자, Artificial Analysis] 벤치마크 비용**
  - Gemini 3.8 Live: Big Bench Audio 40문항 기준 "입력 오디오 1시간당 비용" $0.84, TTFA 1.18초.
  - Extended Thinking(High): $3.50/h, TTFA 1.35초.
  - 출처: [AA Speech-to-Speech](https://artificialanalysis.ai/speech-to-speech) (접속 2026-10-17)

### Inferences
- **[추정]** 누적 재과금이면 한 세션의 입력 토큰은 턴 수 n의 제곱에 비례한다(공식은 7절). 정가 분당 단가($0.005 입력)로 치면 입력 오디오 1시간이 $0.30이다. AA 벤치마크의 실효 비용 $0.84/h는 그보다 약 2.8배 높아서 재과금·thinking 영향과 방향이 맞는다.
- **[추정]** 비용을 좌우하는 손잡이는 네 가지다.
  1. 한 세션(또는 압축 윈도)에 쌓이는 턴 수
  2. 턴마다 Live에 넣는 텍스트(게임 상태 주입 x). 한 번 넣으면 이후 모든 턴에 다시 과금된다.
  3. system_instruction과 tool 선언 크기 S. 매 턴 과금된다.
  4. 세션에 들어가는 오디오가 말한 구간뿐인지, 무음까지인지
- **[추정]** 세션 재개(resumption)는 컨텍스트를 이어 가므로 비용을 줄이지 못한다. 줄이려면 두 가지 중 하나를 한다.
  - 일정 턴(예: 15분)마다 텍스트 요약 1개를 들고 **새 세션**을 연다.
  - 슬라이딩 윈도 트리거를 작게(예: 8k~16k) 잡는다.
- 이 규칙은 AGENTS.md의 "세션 재개와 컨텍스트 압축을 반드시 켠다"와 함께 비용 가드에도 반영해야 한다.

### Gaps
- 재과금은 공식 가격 문서나 Live 문서에 적혀 있지 않다. 포럼 답변 2건(한 건은 답변자 소속 미표시)과 사용자 대조 1건이 근거다.
- 누적된 오디오 컨텍스트가 오디오 요율($3.00)로 다시 과금되는지 텍스트 요율($0.75)로 과금되는지 확인하지 못했다. 이 노트의 계산은 오디오 요율로 잡았으므로 상한 쪽이다.
- 서버 VAD로 마이크를 계속 보낼 때 무음 구간이 입력 과금·컨텍스트에 남는지 확인하지 못했다.
- 3.8 Live의 thinking 토큰이 출력 텍스트 요율($4.50)로 과금되는지, 그 양이 얼마인지 확인하지 못했다.
- 포럼 표본의 턴당 증가량(약 8k 토큰/턴)은 이 노트의 가정(약 475토큰/턴)보다 훨씬 크다. 그 세션에 비디오나 큰 system prompt가 있었는지 알 수 없다.
- 무료 등급 Live의 동시 세션 수·일일 한도는 여전히 공개 자료가 없다.

---

## 3. 대안 플래너: Anthropic, OpenAI, Groq·Cerebras, Mistral, DeepSeek와 독립 지연 측정, JSON 스키마

### Takeaway
- **가격**: Claude Haiku 5.5와 새로 나온 OpenAI `gpt-6-luna`가 둘 다 $0.10/$0.50으로 가장 싸다. gemini-3.8-flash의 1/7.5다.
- **AA 독립 측정 지연**
  - gpt-6-luna(non-reasoning): TTFT 0.94초
  - gpt-oss-120b: 0.86~0.87초
  - Mistral Small 4: 0.82초
  - Haiku 5.5(low): 6.85초, thinking을 켠 상태라 빠르지 않다
  - Sonnet 5.5(low): 1.12초
- 사용자가 잰 gemini-3.8-flash(low) 2.2초를 이기려면 "thinking 끔 / none" 경로가 필요하다.

### Cited Findings
**Anthropic**
- **[unchanged][공식] Haiku 5.5 가격**
  - 프롬프트 ≤100K: 입력 $0.10, 5분 캐시 쓰기 $0.125, 1시간 캐시 쓰기 $0.20, 캐시 읽기 $0.01, 출력 $0.50
  - 프롬프트 >100K: $0.50/$0.625/$1/$0.05/$2.50
  - Batch: $0.05/$0.25
  - `inference_geo: "us"`는 1.1배
  - tool 사용 시스템 프롬프트 오버헤드: 286토큰(auto/none), 406토큰(any/tool)
  - 출처: [Claude API Pricing](https://platform.claude.com/docs/en/about-claude/pricing) (접속 2026-10-17)
- **[unchanged][공식] Sonnet 5.5**: $2/$10, 캐시 읽기 $0.10(기본 입력의 0.05배) — [Claude API Pricing](https://platform.claude.com/docs/en/about-claude/pricing) (접속 2026-10-17)
- **[unchanged][공식] 라인업 표**
  - Haiku 5.5: "Fastest", 기본 effort `medium`, thinking "Adaptive", 1M 컨텍스트, 은퇴 2027-10-07 이후.
  - Sonnet 5.5: "Fast", 기본 effort `high`, 은퇴 2027-09-28 이후.
  - Fable 5.1·Opus 5.5는 "Adaptive (always on)"이고, Haiku·Sonnet 5.5는 "always on" 표기가 없다.
  - Models API의 `capabilities.thinking.types.disabled`로 thinking 끄기 지원 여부를 확인할 수 있다.
  - 출처: [Claude Models overview](https://platform.claude.com/docs/en/about-claude/models/overview) (접속 2026-10-17)
- **[new][제3자, AA]** Haiku 5.5 출시일은 2026-10-07이다 — [AA Claude Haiku 5.5](https://artificialanalysis.ai/models/claude-haiku-5-5) (접속 2026-10-17)
- **[unchanged][공식] Start 등급 한도**
  - Haiku 5.5·Sonnet 5.5: 각 1,000 RPM, 2M ITPM, 400K OTPM. 캐시 읽기는 ITPM에 넣지 않는다.
  - 신규 조직은 더 낮은 Evaluation 등급에서 시작할 수 있다. 무료 등급은 없다.
  - 출처: [Claude Rate limits](https://platform.claude.com/docs/en/api/rate-limits) (접속 2026-10-17)
- **[new][공식] 지출 상한 동작**
  - 월 상한: Start $500, Build $1,000, Scale $200,000.
  - 등급 상한에 닿으면 다음 달 1일 00:00 UTC까지 HTTP 429. `error_code: enforced_spend_limit_reached`이고 `retry-after`는 없다.
  - 사용자가 직접 정한 한도에 닿으면 HTTP 400 `invalid_request_error`. 워크스페이스별 한도도 걸 수 있다.
  - 출처: [Claude Rate limits](https://platform.claude.com/docs/en/api/rate-limits) (접속 2026-10-17)
- **[unchanged]** Structured outputs(GA, `output_config.format`)는 이번에 다시 확인하지 않았다. 기준 문서의 [Claude Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)를 참고한다.

**OpenAI**
- **[new][공식] gpt-6-luna**
  - 가격: 입력 $0.10, 캐시 입력 $0.01, 캐시 쓰기 $0.125, 출력 $0.50
  - 272K 넘는 입력: 입력 2배, 출력 1.5배
  - Batch·Flex 50%, Fast 2배
  - 컨텍스트 1,050,000(입력 최대 922,000), 출력 최대 128,000
  - reasoning effort: `none`/`low`/`medium`(기본)/`high`/`xhigh`/`max`. minimal은 없다.
  - Structured outputs 지원
  - Function calling: Chat Completions에서는 `reasoning_effort: none`일 때만 되고, 그 밖에는 Responses API를 쓴다
  - Build 등급 5,000 RPM / 2M TPM, Free 등급 표기는 없다
  - 출처: [OpenAI gpt-6-luna 모델 페이지](https://developers.openai.com/api/docs/models/gpt-6-luna), [OpenAI API Pricing](https://developers.openai.com/api/docs/pricing) (접속 2026-10-17)
- **[new][제3자]** gpt-6-luna와 gpt-6-sol은 2026-09-22에 출시됐다. 기준 문서(10-10)가 놓쳤다 — [AA GPT-6 Luna](https://artificialanalysis.ai/models/gpt-6-luna), [vpsranking (검색 요약)](https://vpsranking.com/news/ai/ai-2026-09-22-openai-gpt-6-sol-luna/) (접속 2026-10-17)
- **[new][공식] 그 밖의 텍스트 모델 가격 (Standard)**
  - gpt-6-astra $10/$50(캐시 $1). 기준 문서의 Gap이 채워졌다.
  - gpt-6.1-sol $2/$10(캐시 $0.10)
  - gpt-6-sol $2/$10(캐시 $0.20)
  - 출처: [OpenAI API Pricing](https://developers.openai.com/api/docs/pricing) (접속 2026-10-17)
- **[unchanged][공식]** 기존 모델 가격은 그대로다.
  - gpt-5.6-luna $0.20/$0.02/$1.20, gpt-5.6-terra $2/$12, gpt-5.6-sol $4/$20(프로모션 최소 2026-11-21까지)
  - gpt-5.5 $5/$30, gpt-5.4-mini $0.75/$4.50, gpt-5.4-nano $0.20/$1.25
  - gpt-5-mini $0.25/$2.00, gpt-5-nano $0.05/$0.40
  - 출처: [OpenAI API Pricing](https://developers.openai.com/api/docs/pricing) (접속 2026-10-17)
- **[new][공식] 가격표 기타 변경**
  - "Priority processing was renamed Fast mode on July 30, 2026."
  - 2026-03-05 이후 출시 모델의 지역 처리(data residency)는 10% 할증이다.
  - 출처: [OpenAI API Pricing](https://developers.openai.com/api/docs/pricing) (접속 2026-10-17)
- **[unchanged][공식] 사용 등급**
  - Free(허용 지역, 월 $100), Build($5 충전, 월 $500), Launch($100, 월 $5,000), Grow($500, 월 $200,000)
  - Build 등급 Luna 5,000 RPM / 2M TPM
  - 출처: [OpenAI Rate limits](https://developers.openai.com/api/docs/guides/rate-limits) (접속 2026-10-17)
- **[new][공식] 오류 코드**: 트래픽 급증은 429 `slow_down`, 과부하는 503 `server_is_overloaded` — [OpenAI Rate limits](https://developers.openai.com/api/docs/guides/rate-limits) (접속 2026-10-17)

**고속 추론 제공사**
- **[unchanged][공식] Groq gpt-oss-120b**
  - $0.15/캐시 $0.075/$0.60, 약 500 tps
  - 131,072 컨텍스트, 출력 65,536
  - JSON Object·JSON Schema 모드(strict 여부는 명시 없음), tool use, reasoning(low/medium/high)
  - 출처: [Groq GPT-OSS 120B](https://console.groq.com/docs/model/openai/gpt-oss-120b) (접속 2026-10-17)
- **[unchanged/changed][공식] Groq 모델 표**
  - [unchanged] gpt-oss-20b: 1,000 T/s, $0.075/$0.30
  - [changed] Llama 3.1 8B·3.3 70B: 가격이 "Contact sales"로 바뀌었다
  - [new] Preview: qwen/qwen3.8-27b 450 T/s, $0.80/$4.00. minimax-m2.7과 muse-spark-open도 추가됐다
  - Whisper large-v3 $0.111/h, turbo $0.04/h
  - 출처: [Groq Models](https://console.groq.com/docs/models) (접속 2026-10-17)
- **[unchanged][공식] Groq 레이트 리밋 표**
  - gpt-oss-120b·20b·qwen3.8-27b 모두 30 RPM, 1K RPD, 8K TPM, 200K TPD.
  - 페이지는 이를 "Developer plan" 기본 한도라고 적지만, 무료 플랜 탭 수치는 추출되지 않아 여전히 모호하다.
  - 출처: [Groq Rate Limits](https://console.groq.com/docs/rate-limits) (접속 2026-10-17)
- **[unchanged][공식] Cerebras 모델**
  - gpt-oss-120b 약 3,000 tok/s, 컨텍스트 무료 65k / 유료 131k
  - qwen-3.8-27b 약 1,850 tok/s
  - 출처: [Cerebras Models](https://inference-docs.cerebras.ai/models/overview) (접속 2026-10-17)
- **[new][공식] Cerebras 체험 크레딧**
  - 결제수단을 등록하면 1회 $5 크레딧을 준다. 활성화 후 30일에 만료되고, 소진되거나 만료되면 API가 멈춘다.
  - 가격표 본문은 JS 렌더링이라 비어 있었다.
  - 출처: [Cerebras Pricing](https://www.cerebras.ai/pricing) (접속 2026-10-17)
- **[unchanged][제3자] Cerebras gpt-oss-120b 가격**: $0.35/$0.75(LiteLLM 기준, 2026-08-06 검증) — [Future AGI](https://futureagi.com/llm-cost-calculator/cerebras/gpt-oss-120b), [morphllm](https://www.morphllm.com/cerebras-pricing) (검색 요약, 접속 2026-10-17)

**DeepSeek, Mistral**
- **[unchanged][공식] DeepSeek**
  - `deepseek-flash`(= V4.1-Flash): 캐시 적중 $0.003/0.006, 미적중 $0.15/0.30, 출력 $0.60/1.20
  - `deepseek-v4-pro`: $0.66/1.32, 출력 $1.98/3.96
  - 값은 할인/피크 순이다. 피크는 평일 01~04, 06~10 UTC이고 중국 공휴일은 제외한다.
  - 컨텍스트 1M. JSON output·tool call 지원. 동시성 Flash 2,500.
  - [new] 옛 Flash 이름은 은퇴했다. Search/Fetch는 1,000건당 $0.75다.
  - 출처: [DeepSeek Pricing](https://api-docs.deepseek.com/quick_start/pricing) (접속 2026-10-17)
- **[new][공식] Mistral 가격·모델**
  - 가격 페이지에 예시로 "Mistral Large costs $0.5 /M tokens in and $1.5 /M tokens out"이 적혀 있다. Batch 50%, 캐시 입력 최대 90% 할인.
  - 현행 모델: Mistral Small 4(26.03), Medium 3.5(26.04), **Large 4(26.10, 신규)**
  - Small·Medium의 토큰 가격은 이번에도 공식 페이지에서 확인하지 못했다.
  - 출처: [Mistral Pricing](https://mistral.ai/pricing), [Mistral Models overview](https://docs.mistral.ai/getting-started/models/models_overview/) (접속 2026-10-17)

**독립 지연 측정 (AA 리더보드, 날짜 표기 없음, 접속 2026-10-17)**

**[changed][제3자, AA]** 추론 수준별 행이 새로 생겼다. 값은 출력 속도(tok/s), TTFT(초) 순이다.

| 모델 | 추론 수준별 (tok/s, TTFT) |
|---|---|
| Gemini 3.8 Flash | high 147, 23.07초. 기준 문서는 125, 27.18초. low·medium은 속도 측정 없음 |
| Gemini 3.5 Flash-Lite | 449, 6.90초. 기준 문서는 365, 8.96초 |
| Claude Haiku 5.5 | low 171, 6.85초 / medium 181, 11.45초 / high 188, 26.05초 / max 237, 336.91초 |
| Claude Sonnet 5.5 (with fallback) | low 109, 1.12초 / medium 112, 1.80초 |
| GPT-6 Luna | non-reasoning 113, 0.94초 / low 120, 2.14초 / high 119, 18.89초 |
| gpt-oss-120b | high 213, 0.86초 / low 235, 0.87초 |
| gpt-oss-20b | high 225, 0.70초 / low 296, 0.72초 |
| DeepSeek V4.1 Flash | max 176, 1.23초 / non-reasoning 165, 1.27초 |
| Mistral Small 4 | reasoning 169, 0.82초 / non-reasoning 153, 0.92초 |
| Mistral Medium 3.5 | 165, 2.33초 |

출처: [AA Leaderboard](https://artificialanalysis.ai/leaderboards/models)

- **[new][제3자, AA] 지능 지수**: Gemini 3.8 Flash low 33, Haiku 5.5 low 29, GPT-6 Luna low 22 / non-reasoning 18, gpt-oss-120b high 12 — [AA Leaderboard](https://artificialanalysis.ai/leaderboards/models) (접속 2026-10-17)

### Inferences
- **[추정] 비용**: Haiku 5.5와 gpt-6-luna는 플래너 호출당 $0.00055다(입력 3,000, 출력 500 가정). gemini-3.8-flash 2026 가격($0.0041)의 약 1/7.5, 2027 가격의 1/15이다.
- **[추정] 지연**
  - AA 기준으로는 gpt-6-luna(`none`) 0.94초, gpt-oss-120b(Groq/Cerebras) 0.9초 안팎, Sonnet 5.5(low) 1.1초가 사용자 실측 gemini-3.8-flash(low) 2.2초보다 빠를 가능성이 있다.
  - Haiku 5.5는 adaptive thinking을 켜 둔 low에서도 6.85초다. thinking을 끄는 설정(`thinking: {type: "disabled"}`)을 지원하는지 Models API로 먼저 확인해야 한다. 라인업 표에 "always on" 표기가 없어서 끌 수 있을 가능성이 높다.
- **[추정] 품질**: 지능 지수로 보면 thinking을 끈 저가 모델(Luna non-reasoning 18, gpt-oss 10~12)은 Gemini 3.8 Flash low(33)보다 크게 낮다. "처음 보는 말과 수량 판단"을 맡는 Thorkell 플래너에서 품질이 떨어질 위험이 있다.
- **[추정] 다음 실험**: Thorkell 프롬프트·스키마로 같은 조건 A/B를 돌린다. 기준은 한국어 해석 정확도, 검증기 통과율, p50/p95다.
  - gpt-6-luna `none`/`low`
  - Haiku 5.5 thinking off/low
  - Sonnet 5.5 low
  - Groq gpt-oss-120b
  - gemini-3.8-flash low
- AA TTFT는 미국 서버 기준이고 프롬프트 길이 조건이 Thorkell과 다르다. 서울 실측이 최종 기준이다.

### Gaps
- Haiku 5.5의 thinking 끄기 지원 여부와 그때의 TTFT를 확인하지 못했다.
- gemini-3.8-flash(low)와 gpt-6-luna(none)를 같은 조건(서울, 3k 입력, JSON 스키마)으로 잰 독립 자료가 없다.
- Mistral Small 4·Medium 3.5 공식 토큰 가격, Groq·Cerebras 공식 가격표 본문(JS 렌더링)을 확인하지 못했다.
- Groq 무료/Developer 플랜 한도 구분이 여전히 모호하다.
- 후보 모델의 한국어 짧은 대사 → 행동 JSON 품질을 공개 평가로 비교한 자료는 찾지 못했다.

---

## 4. 대안 음성: OpenAI Realtime·GPT-Live-1, ElevenLabs, Grok·Nova, STT+TTS 파이프라인

### Takeaway
- **[unchanged] 정가 분당 단가**는 Gemini 3.8 Live가 여전히 가장 싸다.
- **[new] AA 측정**
  - Gemini 3.8 Live: TTFA 1.18초, 실효 비용 $0.84/입력 1시간
  - GPT-Live-1: 1.24~1.34초
  - gpt-realtime-2.1 Minimal: 0.97초
  - Grok Voice 3.0: 0.81초
- **[new] GPT-Live-1**(API 2026-09-10)은 세션 분당 $0.05에 백엔드 모델 비용이 따로 붙는다. 세션을 한 시간 열어 두면 그것만 $3.00/h라 $2/h 상한을 넘는다.
- **[추정] STT + 텍스트 LLM + TTS 파이프라인**(Gemini Transcribe Live + Haiku/Luna + Gemini 3.8 Flash TTS)은 재과금이 없어서 대화가 많을수록 유리하다. 대신 지연이 늘어난다.

### Cited Findings
**OpenAI**
- **[unchanged][공식] Realtime 가격**
  - gpt-realtime-2.1: 오디오 입력 $32 / 캐시 $0.40 / 출력 $64, 텍스트 $4 / $0.40 / $24
  - gpt-realtime-2.1-mini: 오디오 $10 / $0.30 / $20, 텍스트 $0.60 / $0.06 / $2.40
  - [new] gpt-realtime-2도 오디오 $32 / $0.40 / $64다
  - 전사: gpt-live-transcribe·gpt-realtime-whisper $0.017/분, gpt-transcribe $0.0045/분, gpt-realtime-translate $0.034/분
  - gpt-4o-mini-tts: 오디오 출력 $12
  - 출처: [OpenAI API Pricing](https://developers.openai.com/api/docs/pricing) (접속 2026-10-17)
- **[new][공식] GPT-Live 1 (`gpt-live-1`)**
  - 음성 세션 $0.05/분, 초 단위 과금(분 단위 올림 없음). 백엔드 Responses 호출은 해당 모델 요금이 따로 붙는다.
  - full-duplex(듣기와 말하기를 동시에)다. 추론과 tool 사용은 백엔드 에이전트에 위임한다.
  - Free 등급 미지원. 동시 세션 Build 50, Launch 300, Grow 500.
  - 엔드포인트 `v1/live/sessions`. 지원 언어 목록에 한국어 언급은 없다.
  - 출처: [OpenAI GPT-Live 1 모델 페이지](https://developers.openai.com/api/docs/models/gpt-live-1), [OpenAI API Pricing](https://developers.openai.com/api/docs/pricing) (접속 2026-10-17)
- **[new][제3자]** API 공개는 2026-09-10이다. OpenAI 발표 인용으로 턴테이킹 지연 0.798초(이전 1.41초), Tau3 Voice 86.2%다. 측정 조건은 공개되지 않았다 — [AI Weekly (2026-09-11)](https://aiweekly.co/alerts/openai-launches-gpt-live-1-in-the-api-at-005minute-cuts-turn-taking-latency-to) (접속 2026-10-17)

**독립 측정**
- **[new][제3자, AA] Speech-to-Speech 리더보드 ("As of July 2026" 표기, 접속 2026-10-17)**

  값은 Big Bench Audio, Conversational Dynamics, TTFA, 벤치마크 비용(입력 1시간당) 순이다.

  | 모델 | 값 |
  |---|---|
  | Gemini 3.8 Live | 92%, 96.1%, 1.18초, $0.84 |
  | Gemini 3.8 Live Extended Thinking (High) | 98%, 91.9%, 1.35초, $3.50 |
  | GPT-Live-1 (Sol, low) | 89%, 97.3%, 1.24초, $4.47 |
  | GPT-Live-1 (Astra, medium) | 90%, 94.9%, 1.34초, $5.83 |
  | GPT-Realtime-2.1 High | 96%, 1.21초, $10.75 |
  | GPT-Realtime-2.1 Minimal | 87%, 0.97초, $11.31 |
  | GPT-Realtime-2.1 Mini Minimal | 63%, 0.85초, $4.60 |
  | GPT-Realtime-2.1 Mini High | 75%, 4.28초, $3.45 |
  | Grok Voice 3.0 | 99%, 97.0%, 0.81초, $4.80 |
  | Grok Voice Fast 1.0 | 정가 입력·출력 각 $3/h, 0.78초 |
  | Amazon Nova 2.0 Sonic | 88%, 1.14초, 정가 입력 $0.27/h · 출력 $1.08/h |

  - ElevenLabs와 Hume은 순위표에 없다.
  - 출처: [AA Speech-to-Speech](https://artificialanalysis.ai/speech-to-speech)

**ElevenLabs**
- **[unchanged → 공식 확인][공식] ElevenLabs API 가격 (날짜 표기 없음)**
  - 에이전트 "Speech Engine": $0.08/분, burst $0.16/분, 동시 통화 4~40
  - TTS Flash/Turbo: $0.04/1K자, 약 75ms
  - TTS v3: $0.08/1K자, 70개 이상 언어
  - TTS v3 Conversational: $0.04/1K자, 약 280ms
  - [new] v4·v4 Turbo(약 100ms)
  - STT Scribe v2: $0.22/h. Scribe v2 Realtime: $0.39/h, 약 150ms
  - 한국어는 이름으로 명시되지 않았다
  - 출처: [ElevenLabs API Pricing](https://elevenlabs.io/pricing/api) (접속 2026-10-17)

**Gemini 파이프라인 부품**
- **[new][공식] Gemini 3.5 Transcribe Live**
  - 입력 $3.50(= $0.005/분 오디오), 출력 $21.00(= $0.004/분 텍스트)
  - 혼합 약 $0.009/분(초당 25토큰, 분당 175 텍스트 토큰 가정). 무료 등급 있음
  - 출처: [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing) (접속 2026-10-17)
- **[new][공식] Gemini 3.5 Transcribe(비실시간)**: 약 $0.005/분 — [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing) (접속 2026-10-17)
- **[new][공식] Gemini 3.8 Flash TTS**
  - 입력 $0.50, 출력 오디오 $9.00(= $0.00225/10초 = $0.0135/분)
  - 2027-01-01부터 두 배($1.00/$18.00)
  - 출처: [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing) (접속 2026-10-17)
- **[new][공식] Gemini 3.8 Flash-Lite TTS**: 출력 $6.00(= $0.0015/10초), 2027년 두 배 — [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing) (접속 2026-10-17)
- **[unchanged][공식] Groq Whisper**: large-v3-turbo $0.04/h, large-v3 $0.111/h — [Groq Models](https://console.groq.com/docs/models) (접속 2026-10-17)

### Inferences
- **[추정] 지연**: TTFA만 보면 Grok Voice(0.70~0.81초)와 gpt-realtime-2.1 Minimal(0.97초)이 Gemini 3.8 Live(1.18초)보다 빠르다. 하지만 한국어 품질과 게임 tool call 연동은 어느 쪽도 공개 근거가 없다.
- **[추정] 비용**: AA "입력 1시간당 벤치마크 비용"은 Gemini 3.8 Live가 $0.84로 가장 싸고, 다른 S2S 모델은 $3.45~$11.31이다. 재과금을 감안해도 S2S 중에서는 Gemini가 가장 싸다는 결론은 유지된다.
- **[추정] GPT-Live-1**: 세션 시간 과금이라 "게임 내내 열어 두는 음성"과 맞지 않는다. 대화할 때만 세션을 여는 설계라면 20분/h 기준 $1.00/h에 백엔드 비용이 붙는다.
- **[추정] STT + LLM + TTS 파이프라인**
  - 같은 대화량에서 Gemini Live보다 싸다(7절: 중간 시나리오 약 $0.28/h 대 재과금 Live $0.72~2.00/h).
  - 이유: 텍스트 LLM은 캐싱을 쓸 수 있고, 오디오를 컨텍스트에 쌓지 않는다.
  - 대신 지연이 STT 확정 + LLM TTFT(0.9~2초) + TTS 첫 바이트로 늘어난다. 1.5~3초가 될 수 있다(추정, 실측 없음).
  - Thorkell은 이미 텍스트 플래너와 게임 채팅 경로가 있으므로, 음성 입출력만 붙이는 구조로 갈 수 있다.

### Gaps
- 모든 음성 모델의 한국어 품질(인식률, 자연스러움)과 한국어 TTFA를 비교한 공개 평가는 이번에도 찾지 못했다.
- GPT-Live-1의 한국어 지원 여부, 세션 길이 한도, 전송 방식(WebRTC 여부)을 공식 문서에서 확인하지 못했다.
- OpenAI Realtime의 캐시 적중률 보장(이전 컨텍스트가 캐시 요율로 과금되는 비율)을 확인하지 못했다. 7절 계산은 100% 적중을 가정했다.
- Hume, Azure Voice Live, 국내(Naver·Kakao) 음성 API는 이번 라운드에서 다시 확인하지 않았다. 기준 문서 값이 유지된다.
- Grok Voice와 Nova 2.0 Sonic의 한국어 지원과 공식 가격 페이지는 확인하지 못했다.

---

## 5. 빠른 결정: Jev(TypeSafe)와 새 결정 API, OpenRouter

### Takeaway
- **[unchanged] Jev 가격**: 입력 $0.042/1M, 출력 무료.
- **[new] Jev 1.14.0**(약 2026-10-14): 이미지, 긴 컨텍스트, `box` 응답이 실험 기능으로 나왔다. `jev-latest`는 1주 뒤 1.14로 옮겨진다.
- **한도·가입 상태는 출처끼리 엇갈린다.**
  - 한도: 80 rps / 100k tok/s(2026-10-09 기사) 대 1,200 RPM / 250k tok/s(9월 기사).
  - 가입: 9월 말 신규 가입 중지 대 10-09 "open signup".
- **[new] 결정 API 경쟁자 셋**: OpenAI Decisions API, Cloudflare Clef/Clef-flash, Microsoft Decision-1. Clef는 Jev와 같은 요청 형태라서 대체 경로로 바로 쓸 수 있다.
- OpenRouter 무료 한도는 그대로다.

### Cited Findings
**Jev**
- **[unchanged/new][제3자] 가격·버전 (2026-10-09 갱신 기사)**
  - [unchanged] $0.042/1M 입력, 출력 무료
  - [new] 현행 `jev-1.13.0`. `jev-latest`·`jev-preview`가 이를 가리킨다
  - [new] Vercel AI Gateway에서 `typesafe-ai/jev`로 같은 가격에 제공된다. Vercel 팀당 월 $5 크레딧을 쓸 수 있다
  - [new] 한도 "As of October 2026 … 80 requests per second and 100,000 tokens per second". 초과하면 429다
  - [new] 신규 가입은 2026-09 말 중지됐고, 기존 계정은 계속 쓸 수 있다
  - 출처: [Flavio Copes: How much does Jev cost?](https://flaviocopes.com/jev-pricing/) (접속 2026-10-17)
- **[제3자, 상충] 한도·가입 상태**
  - 다른 기사들은 1,200 RPM, 250,000 tok/s, 요청당 64k(상태+최장 질문 32k)라고 적는다 — [opentweet.io Jev limits (2026-09)](https://opentweet.io/jev/limits) (검색 요약)
  - 반면 "공식 RPM 미공개"라는 기사도 있다 — [Layer3 Labs (2026-09-22)](https://www.layer3labs.io/guides/jev-limits) (접속 2026-10-17)
  - 2026-10-09 비교 기사는 Jev를 "Open signup"으로 적었다 — [Developers Digest](https://www.developersdigest.tech/blog/openai-decisions-api-vs-jev-vs-clef-2026) (접속 2026-10-17)
- **[new][공식] TypeSafe 홈페이지 (게시 2026-10-15)**
  - "$42 per billion input tokens"(= $0.042/1M)
  - "193.6x Faster": System One 작업에서 0.114초 대 LLM 8.566초
  - "early access"
  - Jev 1.14 블로그 링크가 있다
  - 출처: [TypeSafe AI](https://typesafe.ai) (접속 2026-10-17)
- **[new][제3자] Jev 1.14.0 (약 2026-10-14)**
  - "danger zone" 실험 기능: 이미지 입력, `box` 응답, 긴 컨텍스트. API 헤더로 켠다
  - 다국어 지원 개선
  - `jev-latest`는 1주 뒤 1.14.0으로 옮겨진다. 1.13.0은 60일 예고 뒤 내린다
  - 출처: [zeli.app (검색 요약)](https://zeli.app/story/50095353), [ecosistemastartup (검색 요약)](https://ecosistemastartup.com/jev-1-14-typesafe-abre-imagenes-y-contexto-largo/) (접속 2026-10-17)
- **[new][제3자, 경쟁사 측정] Cloudflare의 Jev Decision Index 실행 결과**
  - p50: Jev 524.1ms, Clef 209.3ms, Clef-flash 38.8ms
  - p95: Jev 536.0ms, Clef 238.6ms, Clef-flash 122.4ms
  - 출처: [Developers Digest (2026-10-09)](https://www.developersdigest.tech/blog/openai-decisions-api-vs-jev-vs-clef-2026) (접속 2026-10-17)

**새 결정 API**
- **[new][제3자] OpenAI Decisions API**
  - 2026-10-06 공개 베타. `POST /v1/decisions`, `gpt-6-luna`에서만 동작한다.
  - 입력 $0.10/1M. 출력·캐시 읽기·쓰기는 과금하지 않는다.
  - 질문 형태: predicate(0~1), choice, score. 이미지는 base64 인라인만 받는다.
  - ZDR·HIPAA 대상, US/EU data residency(10% 할증).
  - "Responses API보다 약 10배 빠르다"는 OpenAI 주장뿐이고 수치는 없다. GA는 "in the coming weeks"다.
  - 출처: [AI Weekly (2026-10-07)](https://aiweekly.co/alerts/openai-launches-decisions-api-public-beta-on-gpt-6-luna), [Developers Digest](https://www.developersdigest.tech/blog/openai-decisions-api-vs-jev-vs-clef-2026) (접속 2026-10-17)
- **[new][공식]** OpenAI 데이터 문서에 `/v1/decisions`가 ZDR "Yes, see below for limitations"로 올라 있다 — [OpenAI Your data](https://developers.openai.com/api/docs/guides/your-data) (접속 2026-10-17)
- **[new][제3자] Cloudflare Clef / Clef-flash**
  - 2026-10-01 Workers AI 출시. 크기는 27B / 9B이고 가중치는 Apache 2.0이다.
  - 입력 $0.24 / $0.09 per 1M, 출력 무과금.
  - 컨텍스트 65,536. 요청당 질문 1~64개, 이미지 4장까지.
  - **Jev와 같은 요청 형태(state + questions)**다.
  - 출처: [cryptobriefing (검색 요약)](https://cryptobriefing.com/cloudflare-clef-decision-models-workers-ai/), [eesel Clef pricing (검색 요약)](https://www.eesel.ai/blog/cloudflare-clef-pricing), [Developers Digest](https://www.developersdigest.tech/blog/openai-decisions-api-vs-jev-vs-clef-2026) (접속 2026-10-17)
- **[new][제3자] Microsoft Decision-1**
  - Microsoft Foundry, 입력 $0.042/1M, 출력 무료.
  - Qwen3.5-9B를 후학습한 모델이고, 32K 컨텍스트에 텍스트 전용이다.
  - 자체 측정으로 "Jev보다 2.8배 빠름", "GPT-6 Sol보다 P50 35배 빠름"이라고 주장한다. 재현 조건은 공개하지 않았다.
  - OpenRouter 등재 예정(미확인).
  - 출처: [pasqualepillitteri.it (검색 요약)](https://pasqualepillitteri.it/en/news/22320/microsoft-decision-1-launch-qwen-jev), [testingcatalog (검색 요약)](https://www.testingcatalog.com/microsoft-launches-decision-1-model-in-foundry/), [eesel Decision-1 (검색 요약)](https://www.eesel.ai/de/blog/microsoft-decision-1-preise) (접속 2026-10-17)

**OpenRouter**
- **[unchanged][공식] 무료 한도**
  - `:free` 모델은 20 RPM.
  - 누적 구매 10크레딧 미만이면 50 RPD, 10 이상이면 1,000 RPD. 반올림·수수료를 감안해 9크레딧부터 적용한다.
  - 유료 모델은 플랫폼 요청 상한이 없다. 키별 지출 상한을 걸 수 있다.
  - 출처: [OpenRouter Limits](https://openrouter.ai/docs/api-reference/limits) (접속 2026-10-17)
- **[unchanged, 이번 라운드 미재확인]** 충전 수수료 5.5%(최소 $0.80)와 지연 오버헤드(공식 약 40ms, 독립 측정 80~250ms)는 기준 문서 값이다 — [OpenRouter FAQ](https://openrouter.ai/docs/faq), [OpenRouter Latency](https://openrouter.ai/docs/features/latency-and-performance)
- **[unchanged]** Jev의 OpenRouter 등재는 이번에도 확인하지 못했다. 10-09 기사는 OpenRouter를 언급하지 않는다 — [Flavio Copes](https://flaviocopes.com/jev-pricing/) (접속 2026-10-17)

### Inferences
- **[추정] 지연 비교**: Thorkell 실측 Jev p50 188ms / p95 292ms는 Cloudflare가 잰 Jev 값(p50 524ms)보다 훨씬 빠르다. 경쟁사 측정이고 조건(질문 수, 토큰 길이, 지역)이 다르므로 Thorkell 실측을 우선한다.
- **[추정] Clef-flash 대체 경로**
  - 같은 요청 형태이고, p50 38.8ms / p95 122.4ms(벤더 측정)이며, 1,500토큰 결정 1,800회/h에 $0.24다.
  - Jev가 429를 내거나 가입이 막힐 때 config로 명시적으로 고르는 대체 경로가 될 수 있다. AGENTS.md 규칙 7에 따라 숨은 폴백은 두지 않는다.
- **[추정] 다른 둘**
  - OpenAI Decisions API는 Jev의 2.4배 가격이고 베타다.
  - Microsoft Decision-1은 Jev와 같은 가격이지만 Foundry(Azure) 계정이 필요하다.
- **[추정] 1.14 전환 위험**: Jev 1.14로 `jev-latest`가 옮겨지면 결정 분포가 달라질 수 있다. 결정 로그를 laya 증류에 쓰므로 모델 ID를 `jev-1.13.0`처럼 고정하고 버전을 로그에 남겨야 한다.
- **[추정] 버스트 여유**: 80 rps 한도라면 위험 상황 버스트(분당 수십 회)는 여유가 크다.

### Gaps
- TypeSafe 공식 문서(docs.typesafe.ai)의 레이트 리밋·가입 상태를 직접 확인하지 못했다. 출처끼리 상충한다.
- Clef·Decision-1·Decisions API의 한국어 입력 품질, 서울 기준 지연, 공식 가격 페이지를 확인하지 못했다.
- Microsoft Decision-1의 정확한 출시일(2026-10-12 전후로 추정)과 Foundry 공식 페이지를 확인하지 못했다.

---

## 6. 무료/유료 데이터·프라이버시 약관 (간단히)

### Takeaway
- **Gemini**: 무료 등급 데이터는 제품 개선에 쓰이고 유료는 쓰이지 않는다. 한 프로젝트라도 결제를 켜면 AI Studio 프롬프트도 유료 약관을 따른다.
- **OpenAI·Anthropic API**: 기본으로 학습에 쓰지 않는다.
  - OpenAI는 남용 감시 로그를 최대 30일 보관한다.
  - Anthropic 보관 기간은 7일 또는 30일로 출처가 엇갈린다.

### Cited Findings
- **[unchanged][공식] Gemini 3.8 Flash·3.8 Live·Flash-Lite**: "Used to improve our products" 무료 Yes, 유료 No — [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing) (접속 2026-10-17)
- **[new][공식]** 결제가 켜진 API 프로젝트가 하나라도 있으면 AI Studio 프롬프트도 "Paid Services" 약관을 따른다 — [Gemini API Billing](https://ai.google.dev/gemini-api/docs/billing) (접속 2026-10-17)
- **[new][공식] OpenAI**
  - API 데이터는 2023-03-01 이후 옵트인하지 않으면 학습에 쓰지 않는다.
  - 남용 감시 로그는 최대 30일이다.
  - ZDR은 승인제다. `/v1/realtime`은 Yes, `/v1/decisions`·`/v1/live/sessions`는 "Yes, with limitations"다.
  - 출처: [OpenAI Your data](https://developers.openai.com/api/docs/guides/your-data) (접속 2026-10-17)
- **[new][제3자] Anthropic**
  - 상용 약관상 API 입력·출력은 기본으로 학습에 쓰지 않는다.
  - 보관 기간은 30일이라는 출처와 "2025-09-14부터 7일"이라는 출처가 엇갈린다.
  - 출처: [char.com (검색 요약)](https://char.com/blog/anthropic-data-retention-policy), [Double help center (검색 요약)](https://help.doublehq.com/en/articles/15280179-how-we-use-ai-in-double) (접속 2026-10-17)

### Inferences
- **[추정]** Thorkell은 친구들 목소리(Gemini Live 오디오)를 보낸다. 그래서 무료 등급을 계속 쓰면 친구들 음성이 Google 제품 개선에 쓰일 수 있다. 결제를 연결하는 이유가 하나 더 생긴다.

### Gaps
- Anthropic 공식 보관 기간(7일/30일)을 1차 문서로 확인하지 못했다.
- Groq·Cerebras·DeepSeek·TypeSafe·Cloudflare의 데이터 보관·학습 약관은 이번에 확인하지 않았다.

---

## 7. Thorkell 시간당 비용 재계산 (가정·공식 명시)

### Takeaway
**[추정]** 기준 문서는 음성을 분당 단가로만 계산해서 $0.17~0.48/h로 잡았다. 누적 재과금을 넣으면 Gemini 3.8 Live는 대화량에 따라 크게 달라진다.

| 대화량 | 압축·리셋 없음 | 15분마다 새 세션 | 8k 윈도 |
|---|---|---|---|
| 적음(20턴/h) | $0.21/h | $0.11/h | $0.21/h |
| 중간(60턴/h) | **$2.00/h** | $0.72/h | $0.80/h |
| 많음(120턴/h) | **$8.06/h** | $2.45/h | $1.54/h |

- 현재 구성 전체(gemini-3.8-flash + Jev + Live, 15분 리셋)는 적음 $0.23, 중간 $1.04, 많음 $3.06/h다.
- **대화가 많으면 $2/h 상한을 넘는다.** 상한 안에 머무는 가장 확실한 손잡이는 Live 세션당 턴 수(윈도)를 줄이는 것이다.
- 다음으로 큰 손잡이는 플래너를 Haiku 5.5나 gpt-6-luna로 바꾸거나, 음성을 STT+LLM+TTS로 바꾸는 것이다.

### Cited Findings
입력 가격과 출처(모두 접속 2026-10-17)
- gemini-3.8-flash $0.75/$3.75(2027 $1.50/$7.50). Gemini 3.8 Live 텍스트 입력 $0.75, 오디오 입력 $3.00, 오디오 출력 $12.00. 오디오 25토큰/초. Gemini 3.5 Transcribe Live 약 $0.009/분. Gemini 3.8 Flash TTS $0.00225/10초 — [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Haiku 5.5 $0.10/$0.50 — [Claude API Pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- gpt-6-luna $0.10/$0.50. gpt-realtime-2.1-mini 오디오 $10/캐시 $0.30/$20, 텍스트 $0.60/$0.06. gpt-realtime-2.1 오디오 $32/$0.40/$64, 텍스트 $4/$0.40. gpt-live-1 $0.05/분 — [OpenAI API Pricing](https://developers.openai.com/api/docs/pricing)
- Jev $0.042, OpenAI Decisions $0.10, Clef $0.24, Clef-flash $0.09, Decision-1 $0.042 — 5절 출처
- 재과금 근거 — 2절 포럼 출처

### Inferences

**공식 [추정]** (가격 P는 $/1M 토큰, M = 10^6)

```
플래너      C_plan  = n_p × (I_p·P_in + O_p·P_out) / M
빠른 결정    C_dec   = n_d × I_d × P_in / M

Gemini Live (턴 k = 1..n, 한 세션, 압축 없음)
  턴 k 과금 입력 = [S + k·x] (텍스트) + [(k−1)(a_u + a_r) + a_u] (오디오)
  C_live = { (n·S + x·n(n+1)/2)·P_txt_in
           + ((a_u + a_r)·n(n−1)/2 + n·a_u)·P_aud_in
           + n·a_r·P_aud_out } / M
  a = 25 × 발화 초
  슬라이딩 윈도 W: 턴 k의 컨텍스트 = min(S + 누적, W). system(S)은 항상 남는다.
  15분 리셋: 한 시간을 n/4턴짜리 세션 4개로 나눈다. 2번째 세션부터 S에 요약 1,000토큰을 더한다.

OpenAI Realtime (이전 컨텍스트 100% 캐시 적중 가정)
  C_rt = Σ_k [ a_u·P_aud_in + (k−1)(a_u + a_r)·P_aud_cache
             + x·P_txt_in + (S + (k−1)x)·P_txt_cache ] / M
         + n·a_r·P_aud_out / M

STT + LLM + TTS 파이프라인
  C_pipe = STT분 × $0.009 + TTS초/10 × $0.00225 + n × (2,500·P_in + 150·P_out) / M
```

**가정 [추정]**

| 수준 | 플래너 n_p (I_p=3,000, O_p=500) | 결정 n_d (I_d=1,500) | Live 턴 n | 사용자 발화 a_u | 토르켈 발화 a_r | 턴당 주입 텍스트 x | system+tools S |
|---|---|---|---|---|---|---|---|
| 적음 | 20/h | 600/h | 20 | 4초 = 100 | 5초 = 125 | 100 | 2,000 |
| 중간 | 60/h | 1,200/h | 60 | 5초 = 125 | 6초 = 150 | 200 | 3,000 |
| 많음 | 120/h | 1,800/h | 120 | 5초 = 125 | 6초 = 150 | 300 | 3,000 |

- 오디오는 말한 구간만 보낸다(클라이언트 VAD)고 가정했다.
- 누적 오디오는 오디오 요율로 잡았다(상한 쪽).
- Live thinking 토큰과 tool 응답 토큰은 넣지 않았다.
- 파이프라인 STT는 10/20/60분, TTS는 턴당 a_r초로 잡았다.

**플래너 호출당·시간당 [추정]** (I=3,000, O=500. 괄호는 thinking이 많아 O=1,500일 때 120회/h)

| 모델 | 호출당 | 30/h | 120/h |
|---|---|---|---|
| gemini-3.8-flash (2026) | $0.00413 | $0.12 | $0.50 ($0.95) |
| gemini-3.8-flash (2027~) | $0.00825 | $0.25 | $0.99 ($1.89) |
| gemini-3.5-flash-lite | $0.00215 | $0.06 | $0.26 |
| gemini-3.1-flash-lite | $0.00150 | $0.05 | $0.18 |
| Claude Haiku 5.5 / gpt-6-luna | $0.00055 | $0.02 | $0.07 ($0.13) |
| Claude Sonnet 5.5 | $0.01100 | $0.33 | $1.32 |
| gpt-5.6-luna | $0.00120 | $0.04 | $0.14 |
| Groq gpt-oss-120b | $0.00075 | $0.02 | $0.09 |
| Cerebras gpt-oss-120b (제3자 가격) | $0.00143 | $0.04 | $0.17 |
| DeepSeek flash (할인/피크) | $0.00075/$0.0015 | $0.02/$0.05 | $0.09/$0.18 |

**빠른 결정 시간당 [추정]** (I=1,500)

| 서비스 | 600회/h | 1,800회/h |
|---|---|---|
| Jev / Decision-1 | $0.04 | $0.11 |
| Clef-flash | $0.08 | $0.24 |
| OpenAI Decisions | $0.09 | $0.27 |
| Clef | $0.22 | $0.65 |

**음성만 시간당 [추정]**

| 음성 방식 | 적음 | 중간 | 많음 |
|---|---|---|---|
| Gemini 3.8 Live, 분당 단가만(기준 문서 방식) | $0.04 | $0.13 | $0.26 |
| Gemini 3.8 Live, 재과금, 한 컨텍스트, 압축 없음 | $0.21 | **$2.00** | **$8.06** |
| Gemini 3.8 Live, 재과금, 윈도 16k | $0.21 | $1.48 | $3.06 |
| Gemini 3.8 Live, 재과금, 윈도 8k | $0.21 | $0.80 | $1.54 |
| Gemini 3.8 Live, 재과금, 15분마다 새 세션 + 요약 | $0.11 | $0.72 | $2.45 |
| gpt-realtime-2.1-mini (캐시 100%) | $0.09 | $0.44 | $1.27 |
| gpt-realtime-2.1 (캐시 100%) | $0.27 | $1.27 | $3.56 |
| GPT-Live-1 (세션을 연 분 × $0.05, 백엔드 별도) | 20분 열면 $1.00 | 60분 열면 $3.00 | – |
| STT(Gemini Transcribe Live) + Haiku/Luna + Gemini 3.8 Flash TTS | $0.12 | $0.28 | $0.74 |
| (최악) 마이크 상시 스트림이 컨텍스트에 쌓임, 60턴 | – | 약 $9.6 | – |

**구성별 합계 시간당 [추정, 2026 가격]**

| 구성 | 적음 | 중간 | 많음 |
|---|---|---|---|
| A. 현재: gemini-3.8-flash + Jev + Live(15분 리셋) | $0.23 | $1.04 | $3.06 |
| A-u. 현재, Live 압축·리셋 없음 | $0.33 | **$2.32** | **$8.66** |
| A'. 현재, 2027 Flash 가격(Live 15분 리셋) | $0.31 | $1.29 | $3.56 |
| B. Haiku 5.5 또는 gpt-6-luna 플래너 + Jev + Live(15분 리셋) | $0.16 | $0.83 | $2.63 |
| C. Haiku/Luna 플래너 + Jev + STT·LLM·TTS 파이프라인 | $0.17 | $0.39 | $0.92 |
| D. Haiku/Luna 플래너 + Jev + gpt-realtime-2.1-mini | $0.14 | $0.55 | $1.45 |
| E. GPT-Live-1(20분 세션) + Haiku/Luna 플래너 + Jev | 약 $1.05 + 백엔드 | 약 $1.11 + 백엔드 | 약 $1.18 + 백엔드 |

- **[추정] 상한 판단**: $2/h 상한 안에 들어가려면 "중간" 대화량에서 Live를 윈도 8k 이하나 15분 리셋으로 관리해야 한다. "많음"에서는 A·B 모두 상한을 넘는다. 그때 상한 안에 드는 구성은 C(파이프라인)와 D(realtime-mini), 그리고 윈도 8k Live + 저가 플래너(약 $1.7)뿐이다.
- **[추정] 2027 영향**: 2027-01-01 Flash 가격 인상은 중간 대화량에서 +$0.25/h 정도다. 음성 관리 방식(최대 ±$1.3/h)보다 영향이 작다.
- **[추정] 보정 방법**: 계산이 가장 크게 흔들리는 변수는 턴당 증가량(a_u + a_r + x)과 S다. 포럼 표본(약 8k/턴)이 Thorkell에도 맞다면 위 Live 값은 몇 배로 커진다. 첫 1시간 실플레이에서 Live `usageMetadata`의 턴별 `promptTokenCount`를 모두 합해 기록하고, 콘솔 청구액과 대조해 표를 보정한다.
- **[추정] 코드 쪽 시사점**
  - 비용 가드는 Live 턴별 누적 토큰 합을 실시간으로 세야 한다. 분당 단가로는 부족하다.
  - 게임 상태를 Live 세션에 텍스트로 계속 주입하면(x↑) 이후 턴마다 다시 과금된다. 상태 요약은 짧게 넣거나 tool 응답으로만 준다.

### Gaps
- 실제 Thorkell 프롬프트 크기(I_p, S, x)와 대화 턴 수는 가정값이다. 로그로 재야 한다.
- 누적 오디오의 과금 요율(오디오/텍스트), Live thinking 토큰, 무음 구간 과금은 확인하지 못했다(2절).
- OpenAI Realtime 캐시 적중률, GPT-Live-1 백엔드 호출량은 가정 밖이다.
- 원화 환산과 한국 부가세(해외 디지털 서비스 10%) 적용은 계산하지 않았다.
