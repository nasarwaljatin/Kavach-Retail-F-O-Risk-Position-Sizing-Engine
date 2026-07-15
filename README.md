# Kavach — Retail F&O Risk & Position-Sizing Engine

A real-time guardrail engine that sits between you and your broker: it sizes every position, watches your account against hard risk limits, and can auto-square-off before a normal trading day turns into the kind of day SEBI's loss statistics are made of.

**Phase 1: personal use, one account, one broker.**
**Phase 2: productize for other traders/brokers, once Phase 1 has a live track record.**

---

## Why this exists

SEBI's FY25 study found individual F&O traders' net losses widened 41% YoY to about ₹1.06 lakh crore, with 91% of traders ending the year in the red and an average loss of ~₹1.1 lakh per trader. The pattern behind most of that isn't bad direction calls — it's oversized positions, no stop discipline, and leverage abuse around expiry. This project attacks that specific failure mode, on your own account first.

**What this is:** a sizing + guardrail layer you run against your own capital.
**What this isn't:** a strategy that predicts direction, a signal seller, or investment advice. It doesn't decide *what* to trade — it decides *how much*, and when to stop you.

---

## Tech stack

- **Backend:** Python, FastAPI, Celery + Redis (broker) for periodic risk checks
- **DB:** PostgreSQL (trade history, risk events, config) via SQLAlchemy + Alembic
- **Cache/pub-sub:** Redis (live position state → dashboard)
- **Frontend:** Next.js 14, WebSocket/SSE client for live updates
- **Broker:** Angel One SmartAPI (free — REST for orders/positions/funds, WebSocket for live quotes)
- **Deploy:** Docker Compose locally

---

## Core risk logic

### 1. Fractional Kelly sizing
- Sizes position as a fraction of full Kelly edge formula.

### 2. Volatility-adjusted sizing
- Sizes position such that a stop-out at a multiple of ATR loses exactly a fixed % of capital.

### 3. Circuit breakers (checked every poll cycle)
- DAILY_LOSS_LIMIT: triggers if daily loss % exceeds limit.
- MARGIN_CAP: triggers if margin utilisation % exceeds limit.
- CONCENTRATION: triggers if any single position exposure % of capital exceeds limit.
- ORDER_VELOCITY_REVENGE_TRADING: triggers if order count in last 10 minutes exceeds limit.
- EXPIRY_DAY_OVERSIZE: triggers if new position size on expiry day exceeds baseline * dampener.

---

## Local setup

```bash
cp .env.example .env        # fill in Angel One credentials + secret key
docker compose up --build   # starts postgres, redis, backend, frontend
docker compose exec backend alembic upgrade head
```

Backend: `http://localhost:8000` · Frontend: `http://localhost:3000`
