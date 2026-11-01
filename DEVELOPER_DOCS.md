# SkillSaathi — Developer Documentation

> **Project:** SIH 2026 | **Stack:** React 18 + TypeScript + Vite | **Target:** Vocational career guidance platform for students and parents in India

---

## Architecture Overview

- **Type:** Single-Page Application (SPA) — no server-side rendering, no routing library
- **Rendering:** Custom in-app router implemented as a `switch` on `currentRoute` state in [`App.tsx`](src/app/App.tsx)
- **State management:** Local React state only (`useState`, `useContext`). No Redux, Zustand, or similar
- **Backend:** FastAPI (Python) expected at `http://localhost:8000/api/v1`. Frontend has **resilient fallback** to local mock data when backend is offline
- **Storage:** Browser `sessionStorage` (ephemeral session data) + `localStorage` (language preference only)
- **i18n:** Custom React Context provider. Supports `en`, `mr` (Marathi), `hi` (Hindi). Key stored in `localStorage` under `skillsaathi_language`
- **AI/LLM:** The FastAPI backend RAG pipeline utilizes Google Gemini: **`gemini-embedding-2`** for dense vector course embeddings and retrieval queries, and **`gemini-3.8-flash`** for grounded consensus report synthesis and AI counselling note generation. When `GEMINI_API_KEY` is not provided, the backend falls back gracefully to deterministic rule-based scoring and pure-Python TF-IDF keyword retrieval. Frontend features resilient fallback.

```
Browser
  └── I18nProvider (Context)
        └── App.tsx (in-app router via useState)
              └── AppShell (layout: Sidebar + Topbar + MobileNavigation)
                    └── [Active View] — one of:
                          HomeScreen
                          OnboardingFlow
                          CourseExplorer → CourseDetails
                          AssessmentScreen → AssessmentResults
                          PlaceholderSection (career-pathways, counsellor-support, admin)
```

---

## Setup & Prerequisites

**Requirements:**
- Node.js ≥ 18.x
- npm ≥ 9.x (or equivalent pnpm/yarn)
- (Optional) Python 3.11+ FastAPI backend for live data

**Install & run:**
```bash
# 1. Clone and enter repo
cd "SIH 2026/sih-2026-career-guide"

# 2. Install dependencies
npm install

# 3. Configure environment
cp .env.example .env.local
# Edit .env.local → set VITE_API_BASE_URL=http://localhost:8000/api/v1

# 4. Start dev server
npm run dev
# → Vite serves on http://localhost:5173 (default)

# 5. Build for production
npm run build
# → Output in /dist
```

**Environment variable:**

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `''` (relative) | FastAPI backend base URL. Falls back to mock data if unreachable |

---

## Core Components Map

### Entry Point
- [`src/main.tsx`](src/main.tsx) — React root mount. Wraps `<App>` with `<I18nProvider>`

### Routing
- [`src/app/routes.ts`](src/app/routes.ts) — Route constants (string literals, no router lib)
  - `'/'` → `HomeScreen`
  - `'/onboarding'` → `OnboardingFlow`
  - `'/courses'` / `'/courses/:id'` → `CourseExplorer`
  - `'/counselling'` → `AssessmentScreen`
  - `'/career-pathways'`, `'/counsellor-support'`, `'/admin'` → `PlaceholderSection`
- [`src/app/App.tsx`](src/app/App.tsx) — Root router component. Manages `currentRoute`, `selectedCourseId`, `counsellingCourse` state

### Layout
- [`src/components/layout/AppShell.tsx`](src/components/layout/AppShell.tsx) — Root shell; hosts Sidebar, Topbar, MobileNavigation
- [`src/components/layout/navigationConfig.ts`](src/components/layout/navigationConfig.ts) — Nav item definitions mapped to `ROUTES` constants
- [`src/components/layout/Sidebar.tsx`](src/components/layout/Sidebar.tsx) — Desktop sidebar nav
- [`src/components/layout/Topbar.tsx`](src/components/layout/Topbar.tsx) — Top bar with language switcher
- [`src/components/layout/MobileNavigation.tsx`](src/components/layout/MobileNavigation.tsx) — Bottom tab bar for mobile

### Feature Modules

#### Onboarding (`src/features/onboarding/`)
- [`OnboardingFlow.tsx`](src/features/onboarding/OnboardingFlow.tsx) — Multi-step intake wizard; captures role, education, state/district, career interests
- [`types.ts`](src/features/onboarding/types.ts) — `OnboardingPreferences` interface; `MAHARASHTRA_DISTRICTS` constant
- [`storage.ts`](src/features/onboarding/storage.ts) — `sessionStorage` CRUD for `OnboardingPreferences` under key `skillsaathi_demo_onboarding_prefs_v1`

#### Career Assessment & Counselling (`src/features/counselling/`)
- [`AssessmentScreen.tsx`](src/features/counselling/AssessmentScreen.tsx) — Orchestrator: shows questions → triggers backend consensus → shows results
- [`assessmentTypes.ts`](src/features/counselling/assessmentTypes.ts) — All assessment type definitions (see Data Models)
- [`assessmentQuestions.ts`](src/features/counselling/assessmentQuestions.ts) — Static question bank (localized, with conditional visibility via `isApplicable`)
- [`assessmentService.ts`](src/features/counselling/assessmentService.ts) — Session persistence, answer validation, results generation
- [`careerRecommendationService.ts`](src/features/counselling/careerRecommendationService.ts) — Deterministic scoring engine; matches answers to `MOCK_COURSES`; generates interest summaries, discussion points, next steps
- [`CounsellingScreen.tsx`](src/features/counselling/CounsellingScreen.tsx) — Chat-style interface post-assessment
- [`counsellingService.ts`](src/features/counselling/counsellingService.ts) — Keyword-matching response generator with 650ms simulated latency
- [`counsellingContent.ts`](src/features/counselling/counsellingContent.ts) — Localized response templates, suggested questions, UI text
- [`AssessmentResults.tsx`](src/features/counselling/AssessmentResults.tsx) — Results display; triggers `familyConsensusService.runFamilyConsensus()`
- [`EvidencePanel.tsx`](src/features/counselling/EvidencePanel.tsx) — Chat sidebar that pins a single `Course` and renders the consensus report (shared priorities, disagreements, pathway recommendations). Accepts optional `consensusRecommendations?: ConsensusRecommendation[]` prop (imported from `familyConsensusService`); inner `MissingEvidenceBadges` component renders `missing_evidence_flags[]` as amber warning badges (`bg:#fffbeb`, `color:#92400e`, `border:#fde68a`) beneath each recommendation's student/parent rationale. Renders nothing when the flags array is empty or undefined. Badge section appears in both the active-course panel and the empty-panel fallback.

#### Course Explorer (`src/features/courses/`)
- [`CourseExplorer.tsx`](src/features/courses/CourseExplorer.tsx) — List view with filter sidebar; calls `courseService.filterCourses()`
- [`CourseFilters.tsx`](src/features/courses/CourseFilters.tsx) — Filter controls for stream, education, mode, fees, duration, financial aid, bookmarks, location
- [`CourseCard.tsx`](src/features/courses/CourseCard.tsx) — Course summary card with bookmark toggle
- [`CourseDetails.tsx`](src/features/courses/CourseDetails.tsx) — Full course detail view; triggers `onConsultCounsellor` callback

### Services

#### API Layer (`src/services/api/`)
- [`client.ts`](src/services/api/client.ts) — `ApiClient` class: typed `fetch` wrapper with `GET/POST/PUT/PATCH/DELETE`. Reads `VITE_API_BASE_URL`. Throws `ApiError` (with `.status`, `.details`) on non-2xx responses
- [`endpoints.ts`](src/services/api/endpoints.ts) — Centralized endpoint constants (`ENDPOINTS.*`)
- [`familyConsensusService.ts`](src/services/api/familyConsensusService.ts) — Core consensus orchestrator (see Data Flow)

#### Course Service (`src/services/courses/`)
- [`courseService.ts`](src/services/courses/courseService.ts) — `CourseService` class with in-memory cache (`cachedCourses`). Methods: `getAllCourses()`, `getCourseById()`, `filterCourses()`, `checkLiveStatus()`
  - Maps snake_case backend payload (`BackendCoursePayload`) to camelCase `Course` type
  - Falls back to `MOCK_COURSES` when backend unavailable
  - `isBackendLive: boolean` flag is updated dynamically on each request

#### Mock Data (`src/services/mocks/`)
- [`courses.ts`](src/services/mocks/courses.ts) — `MOCK_COURSES: Course[]` — 6 seed vocational courses across all streams
- [`analytics.ts`](src/services/mocks/analytics.ts) — `MOCK_ANALYTICS: PlatformAnalytics` — hardcoded dashboard metrics
- [`counselling.ts`](src/services/mocks/counselling.ts) — Mock counselling session data

### i18n (`src/i18n/`)
- [`index.tsx`](src/i18n/index.tsx) — `I18nProvider`, `useTranslation()` hook, `t(key, params?)` resolver
  - Resolution order: active language → English fallback → raw key
  - Supports `{variable}` interpolation in translation strings
- Locale files: [`en.ts`](src/i18n/locales/en.ts), [`mr.ts`](src/i18n/locales/mr.ts), [`hi.ts`](src/i18n/locales/hi.ts)

---

## Current Data Flow & Storage

### Storage Layers (Current State)

| Layer | Mechanism | Key | Contents | Lifecycle |
|---|---|---|---|---|
| Language preference | `localStorage` | `skillsaathi_language` | `'en' \| 'mr' \| 'hi'` | Persists across sessions |
| Onboarding prefs | `sessionStorage` | `skillsaathi_demo_onboarding_prefs_v1` | `OnboardingPreferences` JSON | Session only |
| Assessment session | `sessionStorage` | `skillsaathi_career_guidance_session` | `{ answers, activeQuestionIndex, isCompleted, familyId, updatedAt }` | Session only |
| Active family ID | `sessionStorage` | `skillsaathi_active_family_id` | FastAPI family UUID string | Session only |
| Course bookmark state | Component/feature state | — | `Set<string>` of course IDs | In-memory only (not persisted) |

> **RAG Note:** No database is connected to the frontend. All persistent state is browser-only. The FastAPI backend is the source of truth for course and family data.

### Data Ingestion / File Handling

- **No file upload** mechanism exists in the current frontend
- Course data originates from two sources:
  1. `MOCK_COURSES` array in [`src/services/mocks/courses.ts`](src/services/mocks/courses.ts) — 6 hand-authored `Course` objects (static)
  2. FastAPI `GET /courses` — returns array of `BackendCoursePayload[]`; normalized by `courseService.mapBackendCourse()` which handles both snake_case and camelCase field names
- Assessment question bank is static: [`assessmentQuestions.ts`](src/features/counselling/assessmentQuestions.ts) — compiled into the JS bundle

### Core Data Flow: Assessment → Consensus

```
User answers questions (AssessmentScreen)
  │
  ├─ assessmentService.saveSession() → sessionStorage (incremental)
  │
  └─ On submit: assessmentService.generateResults(answers)
        │
        ├─ careerRecommendationService.generateInterestsSummary(answers)  [local]
        ├─ careerRecommendationService.matchCareerPaths(answers)          [local, scores MOCK_COURSES]
        ├─ careerRecommendationService.generateDiscussionPoints(answers)   [local]
        └─ careerRecommendationService.generateNextSteps()                 [local]
              │
              └─ AssessmentResults renders; triggers:
                    familyConsensusService.runFamilyConsensus(answers)
                          │
                          ├─ [LIVE PATH] apiClient.get('/health') → ok
                          │     ├─ POST /families  → { id }
                          │     │     sessionStorage.setItem('skillsaathi_active_family_id', id)
                          │     ├─ POST /families/{id}/student  ← mapped from answers
                          │     ├─ POST /families/{id}/parent   ← hardcoded defaults + mapped concerns
                          │     ├─ POST /families/{id}/analyze  → ConsensusSummaryData
                          │     └─ return { mode: 'live', summary }
                          │
                          └─ [DEMO PATH] health check fails or backend throws
                                generateLocalFallback(answers) → ConsensusSummaryData (static template)
                                return { mode: 'demo', summary }
```

### API Endpoints (Defined, Backend Expected)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Backend liveness check; returns `{ status: 'ok' }` |
| `GET` | `/courses` | List all courses; supports query params: `stream`, `min_education`, `max_fees`, `district`, `state`, `search` |
| `GET` | `/courses/{id}` | Single course detail |
| `GET` | `/courses/categories` | Course category metadata |
| `GET` | `/courses/featured` | Featured course list |
| `POST` | `/families` | Create family session; body: `{ family_name, language, district, state }` |
| `POST` | `/families/{id}/student` | Submit student profile |
| `POST` | `/families/{id}/parent` | Submit parent profile |
| `POST` | `/families/{id}/analyze` | Run consensus engine → `ConsensusSummaryData` |
| `GET` | `/families/{id}/summary` | Fetch existing consensus summary |
| `POST` | `/families/{id}/confidence` | Submit post-counselling confidence score |
| `DELETE` | `/families/{id}` | Delete family session and dependent records (dev/admin only) |
| `GET` | `/counselling/sessions` | List counselling sessions |
| `GET` | `/counselling/sessions/{id}` | Session detail |
| `GET` | `/counselling/sessions/{id}/messages` | Session messages |
| `GET` | `/counselling/sessions/{id}/recommendations` | Session recommendations |
| `GET` | `/career-pathways/explore` | Career pathway exploration |
| `GET` | `/analytics/overview` | Platform analytics overview |
| `GET` | `/analytics/streams` | Stream distribution analytics |
| `GET` | `/analytics/consensus` | Consensus analytics |

---

## Data Models

### `Course`
```typescript
// src/types/course.ts
interface Course {
  id: string;
  title: string;
  slug: string;
  provider: string;
  stream: VocationalStream;            // 'it_tech' | 'healthcare' | 'renewable_energy' | 'manufacturing_engineering' | 'hospitality_tourism' | 'automotive' | 'agriculture_allied' | 'construction_infrastructure' | 'creative_media'
  durationMonths: number;
  trainingMode: 'offline' | 'online' | 'hybrid';
  certificationBody: CertificationBody; // 'NSDC' | 'NCVET' | 'DGT_ITI' | 'Polytechnic' | 'State_Skill_Mission' | 'Industry_Partner'
  eligibility: CourseEligibility;      // { minAge, maxAge?, minEducation, priorExperienceRequired }
  description: string;
  highlights: string[];
  location: string;
  feesInr: number;
  financialAidAvailable: boolean;
  careerOutcome: CareerOutcome;        // { roleTitle, averageStartingSalaryInr, industryDemand, potentialEmployers }
  rating: number;
  enrolledCount: number;
  // Optional (populated from backend or mock detail data):
  nsqfLevel?: number;
  skillsAcquired?: string[];
  careerProgression?: string;
  practicalHours?: number;
  district?: string;
  state?: string;
  sourceName?: string;
  sourceUrl?: string;
  verificationStatus?: string;
  lastUpdated?: string;
  missingEvidenceFlags?: string[];
}
```

### `CounsellingSession` / `CounsellingMessage`
```typescript
// src/types/counselling.ts
type ParticipantRole = 'student' | 'parent' | 'counsellor' | 'system';

interface CounsellingMessage {
  id: string;
  sessionId: string;
  senderRole: ParticipantRole;
  senderName: string;
  content: string;
  timestamp: string;
  language: string;
  meta?: { intent?, identifiedConcerns?, suggestedAction?, referencedCourseIds? };
}

interface FamilyProfile {
  studentName: string; studentAge: number; currentEducation: string;
  studentInterests: string[];
  parentName?: string; parentOccupation?: string; parentPrimaryConcerns?: string[];
  preferredLocation?: string; monthlyBudgetInr?: number;
}

interface PathwayRecommendation {
  id: string; streamTitle: string; fitScore: number; keySkills: string[];
  rationaleForStudent: string; rationaleForParent: string;
  estimatedTimelineMonths: number;
  expectedSalaryRangeInr: { min: number; max: number };
  recommendedCourseIds: string[];
}
```

### `AssessmentQuestion` / `AssessmentAnswers`
```typescript
// src/features/counselling/assessmentTypes.ts
type AssessmentResponseType = 'single_choice' | 'multiple_choice' | 'free_text' | 'numeric_range' | 'rating_scale' | 'yes_no_unsure';
type QuestionCategory = 'participant' | 'education' | 'interests' | 'strengths' | 'environment' | 'learning_style' | 'priorities' | 'followup' | 'confidence' | 'concerns' | 'deep_dive' | 'progression' | 'course_explore' | 'additional';

interface AssessmentQuestion {
  id: string;
  category: QuestionCategory;
  categoryLabel: LocalizedString;     // { en, mr, hi? }
  question: LocalizedString;
  responseType: AssessmentResponseType;
  required: boolean;
  options?: QuestionOption[];
  maxSelections?: number;
  numericConfig?: NumericRangeConfig;
  ratingConfig?: RatingScaleConfig;
  isApplicable?: (answers: AssessmentAnswers) => boolean; // conditional visibility
}

type AssessmentAnswers = Record<string, string | string[] | number>;
```

### `ConsensusSummaryData` (Backend Response / Local Fallback)
```typescript
// src/services/api/familyConsensusService.ts
interface ConsensusSummaryData {
  family_id: string;
  analyzed_at: string;
  status: string;
  overall_consensus_readiness: 'high' | 'moderate' | 'requires_dialogue';
  student_priorities?: string[];
  parent_priorities?: string[];
  shared_strengths: ConsensusSharedPriority[];           // { topic, detail, alignment_score }
  identified_disagreements: ConsensusDisagreement[];     // { topic, student_stance, parent_stance, severity, resolution_pathway }
  unresolved_concerns?: string[];
  top_pathway_recommendations: ConsensusRecommendation[]; // includes fit_score, fees_inr, nsqf_level, etc.
  pathway_comparison?: PathwayComparison;
  discussion_guide: string[];
  pre_confidence_student?: number;
  pre_confidence_parent?: number;
  post_confidence_student?: number;
  post_confidence_parent?: number;
  confidence_status?: 'opt_in_pending' | 'actual_delta_recorded';
  counselling_mode?: 'deterministic' | 'ai_grounded';
  disclaimer: string;
  is_demo_data: boolean;
}
```

### `PlatformAnalytics`
```typescript
// src/types/analytics.ts
interface PlatformAnalytics {
  lastUpdated: string;
  overviewMetrics: MetricSummary[];
  streamDistributions: StreamInterestDistribution[];
  topParentalConcerns: ParentalConcernMetric[];
  regionalDistribution: RegionalMetric[];
}
```

### Common API Wrappers
```typescript
// src/types/common.ts
interface ApiResponse<T>       { success: boolean; data: T; message?: string; timestamp: string; }
interface PaginatedResponse<T> { items: T[]; total: number; page: number; pageSize: number; totalPages: number; }
interface ApiErrorPayload      { success: false; error: { code, message, details? }; timestamp: string; }
type SupportedLanguage = 'en' | 'hi' | 'mr' | 'ta' | 'te' | 'bn' | 'gu' | 'kn' | 'pa' | 'or';
```

---

## RAG Integration Notes

### What to Embed for RAG

| Document type | Source | Suggested chunking |
|---|---|---|
| Course catalog | `MOCK_COURSES` + `GET /courses` | One chunk per `Course` object; include `title`, `description`, `highlights`, `skillsAcquired`, `careerOutcome`, `certificationBody`, `feesInr`, `nsqfLevel` |
| Assessment Q&A bank | `assessmentQuestions.ts` | One chunk per `AssessmentQuestion`; embed all localized `label` + `description` fields |
| Counselling response templates | `counsellingContent.ts` | One chunk per response template category |
| Consensus report | `ConsensusSummaryData` (live or demo) | One chunk per `ConsensusRecommendation`; embed `course_title`, `student_rationale`, `parent_rationale`, `trade_offs` |

### Integration Points

- **Primary RAG ingestion target:** `GET /courses` — structured JSON, backend-authoritative; `BackendCoursePayload` has `source_url`, `verification_status`, `missing_evidence_flags` metadata suited for RAG provenance tracking
- **Retrieval trigger:** Currently happens in `careerRecommendationService.matchCareerPaths()` — deterministic scoring over in-memory array. Replace with vector similarity search over embedded course catalog
- **LLM handoff point:** `familyConsensusService.runFamilyConsensus()` — already structured as an async pipeline that POST's to backend. The backend `counselling_mode: 'ai_grounded'` flag signals when Gemini is connected
- **Session context for RAG:** `AssessmentAnswers` (answers record) is the natural query context; `FamilyProfile` maps to structured metadata filters for retrieval
- **Missing evidence flags:** `Course.missingEvidenceFlags[]` / `ConsensusRecommendation.missing_evidence_flags[]` — explicitly mark data gaps; use as negative signals or uncertainty annotations in RAG responses. **Now visually surfaced in `EvidencePanel.tsx`** via the inner `MissingEvidenceBadges` component — renders each flag string as an amber-styled badge beneath each pathway's rationale text. Empty or undefined arrays render nothing (zero noise when all evidence is present).


### RAG Models & Vector Store Configuration

The RAG pipeline utilizes the following Google Gemini models:

| Component | Model Identifier | API Endpoint / Method | Role & Description | Fallback Mechanism |
|---|---|---|---|---|
| **Course & Query Embeddings** | `gemini-embedding-2` | `models/gemini-embedding-2:batchEmbedContents`<br>`models/gemini-embedding-2:embedContent` | Ingestion & query vectorization (`taskType: RETRIEVAL_DOCUMENT` / `RETRIEVAL_QUERY`). Embeds course titles, descriptions, NSQF levels, eligibility, and curriculum highlights. | Pure-Python in-memory TF-IDF vectorizer + cosine similarity ranking (`_use_vectors=False`). |
| **Consensus Report Synthesis** | `gemini-3.8-flash` | `models/gemini-3.8-flash:generateContent` | Grounded multi-perspective consensus generation (`POST /api/v1/families/{id}/analyze`). Produces structured JSON consensus summary, alignment scores, and unresolved concerns. | Deterministic `FamilyConsensusEngine.analyze_family()` rule engine. |
| **AI Counselling Enhancement** | `gemini-3.8-flash` | `models/gemini-3.8-flash:generateContent` | `AICounsellorAdapter.enhance_analysis()` contextual tone adaptation and actionable family dialogue tips. | Returns base deterministic analysis unchanged. |

### UI Data Gap Surfacing

**Component:** `MissingEvidenceBadges` (inner component of `EvidencePanel.tsx`)

- **Trigger:** `ConsensusRecommendation.missing_evidence_flags` array (non-empty)
- **Visual style:** Inline badge row; each flag is a `<span>` with `bg:#fffbeb` / `color:#92400e` / `border:1px solid #fde68a` / `borderRadius:4px` / `fontSize:0.6875rem`; prefixed with `AlertTriangle` lucide icon
- **Placement:** Rendered beneath `student_rationale` + `parent_rationale` for each pathway in both panel modes (active-course and empty-panel fallback)
- **Null safety:** Guards on empty/undefined array — no render cost when flags are absent
- **Prop threading:** Parent must pass `consensusRecommendations` from `ConsensusSummaryData.top_pathway_recommendations` (available in `AssessmentResults.tsx` after `runFamilyConsensus()` resolves)
