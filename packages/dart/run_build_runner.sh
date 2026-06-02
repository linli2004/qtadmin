#!/bin/bash
PATH="/home/linli/flutter/bin:$PATH"
cd /home/linli/桌面/qt/quanttide-finance-toolkit/packages/dart
dart pub get 2>&1 | tail -3
dart run build_runner build --delete-conflicting-outputs 2>&1
