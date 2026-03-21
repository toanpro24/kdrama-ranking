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
