# K-Drama Actress Ranking

A full-stack web app for ranking and tier-listing K-Drama actresses. Browse actresses, explore their dramas, assign tier rankings (S+, S, A, B, C, D), and view stats.

## Tech Stack

- **Frontend:** React + TypeScript + Vite
- **Backend:** Python + FastAPI
- **Database:** MongoDB

## Prerequisites

- [Node.js](https://nodejs.org/) (v18+)
- [Python](https://www.python.org/downloads/) (3.10+)
- [MongoDB](https://www.mongodb.com/try/download/community) running on `localhost:27017`

## Getting Started

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn main:app --reload
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

### Quick Start (Windows)

Run `run.bat` to install dependencies and launch both servers automatically.

## Deploying Online

### 1. Database — MongoDB Atlas (free)

1. Create an account at [mongodb.com/atlas](https://www.mongodb.com/atlas)
2. Create a free shared cluster
3. Create a database user and whitelist `0.0.0.0/0` for access
4. Get your connection string: `mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/kdrama_ranking`

### 2. Backend — Render (free)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New** → **Web Service**
3. Connect your GitHub repo, set **Root Directory** to `backend`
4. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
5. Add environment variable: `MONGODB_URI` = your Atlas connection string
6. Deploy — note your URL (e.g. `https://kdrama-ranking-api.onrender.com`)

### 3. Frontend — Vercel (free)

1. Go to [vercel.com](https://vercel.com) → **New Project** → import your GitHub repo
2. Settings:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Vite
3. Add environment variable: `VITE_API_URL` = `https://kdrama-ranking-api.onrender.com/api`
4. Deploy

Your app will be live at the Vercel URL.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/actresses` | List all actresses (supports `genre` and `search` query params) |
| GET | `/api/actresses/:id` | Get a single actress |
| POST | `/api/actresses` | Add a new actress |
| PATCH | `/api/actresses/:id/tier` | Update an actress's tier |
| PATCH | `/api/actresses/bulk-tier` | Bulk update tiers |
| DELETE | `/api/actresses/:id` | Delete an actress |
| GET | `/api/dramas` | List all dramas |
| GET | `/api/dramas/:title` | Get drama details |
| GET | `/api/stats` | Get ranking statistics |
| POST | `/api/reset` | Reset data to defaults |
