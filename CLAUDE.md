# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test

### Dart package (`packages/dart/`)

```bash
dart pub get                                 # Install dependencies
dart analyze                                 # Static analysis
dart test                                    # Run all tests
dart run build_runner build --delete-conflicting-outputs  # Regenerate freezed + json_serializable
```

Dart CI is defined in `.github/workflows/dart-check.yml` — runs `pub get → analyze → test` on push/PR touching `packages/dart/**`. Publishing is triggered by GitHub releases with tag prefix `dart/` (see `dart-publish.yml`).

### FastAPI package (`packages/fastapi/`)

Not yet implemented. When it exists, will use pytest, SQLAlchemy, and Alembic. No CI workflow exists yet.

## Project Status

This is a monorepo with two packages:

| Package | Status | Purpose |
|---|---|---|
| `packages/dart` | Published `^0.1.1` | `Journal` / `JournalEntry` / `JournalEntryLine` — optional accounting layer |
| `packages/fastapi` | Planned (not yet created) | `SourceRecord` / `NormalizedRecord` / `ClassificationResult` — main normalization & statistics backend |

**Current implementation is incomplete.** The Dart package only covers the optional downstream accounting layer (`Journal` → `JournalEntry` → `JournalEntryLine`), not the core data pipeline. The FastAPI core is still to be built. See `doc/architecture.md` and `ROADMAP.md`.

## Architecture

### Core Data Flow

```
SourceRecord → NormalizedRecord → ClassificationResult → Statistics
                                              ↓ (optional)
                              Journal / JournalEntry / JournalEntryLine
```

- `RecordLink` is the association layer between `SourceRecord` and `NormalizedRecord` (many-to-many), not a linear processing node
- `ClassificationResult` is an additive dimension, not a fact layer — classification data lives only in `ClassificationResult`, never written back to `NormalizedRecord`
- Statistics are based on `NormalizedRecord`; unclassified records can still enter aggregation/trend/detail queries

### FastAPI Package Structure (planned)

```
packages/fastapi/
├── src/fastapi_quanttide_finance/
│   ├── models/        # SQLAlchemy ORM models
│   ├── schemas/       # Pydantic request/response schemas
│   ├── services/      # Business logic (normalization, classification, statistics, posting)
│   ├── routers/       # HTTP endpoints
│   └── database.py    # DB connection + Alembic config
├── tests/
└── examples/provider/
```

### Layer Stack

```
Routers (HTTP endpoints) → Services (business logic) → Schemas (Pydantic) → Models (SQLAlchemy ORM)
```

## Key Conventions

- **IDs**: Target `int` for all entities. Current Dart models use `String` — migration to `int` is planned in a future breaking release.
- **Amounts**: Use `int` with unit "分" (cents/fen), not `double`. Note: current Dart `JournalEntryLine.amount` is `double` — this is known tech debt that will be fixed when Dart models are synced (M6 in ROADMAP).
- **Raw data preservation**: `raw_payload`, `raw_text`, `evidence_refs` keep original content; no irreversible trimming before storage.
- **Code generation (Dart)**: Models use `freezed` + `json_serializable`. Run `build_runner` after editing model classes.
- **Statistics API**: Unified "dimension + metrics + filter" pattern (not hardcoded `by_department` or `by_expense_type` endpoints).
- **Desensitization**: Applied at data egress only (before sending to external AI), never stored. Uses type-token replacement (`[AMOUNT]`, `[ID_CARD]`, etc.).
- **Classification review flow**: `candidate → accepted/rejected`. Only `accepted` results participate in statistics.

## Key Documentation

| File | Content |
|---|---|
| `ROADMAP.md` | Exploration phase plan with 6 milestones (M1-M6) and validation gates |
| `doc/architecture.md` | System architecture, entity relationships, package structure |
| `doc/entities.md` | Full entity field definitions for `SourceRecord`, `NormalizedRecord`, `RecordLink`, `ClassificationResult` |
| `doc/services.md` | Normalizer interface, registration pattern, built-in normalizer list |
| `doc/api.md` | REST API endpoints and statistics design |
| `doc/security.md` | Data desensitization, classification security, taxonomy validation, sandbox testing |

## Development Path (per ROADMAP)

The current exploration phase (56 days) builds the standardization backbone in **`packages/fastapi`**:

| Milestone | Focus | Key Deliverables |
|---|---|---|
| M1 | Day 14 | ORM models + Pydantic schemas + DB migration |
| M2 | Day 28 | Normalizer interface + `CsvRowNormalizer` + `ManualNormalizer` |
| M3 | Day 35 | Hardcoded taxonomy + classification API + review flow |
| M4 | Day 42 | Aggregate/group/trend/drill-down statistics API |
| M5 | Day 49 | Desensitization + audit logging + taxonomy output validation |
| M6 | Day 56 | Dart model sync (`id` → `int`, `amount` → `int`, `normalizedRecordId` field) |

## Existing Dart Models

- `Journal` — ledger/account (id, name, createdAt)
- `JournalEntry` — voucher with lines (id, journalId, createdAt, description, lines)
- `JournalEntryLine` — debit/credit line (id, type, amount, description, createdAt)
- `LineType` — enum: `debit`, `credit`

All use `freezed` for immutability and `json_serializable` for JSON. Tests check `toJson/fromJson` roundtrip and `copyWith`. Run `dart run build_runner build --delete-conflicting-outputs` after any model change.
