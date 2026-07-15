# Kavach — Retail F&O Risk & Position-Sizing Engine

*(placeholder name, meaning "shield/armor" — rename freely)*

A real-time guardrail engine that sits between you and your broker: it sizes every position, watches your account against hard risk limits, and can auto-square-off before a normal trading day turns into the kind of day SEBI's loss statistics are made of.

**Phase 1 (this README): personal use, one account, one broker.**
**Phase 2 (roadmap at the bottom): productize for other traders/brokers, once Phase 1 has a live track record.**

---

## Why this exists

SEBI's FY25 study found individual F&O traders' net losses widened 41% YoY to about ₹1.06 lakh crore, with 91% of traders ending the year in the red and an average loss of ~₹1.1 lakh per trader. The pattern behind most of that isn't bad direction calls — it's oversized positions, no stop discipline, and leverage abuse around expiry. This project attacks that specific failure mode, on your own account first.

**What this is:** a sizing + guardrail layer you run against your own capital.
**What this isn't:** a strategy that predicts direction, a signal seller, or investment advice. It doesn't decide *what* to trade — it decides *how much*, and when to stop you.

---

## Architecture (Phase 1)

```
┌──────────────┐   poll positions/margins    ┌───────────────────┐
│  Broker API   │ ─────────────────────────▶ │   Risk Worker      │
│ (Angel One    │                             │  (Celery beat,     │
│  SmartAPI)    │ ◀───────────────────────── │  every 10–15s      │
└──────────────┘   square-off orders          │  during mkt hours) │
                                               └─────────┬─────────┘
                                                         │ writes
                                                         ▼
                                               ┌───────────────────┐
                                               │    PostgreSQL      │
                                               │ trades / risk_     │
                                               │ events / config    │
                                               └─────────┬─────────┘
                                                         │ publish
                                                         ▼
                                               ┌───────────────────┐
                                               │       Redis        │
                                               │  pub/sub + live    │
                                               │  state cache        │
                                               └─────────┬─────────┘
                                                         │ subscribe
                                                         ▼
                                               ┌───────────────────┐
                                               │  FastAPI backend    │
                                               └─────────┬─────────┘
                                                         │ REST + WS/SSE
                                                         ▼
                                               ┌───────────────────┐
                                               │  Next.js dashboard  │
                                               │  risk meter,        │
                                               │  kill switch         │
                                               └───────────────────┘
```

## Tech stack

Same stack as QuantBacktester, so there's no new tooling to learn:

- **Backend:** Python, FastAPI, Celery + Redis (broker) for periodic risk checks
- **DB:** PostgreSQL (trade history, risk events, config) via SQLAlchemy + Alembic
- **Cache/pub-sub:** Redis (live position state → dashboard)
- **Frontend:** Next.js 14, WebSocket/SSE client for live updates
- **Broker:** Angel One SmartAPI (free — REST for orders/positions/funds, WebSocket for live quotes)
- **Deploy:** Docker Compose locally → Render (backend/worker) + Vercel (frontend), matching your current deployment pattern

---

## Core risk logic

Two independent sizing methods — use whichever fits the trade, or run both and take the smaller size.

### 1. Fractional Kelly sizing

```python
def fractional_kelly_size(win_rate: float, avg_win: float, avg_loss: float,
                           capital: float, kelly_multiplier: float = 0.3) -> float:
    """
    b = payoff ratio (avg win / avg loss)
    Full Kelly f* = (b*p - q) / b
    kelly_multiplier < 1 because your win_rate/avg_win/avg_loss estimates
    are noisy — never run full Kelly on estimated (not measured) edge.
    """
    b = avg_win / avg_loss
    p = win_rate
    q = 1 - p
    full_kelly = max((b * p - q) / b, 0)
    return capital * full_kelly * kelly_multiplier
```

### 2. Volatility-adjusted sizing (better for options, where "edge" is hard to estimate)

```python
def volatility_adjusted_size(capital: float, risk_per_trade_pct: float,
                              atr: float, stop_distance_multiple: float = 1.5) -> float:
    """
    Sizes so a stop-out at (stop_distance_multiple * ATR) loses exactly
    risk_per_trade_pct of capital. Convert result to lots using instrument lot size.
    """
    risk_amount = capital * (risk_per_trade_pct / 100)
    stop_distance = atr * stop_distance_multiple
    return risk_amount / stop_distance
```

### 3. Circuit breakers (checked every poll cycle)

```python
def check_circuit_breakers(account_state, config) -> list[str]:
    """Returns triggered breaker names. Caller decides: alert, block new orders, or auto square-off."""
    triggered = []

    daily_loss_pct = (account_state.day_pnl / account_state.capital_base) * 100
    if daily_loss_pct <= -config.max_daily_loss_pct:
        triggered.append("DAILY_LOSS_LIMIT")

    if account_state.margin_utilisation_pct >= config.max_margin_utilisation_pct:
        triggered.append("MARGIN_CAP")

    for pos in account_state.positions:
        concentration_pct = (pos.exposure / account_state.capital_base) * 100
        if concentration_pct >= config.max_position_concentration_pct:
            triggered.append(f"CONCENTRATION_{pos.symbol}")

    if account_state.orders_in_last_10min >= config.order_velocity_limit_per_10min:
        triggered.append("ORDER_VELOCITY_REVENGE_TRADING")

    if account_state.is_expiry_day and account_state.new_position_size > (
        account_state.baseline_position_size * config.expiry_day_size_dampener
    ):
        triggered.append("EXPIRY_DAY_OVERSIZE")

    return triggered
```

The `EXPIRY_DAY_OVERSIZE` and `ORDER_VELOCITY_REVENGE_TRADING` breakers exist specifically because SEBI's data shows losses cluster on expiry days and after a losing trade — those are the two patterns worth designing for explicitly, not just a generic stop-loss.

---

## Data model

| Table | Purpose |
|---|---|
| `trades` | id, symbol, side, qty, entry_price, exit_price, pnl, opened_at, closed_at, instrument_type |
| `positions_snapshot` | id, ts, symbol, qty, ltp, exposure, unrealized_pnl, margin_used |
| `risk_events` | id, ts, breaker_type, details_json, action_taken (alert/blocked/squared_off) |
| `risk_config` | key, value, updated_at — one row per tunable (kelly_multiplier, max_daily_loss_pct, etc.) |
| `daily_summary` | date, capital_base, realized_pnl, unrealized_pnl, max_intraday_drawdown, breaker_triggers_count |

---

## Broker integration — Angel One SmartAPI

- Auth: client code + password + TOTP (from your authenticator app's secret) → session token
- REST endpoints you'll need: place/modify/cancel order, positions, funds/margins, order book, LTP/quote
- WebSocket: live quotes for symbols in your open positions
- **Verify exact request/response schemas against the current official SmartAPI docs before coding** — broker APIs change their payloads more often than their pricing pages get updated

Design the `broker/base.py` interface generically (`get_positions()`, `get_margins()`, `place_order()`, `square_off_all()`, `get_quote()`) so `angelone.py` is one implementation of it — that's what lets you swap in Dhan or Upstox later without touching the risk engine at all.

---

## Folder structure

```
kavach/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/            # positions.py, risk.py, killswitch.py
│   │   ├── core/            # config.py, security.py
│   │   ├── broker/          # base.py (interface), angelone.py
│   │   ├── risk/            # sizing.py, circuit_breakers.py, rules_config.py
│   │   ├── models/          # SQLAlchemy models
│   │   ├── workers/         # risk_monitor.py (Celery periodic task)
│   │   └── db/session.py
│   ├── alembic/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/dashboard/page.tsx
│   ├── app/settings/page.tsx
│   ├── components/RiskMeter.tsx, PositionTable.tsx, KillSwitchButton.tsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Environment variables (`.env.example`)

```
# Broker (Angel One SmartAPI)
ANGELONE_CLIENT_CODE=
ANGELONE_PASSWORD=
ANGELONE_TOTP_SECRET=
ANGELONE_API_KEY=

# Database
DATABASE_URL=postgresql://kavach:kavach@db:5432/kavach

# Redis
REDIS_URL=redis://redis:6379/0

# Risk config defaults — tune these to your own account
MAX_DAILY_LOSS_PCT=2.0
MAX_POSITION_CONCENTRATION_PCT=20.0
MAX_MARGIN_UTILISATION_PCT=70.0
KELLY_FRACTION_MULTIPLIER=0.3
ORDER_VELOCITY_LIMIT_PER_10MIN=5
EXPIRY_DAY_SIZE_DAMPENER=0.5

ENV=development
SECRET_KEY=
```

---

## Local setup

```bash
git clone <your-repo-url> kavach && cd kavach
cp .env.example .env        # fill in Angel One credentials + secret key
docker compose up --build   # starts postgres, redis, backend, frontend
docker compose exec backend alembic upgrade head
```

Backend: `http://localhost:8000` · Frontend: `http://localhost:3000`

---

## Build roadmap (2–3 weeks)

**Week 1 — plumbing**
- Repo + Docker Compose skeleton (Postgres, Redis, backend, frontend)
- Angel One auth flow, REST calls for positions/funds/margins
- Read-only dashboard: live position table

**Week 2 — the actual risk engine**
- Sizing module (Kelly + vol-adjusted) and circuit breaker checks
- Celery worker polling every 10–15s during market hours (9:15–15:30 IST), writing to Postgres, publishing to Redis
- Risk meter UI (green/yellow/red against your configured limits)
- Kill-switch endpoint wired to `square_off_all()`

**Week 3 — make it trustworthy before it touches real orders**
- Alerting (Telegram bot or email webhook on breaker trigger)
- **Paper mode**: run the full pipeline against live data without sending real orders, for at least a week
- Backtest the sizing/breaker rules against your own historical trade log — this produces a concrete "here's how much drawdown this would have prevented" number, which is worth more in an interview than the code itself
- Only then flip the kill-switch live, starting with small capital

---

## Testing strategy

1. Unit tests on `sizing.py` and `circuit_breakers.py` with known inputs/outputs (these are pure functions — test them hard, they're the whole point of the project)
2. Paper-trading mode: full pipeline live, orders logged not sent
3. Shadow mode: orders sent to broker's *sandbox*/small lot size before real capital
4. Only then: your own capital, starting small, sizes ramping as the track record builds

---

## Metrics worth tracking (for you *and* your interview story)

- Max intraday drawdown before vs. after running the engine
- Number of breaker triggers, and an estimated ₹ figure for what each one likely prevented
- Variance in risk-per-trade across trades (should shrink — that's the point)
- Worker uptime during market hours (matters if you ever productize this)

---

## Compliance note (read before going live, not after)

Phase 1 as scoped here — automating orders on **your own account, your own capital** — is a different regulatory posture from an "algo provider" under SEBI's April 2026 retail algo framework, which is aimed at anyone routing *other clients'* orders and requires broker empanelment + an exchange-issued Algo-ID. That said: some brokers apply order-velocity (OPS) thresholds even to single-user API setups, and the exact line has been moving. Check your specific broker's current API terms before going live, and don't assume this note is a legal clearance — it isn't one. Empanelment becomes non-negotiable the moment you move to Phase 2 and other people's capital is involved.

---

## Disclaimer

This is software that can place real orders with real money. It is not investment advice, it does not predict market direction, and past performance of any sizing rule doesn't guarantee future results. Test exhaustively in paper mode before connecting it to live capital, and never run it with money you can't afford to lose to a bug.

---

## Phase 2 (productize — later)

- Multi-broker adapters (Dhan, Upstox, Fyers) behind the same `base.py` interface
- Multi-tenant auth, per-user config, broker empanelment as a registered algo vendor
- Compliance dashboard for the broker partner (audit trail, Algo-ID mapping)
- Pricing: per-seat SaaS or a cut of prevented-loss (harder to price, better story)
