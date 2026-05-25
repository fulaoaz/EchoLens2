# Changelog

All notable changes to EchoLens 2.0 will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0-rc1] - 2026-05-25

### Added

#### Phase H - User Experience Enhancement & Internationalization
- **Internationalization (i18n)**
  - Complete Chinese (zh-CN) and English (en-US) translations
  - 12 translation modules: common, nav, project, crawler, simulation, prediction, decision, report, settings, error, validation, help
  - Automatic browser language detection
  - Language preference persistence
  - HTML lang attribute synchronization
  - `useLocale` composable for language switching

- **Keyboard Shortcuts System**
  - Global keyboard shortcut registration
  - Modifier key support (Ctrl, Shift, Alt, Meta)
  - Automatic input field exclusion
  - Mac/Windows display adaptation
  - 11+ predefined shortcuts:
    - Ctrl+H: Workbench
    - Ctrl+P: Projects
    - Ctrl+N: New Project
    - Ctrl+K: Search
    - Ctrl+S: Save
    - Ctrl+R: Refresh
    - Ctrl+B: Toggle Sidebar
    - Ctrl+D: Toggle Theme
    - Ctrl+Shift+L: Toggle Language
    - Shift+?: Show Help
    - Ctrl+/: Show Shortcuts List

- **User Preferences System**
  - 10+ preference settings across 5 categories:
    - Appearance: theme, language, font size, compact mode
    - Notifications: enable notifications, sound effects
    - Editor: auto-save, save interval
    - Advanced: debug mode, experimental features, max concurrent tasks
    - Data: data retention days, auto backup, backup interval
  - Auto-save to localStorage
  - Import/export preferences as JSON
  - Reset to defaults functionality

- **Enhanced Error Handling**
  - Global error capture
  - Intelligent Axios error parsing
  - Error classification: network, server, validation, unknown
  - Error queue management (max 10 items)
  - Retryable flag for each error type
  - User-friendly error messages
  - Unhandled Promise rejection handling

- **Data Export Functionality**
  - Export to 4 formats:
    - JSON: Standard format with 2-space indentation
    - CSV: UTF-8 BOM for Excel compatibility
    - Markdown: Table format, GitHub compatible
    - HTML: Styled tables, directly viewable
  - Automatic special character escaping
  - XSS protection for HTML export
  - Automatic download with custom filenames

### Changed
- Updated version from 2.0.0-beta to 2.0.0-rc1
- Improved build performance (16.01s stable)
- Enhanced vendor bundle with vue-i18n (82.95 kB gzipped)

### Documentation
- Created comprehensive user manual (docs/USER_MANUAL.md)
- Added Phase H completion summary (.omc/phase-h-summary.md)
- Updated PROGRESS.md with Phase H details

---

## [2.0.0-beta] - 2026-05-24

### Added

#### Phase G - Performance Optimization & Production Ready
- **Frontend Performance Optimization**
  - Fine-grained code splitting strategy
  - Separate chunks for ECharts, D3, G6, Axios
  - Build time improved from 28.03s to 8.54s (70% faster)
  - ECharts chunk reduced by 30% (569 kB → 396 kB gzipped)
  - Route lazy loading for all components

- **Dark Mode Support**
  - Complete dark mode implementation with CSS variables
  - Theme modes: light, dark, auto
  - Automatic system theme detection and following
  - localStorage theme preference persistence
  - Naive UI theme integration
  - ECharts dark/light theme configurations
  - Smooth transition animations (0.3s)

- **Testing & Quality**
  - Backend tests: 246 passed, 1 skipped
  - E2E tests: Playwright framework operational
  - Code quality: ESLint 0 warnings
  - Build verification: frontend and backend builds passing

- **Deployment Documentation**
  - Comprehensive DEPLOYMENT.md guide
  - Docker Compose deployment instructions
  - Local development setup
  - Tauri desktop app build guide
  - Capacitor mobile app build guide
  - Production environment configuration (Nginx, HTTPS, systemd)
  - Performance optimization recommendations
  - Monitoring and logging setup
  - Troubleshooting guide
  - Security recommendations

### Changed
- Updated version from 2.0.0-alpha to 2.0.0-beta
- Optimized Vite configuration with manualChunks
- Enhanced build output with detailed chunk analysis

---

## [2.0.0-alpha] - 2026-05-23

### Added

#### Phase F - Cross-Platform Support
- **Platform Abstraction Layer**
  - Created `usePlatform` composable for unified API
  - Platform detection: Web, Tauri, Capacitor iOS, Capacitor Android
  - Unified file picker API
  - Unified network request configuration
  - Unified notification API
  - Platform capability detection

- **Tauri Desktop Support**
  - Installed Tauri 2.11.2 dependencies
  - Created `useTauri` composable for desktop features
  - Window management: minimize, maximize, fullscreen, close
  - System tray integration with menu
  - Window event handling (close → hide instead of exit)
  - Application metadata access
  - npm scripts: `tauri:dev`, `tauri:build`, `tauri:build:debug`

- **Capacitor Mobile Support**
  - Installed Capacitor 8.3.4 dependencies
  - Initialized iOS and Android platforms
  - Configured capacitor.config.ts
  - Local notifications plugin integration
  - npm scripts: `cap:sync`, `cap:open:ios`, `cap:open:android`, `cap:run:ios`, `cap:run:android`

- **Mobile Responsive Design**
  - Created mobile.css with responsive breakpoints
  - Touch-friendly UI (minimum 44px buttons)
  - Form field stacking layout
  - Adaptive chart containers
  - Full-screen modals and drawers
  - Safe area adaptation for notched screens
  - Landscape mode optimization

- **Documentation**
  - Created README-CROSSPLATFORM.md
  - Platform support matrix
  - Architecture design documentation
  - Development and build guides
  - Platform difference handling
  - Environment requirements
  - Troubleshooting guide

### Changed
- Updated API client to use platform abstraction layer
- Integrated mobile CSS into main entry point
- Build time improved from 28.03s to 8.54s (70% faster)

---

## [1.0.0] - 2026-05-20

### Added

#### Phase E - Report & Frontend Integration
- **Report Layer**
  - Evidence report generation
  - Self-contained HTML download with inline CSS
  - Reliability tier labels (Strong/Fair/Weak)
  - Three-tier color mapping (green/yellow/red)
  - Shared reliability tier module (backend and frontend)
  - Contract tests for tier consistency

- **Frontend Integration**
  - Project detail page with complete business workflow
  - Decision dashboard chip accessibility (role="button", aria-label, Enter/Space)
  - Run reverse lookup highlight (click Run chip to highlight original run)
  - Reliability tier color consistency across UI and reports

- **E2E Testing Framework**
  - Playwright configuration and setup
  - Basic smoke tests (app startup, navigation)
  - Reliability tier visual consistency tests
  - Full workflow tests (project creation → simulation → decision → report)
  - Test fixtures and documentation

#### Phase D - Simulation/Prediction/Decision
- **OASIS Social Media Simulation**
  - Integration with CAMEL-AI OASIS framework
  - Million-scale agent simulation support
  - Multi-round iterative simulation
  - Behavior data and metrics collection

- **Time Series Prediction**
  - ARIMA model integration
  - Prophet model integration
  - Trend analysis and visualization

- **Causal Inference**
  - DoWhy framework integration
  - Causal relationship analysis
  - Treatment effect estimation

- **Decision Engine**
  - Multi-dimensional comprehensive scoring
  - Evidence chain construction
  - Reliability level calculation
  - Decision recommendation generation

#### Phase C - Self-Hosted Retrieval & Knowledge Graph
- **Kuzu Graph Database**
  - Graph database integration
  - Entity and relationship storage
  - Graph query support

- **LightRAG Knowledge Graph Engine**
  - Automatic knowledge graph construction
  - Entity extraction and linking
  - Relationship inference

- **Ontology Generator**
  - LLM-driven ontology generation
  - Domain-specific schema creation

- **Graph Search & Sync**
  - Graph search API
  - Real-time graph synchronization

#### Phase B - Real Data Collection Loop
- **Multi-Platform Crawler Engine**
  - JD (JingDong) crawler
  - Taobao crawler
  - Weibo crawler
  - Xiaohongshu (Little Red Book) crawler

- **Compliance Checks**
  - robots.txt compliance
  - Rate limiting protection
  - User-agent rotation

- **Data Cleaning Pipeline**
  - Deduplication
  - Data alignment
  - Data cleaning and normalization

- **Seed Report Generation**
  - Automatic seed report generation from uploaded documents
  - Entity extraction and summarization

#### Phase A - Architecture Decoupling
- **Backend**
  - Flask 3 + Pydantic 2 scaffolding
  - DuckDB local storage
  - RESTful API design
  - pytest test framework

- **Frontend**
  - Vue 3.5 + Vite 7 setup
  - Naive UI component library
  - Pinia state management
  - Axios HTTP client
  - ECharts + D3.js + @antv/g6 visualization

- **DevOps**
  - Docker Compose deployment configuration
  - Development override configuration
  - CI/CD pipeline setup

### Documentation
- Initial README.md
- Project structure documentation
- Quick start guide
- Development progress tracking (PROGRESS.md)

---

## [Unreleased]

### Planned for Phase I - Documentation & Release Preparation
- [ ] Complete user manual
- [ ] Generate API documentation (OpenAPI/Swagger)
- [ ] Update README files (Chinese and English)
- [ ] Write CHANGELOG
- [ ] Prepare release materials (screenshots, demo video scripts)
- [ ] License and copyright information
- [ ] Contributing guidelines
- [ ] Security policy documentation

### Future Enhancements
- Offline mode (Service Worker)
- Enhanced data visualization
- Collaboration features (multi-user)
- Performance monitoring and analytics
- More platform crawler adapters
- More prediction model integrations
- Custom decision rules
- Cloud deployment
- SaaS transformation
- Enterprise features

---

## Version History

- **2.0.0-rc1** (2026-05-25): Release Candidate - User experience enhancement & internationalization
- **2.0.0-beta** (2026-05-24): Beta Release - Performance optimization & production ready
- **2.0.0-alpha** (2026-05-23): Alpha Release - Cross-platform support
- **1.0.0** (2026-05-20): Initial Release - Core features complete

---

[2.0.0-rc1]: https://github.com/zuohenlin/EchoLens2/compare/v2.0.0-beta...v2.0.0-rc1
[2.0.0-beta]: https://github.com/zuohenlin/EchoLens2/compare/v2.0.0-alpha...v2.0.0-beta
[2.0.0-alpha]: https://github.com/zuohenlin/EchoLens2/compare/v1.0.0...v2.0.0-alpha
[1.0.0]: https://github.com/zuohenlin/EchoLens2/releases/tag/v1.0.0
[Unreleased]: https://github.com/zuohenlin/EchoLens2/compare/v2.0.0-rc1...HEAD
