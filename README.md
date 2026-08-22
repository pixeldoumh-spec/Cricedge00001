# CricEdge Cricket Analytics Engine

This is a Bloomberg-Terminal-grade cricket analytics engine that predicts match outcomes and enables sophisticated betting portfolios.

## Quick Start

### Prerequisites
- Node.js 18+ (frontend)
- Python 3.9+ (backend)
- MongoDB (for data persistence)

### Frontend Setup

```bash
cd frontend
npm install
# Create .env.local file with:
# REACT_APP_BACKEND_URL=http://localhost:8000/api
npm start
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Create .env file with:
# MONGO_URL=mongodb://localhost:27017
# DB_NAME=cricedge
# ODDS_API_KEY=your_key_here
# ODDS_API_BASE=https://api.thesportsdb.com/api/v1
# CORS_ORIGINS=http://localhost:3000

# Run the server
python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

API docs available at [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Architecture

### Frontend (React 19 + Tailwind)
- **Pages**: Fixture Explorer (`/`), Fixture Detail (`/fixture/:id`), Portfolios (`/portfolio`)
- **Builders**: Same-Game Multi (one fixture, multiple markets) & Multibet (multiple fixtures)
- **State**: React hooks + localStorage for persistence
- **API**: Centralized axios client with retry logic & error handling

### Backend (FastAPI + PyMongo)
- **Endpoints**:
  - `GET /api/fixtures` — list upcoming fixtures
  - `GET /api/fixtures/{id}/predictions` — market odds & AI predictions
  - `GET /api/health` — model status
  - `POST /api/admin/train-model` — retrain ML model
- **Models**: Logistic regression per cricket format (T20/ODI/Test)
- **Data**: MongoDB for fixtures, odds, and model artifacts

---

## Testing

### Run Frontend Tests
```bash
cd frontend
npm test
```

### Run Backend Tests
```bash
cd backend
pytest
# With coverage:
pytest --cov=. --cov-report=html
```

---

## Features

✅ **Fixture Explorer** — Browse live fixtures with AI confidence scores  
✅ **Market Predictions** — 6+ market types per format (Match Winner, Totals, Player Props)  
✅ **Same-Game Multi** — Build correlated multis from a single match  
✅ **Multibet Builder** — Cross-fixture combination engine  
✅ **Live Odds** — Real-time bookmaker odds integration  
✅ **Model Insights** — See training data quality & Elo-based rankings  

---

## Known Issues & Roadmap

### High Priority
- [ ] Add JWT authentication & rate limiting
- [ ] Implement WebSocket for live odds updates
- [ ] Refactor `App.js` into modular components *(IN PROGRESS)*

### Medium Priority
- [ ] Add frontend unit tests (Jest + React Testing Library)
- [ ] Improve error handling & user feedback
- [ ] Add data validation (Pydantic on backend, Zod on frontend)

### Nice-to-Have
- [ ] Historical performance dashboard
- [ ] Model retraining scheduler
- [ ] User preferences & saved portfolios

---

## Environment Variables

### Frontend (`.env.local`)
```
REACT_APP_BACKEND_URL=http://localhost:8000/api
```

### Backend (`.env`)
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=cricedge
ODDS_API_KEY=your_key
ODDS_API_BASE=https://api.thesportsdb.com/api/v1
CORS_ORIGINS=http://localhost:3000,https://example.com
```

---

## API Documentation

Full interactive API docs at `/docs` (Swagger UI) or `/redoc` (ReDoc).

### Example Requests

**Get upcoming fixtures:**
```bash
curl http://localhost:8000/api/fixtures?format=T20
```

**Get fixture predictions:**
```bash
curl http://localhost:8000/api/fixtures/f-001/predictions
```

**Check API health:**
```bash
curl http://localhost:8000/api/health
```

**Trigger model retraining:**
```bash
curl -X POST http://localhost:8000/api/admin/train-model
```

---

## Contributing

1. Create a branch: `git checkout -b feature/my-feature`
2. Make changes and add tests
3. Run tests: `npm test` (frontend) or `pytest` (backend)
4. Commit: `git commit -am 'Add my feature'`
5. Push: `git push origin feature/my-feature`
6. Open a PR

---

## License

MIT
