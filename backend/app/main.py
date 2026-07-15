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

# Async Redis client for WebSocket subscriptions
redis_async_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize async redis connection
    global redis_async_client
    logger.info("Initializing Async Redis client for WebSocket support...")
    redis_async_client = async_redis.from_url(settings.REDIS_URL, decode_responses=True)
    yield
    # Shutdown: close connections
    logger.info("Closing Async Redis client...")
    await redis_async_client.close()

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
    WebSocket endpoint that subscribes to Redis pub/sub 'kavach:risk_state'
    and streams live risk state updates to the dashboard.
    """
    await websocket.accept()
    logger.info("WebSocket client connected.")
    
    pubsub = redis_async_client.pubsub()
    await pubsub.subscribe("kavach:risk_state")
    
    # Send initial state or a connection ack
    await websocket.send_json({"type": "ACK", "message": "Connected to Kavach Live Risk Stream"})
    
    try:
        while True:
            # We listen to pub/sub messages asynchronously
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                data = json.loads(message.get("data", "{}"))
                await websocket.send_json(data)
            
            # Simple heartbeat/check to ensure client hasn't closed connection
            # We can receive text or bytes, but we just check if it throws an error
            try:
                # Receive with a tiny timeout to avoid blocking
                await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"Error in WebSocket handler: {e}")
    finally:
        await pubsub.unsubscribe("kavach:risk_state")
        await pubsub.close()
