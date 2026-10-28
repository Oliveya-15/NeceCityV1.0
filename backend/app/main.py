"""Starting point of the backend: creates the app and connects all the routes."""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401  (makes sure all tables are known before create_all)
from app.config import get_settings
from app.database import Base, engine
from app.log import configure_logging, get_logger
from app.routes import analyze, cities, detections, map as map_routes, ml_status, priorities, problems

settings = get_settings()
configure_logging(settings.ENVIRONMENT)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # runs once when the server starts
    Base.metadata.create_all(engine)      # creates the tables if they do not exist yet
    from app.ml.detector import get_detector
    detector = get_detector()             # loads the model now, not on the first request
    logger.info("Model ready: %s", detector.is_ready)
    yield


app = FastAPI(title="NeceCity API", version="1.0.0", lifespan=lifespan)

# lets the React site (a different address) call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    logger.info("%s %s -> %s (%.0f ms)", request.method, request.url.path, response.status_code, (time.time() - start) * 1000)
    return response


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.exception("Unexpected error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})


PREFIX = "/api/v1"
for module in (cities, problems, analyze, detections, map_routes, priorities, ml_status):
    app.include_router(module.router, prefix=PREFIX)

# photos uploaded by users are served from here
app.mount("/uploads", StaticFiles(directory=str(settings.upload_folder)), name="uploads")


@app.get(f"{PREFIX}/health")
def health():
    return {"status": "ok", "app": "NeceCity", "environment": settings.ENVIRONMENT}
