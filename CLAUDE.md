# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test (Dart package)

All commands run from `packages/dart/`:

```bash
dart pub get              # Install dependencies
dart analyze              # Static analysis
dart test                 # Run all tests
dart run build_runner build --delete-conflicting-outputs  # Regenerate freezed + json_serializable code
```

## Architecture

**Monorepo** with two planned packages:

- **`packages/dart`** — Published as [`quanttide_finance`](https://pub.dev/packages/quanttide_finance) `^0.1.1`. Provides freezed immutable models for the optional accounting layer:
  - `Journal` — A named ledger/account (id, name, createdAt)
  - `JournalEntry` — A journal entry with lines (id, journalId, createdAt, description, lines)
  - `JournalEntryLine` — A single debit or credit line (id, type, amount, description, createdAt)
  - `LineType` — Enum: `debit`, `credit`

- **`packages/fastapi`** — Planned but not yet implemented. Will house `SourceRecord`, `NormalizedRecord`, `ClassificationResult`, and statistics API — the main business logic.

## Data Flow

```
SourceRecord → NormalizedRecord → ClassificationResult → Statistics
                                              ↓ (optional)
                              Journal / JournalEntry / JournalEntryLine
```

## Key Conventions

- **Code generation**: Models use `freezed` + `json_serializable`. After editing model classes, run `build_runner` to regenerate `.freezed.dart` and `.g.dart` files.
- **Amounts**: Use `int` with unit "分" (cents/fen), not `double`.
- **IDs**: Target type is `int`; current Dart models use `String`.
- **CI**: `dart-check.yml` runs `dart pub get → dart analyze → dart test` on any push/PR touching `packages/dart/**`. Publishing is triggered by GitHub releases with tag prefix `dart/`.
