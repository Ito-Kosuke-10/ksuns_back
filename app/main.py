from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, simulations_simple, dashboard, axes, qa, detail_questions, deep_questions, plans
from app.core.config import get_settings
from app.core.logging_config import setup_logging

setup_logging()
settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


# Routers
app.include_router(auth.router)
app.include_router(simulations_simple.router)
app.include_router(dashboard.router)
app.include_router(axes.router)
app.include_router(qa.router)
app.include_router(detail_questions.router)
app.include_router(deep_questions.router)
app.include_router(plans.router) # からちゃん追加部分