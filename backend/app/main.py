import json
import logging
import asyncio
import redis.asyncio as async_redis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api import positions, risk, killswitch, dashboard

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("kavach.main")

# Background task runner loop
async def risk_monitor_loop():
    logger.info("Starting background risk monitoring thread loop...")
    from app.workers.risk_monitor import risk_monitor_tick
    while True:
        try:
            # Execute the tick task in a separate thread to avoid blocking the event loop
            await asyncio.to_thread(risk_monitor_tick)
        except Exception as e:
            logger.error(f"Error in background risk monitor loop: {e}")
        await asyncio.sleep(10)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: spawn background risk loop
    app.state.risk_task = asyncio.create_task(risk_monitor_loop())
    yield
    # Shutdown: cancel task
    logger.info("Stopping background risk monitoring task...")
    app.state.risk_task.cancel()

app = FastAPI(
    title="Kavach — Retail F&O Risk & Position-Sizing Engine",
    description="Real-time position-sizing & risk guardrails engine.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, restrict this to dashboard domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API endpoints
app.include_router(positions.router)
app.include_router(risk.router)
app.include_router(killswitch.router)
app.include_router(dashboard.router)

@app.get("/health")
def health_check():
    """Health check endpoint for Docker / orchestration monitoring."""
    return {
        "status": "healthy",
        "env": settings.ENV,
        "paper_mode": settings.PAPER_MODE,
        "api_key_configured": settings.ANGELONE_API_KEY != ""
    }

@app.websocket("/ws/risk")
async def websocket_risk_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint that subscribes to in-memory pubsub_manager
    and streams live risk state updates to the dashboard.
    """
    from app.core.pubsub import pubsub_manager
    await pubsub_manager.connect(websocket)
    
    # Send connection ack
    await websocket.send_json({"type": "ACK", "message": "Connected to Kavach Live Risk Stream"})
    
    try:
        while True:
            # Keep connection open and check heartbeats
            # If client disconnects, receive_text will raise WebSocketDisconnect
            await websocket.receive_text()
    except WebSocketDisconnect:
        pubsub_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error in WebSocket handler: {e}")
        pubsub_manager.disconnect(websocket)
