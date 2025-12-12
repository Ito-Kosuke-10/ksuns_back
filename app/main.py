from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, simulations_simple, dashboard, axes, qa, detail_questions, deep_questions, plans, concept, revenue_forecast
from app.core.config import get_settings
from app.core.logging_config import setup_logging

# ...他の import 文の並びに追加
from app.api import free_chat  # ★これを追加

setup_logging()
settings = get_settings()

app = FastAPI(title=settings.app_name)

# CORS設定: 環境変数が設定されていない場合は localhost:3000 を許可
# 空のリストの場合はデフォルト値を使用
if not settings.cors_origins or len(settings.cors_origins) == 0:
    cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
else:
    cors_origins = settings.cors_origins
    # localhost:3000 が含まれていない場合は追加
    if "http://localhost:3000" not in cors_origins:
        cors_origins.append("http://localhost:3000")
    if "http://127.0.0.1:3000" not in cors_origins:
        cors_origins.append("http://127.0.0.1:3000")

print(f"🔧 CORS設定: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
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
app.include_router(free_chat.router, prefix="/api", tags=["chat"]) # ★はまさん追加部分
app.include_router(concept.router) # コンセプト軸の質問カードAPI
app.include_router(revenue_forecast.router) # 収支予測軸の質問カードAPI