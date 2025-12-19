from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db.init_master import init_master_db
from app.routers import auth, companies

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_master_db()
    yield

app = FastAPI(
    title="Winpol SaaS Backend",
    version="1.0.0",
    lifespan=lifespan
)

# app.include_router(auth.router, prefix="/auth", tags=["Auth"])
# app.include_router(companies.router, prefix="/companies", tags=["Companies"])
