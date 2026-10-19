# 사람의 Valheim 첫 플레이 관찰: 스폰부터 에이크쉬르까지 (2026-10-17)

처음 하는 사람이 실제로 어떤 화면 정보를 보고 무엇을 결정하는지 영상 10개로 확인했다. 2인 협동도 함께 봤다. 토르켈의 지각 범위와 행동 규칙을 정할 근거로 쓴다.

## 요약

- **첫 보스까지 걸린 실시간은 1.5~3시간이다.**
  - 혼자 한 블라인드 플레이어 둘은 약 3시간 걸렸다(V1, V7).
  - 한국어 솔로 방송은 VOD 1:37:56에 잡았다(V3).
  - 게임 안에서는 2~6일째에 잡았다.
- **처음 하는 사람이 가장 오래 막힌 곳은 망치(Hammer)를 모르는 것이다.**
  - 망치가 없으면 모닥불, 작업대, 침대를 아예 지을 수 없다.
  - V7은 약 1시간, V1은 영상 40분까지 이 단계에서 헤맸다.
- **보스 위치는 거의 모두 스폰 옆 베그비시르로 알았다.**
  - 베그비시르에서 `[E] Register location`을 누르면 지도에 보스 아이콘이 생긴다.
- **소환 조건은 세 단서를 이어 붙여서 알아냈다.**
  - 제단 옆 룬스톤 문구 "그의 일족을 사냥해라"
  - 제단 돌 위의 사슴 조각상
  - 제물을 올렸을 때 나오는 실패 메시지 `미완성 제물: 사슴의 트로피 1 / 2`
- **준비 없이 소환하는 실수가 흔했다(V1, V4).**
  - 에이크쉬르는 제단에 머물지 않고 집이나 스폰 근처까지 따라왔다.
  - 집을 부쉈다.
  - 죽어도 보스 체력은 회복되지 않았다.
- **보스전에서 실제로 통한 것은 네 가지다.**
  - 음식 3개
  - 활(또는 창과 방패)
  - "두 번 때리고 빠지기"
  - 번개를 옆으로 피하기
- **협동에서는 역할이 저절로 나뉘었다.**
  - 한 명은 나무를 베어 건네고, 한 명은 짓는다.
  - 보스전에서는 한 명이 어그로를 끌고 다른 사람들이 활을 쏜다.
  - 위치는 "지도에서 다른 플레이어에게 보이기"로 공유했다.
- **한국어 UI에는 번역되지 않은 토큰이 그대로 찍힌다.**
  - 예: `[tutorial_altar_label]이(가) 백과사전에 추가되었습니다`
  - 지각 파이프라인에서 걸러야 한다.

## 0. 표기와 한계

### 근거 표기

| 표기 | 뜻 |
|---|---|
| `SEEN V3 1:16:38` | 해당 영상의 그 시각 프레임을 직접 봤다 |
| `HEARD V1 0:36:00` | 자동 자막에 나온 말이다 |
| `WIKI url` | 위키나 가이드에서 가져왔다 |
| `REPO path` | 레포의 디컴파일 메모에서 가져왔다 |

### 영상 쪽 한계

- 자막 타임스탬프는 롤링 자막을 20초 단위로 묶은 구간의 시작 시각이다. 실제 발화는 그 뒤 20초 안에 있다.
- 오디오는 받지 않았다. 소리 단서(음악 변화, 동물 소리)는 해설자가 말로 언급한 것만 적었다.
- 대부분 편집된 영상이다. 영상 시각과 실제 플레이 시간이 다르다.
  - V1은 3시간 넘는 플레이를 84분으로 줄였다.
  - V4는 8분 45초로 줄였다.

## 1. 영상 목록

| 별칭 | 영상 | 채널 / 업로드 / 길이 / 언어 | 성격 | 실제로 본 것 |
|---|---|---|---|---|
| V1 | [I tried Valheim 1.0 as a Brand New Player...](https://www.youtube.com/watch?v=b-tIUNNQZ7s) | LUCYJROBYN / 2026-09-28 / 1:24:07 / 영어 | 1.0, 솔로, 완전 블라인드, 키보드. 처치까지 진행 | 자막 전체<br>360p 30초 간격 168프레임(접촉 시트)<br>720p 구간 29개에서 3초 간격 프레임: 0:36~0:45, 1:00~1:12, 2:10~2:20, 3:25~3:35, 4:00~4:15, 6:35~6:45, 9:30~10:05, 11:08~11:20, 12:05~12:15, 17:02~17:40, 29:05~29:50, 35:50~36:55, 40:20~40:35, 42:30~43:18, 45:10~45:20, 57:25~57:40, 1:01:00~1:01:15, 1:04:10~1:04:25, 1:06:15~1:06:25, 1:09:40~1:09:55, 1:10:50~1:11:00, 1:20:35~1:20:50, 1:22:05~1:22:25 |
| V2 | [Two Friends Play Valheim for the FIRST Time… \| Valheim #1](https://www.youtube.com/watch?v=SZBycipUF5E) | Quay / 2026-09-14 / 1:13:04 / 영어 | 2인 협동, 콘솔 패드. **한 명은 경험자, 한 명은 처음.** 처치까지 진행 | 자막 전체<br>360p 30초 간격 146프레임<br>720p: 2:16~2:22, 14:31~14:37, 41:16~41:28, 45:21~45:33, 46:21~46:33, 47:41~47:53, 52:46~52:52 |
| V3 | [발헤임#1[첫번째 보스 에이크쉬르]](https://www.youtube.com/watch?v=1oZHseJVWMU) | 김이지 / 2024-07-11 / 1:49:07 / 한국어 | 솔로 첫 방송 VOD, 패드, **한국어 UI**. **시청자 채팅이 힌트를 줌.** 처치까지 진행 | 자막 전체<br>360p 30초 간격 218프레임<br>720p 구간 28개: 1:34~3:35, 4:00~4:15, 5:20~5:30, 9:15~9:25, 20:25~20:45, 23:50~24:00, 25:55~26:10, 27:40~27:55, 38:30~38:45, 39:50~40:05, 42:35~42:45, 51:25~51:40, 52:50~53:05, 54:05~54:15, 1:16:25~1:16:40, 1:17:40~1:18:30, 1:21:40~1:21:55, 1:26:45~1:26:55, 1:28:00~1:28:10, 1:29:30~1:29:45, 1:37:55~1:38:10, 1:40:50~1:41:00, 1:44:10~1:44:45 |
| V4 | [실수로 보스를 불러버렸다 \| 발헤임 1일차](https://www.youtube.com/watch?v=6226AodkzBw) | 소판돈PC방 / 2026-08-27 / 8:45 / 한국어 | 3인 협동(금색곱슬, TOMATO, 촬영자), 키보드, **한국어 UI**, 편집본. 처치까지 진행 | 자막 전체<br>720p 10초 간격 53프레임<br>원본 해상도 프레임 26장: 0:30, 1:10, 1:42, 2:20~3:10, 3:30~3:58, 4:00, 5:10~5:50, 6:20, 6:40, 7:50, 8:00, 8:30 |
| V5 | [Valheim 1.0 - Eikthyr bossfight (default difficulty settings, co-op)](https://www.youtube.com/watch?v=cB7faj6eohA) | gaki.gaming / 2026-09-30 / 3:07 / 영어 UI | 2인 협동 보스전만 담음. **처음 하는 사람인지 불확실.** 자막 없음 | 360p 5초 간격 37프레임<br>720p 프레임: 0:20, 0:31, 0:40, 0:47, 1:15, 1:36, 2:05, 2:22, 2:40, 2:45 |
| V6 | [PLAYING VALHEIM FOR THE FIRST TIME -- Valheim blind playthrough (co-op) -- Ep. 1](https://www.youtube.com/watch?v=t6ssXshDOHI) | lil indigestion / 2023-08-08 / 1:01:45 / 영어 | 부부 2인, **둘 다 완전 블라인드**. 1화 안에 보스까지 가지 못함 | 자막 전체<br>720p: 12:31~12:37, 54:41~54:53, 58:51~59:03 |
| V7 | [I Played Valheim For The First Time In 2026](https://www.youtube.com/watch?v=iCcFJjGsK54) | Huestale / 2026-07-28 / 13:57 / 영어 | 솔로 블라인드. 3시간 플레이를 편집함. 처치까지 진행 | 자막 전체<br>720p: 5:21~5:33, 6:26~6:32, 7:11~7:17 |
| V8 | [Valheim Coop Episode 1 - First Boss](https://www.youtube.com/watch?v=jUynBlg2rBk) | Sovereign / 2021-03-25 / 15:57 / 영어 | 3인 협동, **일부 경험자** | 자막만 |
| V9 | [Eikthyr \|\| Valheim [Co-op] [Episode 1]](https://www.youtube.com/watch?v=HSiuckR5tUQ) | AbbyInc / 2021-02-25 / 13:26 / 영어 | 2인, 파트너가 안내함 | 자막만 |
| V10 | [[발헤임01]초보 바이킹과 첫 번째 보스 에이크쉬르](https://www.youtube.com/watch?v=NHLCvgGkovI) | Foreigner Lee / 2021-04-03 / 10:43 / 한국어 | 솔로 편집본 | 자막만. 자동 자막 품질이 나빠서 화면 글을 읽어 준 부분만 썼다 |

### 받았지만 쓰지 못한 영상

[발헤임 멀티 1일차](https://www.youtube.com/watch?v=kNRq_KMTI0M)(랜선남매, 2021-07-04, 2:17:31)와 [1보스 에이크쉬르](https://www.youtube.com/watch?v=I_5OwQw6Dzk)(2021-07-11)는 자동 자막이 의미 없는 글자로 깨져 있었다. 프레임도 보지 않았다.

### 버전

- 2026년 영상 V1, V2, V4, V5, V7은 1.0 빌드다.
  - 근거: 크래프팅 창에 `Parry adrenaline` / `반격 아드레날린`이 있다(SEEN V1 6:39, V4 3:10).
  - 근거: 에이크쉬르 힘에 `Swim stamina usage`가 있다(SEEN V1 1:22:15).
- V3(2024)은 1.0 이전 빌드다.
  - 힘 설명에 달리기와 점프만 있다(SEEN V3 1:44:37).
  - 스탯 이름이 `방어구 차단`이다(SEEN V3 9:19).

## 2. 첫 플레이 타임라인: 스폰에서 에이크쉬르 처치까지

### 2.1 영상별 소요 시간

| 영상 | 처치 시점 | 게임 날짜 | 사망 | 비고 |
|---|---|---|---|---|
| V1 | 편집 1:20:34. 실시간 3시간 이상("I've been playing for 2 hours" HEARD 0:54:58) | "Day 6"(HEARD 1:18:33) | 4~5회 | 36:20에 준비 없이 소환했고, 이후 보스가 계속 따라옴 |
| V3 | VOD 1:37:56 | "2일차"(HEARD 0:33:03) 다음 날 | 2회(나무 1:08:32, 보스 약 1:29) | 첫 도전은 음식 1개로 죽었다. 채팅이 "음식 세 가지"를 알려 줌(HEARD 1:28:39) |
| V4 | 편집 약 7:46 | 제목은 "1일차" | 1회 이상 | 집 근처에서 실수로 소환했고 집이 부서짐 |
| V7 | 편집 11:49. 실시간 약 3시간("After 3 hours" HEARD 12:53) | ? | 0(보스) | 사슴 쫓기와 망치 모름으로 약 1시간 허비. 갑옷 없이 활로 첫 시도에 잡음 |
| V2 | 편집 47:52 | 2일째 아침(43:25에 잠) | 0(보스) | 경험자가 이끌었다. 활과 화살 73발(HEARD 42:08) |
| V5 | 소환 0:31 → 처치 약 2:40(전투 약 2분) | ? | 0 | 음식 3개, Rested, 나무 타워 실드 |
| V6 | 1시간 안에 가지 못함 | 1~2일 | 1회(나무) | "about one hour away from being able to take it on"(HEARD 1:00:16) |

### 2.2 단계별 흐름

| # | 단계 | 전형적 시점 | 계기 | 쓴 정보 | 근거 |
|---|---|---|---|---|---|
| 1 | 발키리에 실려 도착, 희생석 원 안에 떨어짐 | 0분 | 컷신 | 오프닝 텍스트를 읽음. 비가 오면 `몸이 젖었습니다`가 뜸 | HEARD V3 0:00~1:34. HEARD V6 1:52 |
| 2 | 후긴이 말을 걸고, 베그비시르에서 위치 등록 | 0~3분 | 후긴 머리 위 노란 `!` | 후긴 대사: "열 번째 세계에 온 것을 환영한다, 전사여… 주변에 있는 거석들은 희생석이라고 부른다…"<br>베그비시르 hover: `Vegvisir Eikthyr [E] Register location`<br>베그비시르 문구: "이 돌을 가까이서 살펴보면, 에이크쉬르, 그대의 첫번째 사냥감의 소환 장소를 들어낼 것이다…" | SEEN V4 0:30. SEEN V1 0:39. SEEN V3 2:39 |
| 3 | 희생석 문구 읽기("His antlers are branches of iron…") | 1분 | 호기심 | 보스가 뿔 달린 큰 사슴이라는 것만 앎 | HEARD V1 1:04, V7 1:04 |
| 4 | 주먹질, 나뭇가지와 돌 줍기 | 1~5분 | 후긴 "Just pick things up… stone axe out of wood and stone" | hover 이름과 `[E]` 프롬프트. 큰 통나무는 hover가 `Log`뿐이라 주울 수 없음 | HEARD V1 2:51~3:31. SEEN V1 3:29 |
| 5 | 첫 적 조우(그레이링, 멧돼지) | 2~5분 | 갑자기 다가옴 | 머리 위 이름 `Greyling`/`어린 회색 난쟁이`, 빨간 `!`, 빨간 체력바 | SEEN V1 2:14. SEEN V3 26:02. HEARD V6 9:28 |
| 6 | 라즈베리를 먹고 음식 개념을 알게 됨 | 3~5분 | 후긴 "A tasty morsel!" | 왼쪽 아래 음식 아이콘과 남은 시간(10m) | SEEN V1 4:04. HEARD V1 4:13 |
| 7 | 몽둥이 → 돌도끼 | 6~15분 | 나무나 돌을 처음 줍는 순간 `새로운 제작법 몽둥이` | 제작 창에 아는 레시피만 나옴. 돌을 줍기 전에는 Torch와 Club 둘뿐 | SEEN V1 6:39. SEEN V3 5:24, 9:19 |
| 8 | 첫 밤, 추위 | 10~25분 | 화면이 어두워짐, 후긴 "Be wary of the weather" | 상태 `Cold`/`추위`, `Wet`/`젖음`, 왼쪽 위 `춥습니다` | SEEN V1 9:57. SEEN V3 26:02 |
| 9 | 첫 사망과 시체 회수 | 10~70분 | 밤의 그레이링이나 쓰러지는 나무 | 지도 위 해골 표시, `No skill drain 9:49`, 묘비 `Here rests Bryce` | SEEN V1 11:15, 12:09. HEARD V1 12:10. HEARD V6 11:32 |
| 10 | **망치 제작(막히는 지점)** | 14분~1시간 이상 | 후긴 다시 읽기, 동료의 말, 우연 | `New build piece Workbench / Cooking Station…`, `11 New unlocks in message log.` | SEEN V7 6:29. SEEN V1 40:30. HEARD V7 3:14, 6:25 |
| 11 | 모닥불, 요리대 | 망치 직후 | 추위, 생고기 | `모닥불 돌 5 나무 2`. 요리대는 불 위에 있어야 함 | SEEN V3 27:47. HEARD V6 38:31. HEARD V1 44:50 |
| 12 | 작업대 + 벽과 지붕 | 망치 후 수십 분 | 작업대를 쓰려 하자 `The crafting station needs a roof` | 지붕 판정은 상태 아이콘 `Shelter`/`피난처`로 확인함 | SEEN V1 45:14, 1:01:07. HEARD V3 39:53. SEEN V3 38:34 |
| 13 | 침대(리스폰 지점), 상자 | 작업대 후 | 후긴 "if you wish you were home… building a bed"(사망 시 대사) | `Can't sleep at this time`, "This bed needs to be placed near a fire" | HEARD V1 1:00:51~1:01:11, 1:11:30. HEARD V6 19:32 |
| 14 | 사슴 사냥: 가죽, 트로피, 고기 | 수시로 | 레시피(가죽 갑옷, 활), 소환 조건 | 사슴 이름 위 빨간 `!`가 뜨면 도망감. 웅크리면 조준점에 눈 모양 표시 | SEEN V3 52:57. SEEN V1 9:34. HEARD V7 5:21~6:04 |
| 15 | 보스 제단 찾아가기 | 35분~1시간 15분 | 지도 아이콘, "그냥 보러 가자" | 큰 지도의 뿔 아이콘(`에이크쉬르`), 미니맵 | SEEN V3 51:32. HEARD V1 20:54, 35:19. HEARD V2 9:57 |
| 16 | 제단에서 후긴 대사, 룬스톤 문구 | 제단 도착 | 후긴 `!` | "Calling forth the beast / 짐승을 부르게: 버려진 자 중 하나를 소환할 수 있는 제단을 찾았군…", 룬스톤 hover `그의 일족을 사냥해라`, 돌 위 사슴 조각상 | SEEN V1 35:57. SEEN V3 1:16:38. SEEN V4 2:50 |
| 17 | 제물 시도와 실패 메시지 | 제단 | 제단 hover `신비로운 제단 [1-8] 아이템 제안` | `아무 일도 일어나지 않았다`(멧돼지 트로피), `미완성 제물: 사슴의 트로피 1 / 2` | HEARD V3 1:17:27~1:18:19. SEEN V4 3:10. SEEN V7 5:33 |
| 18 | 소환과 전투 | 트로피 2개를 모은 즉시(준비 없이 하는 경우가 많음) | `You make the sacrifice`, `Removed Deer Trophy x2` | 화면 위쪽 보스바 `EIKTHYR`/`에이크쉬르` | SEEN V1 36:33, 36:49. SEEN V4 3:30 |
| 19 | 처치와 전리품 | — | 쓰러진 보스 | `트로피 수집 완료 에이크쉬르의 트로피`, `추가된 사슴의 단단한 뿔` | SEEN V4 8:00. SEEN V3 1:37:59 |
| 20 | 희생석에 트로피를 걸고 힘 받기 | 처치 후 바로 | 후긴 "Return to the sacrificial stones with your Forsaken trophy" | 잘못 고르면 `이 아이템은 부착할 수 없습니다`. 성공하면 `힘을 얻었습니다`. 툴팁 `달리기 스태미나 소모도: -60%` | HEARD V1 1:21:18. SEEN V3 1:44:17, 1:44:37. SEEN V1 1:22:15 |

### 2.3 제작·건설 순서

| 영상 | 순서 |
|---|---|
| V1 | 몽둥이(6:59) → 돌도끼(14:56) → **망치(40:15)** → 작업대(42:26) → 벽과 지붕(45~57분) → 누더기 바지·튜닉(57:25) → 침대(1:00:51) → 모닥불과 요리대(1:03:45, 돌 부족으로 늦어짐) → 부싯돌 창(1:06:15) |
| V3 | 몽둥이 레시피(5:23) → 돌도끼(9:17) → 망치(16:24) → 모닥불(26:29~29:06) → 요리대(29:52) → 폐허 안 작업대(39:32) → 벽과 지붕(40~48분) → 부싯돌 창(약 56분) → 나무 방패, 부싯돌 도끼(1:07:47) → 보스. 활은 없었다 |
| V6 | 돌도끼(8:46) → 망치와 몽둥이(13:56) → 작업대(17:45) → 침대 2개(19:32) → 모닥불(20:53) → 요리대(25:42) → 괭이(42:43) → 상자(52:35). 활은 가죽이 모자라 미룸(51:54) |
| V7 | 돌도끼(2:32) → 사슴을 맨손과 근접 무기로 쫓으며 약 45분 → **망치(6:25)** → 작업대와 벽(7:07) → 활과 요리대(8:32) → 보스(9:13) |
| V2(안내받음) | 모닥불(14:29) → 요리대(15:12) → 작업대(18:34) → 집(21~35분) → 부싯돌 도끼(30:13) → 몽둥이(36:21) → 조잡한 활과 화살(38:57) → 보스(45:15) |

공통 순서는 이렇다.

```
줍기 → 몽둥이/돌도끼 → 망치 → (모닥불·요리대) → 작업대 + 지붕 → 침대
     → 가죽(멧돼지)·사슴 → 창/방패/활 → 음식 3개 → 보스
```

### 2.4 재료 출처 (영상에서 확인한 것)

| 재료 | 출처 |
|---|---|
| 나무 | 땅의 나뭇가지<br>주먹이나 도끼로 너도밤나무(Beech, `너도 밤나무`)<br>자작·참나무는 `too hard`라고 했다(HEARD V6 9:07, V1 7:59). 한국어 해설: "자작나무는 딴딴해서 안 돼"(HEARD V3 40:36) |
| 돌 | 땅에 떨어진 작은 돌만 주울 수 있다. 큰 바위는 곡괭이가 필요하다("Need to be mining. Too hard." HEARD V1 7:59)<br>돌이 귀하다는 불평이 흔했다(HEARD V3 13:13, V1 58:27) |
| 부싯돌 | 물가·강가("flint near the river" HEARD V1 12:52, "near shoreline" HEARD V2 8:25)<br>줍자마자 `New crafting recipe`가 3개 뜸(SEEN V6 54:47) |
| 송진 | 그레이링 처치(HEARD V1 4:56, 19:33) |
| 가죽 조각 | 멧돼지("leather scraps only from pigs" HEARD V8 6:12) |
| 사슴 가죽·고기·트로피 | 사슴(SEEN V3 54:09 `추가된 사슴 가죽 x2`, `새로운 재료 사슴 고기`, `새로운 건설 조각 무두질 받침대`) |
| 음식 | 라즈베리, 버섯, 민들레(채집)<br>넥 꼬리(물가의 넥) |
| 동전·화살·호박·깃털 | 폐가 상자(HEARD V1 28:00, V6 36:03) |
| 뼈 조각 | 해골 잔해(HEARD V3 38:01) |

### 2.5 제단을 어떻게 찾았나

- **베그비시르 등록 → 지도 아이콘으로 찾은 경우가 대부분이다.**
  - V1, V3, V6은 처음엔 지도의 사망 해골 아이콘과 보스 아이콘을 헷갈렸다. V1: "the horned creature on the map is what I'm looking for"(HEARD V1 20:54).
  - V6은 50분 지나서야 "there's a thing over here that means map location… tells us where Eikthyr is"라고 다시 떠올렸다(HEARD V6 53:38).
  - 큰 지도에는 이름이 붙은 보스 아이콘이 있고 버튼 `핀 추가 / 크로스오프 핀 / 핀 제거 / 핑 / 다른 플레이어에게 보이기`가 있다(SEEN V3 51:32).
- **"싸울 생각은 없고 보기만 하겠다"며 미리 가 보는 경우가 많다.**
  - "I don't want to fight him yet. I just want to see."(HEARD V1 1:25)
  - "보스를 빨리 봐야 좀 뭐가 느낌이 올 거 같은데"(HEARD V3 1:06:09)
- 우연히 마주친 경우도 있다(V7 3:59 "Wait, is this one of the bosses here?").
- V4 일행은 우연히 제단 근처에 집을 지었다. 그 결과 소환하자마자 보스가 집을 부쉈다(HEARD V4 3:53~4:56).

### 2.6 소환 조건을 어떻게 알았나

1. **제단의 후긴 대사는 "조건에 맞는 아이템"이라고만 한다.** 무엇인지는 말하지 않는다(SEEN V3 1:16:38, V1 35:57).
2. **제단 옆 룬스톤에 "그의 일족을 사냥해라" / "Hunt his kin"이 있다.**
   - SEEN V4 2:50(빨간 글씨 hover)
   - HEARD V7 3:59, V9 9:42
   - V1은 바로 "A deer. Hunt his kin. Also, I need to kill a deer."라고 해석했다(HEARD V1 36:00).
3. **제단 돌 위에 사슴 조각상이 있다.** SEEN V1 35:57. V3에서는 시청자가 "사슴 석상"이라고 알려 줬다(SEEN V3 1:18:24 채팅).
4. **시도해서 실패 메시지를 본다.**
   - 멧돼지 트로피를 올리면 `아무 일도 일어나지 않았다`(HEARD V3 1:17:56).
   - 사슴 트로피 1개면 `미완성 제물: 사슴의 트로피 1 / 2`(SEEN V4 3:10, V7 5:33). 이 메시지로 수량을 알았다("두 개 필요해" HEARD V4 2:51).
5. **혼동 사례**
   - 스폰 희생석에 사슴 트로피를 걸려다 `You can't attach this item`이 떴다. 그다음 "we have to do better than a deer"라고 잘못 결론 냈다(SEEN V6 58:57, HEARD V6 58:54~59:14).
   - V3는 처치 후 트로피 걸 곳을 찾느라 다른 돌에서 `이 아이템은 부착할 수 없습니다`를 봤다(SEEN V3 1:44:17).
6. 경험자가 말로 알려 준 경우도 있다("kill like two deer… place them on the podium" HEARD V2 10:38).

### 2.7 보스전 전술

| 전술 | 근거 |
|---|---|
| 음식 3칸을 다 채우고 싸운다. 체력이 커지고 회복이 빨라진다 | V3의 첫 도전은 음식 1개라 체력 19에서 죽었다(SEEN V3 1:28:04). 음식 세 개를 먹은 두 번째 도전은 "체력도 많아지고 회복량도 커져 가지고… 가장 큰 팁"(HEARD V3 1:39:06)<br>V5는 음식 3개에 체력 100(SEEN V5 0:20) |
| 활로 거리를 둔다 | V4 3인 모두 활(SEEN V4 6:20, 6:40)<br>V2 화살 73발(HEARD 42:08)<br>V7은 갑옷 없이 활로 처치(HEARD 10:16~11:49) |
| 근접은 두 번 때리고 빠진다 | "only taking two shots there and then backing up"(HEARD V1 1:17:44)<br>"squeeze in a couple of hits… don't get greedy"(HEARD V9 10:04) |
| 번개는 옆으로 피한다. 바위 뒤에 숨어도 맞는다 | "번개 이렇게 옆으로 피하면 된다"(HEARD V4 6:00)<br>"I wasn't safe behind the rock"(HEARD V1 37:25)<br>"it still hit me even though I'm standing behind a rock"(HEARD V8 14:34) |
| 스태미나를 관리하고 구르기를 쓴다 | "스태미나가 되게 중요하네요"(HEARD V3 59:53, 1:32:43)<br>"스태미나 없으니까 땡기다 망하네"(HEARD V4 6:43)<br>V2 "hold left bumper and B, you can roll"(HEARD 46:43) |
| 방패로 막는다 | V3 나무 방패와 창(SEEN V3 1:16:32, 1:26:49)<br>V5 나무 타워 실드와 몽둥이로 앞에서 받아 냄(SEEN V5 1:15~2:40) |
| 쓰러지는 나무에 주의하고, 끝나면 나무를 줍는다 | "He's knocking so many trees down. I'm going to get so much wood"(HEARD V1 1:09:47)<br>"통나무가 되게 불안한데"(HEARD V3 1:35:58) |
| 보스를 집에서 떼어 놓는다 | "I'm trying to drag this fight away from the house"(HEARD V1 1:14:51) |
| 협동에서는 한 명이 어그로를 끌고 나머지가 쏜다. 좌우로 갈라 돈다 | "최고의 탱커야"(HEARD V4 5:40)<br>"지형 내가 왼쪽으로 돌게. 너 오른쪽으로"(HEARD V4 6:00)<br>V5: 타워 실드 탱커 1명과 측면 근접 1명(SEEN V5 2:40) |
| 공략 사실(위키·가이드) | 체력 500. 사슴 트로피 2개. 공격은 근접 뿔, 전방 번개 돌진, 주변 번개 발구르기. 드롭은 트로피와 단단한 뿔 3개. 힘은 달리기·점프·수영 스태미나 -60%, 5분([Nodecraft, 2026-09-27 갱신](https://nodecraft.com/support/games/valheim/general/valheim-boss-guide-eikthyr)) |

### 2.8 보스 소환 후 행동 (영상에서 본 것)

- 준비 없이 소환하면 사람은 죽은 뒤 장비를 찾으러 간다. 그사이 에이크쉬르는 제단에 머물지 않고 스폰이나 집 근처를 배회한다.
  - "He's gatekeeping spawn"(HEARD V1 41:46)
  - "I thought he'd stay in his little area"(HEARD V1 41:46)
- 보스 체력은 플레이어가 죽어도 회복되지 않는다.
  - "his health doesn't regen"(HEARD V1 1:11:30)
  - "아까 때린 거 유지돼 있네요"(HEARD V3 1:29:24, SEEN V3 1:29:37 보스바가 깎인 채 남음)
- 사람은 이것을 "죽어 가며 조금씩 깎는" 전략으로 썼다(V1 1:11~1:20, 사망 여러 번).

## 3. 지각 채널 목록

| 채널 | 언제 나타나나 | 보여 주는 것 | 한국어 UI 예 | 근거 |
|---|---|---|---|---|
| 조준점 hover 텍스트 | 시선 레이가 상호작용 대상에 닿고 눈에서 5m 안 | 대상 이름과 키 프롬프트 | `후긴 [E] 대화하기` / 패드 `(A) 대화하기`<br>`나무 대문 [E] 열기`<br>`상자 [E] 열기 (길게 눌러 묶음으로 만들기)`<br>`상자 ( 비어 있음 )`<br>`신비로운 제단 [1-8] 아이템 제안`<br>`희생의 돌 (A) 읽기` | SEEN V4 2:40, 2:50, 3:10, 3:52<br>SEEN V3 1:44:17<br>거리는 REPO `docs/api/1.0.16.md`(`m_maxInteractDistance` 5) |
| hover인데 행동이 없는 것 | 위와 같음 | 이름만 | `Log`, `Beech`, `Too far`(건설 중 멀 때) | SEEN V1 3:29, 45:14<br>SEEN V2 2:19 |
| 생물 머리 위 이름·체력바 | 로컬 플레이어 10m 안(보스 100m). 마지막 hover 후 60초 유지 | 이름, 빨간 체력바, 별(레벨), 경계 표시 | `어린 회색 난쟁이`, `사슴`(옆에 ★) | SEEN V3 26:02, 52:57<br>SEEN V1 2:14, 9:34, 17:06<br>거리 규칙 REPO `docs/api/1.0.16.md` `EnemyHud` |
| 경계 표시 | 생물이 플레이어를 인지했을 때 | 빨간 `!`(달려들거나 도망치는 중). 노란 `((•))`(소리를 듣고 살피는 것으로 추정) | 기호뿐 | SEEN V1 2:14(그레이링 빨간 !), 17:06(넥 노란 ((•)))<br>SEEN V3 52:57(사슴 빨간 !, "느낌표 안 떴어" HEARD 51:43) |
| 다른 플레이어 이름표 | 항상(웅크리면 숨겨짐) | 이름과 초록 체력바 | `금색곱슬`, `TOMATO` | SEEN V4 0:30, 3:40, 6:20<br>SEEN V2 14:34(밤, 멀리서도)<br>REPO `EnemyHud` |
| 보스 체력바 | 보스가 경계 상태로 가까이 있을 때 | 화면 위 가운데에 이름과 큰 빨간 바 | `에이크쉬르` | SEEN V4 3:30, 6:40<br>SEEN V3 1:28:04 |
| 피해 숫자 | 타격 순간 | 흰색 숫자(보통), 초록 `+N`(회복 틱)<br>노랑=약점, 회색=내성(영상 프레임에서는 확인하지 못함) | `5.2`, `14.5`, `+2`, `+7.5` | SEEN V3 5:24, 1:28:04<br>SEEN V4 6:40<br>SEEN V5 1:15<br>색 규칙은 [Gamepressure](https://www.gamepressure.com/valheim/combat/zee2f1) |
| "too hard" 류 텍스트 | 도구 등급이 모자란 나무나 바위를 칠 때 | 짧은 텍스트 | 한국어 문구는 프레임으로 확인하지 못함 | HEARD V6 9:07, V1 7:59<br>REPO `protocol/PROTOCOL.md` `damage_dealt.type=too_hard` |
| 화면 가운데 큰 노란 메시지 | 행동 실패나 중요 사건 | 한 줄 | `미완성 제물: 사슴의 트로피 1 / 2`<br>`이 아이템은 부착할 수 없습니다`<br>`힘을 얻었습니다`<br>`죽었습니다!`<br>`+7 체력 +20 스태미나`(먹을 때)<br>`You make the sacrifice`<br>`The crafting station needs a roof` | SEEN V4 3:10, 3:54, 약 3:40~3:50(썸네일)<br>SEEN V3 1:44:17, 1:44:37<br>SEEN V1 36:33, 45:14 |
| 왼쪽 위 알림 | 줍기, 해금, 상태 진입 | 획득 수량과 해금 카드 | `추가된 나무 x2`<br>`새로운 재료 / 나무`<br>`새로운 제작법 / 몽둥이`<br>`새로운 건설 조각 / 나무 바닥 2x2`<br>`트로피 수집 완료 / 에이크쉬르의 트로피`<br>`1 신규 아이템 메시지 로그에 기록`<br>`피난처에 들어왔습니다`<br>`노출되었습니다`<br>`춥습니다` | SEEN V3 5:24, 39:57, 54:09, 1:37:59, 38:34, 26:02<br>SEEN V4 5:30<br>SEEN V1 29:15(`You are exposed`) |
| 번역되지 않은 토큰 | 후긴 글이 백과사전에 등록될 때 | 원시 레이블 | `[tutorial_stemple1_label]이(가) …에 추가되었습니다`<br>`[tutorial_altar_label]이(가) 백과사전에 추가되었습니다` | SEEN V4 0:30(2026)<br>SEEN V3 1:16:38(2024)<br>영어판은 `Hugin: Cold added to the compendium`(SEEN V1 9:57) |
| 채팅·외침 | 다른 플레이어가 말하거나 스폰할 때 | 왼쪽 위 노란 글씨 `이름: 내용` | 예 `Dag: I HAVE ARRIVED!` | SEEN V2 45:27 |
| 후긴 | 튜토리얼 조건 충족 시(처음 줍기, 첫 밤, 첫 사망, 망치·작업대 제작, 방패, 제단 도착). 3m 안에 들어가면 자동으로 말함 | 머리 위 노란 `!`(멀리서도 보임), 굵은 제목과 본문 | 제목 `짐승을 부르게`, 본문 `작업대를 지었군. 작업대는 좀 더 복잡한 아이템을…`, 짧은 말 `반갑네.` | SEEN V3 1:38, 3:27, 39:57, 1:16:38<br>SEEN V1 4:04, 9:57, 35:57<br>REPO `docs/api/1.0.16.md`(`Raven` 3m) |
| 룬스톤 | 다가가서 읽기 | 빨간 글씨 로어(힌트 섞임) | `여행자여, 기다려라… 목초지를 떠나지 말고, 집은 나무에서 멀리 지으라. 뿔이 난 것을 두려워하고…` | SEEN V3 20:32<br>SEEN V1 17:34<br>HEARD V1 17:46, 31:49, 1:02:36 |
| 희생석과 베그비시르 | 스폰 원 | 보스별 거석. 빨간 룬 판. 위치 등록 | `Vegvisir Eikthyr [E] Register location`, `이 돌은 베그비시이다…` | SEEN V1 0:39<br>SEEN V3 2:39 |
| 제단 | 보스 제단 | 제단 돌, 옆 룬스톤, 사슴 조각상 | `신비로운 제단`, `그의 일족을 사냥해라` | SEEN V4 2:50<br>SEEN V1 35:57 |
| 체력 | 항상(왼쪽 아래) | 빨간 세로 바와 숫자 | `25`, `4`(위험) | SEEN V1 1:10:54(4)<br>SEEN V3 1:28:04(19) |
| 스태미나 | 소모 중일 때 화면 아래 가운데 | 노란 가로 바와 숫자 | `45` | SEEN V4 3:30<br>SEEN V3 5:24 |
| 음식 칸 | 먹은 뒤 | 아이콘 최대 3개와 남은 시간 | `10m`, `54s` | SEEN V1 6:39, 9:34<br>SEEN V3 1:37:59(3칸) |
| 상태 효과 | 미니맵 왼쪽 | 아이콘, 이름, 타이머 | `젖음 1:27`<br>`추위`<br>`불`<br>`피난처`<br>`휴식중 편안함:4`<br>`휴식함 11:00`<br>`스킬 저하 임시 면역`<br>영어 `Corpse run 18`<br>힘 `에이크쉬르 3:48` | SEEN V4 1:10, 2:40, 8:30<br>SEEN V3 1:16:32<br>SEEN V1 1:20:42 |
| 미니맵과 바이옴 이름 | 항상(오른쪽 위) | 지형, 마커, 바이옴 이름 | `목초지` | SEEN V4 전 프레임 |
| 큰 지도 | `M` | 탐험한 곳, 보스 아이콘, 핀, 다른 플레이어 | `다른 플레이어에게 보이기` 토글 | SEEN V3 51:32<br>HEARD V2 2:34, V6 54:22, V8 0:45 |
| 제작 창 | `Tab` | **이미 아는 레시피만** 보임. 재료 칸에서 부족한 것은 빨간색. 무게 `16/300` | `제작`, `횃불 / 돌 도끼 / 몽둥이 / 망치`, `나무를 베는 데 사용하는 조잡한 도끼입니다.` | SEEN V1 6:39(Torch·Club 둘뿐)<br>SEEN V3 9:19<br>SEEN V4 4:00 |
| 작업대 창 | 지붕 있는 작업대에서 `E` | 레벨(★1), 제작·업그레이드 탭, 목록 | `WORKBENCH`, `Rag Tunic, Flint Knife, … Crude Bow, Wood Shield…` | SEEN V1 57:32 |
| 건설 배치 UI | 망치를 들고 우클릭 | 조각 이름, 재료, 필요 작업대, 키 안내 | `모닥불 돌 5 나무 2`<br>`나무 벽 나무 2 작업대`<br>`초가지붕 용마루 45°`<br>키: `배치 / 제거 / 건설 메뉴 / 스냅핑 옵션 토글 / 스냅핑 전환 / 복사 / 회전` | SEEN V3 27:47, 42:39<br>SEEN V4 2:20 |
| 아이템 툴팁 | 인벤토리 hover | 음식 효과 | `요리한 멧돼지 고기 / 체력: 30 / 스태미나: 10 / 지속 시간: 20m / 치유: 2 hp/tick` | SEEN V3 1:21:47 |
| 불 상호작용 | 모닥불 hover | 연료와 키 | `Fire (Fuel 1/10) [E] Use Wood [1-8] Use item` | SEEN V1 1:04:17 |
| 스킬 상승 | 행동 반복 시 | 캐릭터 주변 노란 글씨와 왼쪽 위 | `Skill improved Axes: 2` | SEEN V1 17:34<br>HEARD V6 13:36 |
| 업적·트로피 팝업 | 보스 처치 | 큰 아이콘 | `Eikthyr`, `Stronger Together`(친구와 함께 처치) | SEEN V5 2:45 |
| 소리(해설로만 확인) | 상시 | 숲속 움직임, 밤 음악, 사슴 울음, 보스 등장 음악 | — | HEARD V1 1:25 "I can hear something moving around in the trees", V6 43:23 "music is starting to freak me out", V3 56:35 "개 우는 소리… 사슴 오는 소리였어", V1 1:15:13 "The music just starts again" |

## 4. 결정 패턴

### 4.1 처음 보는 생물

- **이름표를 읽고 이름을 부른다.**
  - 처음엔 생김새로 추측한다. 그다음 이름표로 고친다. "뭐야 고블린"(HEARD V3 5:44) → "난쟁이라고 나왔는데 고블린이 아니고"(HEARD V3 41:17).
  - "넥이라는 애가 있네요. 개구리인가"(HEARD V3 1:00:56).
  - "Greyling. I'm going to punch him."(HEARD V1 2:11)
- **일단 때려 본다.**
  - 피해 숫자를 보고 상대가 강한지 판단한다.
    - "Dude, I'm hitting this thing for zero"(HEARD V7 2:09)
    - "I do no damage to that thing. There's not even a chance"(트롤, HEARD V2 1:01:01)
  - 상대가 강하면 바로 물러난다. "Let's just leave him"(HEARD V2 1:04:04).
- **"이거 우호적인가?"라고 묻는다.**
  - "Are they friendly? It doesn't seem like he wants to attack me… Maybe fire scares all creatures"(HEARD V1 19:33~19:54)
  - "is it like a tree protector?"(HEARD V6 9:50)
- **룬스톤으로 생물 지식을 얻는다.**
  - 멧돼지는 불을 무서워하고 길들일 수 있다(HEARD V1 18:09).
  - 넥 꼬리는 맛있다(HEARD V1 31:49).

### 4.2 작업 중 공격당함

- **무기로 바꿔 든다.** "Equip. Let's go then grey dwarf"(HEARD V1 26:57). 도구가 깨지면 auto-run으로 도망치면서 새 몽둥이를 제작한다(HEARD V1 26:33).
- **짜증을 내면서도 작업을 멈춘다.**
  - "No Grayling, leave me alone, I'm constructing"(HEARD V9 3:54)
  - "Go away, grayling. Not the time."(HEARD V1 1:10:30, 보스전 중)
- **협동이면 동료를 부른다.**
  - "You under attack?" "Yeah, there's a skeleton." "I'm here"(HEARD V2 19:22)
  - "Do you need help?" "I think I'm okay"(HEARD V6 26:22)

### 4.3 체력이 낮을 때

- **먼저 먹으려 한다.** 이미 먹은 음식이면 안 된다.
  - "Eat more raspberries… You can't eat any more raspberries"(HEARD V1 23:41)
  - 한국어: `더 먹을 수 없어` → "저 9라고 써 있는게 혹시 분이야? 9분 뒤에 먹을 수 있다고"(HEARD V3 35:34)
- **뒤로 빠지고 자연 회복을 기다린다.**
  - "Okay, we need some health… Come back to me, health"(HEARD V1 1:10:07)
  - "피 좀 치우고 싸우자"(HEARD V3 1:36:25)
- **협동이면 상대 체력을 묻고 맞을 사람을 정한다.**
  - "How many health do you have?" "33." "I'll let you take the hits then"(HEARD V6 34:41)
  - "피 남았어 피 남았어"(HEARD V4 7:03)
- **장비가 별로 없으면 죽음을 비용으로 받아들인다.** "So be it if I die. I don't have enough stuff to be worried about dying yet."(HEARD V1 35:19)

### 4.4 밤

- **횃불을 꺼낸다.** "It's actually becoming night time now. I'm scared."(HEARD V1 9:43)
- **피난처를 찾거나 짓는다.**
  - 폐가: "Ah, shelter. Day two. At least I'm inside now."(HEARD V1 14:14)
  - V3는 폐허를 임시 거점으로 썼다(HEARD V3 39:10).
- **침대가 생기면 잔다.**
  - "we should go to bed, right? It's cold"(HEARD V6 44:46)
  - "you want to go to sleep in the morning?"(HEARD V2 43:25)
- **음악 변화로 위험을 감지한다.** "I wonder if more enemies come out at night, music is really starting to freak me out"(HEARD V6 43:23)

### 4.5 비와 젖음

- **젖은 것을 알아채고 이유를 궁금해한다.** "Why is my guy wet?"(HEARD V2 1:33). 상태 `젖음`에는 타이머가 있다(SEEN V4 1:10 `젖음 1:27`).
- **후긴이 젖음과 추위가 스태미나 회복을 줄인다고 알려 준다.** 사람은 불 옆으로 간다.
  - "when I stand close to the fire, the wet effect goes down way quicker"(HEARD V1 1:06:57)
  - "when you're by a fire you get un-wet faster"(HEARD V9 5:54)

### 4.6 음식 선택

- **처음엔 손에 잡히는 것을 먹는다.** 라즈베리, 버섯 순이다. 버섯은 먹어도 되는지 망설인다(HEARD V1 24:02 "I don't know what mushrooms do").
- **요리를 시작하면 툴팁 숫자로 비교한다.**
  - "멧돼지고기 체력 30 스태미나 10… 사슴이 돼지보다 상위… 넥 꼬리 25에 8"(HEARD V3 1:21:38~1:23:48)
  - 결론: "순서가 사슴, 멧돼지, 넥"
- **3칸 규칙은 늦게 알게 되거나 남에게서 배운다.**
  - V6은 같은 음식을 겹쳐 먹으려 했다(HEARD V6 35:43).
  - V3는 시청자 채팅에서 배웠다(HEARD V3 1:28:39).
- **요리 실수가 있다.**
  - 너무 오래 구워서 숯이 됐다(HEARD V1 1:04:29).
  - 요리대에 불이 없었다(HEARD V6 38:31).
  - 날고기를 불에 넣으려 했다(HEARD V9 3:54~4:14).
- **허기 신호는 "You could eat another bite"다**(HEARD V1 52:51, V9 4:14). 한국어판은 `뭔가를 더 먹을 수 있다`류로 들렸다(HEARD V3 56:13, 1:47:49).

### 4.7 인벤토리가 가득 찼을 때

- **먹어서 칸을 비운다.** "Inventory full. Oh, bollocks. Let's eat this. And then we can craft"(HEARD V1 1:06:15)
- **가치 낮은 것을 버린다.** "No room in inventory… I'll drop the dandelions"(HEARD V1 1:20:34, 보스 트로피를 주울 때)
- **무게 한도를 의식한다.**
  - "I've also got a carry weight limitation"(HEARD V1 18:51)
  - "무게한도 300"(HEARD V3 1:40:27). 화면에 `18/300` 표시(SEEN V4 3:10)
- **상자를 짓는다.** "we really need to get some storage… chest"(HEARD V2 50:13)

### 4.8 사망과 묘비

- **지도의 해골 표시를 보고 맨몸으로 시체를 찾으러 간다.**
  - "So, that skull on the map is where I dropped my stuff"(HEARD V1 11:30)
  - 묘비 hover: "Here rests Bryce"(HEARD V1 12:10)
  - 회수하면 `Corpse run` 버프(SEEN V1 1:20:42)
- **첫 사망 뒤에는 스킬 손실이 없어 안도한다.** "I didn't lose any skills because it was my first death"(HEARD V6 11:53). 실제로는 `No skill drain` 10분 버프다(SEEN V1 11:15 `9:49`).
- **협동이면 동료가 장비를 들고 온다.** "follow me, I have your stuff"(HEARD V6 11:32)
- **리스폰 위치를 깨닫는다.** 침대가 없으면 스폰 원이다. "리스폰 장소가 게임 처음에 나왔던 데인 거 보면 침대가 있으면 리스폰 위치를 바꿀 수 있나 보다"(HEARD V3 1:09:15)
- **사망 직후 게임을 껐다 켜서 되돌리려 했다.** 불러오기 기능은 없다(HEARD V3 1:28:39~1:29:02).

### 4.9 협동 분업

- **채집과 건설로 나눈다.**
  - "I'm cutting them for you"(HEARD V6 13:36)
  - "I can chop some trees for you to make it quicker"(HEARD V2 2:14)
  - 나무를 갖다 준다(HEARD V2 22:04 "Bro, I brought the wood to you")
- **도구를 만들어 주고 장비를 넘겨준다.**
  - "I'll build you a new one"(HEARD V2 20:47)
  - "Can you even make a flint axe? Cuz I can make you one"(HEARD V2 30:13)
  - "Here's your old hammer back"(HEARD V2 29:31)
- **탐색을 나눈다.** "Jonah head west and I'll head east"(HEARD V8 0:45). 반대로 한 명이 혼자 떠나서 갈등이 생기기도 한다(HEARD V6 28:25).
- **요리를 맡는다.** "I built a cooking rack… you can cook your meat"(HEARD V8 12:06). 한 사람이 둘 몫을 굽는다(HEARD V6 39:14~40:58).
- **위치를 공유한다.** 지도 `visible to other players`(HEARD V2 2:34, V6 54:22, V8 0:45)와 핑, 핀(HEARD V6 54:00).
- **보스전 역할: 탱커(어그로)와 원거리 딜러.**
  - "최고의 탱커"(HEARD V4 5:40)
  - V5 타워 실드 탱커(SEEN)
  - V9 "I'm trying to tank both of these guys… I'm coming"(HEARD 11:12)

### 4.10 한 사람이 다른 사람에게 하는 전형적인 말

| 종류 | 예 |
|---|---|
| 위치와 이동 | "Where are you?" / "I see you down there" / "Follow me" / "Let's go home" / "어디 가냐" / "가자 가자" |
| 경고 | "Watch out!" / "Timber!" / "Travis, they're on you" / "Get away from him" / "너한테 온다" / "도망가" / "나무 조심" / "그 주변으로 가면 안 돼" |
| 도움 요청과 제공 | "Do you need help?" / "I'm here" / "Here's some wood I got" / "Need some food? I got some food on me" / "How much leather do you have?" |
| 상태 확인 | "You good? You got food?" / "How many health do you have?" / "너네 어그로 끌려 있냐?" / "피 남았어" |
| 조작 가르치기 | "Tab 눌러보면 제작 있어"(HEARD V4 0:41) / "F 누르면 돼"(힘 사용, HEARD V4 8:09) / "if you right click the food you eat it"(HEARD V6 13:15) |
| 계획 | "So now our kind of mission is to get a home"(HEARD V2 11:26) / "let's get some bows and go hunt some deers"(HEARD V2 38:36) / "We can lowkey fight the deer boss right now if you want"(HEARD V2 41:46) / "저 에이크쉬르 있잖아. 거기 한번 가보자"(HEARD V4 2:31) |
| 발견 공유 | "There's a chest in here" / "I found a tin deposit" / "아 이게 보스들 힌트인가 보네"(HEARD V4 7:46) |

## 5. 처음 하는 사람의 실수와 회복

| 실수 | 사례 | 어떻게 회복했나 |
|---|---|---|
| 망치를 몰라 건설·불·침대를 못 함 | V7 약 1시간(HEARD 3:14, 6:25 "There is no way that I needed to make a hammer")<br>V1 영상 40분까지 | 후긴 대사를 다시 읽음: "I don't think I've really understood something about the crafting"(HEARD V1 39:13). 망치를 들자 해금 메시지가 쏟아짐(SEEN V1 40:30) |
| 쓰러지는 나무에 깔려 죽음 | V6 11:12<br>V3 1:08:32<br>V4 2:08 | 경험자가 경고함("Just be careful with the tree. They will kill you" HEARD V2 17:47)<br>"always stand uphill from the logs"(HEARD V6 16:42) |
| 등급이 맞지 않는 나무나 바위를 침 | V6 9:07, V1 7:59 "too hard" | 너도밤나무, 작은 돌로 바꿈 |
| 준비 없이 소환함 | V1 36:20(옷과 음식 부족)<br>V4(집 근처) | 사망 → 장비 회수 → 준비 → 재도전. 보스 체력이 남는 것을 이용함 |
| 잘못된 돌이나 트로피를 씀 | 스폰 희생석에 사슴 트로피(SEEN V6 58:57)<br>제단에 멧돼지 트로피(HEARD V3 1:17:56) | 실패 메시지를 보고 다른 것을 시도함 |
| 작업대에 지붕이 없음, 경사지에 건축 | V1 45:10~57:25(지붕 판정 맞추는 데 약 12분)<br>"maybe you just shouldn't build on a hill"(HEARD V1 52:23) | 평지로 옮김. 상태 `Shelter`로 확인함 |
| 작업대 위치를 잃어버림 | "I've completely lost where I put my crafting bench"(HEARD V1 43:48) | 하나 더 지음. 지도에 핀을 찍음(SEEN V3 51:32 "우리 집") |
| 스태미나가 없는데 강을 헤엄침 | V1 22:16~23:41(체력 6) | 운. 그 뒤로 "swimming is improved"를 확인하고 다시 건넘 |
| 음식 1개로 보스전 | V3 첫 도전에서 죽음 | 채팅으로 3칸을 배움. 3개 먹고 재도전해 처치 |
| 집 안의 불과 연기, 불에 서 있음 | "is my house on fire? It's smoking"(HEARD V7 8:32)<br>"I'm on fire"(HEARD V6 44:05) | 불을 옮기거나 창을 냄 |
| 벌집을 치다가 집을 부수고 독에 걸림 | V1 29:20~31:08 | 도망침. "I need like a ranged weapon" |
| 사슴을 근접 무기로 오래 쫓음 | V7 약 45분<br>V3 52:10~54:03 | 활이나 투창을 떠올림("역시 원거리가 있어야 되나" HEARD V3 53:21). 웅크려 접근함 |
| 트롤이나 검은 숲에 들어감 | V2 1:00:38~1:08:23<br>V9 4:39<br>V8 1:46 | 피해 숫자가 의미 없다는 것을 보고 도망침. 강을 건넘 |
| 지도 아이콘을 헷갈림 | 사망 해골을 보스로 착각(HEARD V1 20:54, 35:19) | 아이콘 모양을 다시 확인함 |
| 후긴이나 꿈 텍스트를 놓침 | "it disappeared before I could read it all"(HEARD V6 22:15) | 작업대 백과사전에서 다시 읽음(HEARD V6 26:02) |
| 친구 공격(friendly fire)을 실수로 켬 | HEARD V6 12:34, 46:50 | 설정에서 끔 |

## 6. 토르켈에 주는 시사점

1. **지각 스키마는 위 3절 표를 그대로 따른다.**
   - 거리 규칙: hover 5m, 생물 이름표 10m, 보스바 100m, 후긴 3m.
   - 이 규칙은 `EnemyHud`·`Raven`과 같은 기준이어야 한다(REPO `docs/api/1.0.16.md`).
   - 가운데와 왼쪽 위 메시지는 **로컬라이즈된 문자열 그대로** 넘긴다.
   - `[tutorial_*_label]` 같은 원시 토큰은 사람에게도 깨져 보인다. 그래도 정보 동등성 규칙 5에 따라 프롬프트에서 뺀다. 같은 줄의 "…추가되었습니다"만 남긴다.
2. **실패 메시지를 1급 관찰로 다룬다.**
   - `미완성 제물: X 1 / 2`, `아무 일도 일어나지 않았다`, `이 아이템은 부착할 수 없습니다`, `The crafting station needs a roof`, `더 먹을 수 없어`, `too hard`.
   - 사람은 이 메시지로 규칙을 배웠다. 결과 코드와 함께 두뇌에 보내 지식으로 쌓는다.
3. **장기 목표 사다리를 고정한다.**
   - 망치 → 작업대 + 지붕 → 침대·모닥불 → 가죽·사슴 → 활 또는 창과 방패 → 음식 3개 → 사슴 트로피 2개 → 제단 → 처치 → 희생석에 트로피.
   - 사람이 가장 오래 막힌 망치·지붕 단계는 토르켈이 먼저 제안해도 자연스럽다. 협동에서 경험자가 하던 역할이다.
4. **보스 소환은 동료 합의가 있을 때만 한다.**
   - 조건: 음식 3칸, 낮, 집과 거리를 둔 상태.
   - 트로피를 실수로 올리지 않도록 제단에서 `[1-8]` 아이템 제안을 막는 안전장치를 둔다.
   - 소환한 뒤에는 보스를 집에서 떼어 놓는다.
5. **보스전 기본 행동은 "2번 치고 빠지기"다.**
   - 체력이 낮거나 스태미나가 없으면 뒤로 빠진다. 번개 예고가 보이면 옆으로 구른다.
   - 리더가 근접이면 토르켈은 활을 쏘고, 리더가 활이면 토르켈이 어그로를 끈다.
   - "너한테 간다", "피 얼마 남았어?"처럼 짧게 콜아웃한다.
6. **인터럽트 우선순위(관찰 근거)**
   - 빨간 `!` 생물이 가까움 → 무기 들기
   - 체력 < 30% → 먹기, 안 되면 후퇴
   - `추위` + `젖음` → 불 옆으로 가거나 횃불 들기
   - 밤 → 침대나 피난처
   - 하던 작업은 목표 스택에 남겨 두고 위협이 끝나면 돌아간다(V1처럼 "Not the time"이라며 짜증만 내고 잊지 않는다).
7. **모르는 것은 물어본다.**
   - 이름표를 처음 보는 생물이면 "저거 뭐지? 그레이링이래" 식으로 이름을 읽어 준다. 한 번 때려 보고 피해 숫자로 강약을 판단한다.
   - LLM의 사전 지식으로 "그레이드워프는 불에 약하다"처럼 미리 말하지 않는다(누출 금지). 룬스톤이나 후긴에서 읽은 것만 인용한다.
8. **협동 분업을 말로 제안한다.**
   - 예: "내가 나무 벨게, 너는 지어", "가죽 몇 개 있어?", "망치 하나 만들어 줄까?"
   - 지도에서 `다른 플레이어에게 보이기`를 켜 두고 위치를 공유한다(이미 `leader_on_map` 경로가 있다).
9. **속도를 사람처럼 맞춘다.**
   - 처음 하는 사람은 1.5~3시간에 2~5번 죽고 잡는다.
   - 토르켈이 너무 빨리 정답을 내면 "첫 플레이 동료"로서 어색하다.
   - 반대로 V7처럼 1시간 막히는 것도 재미를 깬다. 막힌 지 N분이 지나면 힌트를 말로 낸다.

## 7. 보지 못한 것

- **소리를 듣지 못했다.** 오디오를 받지 않았다. 음악 변화, 생물 소리, 보스 등장 소리는 해설자의 말로만 확인했다.
- **피해 숫자의 색(노랑 약점, 회색 내성)은 프레임에서 확인하지 못했다.** 본 숫자는 모두 흰색이나 초록이었다. 색 규칙은 가이드 출처다.
- **`too hard`의 한국어 문구는 확인하지 못했다.** 영어는 자막으로만 확인했다.
- **사망 메시지 `죽었습니다!`는 320px 썸네일에서만 읽었다**(V4 약 3:40~3:50). 원본 해상도 프레임에서는 시점을 맞추지 못했다.
- **생물 이름표가 뜨는 정확한 거리는 영상에서 잴 수 없었다.** 10m는 디컴파일 메모 기준이다.
- **V3의 판단 일부는 시청자 채팅이 개입한 결과다.** 음식 3칸, 자동 줍기, 사슴 석상이 그렇다. V2, V8, V9에는 경험자가 섞여 있다. 완전 블라인드는 V1, V6, V7, V4(추정)다.
- **2021년 한국어 영상 3개는 자동 자막 품질이 나빴다**(kNRq_KMTI0M, I_5OwQw6Dzk, V10). 결론에 쓰지 않았다.
- **편집본이라 영상 시각과 실제 시간이 다르다.** 실시간은 해설자가 직접 말한 것만 적었다.

## 출처

### 영상 (모두 2026-10-17 시청·자막 수집)

| 별칭 | URL |
|---|---|
| V1 | https://www.youtube.com/watch?v=b-tIUNNQZ7s |
| V2 | https://www.youtube.com/watch?v=SZBycipUF5E |
| V3 | https://www.youtube.com/watch?v=1oZHseJVWMU |
| V4 | https://www.youtube.com/watch?v=6226AodkzBw |
| V5 | https://www.youtube.com/watch?v=cB7faj6eohA |
| V6 | https://www.youtube.com/watch?v=t6ssXshDOHI |
| V7 | https://www.youtube.com/watch?v=iCcFJjGsK54 |
| V8 | https://www.youtube.com/watch?v=jUynBlg2rBk |
| V9 | https://www.youtube.com/watch?v=HSiuckR5tUQ |
| V10 | https://www.youtube.com/watch?v=NHLCvgGkovI |

### 가이드 (커뮤니티·상업, 공식 아님)

- Nodecraft, "Valheim Boss Guide: Eikthyr"(2026-09-27 갱신, 2026-10-17 접근): https://nodecraft.com/support/games/valheim/general/valheim-boss-guide-eikthyr
- Gamepressure, "Valheim: Combat Guide"(피해 숫자 색, 2026-10-17 접근): https://www.gamepressure.com/valheim/combat/zee2f1
- Fandom 위키와 wiki.gg는 2026-10-17 시점에 402/401 응답이라 읽지 못했다.

### 레포 내부 (디컴파일 메모)

- `docs/api/1.0.16.md`: `EnemyHud`, `Raven`, `MessageHud`, `Player.FindHoverObject`, 지식 해금 함수
- `protocol/PROTOCOL.md`: `damage_dealt.type`
