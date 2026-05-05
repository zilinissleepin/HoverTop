#!/bin/bash
set -e

echo "Building HoverTop.app..."
cd swift
swift build -c release
cd ..

# 创建 .app bundle
APP_DIR="swift/.build/HoverTop.app"
mkdir -p "$APP_DIR/Contents/MacOS"
cp swift/.build/release/HoverTop "$APP_DIR/Contents/MacOS/"

cat > "$APP_DIR/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>HoverTop</string>
    <key>CFBundleIdentifier</key>
    <string>com.hovertop.app</string>
    <key>CFBundleName</key>
    <string>HoverTop</string>
    <key>CFBundleVersion</key>
    <string>0.1.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>LSUIElement</key>
    <true/>
</dict>
</plist>
PLIST

echo "Done: $APP_DIR"
