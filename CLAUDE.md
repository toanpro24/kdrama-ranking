# K-Drama Actress Tier List

A social platform where users rank K-drama actresses into tier lists, follow other users, compare rankings, and get AI-powered drama recommendations.

**Live Demo:** Deployed on Vercel (frontend) + Railway (backend)

## Architecture

```
React/TypeScript (Vite) → FastAPI (Python) → MongoDB Atlas
        ↓                       ↓
  Firebase Auth          Claude API (AI Chat)
                               ↓
                         TMDB API (drama data)
```

- **Frontend:** React 18, TypeScript, Vite, deployed on Vercel
- **Backend:** Python 3.12, FastAPI, deployed on Railway via Docker
- **Database:** MongoDB (Atlas in prod, Docker locally)
- **Auth:** Firebase Auth (Google OAuth)
- **AI:** Anthropic Claude Haiku 4.5 for streaming recommendations
- **Images:** Cloudinary CDN
- **CI/CD:** GitHub Actions (tests, lint, build on every push)

## Project Structure

```
kdrama-ranking/
├── backend/
│   ├── main.py              # FastAPI app entry, lifespan, middleware, router registration
│   ├── models.py            # Pydantic models (Drama, ActressCreate, TierUpdate, ProfileUpdate)
│   ├── database.py          # MongoDB collections, indexes
│   ├── auth.py              # Firebase token verification (get_current_user, require_user)
│   ├── helpers.py           # Shared utils (_oid, _merge_user_data, _ensure_user_list, TIER_WEIGHT)
│   ├── tmdb.py              # TMDB API integration (search, credits, gallery photos)
│   ├── rate_limit.py        # SlowAPI rate limiter
│   ├── seed.py              # Default actress seed data
│   ├── drama_metadata.py    # Static drama metadata (DRAMA_META dict)
│   ├── Dockerfile           # Python 3.12-slim, uvicorn
│   ├── routes/
│   │   ├── actresses.py     # CRUD, tier updates, TMDB search (GET/POST /actresses, PATCH /tier)
│   │   ├── dramas.py        # Drama details, watchlist (GET /dramas/:title, GET /watchlist)
│   │   ├── profiles.py      # User profiles, sharing (GET/PUT /profile, GET /shared/:slug)
│   │   ├── social.py        # Follow system (POST/DELETE /follow/:slug, GET /following)
│   │   ├── leaderboard.py   # Global rankings, trending, compare (GET /leaderboard, /trending, /compare)
│   │   ├── chat.py          # AI chat with Claude API streaming SSE (POST /chat)
│   │   └── admin.py         # Admin operations (API key protected)
│   └── tests/
│       ├── conftest.py      # Pytest fixtures (test client, mock DB)
│       ├── test_api.py      # Actress CRUD endpoint tests
│       ├── test_helpers.py  # Helper function tests
│       ├── test_leaderboard.py
│       ├── test_models.py   # Pydantic validation tests
│       ├── test_profiles.py
│       ├── test_social.py
│       ├── test_tmdb.py
│       └── test_validation.py
├── frontend/
│   └── src/
│       ├── App.tsx           # Main tier list view (drag-and-drop, search, add actresses)
│       ├── ActressCard.tsx   # Card component (image, name, tier badge)
│       ├── ActressDetail.tsx # Full profile (dramas, gallery, ratings, community stats)
│       ├── ActressSelect.tsx # Actress picker component
│       ├── ActressContext.tsx # React context for actress state management
│       ├── AuthContext.tsx   # Firebase auth context (user, signIn, logout)
│       ├── Leaderboard.tsx   # Global rankings across public users
│       ├── CompareLists.tsx  # Side-by-side tier list comparison with agreement %
│       ├── Compare.tsx       # Compare page wrapper
│       ├── Watchlist.tsx     # Drama tracking (watching, plan to watch, dropped)
│       ├── Recommendations.tsx # AI chat interface
│       ├── SharedTierList.tsx  # Public view of someone's tier list
│       ├── FollowingPage.tsx # Users you follow
│       ├── StatsPage.tsx     # Personal analytics
│       ├── UserSettings.tsx  # Profile editing, visibility controls
│       ├── Timeline.tsx      # Activity timeline
│       ├── DramaDetail.tsx   # Individual drama page
│       ├── api.ts            # API client (fetch wrappers, auth headers, SSE streaming)
│       ├── types.ts          # TypeScript interfaces (Actress, Drama, UserProfile, etc.)
│       ├── constants.ts      # Tier definitions, genre list
│       ├── firebase.ts       # Firebase config
│       ├── toast.ts          # Toast notification utility
│       ├── useTouchDrag.ts   # Custom hook for mobile drag-and-drop
│       └── __tests__/        # 12 test files (Vitest + React Testing Library)
├── docker-compose.yml        # 3 services: backend, frontend, mongo
└── render.yaml               # Render deployment config
```

## Database Schema (MongoDB)

7 collections with the following indexes:

| Collection | Purpose | Key Indexes |
|---|---|---|
| `actresses` | Shared actress data (name, dramas, gallery) | `dramas.title` |
| `user_rankings` | Per-user tier rankings (splus/s/a/b/c/d) | `(userId, actressId)` unique |
| `user_drama_status` | Per-user watch status & ratings | `(userId, actressId, dramaTitle)` unique |
| `user_actresses` | Which actresses each user has in their pool | `(userId, actressId)` unique |
| `user_profiles` | Display name, bio, share slug, visibility | `userId` unique, `shareSlug` unique sparse |
| `user_follows` | Follow relationships | `(followerId, followingId)` unique |
| `leaderboard_cache` | Cached aggregated rankings | `cachedAt` TTL 5 min |

**Design:** Actress data is shared (one source of truth). User-specific data (tiers, ratings, watch status) lives in separate collections joined by actressId. This is a normalized design avoiding data duplication.

## Key Design Patterns

- **Leaderboard cache stampede protection:** `threading.Lock()` ensures only one thread rebuilds the cache when TTL expires
- **TTL index:** MongoDB auto-deletes leaderboard cache after 5 min (`expireAfterSeconds=300`)
- **Lazy user initialization:** `_ensure_user_list()` copies default seed actresses on first login
- **Slug collision handling:** Profile slugs retry with `-1`, `-2` suffixes on `DuplicateKeyError`
- **Guest mode:** `get_current_user()` returns `None` for unauthenticated users; `require_user()` enforces auth
- **SSE streaming:** AI chat uses Server-Sent Events for real-time token streaming from Claude API
- **Per-user data merging:** `_merge_user_data()` overlays user tiers/ratings onto shared actress docs

## Running Locally

```bash
# With Docker
docker compose up

# Without Docker
cd backend && pip install -r requirements.txt && uvicorn main:app --reload
cd frontend && npm install && npm run dev
```

## Environment Variables

Backend (`.env`):
- `MONGODB_URI` - MongoDB connection string
- `ANTHROPIC_API_KEY` - Claude API key for AI chat
- `TMDB_API_KEY` - TMDB API key for actress/drama search
- `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY` - Firebase Admin SDK
- `ALLOWED_ORIGINS` - CORS origins (comma-separated)
- `ADMIN_API_KEY` - Admin endpoint protection

Frontend (`.env`):
- `VITE_API_URL` - Backend API base URL
- `VITE_FIREBASE_*` - Firebase client config

## Testing

```bash
# Backend (136 tests)
cd backend && pytest

# Frontend (132 tests)
cd frontend && npm test
```

268+ total tests across 20 test suites. CI/CD runs on every push via GitHub Actions.

## Code Conventions

- Backend uses FastAPI dependency injection for auth (`Depends(get_current_user)`)
- All routes are organized in `routes/` as `APIRouter` modules with `/api` prefix
- Pydantic models for request/response validation
- Frontend uses React Context for global state (ActressContext, AuthContext)
- TypeScript interfaces in `types.ts`, API calls in `api.ts`
- Rate limiting via SlowAPI on write/expensive endpoints
- IMPORTANT: This project is about K-drama actresses only. Never add actors or male leads.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **kdrama-ranking** (663 symbols, 1519 relationships, 32 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## When Debugging

1. `gitnexus_query({query: "<error or symptom>"})` — find execution flows related to the issue
2. `gitnexus_context({name: "<suspect function>"})` — see all callers, callees, and process participation
3. `READ gitnexus://repo/kdrama-ranking/process/{processName}` — trace the full execution flow step by step
4. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` — see what your branch changed

## When Refactoring

- **Renaming**: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first. Review the preview — graph edits are safe, text_search edits need manual review. Then run with `dry_run: false`.
- **Extracting/Splitting**: MUST run `gitnexus_context({name: "target"})` to see all incoming/outgoing refs, then `gitnexus_impact({target: "target", direction: "upstream"})` to find all external callers before moving code.
- After any refactor: run `gitnexus_detect_changes({scope: "all"})` to verify only expected files changed.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Tools Quick Reference

| Tool | When to use | Command |
|------|-------------|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360-degree view of one symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers/importers | MUST update these |
| d=2 | LIKELY AFFECTED — indirect deps | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/kdrama-ranking/context` | Codebase overview, check index freshness |
| `gitnexus://repo/kdrama-ranking/clusters` | All functional areas |
| `gitnexus://repo/kdrama-ranking/processes` | All execution flows |
| `gitnexus://repo/kdrama-ranking/process/{name}` | Step-by-step execution trace |

## Self-Check Before Finishing

Before completing any code modification task, verify:
1. `gitnexus_impact` was run for all modified symbols
2. No HIGH/CRITICAL risk warnings were ignored
3. `gitnexus_detect_changes()` confirms changes match expected scope
4. All d=1 (WILL BREAK) dependents were updated

## Keeping the Index Fresh

After committing code changes, the GitNexus index becomes stale. Re-run analyze to update it:

```bash
npx gitnexus analyze
```

If the index previously included embeddings, preserve them by adding `--embeddings`:

```bash
npx gitnexus analyze --embeddings
```

To check whether embeddings exist, inspect `.gitnexus/meta.json` — the `stats.embeddings` field shows the count (0 means no embeddings). **Running analyze without `--embeddings` will delete any previously generated embeddings.**

> Claude Code users: A PostToolUse hook handles this automatically after `git commit` and `git merge`.

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
