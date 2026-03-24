# K-Drama Actress Tier List

A full-stack web app for ranking Korean drama actresses into tiers, tracking your drama watchlist, and discovering new shows through AI-powered recommendations.

**Live:** [kdrama-ranking-1.vercel.app](https://kdrama-ranking-1.vercel.app/)

## Features

### Tier Ranking System
- Drag-and-drop actresses into 6 tiers (S+, S, A, B, C, D)
- Touch drag support on mobile (long-press to pick up)
- Search, filter by genre, and sort the unranked pool
- Export your tier list as a PNG image

### Actress Profiles
- Detailed profiles with bio, photo gallery, filmography, and awards
- Auto-populated from TMDB (The Movie Database)
- Gallery photos hosted on Cloudinary CDN for fast loading
- Gallery size scales with tier placement
- Filmography split into K-Dramas vs TV Shows

### Drama Tracking
- Rate dramas 1-10 stars
- Track watch status: Watching, Plan to Watch, Watched, Dropped
- Dedicated watchlist page with filters
- Drama detail pages with cast, synopsis, and metadata

### Discovery
- **Browse Dramas** — timeline view of all dramas by year
- **Compare** — side-by-side actress comparison with shared dramas highlighted
- **Stats** — tier distribution, genre breakdown, full roster view
- **For You** — AI-powered drama recommendations based on your rankings and ratings

### AI Chat Assistant
- Ask questions about K-dramas and get personalized suggestions
- Context-aware — knows your watch history and tier preferences
- Powered by Claude (Anthropic)

### Authentication
- Sign in with Google (Firebase) to save your data across devices
- Guest mode available for browsing without an account

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite |
| Backend | Python, FastAPI, httpx (async) |
| Database | MongoDB (Atlas) |
| Auth | Firebase Authentication |
| AI | Anthropic Claude API |
| External Data | TMDB API |
| Image CDN | Cloudinary |
| CI/CD | GitHub Actions |
| Testing | Vitest + RTL + MSW (frontend), pytest + respx (backend) |
| Deployment | Vercel (frontend), Railway (backend), MongoDB Atlas |
| Containerization | Docker + Docker Compose |

## Project Structure

```
kdrama-ranking/
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main tier list page
│   │   ├── ActressDetail.tsx    # Actress profile page
│   │   ├── DramaDetail.tsx      # Drama detail page
│   │   ├── Compare.tsx          # Side-by-side comparison
│   │   ├── Timeline.tsx         # Browse dramas by year
│   │   ├── Recommendations.tsx  # AI-powered recommendations + chat
│   │   ├── StatsPage.tsx        # Ranking statistics
│   │   ├── Watchlist.tsx        # Drama watch tracking
│   │   ├── ActressContext.tsx   # Shared state (SWR pattern)
│   │   ├── AuthContext.tsx      # Firebase auth provider
│   │   ├── ErrorBoundary.tsx    # Global error boundary
│   │   ├── useTouchDrag.ts     # Mobile drag-and-drop hook
│   │   ├── api.ts              # API client
│   │   ├── styles/             # Modular CSS (10 files)
│   │   └── __tests__/          # 70 frontend tests
│   ├── Dockerfile              # Multi-stage build (Node + nginx)
│   └── package.json
├── backend/
│   ├── main.py                 # FastAPI app (25+ endpoints)
│   ├── models.py               # Pydantic schemas
│   ├── auth.py                 # Firebase token verification
│   ├── database.py             # MongoDB connection
│   ├── seed.py                 # Initial data seeding
│   ├── drama_metadata.py       # Preloaded drama metadata
│   ├── rescrape_all.py         # Gallery photo scraper (Cloudinary)
│   ├── tests/                  # 114 backend tests
│   └── Dockerfile              # Python 3.12 slim
├── .github/workflows/ci.yml    # CI pipeline (tests, lint, build)
├── docker-compose.yml          # Local dev with MongoDB
├── render.yaml                 # Railway deployment config
├── run.bat / run.sh            # One-command local launchers
└── README.md
```

## Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) v18+
- [Python](https://www.python.org/downloads/) 3.10+
- [MongoDB](https://www.mongodb.com/try/download/community) running locally (or use Docker)

### Quick Start (Docker)

```bash
docker compose up --build
```

This starts the backend (port 8000), frontend (port 3000), and a local MongoDB instance. Open `http://localhost:3000`.

### Quick Start (Windows)

```bash
run.bat
```

This installs dependencies and launches both servers. The app opens at `http://localhost:5173`.

### Manual Setup

**Backend:**

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # Edit with your API keys
python -m uvicorn main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

#### Backend (`backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGODB_URI` | Yes | MongoDB connection string |
| `TMDB_API_KEY` | Yes | [TMDB API](https://www.themoviedb.org/settings/api) key for actress/drama data |
| `FIREBASE_PROJECT_ID` | Yes | Firebase project ID |
| `FIREBASE_CLIENT_EMAIL` | Yes | Firebase service account email |
| `FIREBASE_PRIVATE_KEY` | Yes | Firebase service account private key |
| `ADMIN_API_KEY` | Yes | Secret key for admin endpoints |
| `ALLOWED_ORIGINS` | No | Comma-separated CORS origins (defaults to localhost) |
| `ANTHROPIC_API_KEY` | No | Claude API key for AI recommendations |
| `CLOUDINARY_CLOUD_NAME` | No | Cloudinary cloud name for gallery photos |
| `CLOUDINARY_API_KEY` | No | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | No | Cloudinary API secret |

#### Frontend (`frontend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | Yes | Backend API base URL (e.g. `http://localhost:8000/api`) |

## Running Tests

```bash
# Frontend (70 tests)
cd frontend && npm test

# Backend (114 tests)
cd backend && python -m pytest tests/ -v
```

Tests run automatically on every push via GitHub Actions CI.

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/actresses` | Optional | List actresses (supports `genre`, `search` params) |
| GET | `/api/actresses/:id` | Optional | Get actress details with user-specific ratings |
| POST | `/api/actresses` | No | Add new actress (TMDB or manual) |
| PATCH | `/api/actresses/:id/tier` | Required | Update tier placement |
| DELETE | `/api/actresses/:id` | Admin | Delete an actress |
| GET | `/api/dramas/:title` | Optional | Get drama details with cast |
| PATCH | `/api/actresses/:id/dramas/:title/watch-status` | Required | Update watch status |
| PATCH | `/api/actresses/:id/dramas/:title/rating` | Required | Rate a drama (1-10) |
| GET | `/api/watchlist` | Required | Get user's watchlist |
| GET | `/api/stats` | Optional | Tier and genre statistics |
| GET | `/api/search-actress` | No | Search TMDB for actresses (rate limited) |
| GET | `/api/search-actress/:tmdb_id` | No | Fetch full actress data from TMDB |
| POST | `/api/chat` | No | AI chat (streaming, rate limited) |
| POST | `/api/refresh-all` | Admin | Refresh all TMDB data |
| POST | `/api/reset` | Admin | Reset to seed data |

Interactive API docs available at `/docs` when running locally.

## Deployment

### Database — MongoDB Atlas (free)

1. Create a free cluster at [mongodb.com/atlas](https://www.mongodb.com/atlas)
2. Create a database user and whitelist `0.0.0.0/0`
3. Copy the connection string

### Backend — Railway

1. Push to GitHub
2. Create a new project on [railway.app](https://railway.app)
3. Set root directory to `backend`
4. Add environment variables (see table above)
5. Deploy

### Frontend — Vercel

1. Import your GitHub repo on [vercel.com](https://vercel.com)
2. Set root directory to `frontend`, framework preset to Vite
3. Add `VITE_API_URL` pointing to your backend
4. Deploy

## Security

- CORS restricted to configured origins (no wildcard in production)
- Firebase token verification on all authenticated endpoints
- Admin endpoints require a separate API key
- Rate limiting on expensive operations (TMDB search, AI chat, data refresh)
- TMDB API key never exposed to the client
- In-memory TTL cache (10 min) to reduce external API calls


## License

MIT
