# Gemini·Jev 예상 비용과 키 발급 절차 (2026-10-02 확인)

표기: [공식] 벤더 문서, [포럼] Google 개발자 포럼(직원 답변 포함), [커뮤니티] 제3자 글, [추정] 이 문서의 계산.

## 1. 단가

| 모델 (Thorkell에서의 역할) | 입력 | 출력 | 비고 |
|---|---|---|---|
| `gemini-3.8-flash` (플래너·회고) | $0.75 / 1M 토큰 | $3.75 / 1M 토큰 (thinking 포함) | 2026-12-31까지 도입가. **2027-01-01부터 $1.50 / $7.50** [공식] |
| `gemini-3.8-live` (음성 대화) | 텍스트 $0.75, **오디오 $3.00 / 1M** (≈ $0.005/분) | 텍스트 $4.50, **오디오 $12.00 / 1M** (≈ $0.018/분) | 오디오는 초당 25토큰 [공식] |
| `gemini-3.5-flash-lite` (대화에서 사실 추출용 후보) | $0.30 | $2.50 | [공식] |
| `gemini-3.8-flash-tts` (대안 경로) | 텍스트 $0.50 | 오디오 $9.00 (≈ 10초당 $0.00225) | 2027년 두 배 [공식] |
| Jev (빠른 결정) | **$0.042 / 1M** (공식 표기 "$42 per billion input tokens") | **무료** | [공식] typesafe.ai |

- 무료 등급: 위 Gemini 모델은 모두 무료 등급이 있다. 다만 **무료 등급 데이터는 "제품 개선에 사용"된다.** 마이크 음성도 해당된다 [공식].
- Google Cloud 신규 크레딧($300 체험)은 Gemini API·AI Studio에 쓸 수 없다 [공식].

## 2. Live 과금에서 주의할 점

- Google 직원 답변(2026-07-07): "Gemini Live re-bills the entire cumulative context on every single turn."
  - 이전 턴의 원본 오디오 토큰을 문맥에 그대로 들고 있으므로, **매 턴 누적 문맥 전체가 다시 입력으로 과금된다** [포럼].
  - 보고된 세션: 2~29턴에서 마지막 프롬프트가 약 8.6k~261k 토큰. 비용은 통화 시간보다 턴 수에 비례했다 [포럼].
- sliding window 압축을 켜면 압축된 양에 이번 턴의 새 토큰을 더한 만큼만 과금된다 [커뮤니티 요약].
  - 따라서 **압축 트리거와 목표 토큰을 작게 잡는 것이 비용 통제의 핵심이다.**
  - 현재 코드(`brain/thorkell/talk/live.py`)는 `{"sliding_window": {}}`로 기본값을 쓰고 있다. 명시적으로 작은 값을 넣어야 한다 [추정].
- 마이크를 계속 열어 두면 말하지 않는 시간의 오디오도 입력 토큰이 된다(초당 25토큰). 그래서 누르고 말하기나 클라이언트 VAD로 말할 때만 보내는 편이 싸다 [추정].

## 3. 시간당·월 예상 비용 [추정]

가정: 게임 1시간 동안 리더 발화 30번, Thorkell이 먼저 말하는 음성 15번(턴 45개), Thorkell 발화 약 4분, 플래너 호출 12번(입력 4k, 출력·thinking 1.1k 토큰), Jev 결정 100~600번(번당 약 600토큰).

| 항목 | 시간당 (2026 단가) | 계산 |
|---|---|---|
| 플래너 (3.8 Flash) | 약 $0.09 | 12 × 4k × $0.75/M + 12 × 1.1k × $3.75/M. 2027년에는 약 $0.17 |
| 회고·추출 (나중에 LLM으로 켜면) | 약 $0.05 | Flash 10회 + Flash-Lite 20회 |
| 음성 (3.8 Live), 압축을 작게(문맥 약 8k) + 말할 때만 송신 | **약 $1.1~1.4** | 45턴 × 8k × $3/M ≈ $1.08, 출력 4분 × $0.018 ≈ $0.07 |
| 음성 (3.8 Live), 기본 압축 + 마이크 상시 송신 | **약 $5 이상** | 문맥이 수만 토큰으로 커진 채 매 턴 재과금 |
| Jev | **약 $0.003~0.015** | 6만~36만 토큰 × $0.042/M |

| 사용 형태 (월 60시간 = 하루 2시간) | 월 비용 |
|---|---|
| 채팅만(음성 끔) + 플래너 + Jev | **약 $9** (2027년 약 $15) |
| 음성 포함, 압축·송신 최적화 | **약 $70~90** |
| 음성 포함, 최적화 안 함 | $300 이상 |
| 대안: 로컬 ASR(WhisperKit) + Flash 텍스트 답 + 로컬 한국어 TTS(Supertonic) | 약 $10~20. 대신 응답이 약 2~3초로 느리고 끼어들기가 덜 자연스러움 |

Jev는 월 1달러도 안 된다. 크레딧 $5(받을 수 있다면)는 약 1억 2천만 토큰, 즉 결정 약 20만 번이다.

## 4. Gemini API 키 발급
1. Google 계정으로 https://aistudio.google.com/apikey 에 들어간다. 한국은 지원 지역이다 [공식].
2. 처음이면 약관에 동의한다. 그러면 AI Studio가 기본 Google Cloud 프로젝트와 API 키를 자동으로 만든다 [공식].
   - 기존 Cloud 프로젝트를 쓰려면 Dashboard → Projects → **Import projects**에서 고른다.
3. **API Keys** 페이지에서 키를 만든다.
   - 2026-05-28부터 새 키는 서비스 계정에 묶인 auth key로 만들어지고, 유출 감지 시 빠르게 차단된다 [공식].
   - 제한 없는 키가 있으면 **Add restrictions → Restrict to Gemini API only**를 건다.
4. (유료 등급) **Set up billing**에서 결제 계정을 만들거나 고른다. 연락처와 결제 수단을 넣고 결제 방식을 고른다 [공식].
   - **Prepay**: 크레딧 선구매, 최소 $5, 최대 $5,000. 자동 충전(**Setup auto-reload**)과 **Monthly Limit**을 설정할 수 있다.
   - **Postpay**: 월말 청구.
   - 결제 계정을 연결하면 Tier 1(월 한도 $250)이 된다.
5. 지출 통제: AI Studio의 Spend 페이지에서 **Monthly spend cap → Edit spend cap**으로 프로젝트 월 상한을 건다. 사용량은 Dashboard → Usage에서 본다 [공식].
6. 환경 변수: `GEMINI_API_KEY`와 `GOOGLE_API_KEY`가 둘 다 있으면 **`GOOGLE_API_KEY`가 우선**한다 [공식]. 셸에 다른 `GOOGLE_API_KEY`가 남아 있지 않은지 확인한다.

## 5. Jev 키 발급
- 공식 사이트(https://typesafe.ai)는 "early access"와 콘솔 https://console.typesafe.ai/ 만 안내한다. 공개 가입 여부는 명시하지 않는다 [공식].
- 커뮤니티 보도 [커뮤니티]:
  - 2026-09-20: 크레딧 $5와 함께 공개 가입 시작
  - 2026-09-22: 수요 폭주로 신규 가입 일시 중단(기존 계정은 영향 없음)
  - 9월 18일자 가이드는 대기자 명단 방식이라고 적었다
  - **지금 바로 가입되는지는 직접 확인해야 한다.**
- 절차:
  1. console.typesafe.ai에서 가입한다(또는 대기자 명단에 등록 → 초대 메일).
  2. 계정이 열리면 키 페이지(`/settings/keys` 또는 `/keys`)에서 키를 만든다. 키는 `ts_`로 시작하며 한 번만 보인다.
  3. Playground(`/playground`)에서 질문을 시험해 본다.
  4. 호출 형식: `POST https://api.typesafe.ai/v1/systemone`, 헤더 `Authorization: Bearer $TYPESAFE_API_KEY`
  - 모델 ID는 자료마다 `jev-latest`/`jev-preview`/`jev-1.13.0`으로 다르다. `thorkell contract jev`로 확인한다.
- 대안:
  - **Vercel AI Gateway**의 `typesafe-ai/jev`는 대기자 명단 없이 같은 단가라고 한다 [커뮤니티]. 요청 형식이 달라서 `brain/thorkell/models/systemone.py`에 어댑터가 필요하다(미확인).
  - 이전 조사의 OpenRouter `typesafe/jev-1.13`은 2026-10-02 현재 페이지가 404였다(확인 불가).
  - 키 없이도 `decide.* = "rules"`로 돌아가고, 나중에 로컬 laya(Apache-2.0)로 바꿀 수 있다.

## 6. 키를 1Password에 넣고 쓰기
1. 1Password 앱 → 설정 → 개발자 → **1Password CLI와 통합**을 켠다(또는 터미널에서 `op signin`).
2. 앱에서 새 항목 → "API 자격 증명"을 만든다. 제목은 `Gemini API`, `TypeSafe Jev`로 하고 `credential` 필드에 키를 붙여 넣는다. 셸에 키를 직접 치지 않는다(히스토리에 남음).
3. 값을 출력하지 않고 참조가 풀리는지만 확인한다: `op read "op://Private/Gemini API/credential" | wc -c` (보관함 이름이 다르면 바꾼다).
4. `brain/secrets.op.example`을 `brain/secrets.op`로 복사하고 경로를 맞춘다(gitignore 대상, op:// 참조만 담김).
5. 실행: `cd brain && op run --env-file secrets.op -- uv run thorkell contract flash` (`jev`, `live`도 같은 방식).

## 7. 실측 계약 결과 (2026-10-02, `thorkell contract flash|jev|live`, 각 1회 실행)

원본: `artifacts/contracts/flash-20261002-095048.json`, `jev-20261002-095057.json`, `live-20261002-095113.json`(gitignore 대상).

| 모델 | 확인한 것 | 결과 | 반영 |
|---|---|---|---|
| `gemini-3.8-flash` | thinking `minimal` | **400 거절**: "THINKING_LEVEL_MINIMAL is not supported for this model" | 설정에서 `minimal`을 뺐다(읽을 때 `ConfigError`) |
| | thinking `low` | 2.24초, 스키마에 맞는 JSON, 생각 토큰 0 | 플래너 기본값 `low` 유지 |
| | thinking `medium` | **40.42초**, 생각 토큰 176 | 생각 양에 비해 너무 느리다. 1회 측정이라 대기열 탓일 수 있다. 다시 재기 전까지 실시간 경로에 쓰지 않는다 |
| Jev `jev-1.13.0` | `threat_response` 10회 | 오류 0, **p50 188ms / p95 292ms** | 마감 600ms 안에 든다 |
| | 답의 경향 | 체력 72%, 그레이드워프 3m 상황에서 `retreat_to_leader` 0.57~0.64, `fight` 0.24~0.29 | 위협 대응은 지금 규칙보다 물러서는 쪽이다. 실게임 로그로 다시 본다 |
| `gemini-3.8-live` | 도구 호출 | "지금 뭐 하고 있어?"에 `ask_status`를 불렀다 | |
| | `FunctionResponse.scheduling` | 별도 필드(`WHEN_IDLE`)로 보낸 응답을 받아들였다 | `talk/live.py` 방식 확인 |
| | 첫 음성 | 질문 뒤 **1.19초**, 도구 응답 뒤 **0.69초** | 계획의 p50 2.0초 목표 안 |
| | 말투·재개 | 반말 한국어 전사("나무 모으기를 하고 있어. 현재 열 개 중에 네 개를 모았지."), `resumable` true | |

### 7.1 리허설에서 겪은 사용 한도 (2026-10-02 15:45, 실측)

- 지금 키는 **무료 등급**이다. `gemini-3.8-flash`가 429로 거절했다: "Rate limit exceeded for model gemini-3.8-flash (limit: **20 requests per day** on Free Tier)". 계약 확인·탐침·리허설 대화로 하루 한도를 다 썼다.
- SDK(google-genai 2.26) 기본 재시도는 429에도 서버가 말한 대기(약 30초)만큼씩 세 번 다시 한다. 그래서 인사 한마디가 **91초** 뒤에야 실패했고, 그동안 토르켈은 아무 말이 없었다.
- 반영(`brain/thorkell/models/gemini.py`):
  - 429는 다시 하지 않고 바로 `ModelError(status=429)`를 낸다(0.5초).
  - 토르켈은 "계획 모델 사용 한도에 걸렸어. 정해진 말은 바로 알아들어"라고 말한다.
  - 5xx만 한 번 다시 하고, 요청 시간 제한은 60초다.
- 정해진 말("따라와", "기다려", "멈춰", "나무 N개 캐줘")은 플래너를 거치지 않으므로 한도와 상관없이 된다.
- [추정] 같이 플레이하면 잡담·새 부탁마다 1회씩 쓴다. 하루 20회로는 한 시간도 버티기 어렵다. 실제 플레이에는 유료 등급(4절 결제 설정)이 필요하다.

## 출처 (모두 2026-10-02 확인)
- [공식] Gemini 가격: https://ai.google.dev/gemini-api/docs/pricing
- [공식] API 키: https://ai.google.dev/gemini-api/docs/api-key
- [공식] 결제: https://ai.google.dev/gemini-api/docs/billing
- [공식] 지원 지역: https://ai.google.dev/gemini-api/docs/available-regions
- [포럼] Live 누적 문맥 재과금(Google 직원 답변 2026-07-07): https://discuss.ai.google.dev/t/does-gemini-live-native-audio-bill-cumulative-prompt-tokens-on-every-turn-cost-seems-to-scale-with-turn-count-not-call-duration/173248
- [공식] TypeSafe: https://typesafe.ai
- [커뮤니티] Jev 가격·가입: https://www.eesel.ai/blog/typesafe-jev-pricing , https://apidog.com/blog/jev-api-key/ (2026-09-18), https://jev-ai.live/get-access/
