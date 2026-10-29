from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.adapters.driving.api.routes import router as game_router
from app.adapters.driving.websocket.ws_routes import ws_router
from app.adapters.driven.persistence.db_config import create_db_and_tables
from app.adapters.driven.persistence.sql_repository import SQLGameRepository
from app.core.use_cases.data_loader import DataLoader
from app.core.i18n import set_current_lang

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    repo = SQLGameRepository()
    loader = DataLoader(repo)
    loader.load_static_locations()
    loader.load_commands()
    loader.seed_items()
    loader.seed_recipes()
    loader.seed_skills()
    yield

app = FastAPI(
    title="Hexagonal Text RPG",
    description="A text-based RPG backend using Hexagonal Architecture",
    version="0.1.0",
    lifespan=lifespan
)

@app.middleware("http")
async def language_middleware(request: Request, call_next):
    lang_header = request.headers.get("X-Game-Lang") or request.headers.get("Accept-Language") or "en"
    set_current_lang(lang_header)
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For dev, ideally specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game_router, prefix="/api/v1")
app.include_router(ws_router)

@app.get("/")
def health_check():
    return {"status": "ok", "system": "Hexagonal Core operational"}
