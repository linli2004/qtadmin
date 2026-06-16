# Human Module Changelog

> QtCloud HR — Human resources module changelog.

---

## v0.10.0 — Flutter Kanban UI: Full Pipeline Management (2026-06-16)

### Added

- **Main Shell** (`src/hr-kanban/lib/main.dart`)
  - Responsive layout: NavigationRail (desktop) / NavigationBar (mobile)
  - 4-tab navigation: Pipeline, Queue, Pool, Settings
  - IndexedStack for tab state preservation
- **Pipeline Screen** (`src/hr-kanban/lib/screens/pipeline_screen.dart`)
  - Kanban-style pipeline grouped by 8 TalentStatus columns
  - Candidate cards with name, email, sub-stage, wait-day badges
  - Wait-day color coding: yellow (7+), orange (14+)
  - Drag-and-drop status transitions
  - Candidate detail bottom sheet (email, attachments, timeline)
  - Real-time search by name or email
- **Queue Screen** (`src/hr-kanban/lib/screens/queue_screen.dart`)
  - Pending email queue sorted by time descending
  - Confidence badges: high (green), medium (yellow), low (gray)
  - Confirm/adjust/ignore actions
  - Recruitment title assignment on confirm
- **Pool Screen** (`src/hr-kanban/lib/screens/pool_screen.dart`)
  - Filter by recruitment project
  - Unpool with recruitment reassignment
- **Settings Screen** (`src/hr-kanban/lib/screens/settings_screen.dart`)
  - AI config form: provider, model, API key (obscured), temperature slider, prompt template
  - Server URL field with instant save
  - Connection test with loading state
- **API Service** (`src/hr-kanban/lib/services/api_service.dart`)
  - Full REST client: pipeline, queue, applications, candidates, messages, pool, AI config
  - Mutable baseUrl for runtime server switching
- **Theme System** (`src/hr-kanban/lib/theme/hr_theme.dart`)
  - HrThemeExtension: 8 status colors, spacing tokens, font tokens
  - Dark theme with ColorScheme.dark
- **Widgets**: StatusBadge, EmptyState, ErrorView, InfoRow

### Tests

- Widget smoke test: app renders all 4 navigation tabs
