#!/bin/zsh
# Thorkell.app(SwiftUI)을 빌드해서 ~/Applications/Thorkell.app 에 둔다.
# 앱에는 이 레포의 경로가 들어간다(엔진 `thorkell play`를 여기서 실행한다). 레포를 옮기면 다시 실행한다.
#   tools/gui/build.sh [앱 경로]
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
APP="${1:-$HOME/Applications/Thorkell.app}"
WORK="$REPO/artifacts/gui"

rm -rf "$WORK"
mkdir -p "$WORK/Thorkell.iconset"
print "컴파일 중..."
xcrun swiftc -swift-version 5 -parse-as-library -O -target arm64-apple-macos14.0 \
  -o "$WORK/Thorkell" "$HERE/Thorkell.swift"

print "아이콘 만드는 중..."
xcrun swift "$HERE/make-icon.swift" "$WORK/icon-1024.png"
for px in 16 32 128 256 512; do
  sips -z $px $px "$WORK/icon-1024.png" --out "$WORK/Thorkell.iconset/icon_${px}x${px}.png" >/dev/null
  sips -z $((px * 2)) $((px * 2)) "$WORK/icon-1024.png" --out "$WORK/Thorkell.iconset/icon_${px}x${px}@2x.png" >/dev/null
done
iconutil -c icns "$WORK/Thorkell.iconset" -o "$WORK/Thorkell.icns"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$WORK/Thorkell" "$APP/Contents/MacOS/Thorkell"
cp "$WORK/Thorkell.icns" "$APP/Contents/Resources/Thorkell.icns"
cat >"$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Thorkell</string>
  <key>CFBundleDisplayName</key><string>Thorkell</string>
  <key>CFBundleIdentifier</key><string>local.thorkell.app</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>CFBundleShortVersionString</key><string>0.1</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>Thorkell</string>
  <key>CFBundleIconFile</key><string>Thorkell</string>
  <key>CFBundleDevelopmentRegion</key><string>ko</string>
  <key>LSMinimumSystemVersion</key><string>14.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>ThorkellRepo</key><string>$REPO</string>
</dict>
</plist>
PLIST
plutil -lint "$APP/Contents/Info.plist" >/dev/null
codesign --force --sign - "$APP" >/dev/null
print "만들었습니다: $APP"
