# AgriSpray API

Smart spray timing recommendation engine for Saskatchewan farmers.

## Quick start

```bash
cp .env.example .env
docker-compose up --build
```

API docs at http://localhost:8000/docs

## Project structure

```
agrispray/
├── app/
│   ├── api/                  # FastAPI route handlers
│   │   ├── fields.py         # Farm field CRUD
│   │   ├── recommendations.py # Core recommendation endpoint
│   │   └── weather.py        # Weather passthrough endpoints
│   ├── core/
│   │   └── config.py         # Settings from .env
│   ├── db/
│   │   ├── base.py           # SQLAlchemy declarative base
│   │   └── session.py        # Async engine + session factory
│   ├── models/
│   │   ├── field.py          # Farm, Field, CropType
│   │   └── spray_event.py    # Spray event log
│   ├── schemas/
│   │   ├── field.py          # Pydantic request/response models
│   │   └── recommendation.py
│   ├── services/
│   │   ├── gdd_engine.py     # Growing Degree Day accumulation + stage evaluator
│   │   ├── spray_scorer.py   # Weather condition scoring
│   │   ├── recommendation_engine.py  # Combines both signals
│   │   └── weather_client.py # Environment Canada + John Deere API clients
│   └── main.py               # FastAPI app + lifespan
├── tests/
│   ├── unit/
│   │   ├── test_gdd_engine.py
│   │   └── test_spray_scorer.py
│   └── integration/          # (next step — API endpoint tests)
├── .env.example
├── .gitlab-ci.yml
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Core endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/recommendations/{field_id}` | Get spray recommendation for a field |
| POST | `/api/v1/fields/` | Register a new field |
| GET | `/api/v1/fields/{field_id}` | Get field details |
| GET | `/api/v1/fields/farm/{farm_id}` | List all fields for a farm |
| GET | `/api/v1/weather/current?lat=&lon=` | Current conditions |
| GET | `/api/v1/weather/forecast?lat=&lon=` | 48-hour forecast |
| GET | `/health` | Health check |

## How the decision engine works

```
Plant date + LSD coords
        │
        ▼
  Historical weather (EC API)
        │
        ▼
  GDD accumulation ──► Plant stage (pre-emergence / optimal / too late)
        │
        │  If stage is NOT spray-eligible ──► DO NOT SPRAY
        │
        ▼
  Current conditions + forecast
        │
        ▼
  Spray scorer (wind / temp / humidity / rain / inversion)
        │
        ▼
  SPRAY NOW  /  WAIT  /  DO NOT SPRAY  + plain-language reason
```

## Running tests

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit/ -v
```

## Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Async PostgreSQL connection string | — |
| `ECCC_BASE_URL` | Environment Canada API base | `https://api.weather.gc.ca` |
| `JOHN_DEERE_CLIENT_ID` | JD Operations Center OAuth client | *(optional)* |
| `JOHN_DEERE_CLIENT_SECRET` | JD Operations Center OAuth secret | *(optional)* |
| `SECRET_KEY` | App secret key | change in prod |

## GitLab CI

The pipeline runs on every push:
1. **unit-tests** — pytest with coverage report
2. **lint** — ruff code quality check
3. **build-image** — Docker image to GitLab registry *(main branch only)*
4. **deploy-staging** — deploy hook *(main branch only, configure your target)*
