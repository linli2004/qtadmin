# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test

### FastAPI package (`packages/fastapi/`)

Run all commands from `packages/fastapi/` — activate the venv first:

```bash
source .venv/bin/activate
pip install -e ".[dev]"   # one-time setup
python -m pytest          # run all tests
python -m pytest tests/test_schemas.py -v  # run a specific test file
```

Test infrastructure (see `tests/conftest.py`):
- File-based SQLite (`data/test.db`), rebuilt per session
- Alembic migrations applied via `command.upgrade()` before tests
- `PRAGMA foreign_keys=ON` enabled for FK integrity testing
- `client` fixture overrides `get_db` dependency for TestClient

Alembic migration workflow:

```bash
alembic revision --autogenerate -m "description"  # generate migration
alembic upgrade head                                # apply
alembic downgrade -1                                # rollback one step
```

FastAPI CI workflow is deferred (M0 backlog). Dart CI is in `.github/workflows/dart-check.yml`.

### Dart package (`packages/dart/`)

```bash
dart pub get                                 # Install dependencies
dart analyze                                 # Static analysis
dart test                                    # Run all tests
dart run build_runner build --delete-conflicting-outputs  # Regenerate freezed + json_serializable
```

## Project Status

| Package | Status | Content |
|---|---|---|
| `packages/dart` | Published `^0.1.1` | `Journal` / `JournalEntry` / `JournalEntryLine` — optional accounting layer |
| `packages/fastapi` | M2 complete (0.1.0) | `SourceRecord` / `NormalizedRecord` / `RecordLink` / `ClassificationResult` — core models + schemas + CsvRowNormalizer + ManualNormalizer + normalize routes + GET endpoints (57 tests) |

See `doc/architecture.md` and `ROADMAP.md` for the full plan. Current phase: M3 (Classification Service).

## Architecture

### Core Data Flow

```
SourceRecord → NormalizedRecord → ClassificationResult → Statistics
                                              ↓ (optional)
                              Journal / JournalEntry / JournalEntryLine
```

- `RecordLink` is the association layer between `SourceRecord` and `NormalizedRecord` (many-to-many), not a linear processing node
- `ClassificationResult` is an additive dimension — data lives only in `ClassificationResult`, never written back to `NormalizedRecord`
- Statistics are based on `NormalizedRecord`; unclassified records can still enter aggregation/trend/detail queries

### FastAPI Package Structure

```
packages/fastapi/
├── pyproject.toml
├── alembic.ini                              # Alembic configuration
├── src/
│   ├── alembic/                             # Migration scripts
│   │   ├── env.py
│   │   └── versions/
│   └── fastapi_quanttide_finance/
│       ├── app.py                           # FastAPI application + /health
│       ├── database.py                      # SQLAlchemy engine + Base + get_db
│       ├── models/                          # ORM models
│       ├── schemas/                         # Pydantic Create/Read/Update schemas
│       ├── services/                        # Normalizer interface + CsvRowNormalizer + ManualNormalizer
│       └── routers/                         # SourceRecord CRUD + normalize endpoint
├── tests/
│   ├── conftest.py                          # Test fixtures (SQLite + Alembic)
│   ├── test_health.py                       # Health check
│   ├── test_database.py                     # DB connectivity
│   ├── test_models.py                       # ORM integration tests
│   └── test_schemas.py                      # Pydantic validation tests
└── data/                                    # SQLite DB files (gitignored)
```

### Layer Stack

```
Routers (HTTP endpoints) → Services (business logic) → Schemas (Pydantic) → Models (SQLAlchemy ORM)
```

## Schema Validation Patterns

All write paths go through Pydantic schemas — ORM models are never instantiated directly from raw user input.

**Enum validation** via `field_validator` (not DB-level enum, for SQLite compatibility):

```python
@field_validator("source_type")
@classmethod
def validate_source_type(cls, v: str) -> str:
    allowed = {"image", "chat", "form", "csv_row", "bank_tx", "api", "manual", "other"}
    if v not in allowed:
        raise ValueError(...)
    return v
```

**Overflow handling** strategy per `doc/entities.md`:
- `raw_text` > 65535 chars → **reject** (ValidationError, 422)
- `description` > 1000 chars → **truncate** silently
- `amount_cents` → `Field(ge=0)`, direction expressed by `outflow`/`inflow`

## Key Conventions

- **IDs**: `int` for all entities. Current Dart models still use `String` — migration planned in M6.
- **Amounts**: `int` with unit "分" (cents). Current Dart `JournalEntryLine.amount` is still `double` — known tech debt for M6.
- **Raw data preservation**: `raw_payload`, `raw_text`, `evidence_refs` store original content; no irreversible trimming before storage.
- **Code generation (Dart)**: Models use `freezed` + `json_serializable`. Run `build_runner` after editing.
- **Statistics API**: Unified "dimension + metrics + filter" pattern (not hardcoded endpoints).
- **Desensitization**: Applied at data egress only (before external AI), never stored. Type-token replacement (`[AMOUNT]`, `[ID_CARD]`, etc.).
- **Classification review flow**: `candidate → accepted/rejected`. Only `accepted` results participate in statistics.

## Key Documentation

| File | Content |
|---|---|
| `ROADMAP.md` | Exploration phase plan with milestones and validation gates |
| `doc/architecture.md` | System architecture, entity relationships, package structure |
| `doc/entities.md` | **Single source of truth** for field defaults, constraints, enum values, truncation rules |
| `doc/services.md` | Normalizer interface, registration pattern, built-in normalizer list |
| `doc/api.md` | REST API endpoints and statistics design |
| `doc/security.md` | Data desensitization, classification security, taxonomy validation |

## Milestones (per ROADMAP)

| Phase | Deliverables |
|---|---|
| **M0** ✅ Done | Project scaffolding, Alembic, health check, test fixtures, doc updates |
| **M1** ✅ Done | 4 ORM models + 4 Pydantic schemas + Alembic migration (30 tests) |
| **M2** ✅ Done | Normalizer interface + registration + `CsvRowNormalizer` + `ManualNormalizer` + normalize + list/get routes (57 tests) |
| **M3** | Hardcoded taxonomy + classification API + review flow |
| **M4** | Aggregate/group/trend/drill-down statistics API |
| **M5** | Desensitization + audit logging + taxonomy validation |
| **M6** | Dart model sync (`id` → `int`, `amount` → `int`, `normalizedRecordId`) |

## Existing Dart Models

- `Journal` — ledger/account (id, name, createdAt)
- `JournalEntry` — voucher with lines (id, journalId, createdAt, description, lines)
- `JournalEntryLine` — debit/credit line (id, type, amount, description, createdAt)
- `LineType` — enum: `debit`, `credit`

All use `freezed` + `json_serializable`. Tests verify `toJson/fromJson` roundtrip and `copyWith`.
