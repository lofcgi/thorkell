#!/bin/zsh -l
# Thorkell 실행기: 터미널에서 리허설(내 월드 복사본에서 토르켈과 같이 플레이)을 시작한다.
# Finder에서 두 번 클릭하거나 Thorkell.app(tools/launcher/make-app.sh로 생성)으로 연다.
#   THORKELL_WORLD   리허설할 월드(기본 helloworld)
#   --check          준비 상태만 점검하고 게임은 띄우지 않는다
# 원본 세이브·Steam Cloud·설정은 건드리지 않는다(thorkell play가 끝날 때 다시 확인한다).

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORLD="${THORKELL_WORLD:-helloworld}"
CHECK_ONLY=0
[[ "$1" == "--check" ]] && CHECK_ONLY=1

printf '\e]0;Thorkell\a'
print -P "%B토르켈 리허설 실행기%b  (월드: $WORLD)"
print "레포: $REPO"
print

finish() {
  print
  if [[ $CHECK_ONLY -eq 0 && -t 0 ]]; then
    read -k 1 "?아무 키나 누르면 창을 닫습니다."
    print
  fi
  exit "$1"
}

fail() {
  print -P "%F{red}[멈춤]%f $1"
  finish 1
}

for tool in uv dotnet; do
  command -v "$tool" >/dev/null || fail "$tool 명령을 찾을 수 없습니다. 설치 후 다시 실행하세요."
done

# 1. 진짜 Valheim은 꺼져 있어야 한다(리허설은 복사본 게임으로 한다).
GAME="$HOME/Library/Application Support/Steam/steamapps/common/Valheim"
if pgrep -f "$GAME/Valheim.app" >/dev/null; then
  fail "진짜 Valheim이 켜져 있습니다. 게임을 끄고 다시 실행하세요."
fi

# 2. Steam이 켜져 있어야 한다. 꺼져 있으면 켜고, 로그인할 시간을 준다.
if ! pgrep -x steam_osx >/dev/null; then
  print "Steam을 켭니다..."
  [[ $CHECK_ONLY -eq 1 ]] && fail "Steam이 꺼져 있습니다."
  open -a Steam
  for i in {1..120}; do
    pgrep -x steam_osx >/dev/null && break
    sleep 1
  done
  pgrep -x steam_osx >/dev/null || fail "Steam이 2분 안에 켜지지 않았습니다. Steam을 직접 켜고 로그인한 뒤 다시 실행하세요."
  print "Steam이 켜졌습니다. 로그인 창이 보이면 로그인한 뒤 엔터를 누르세요."
  read -r
fi
print "✓ Steam 실행 중, 진짜 Valheim은 꺼져 있음"

# 3. 플러그인을 최신 코드로 빌드한다(바뀐 게 없으면 몇 초면 끝난다).
print "플러그인 빌드 확인 중..."
mkdir -p "$REPO/artifacts"
if ! dotnet build "$REPO/Thorkell.sln" -c Release -nologo -v quiet >"$REPO/artifacts/launcher-build.log" 2>&1; then
  fail "플러그인 빌드가 실패했습니다. 로그: $REPO/artifacts/launcher-build.log"
fi
print "✓ 플러그인 빌드"

# 4. 모델 키: 레포 루트 .env가 있으면 Gemini Flash + Jev로, 없으면 규칙만(정해진 말만 알아듣는다).
cd "$REPO/brain" || fail "brain 폴더가 없습니다."
if [[ -f "$REPO/.env" ]]; then
  RUN=(uv run --env-file ../.env thorkell play --rehearsal "$WORLD" --config thorkell.play.toml)
  print "✓ 모델 사용(Gemini Flash + Jev, 키는 .env에서)"
else
  RUN=(uv run thorkell play --rehearsal "$WORLD")
  print "! .env가 없어 모델 없이 규칙만 씁니다(따라와·기다려·멈춰·뭐해·나무 N개·받아)."
fi

# 5. 백업: 없으면 thorkell play가 먼저 만든다. 있으면 그대로 쓴다.
BACKUPS=("$HOME/Library/Application Support/Thorkell/backups/"*/manifest.json(N))
LATEST="${BACKUPS[-1]:-}"
if [[ -n "$LATEST" ]]; then
  print "✓ 백업 있음: $(basename "$(dirname "$LATEST")")"
else
  print "! 백업이 아직 없습니다. 시작하면서 먼저 만듭니다(원본은 읽기만 함)."
fi

if [[ $CHECK_ONLY -eq 1 ]]; then
  print
  print "점검 끝. 실행할 명령: (cd brain && ${RUN[*]})"
  finish 0
fi

print
print "이제 내 게임 창(리허설 복사본)을 띄웁니다. 창이 뜨면:"
print "  캐릭터 선택 → 월드 '$WORLD' → '서버 시작' 켜기(crossplay 켬) + 정해 둔 비밀번호 → 시작"
print "토르켈은 시작 신전에 나타납니다. 끝낼 때는 여기에 /quit 를 입력하세요."
print
"${RUN[@]}"
finish $?
