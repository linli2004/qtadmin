#!/bin/bash
export PATH="/home/linli/flutter/bin:$PATH"
cd /home/linli/桌面/qt/quanttide-finance-toolkit/packages/flutter
flutter pub get 2>&1 | tail -3
flutter pub run build_runner build --delete-conflicting-outputs 2>&1 | tail -5
echo "---BUILD DONE---"
flutter test 2>&1 | tail -20
